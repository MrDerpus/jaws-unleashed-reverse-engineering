/*
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Jaws Unleashed reverse engineering tools
 * Copyright (C) 2026 MrDerpus and contributors
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include "hwtrace.h"
#include <tlhelp32.h>
#include <stdio.h>
#include <string.h>

static const DWORD TEXT_LO = 0x401000, TEXT_HI = 0x7CE000;   /* Jaws.exe .text */
static const int   MAX_HITS = 256, MAX_RETS = 4;

struct Hit {
    int   dr;
    DWORD eip;
    DWORD ret[MAX_RETS];
    DWORD count;
    DWORD sample;              /* value at the watched address after the write */
};

static Hit           g_hits[MAX_HITS];
static volatile LONG g_nhits    = 0;
static volatile LONG g_dropped  = 0;
static volatile LONG g_lock     = 0;
static volatile LONG g_active   = 0;
static DWORD         g_addr[4];
static char          g_label[4][32];
static int           g_n        = 0;
static PVOID         g_veh      = nullptr;
static volatile LONG g_grace    = 0;   /* stays set after a stop: late events are still ours */

/* Looks like a return address: inside .text and preceded by a call. */
static bool IsRetAddr(DWORD v)
{
    if (v < TEXT_LO + 6 || v >= TEXT_HI) return false;
    const BYTE* p = (const BYTE*)v;
    if (p[-5] == 0xE8) return true;                                     /* call rel32 */
    if (p[-6] == 0xFF && (p[-5] & 0x38) == 0x10) return true;           /* call [disp32] / [r+disp32] */
    if (p[-3] == 0xFF && (p[-2] & 0x38) == 0x10 && (p[-2] & 0xC0) == 0x40) return true; /* call [r+disp8] */
    if (p[-2] == 0xFF && (p[-1] & 0xF8) == 0xD0) return true;           /* call r32 */
    if (p[-2] == 0xFF && (p[-1] & 0xF8) == 0x10) return true;           /* call [r32] */
    return false;
}

/* First few raw events go straight to the log with Win32 calls (no CRT in
 * an exception handler), so a failed run still shows what Wine delivered. */
static volatile LONG g_rawlogged = 0;
static void RawLog(const char* s)
{
    HANDLE f = CreateFileA("C:\\jaws_mod.log", FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE,
                           nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE) return;
    DWORD w;
    WriteFile(f, s, lstrlenA(s), &w, nullptr);
    CloseHandle(f);
}

static LONG CALLBACK TraceHandler(PEXCEPTION_POINTERS ep)
{
    if (ep->ExceptionRecord->ExceptionCode != EXCEPTION_SINGLE_STEP) return EXCEPTION_CONTINUE_SEARCH;
    CONTEXT* c = ep->ContextRecord;
    DWORD dr6 = c->Dr6;
    if (InterlockedIncrement(&g_rawlogged) <= 5) {
        char b[160];
        wsprintfA(b, "[jaws_mod] HW trace raw: eip %08lX dr6 %08lX dr7 %08lX efl %08lX flags %08lX\r\n",
                  c->Eip, dr6, c->Dr7, c->EFlags, c->ContextFlags);
        RawLog(b);
    }
    /* Under Wine Dr6 may come back empty; while a trace runs (or shortly
     * after, for late events) any single step that isn't a trap-flag step
     * is ours. */
    bool ours = (dr6 & 0xF) || ((g_active || g_grace) && !(c->EFlags & 0x100));
    if (!ours) return EXCEPTION_CONTINUE_SEARCH;
    c->Dr6 = 0;
    if (!g_active) return EXCEPTION_CONTINUE_EXECUTION;

    int dr = 0;
    while (dr < 4 && !(dr6 & (1u << dr))) ++dr;
    if (dr == 4) dr = -1;

    Hit h = {};
    h.dr  = dr;
    h.eip = c->Eip;
    int nr = 0;
    const DWORD* sp  = (const DWORD*)c->Esp;
    const DWORD* top = (const DWORD*)((NT_TIB*)NtCurrentTeb())->StackBase;
    for (int i = 0; i < 0x200 && nr < MAX_RETS && sp + i < top; ++i)
        if (IsRetAddr(sp[i])) h.ret[nr++] = sp[i];
    if (dr >= 0 && dr < g_n) h.sample = *(const DWORD*)g_addr[dr];

    while (InterlockedCompareExchange(&g_lock, 1, 0) != 0) {}
    int i = 0;
    for (; i < g_nhits; ++i)
        if (g_hits[i].dr == h.dr && g_hits[i].eip == h.eip && !memcmp(g_hits[i].ret, h.ret, sizeof(h.ret))) break;
    if (i < g_nhits) { ++g_hits[i].count; g_hits[i].sample = h.sample; }
    else if (g_nhits < MAX_HITS) { h.count = 1; g_hits[g_nhits] = h; ++g_nhits; }
    else ++g_dropped;
    InterlockedExchange(&g_lock, 0);
    return EXCEPTION_CONTINUE_EXECUTION;
}

/* Debug registers are per thread and a thread can't safely set its own, so a
 * helper thread suspends every other thread of the process and sets them. */
struct SetArgs { DWORD dr[4]; DWORD dr7; DWORD tid; int ok; int failed; };

static DWORD WINAPI SetAllThreads(LPVOID arg)
{
    SetArgs* a = (SetArgs*)arg;
    DWORD pid = GetCurrentProcessId(), self = GetCurrentThreadId();
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (snap == INVALID_HANDLE_VALUE) return 0;
    THREADENTRY32 te; te.dwSize = sizeof(te);
    for (BOOL more = Thread32First(snap, &te); more; more = Thread32Next(snap, &te)) {
        if (te.th32OwnerProcessID != pid || te.th32ThreadID == self) continue;
        if (a->tid && te.th32ThreadID != a->tid) continue;
        HANDLE t = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_SET_CONTEXT, FALSE, te.th32ThreadID);
        if (!t) { ++a->failed; continue; }
        if (SuspendThread(t) != (DWORD)-1) {
            CONTEXT c = {};
            c.ContextFlags = CONTEXT_DEBUG_REGISTERS;
            if (GetThreadContext(t, &c)) {
                c.Dr0 = a->dr[0]; c.Dr1 = a->dr[1]; c.Dr2 = a->dr[2]; c.Dr3 = a->dr[3];
                c.Dr6 = 0; c.Dr7 = a->dr7;
                if (SetThreadContext(t, &c)) ++a->ok; else ++a->failed;
            } else ++a->failed;
            ResumeThread(t);
        } else ++a->failed;
        CloseHandle(t);
    }
    CloseHandle(snap);
    return 0;
}

static bool ApplyAll(SetArgs& a)
{
    HANDLE h = CreateThread(nullptr, 0, SetAllThreads, &a, 0, nullptr);
    if (!h) return false;
    WaitForSingleObject(h, 5000);
    CloseHandle(h);
    return a.ok > 0;
}

bool HwTraceActive() { return g_active != 0; }

bool HwTraceStart(const DWORD* addrs, const char* const* labels, int n, char* err, size_t err_sz)
{
    if (g_active) { snprintf(err, err_sz, "trace already running"); return false; }
    if (n < 1 || n > 4) { snprintf(err, err_sz, "bad watch count"); return false; }
    g_n = n;
    g_nhits = 0; g_dropped = 0;
    SetArgs a = {};
    a.tid = GetCurrentThreadId();       /* the game's main thread (render + shark update) */
    g_rawlogged = 0;
    for (int i = 0; i < n; ++i) {
        g_addr[i] = addrs[i] & ~3u;
        snprintf(g_label[i], sizeof(g_label[i]), "%s", labels[i]);
        a.dr[i] = g_addr[i];
        a.dr7 |= (1u << (2 * i)) | (0x1u << (16 + 4 * i)) | (0x3u << (18 + 4 * i));   /* local enable, write, 4 bytes */
    }
    if (!g_veh) g_veh = AddVectoredExceptionHandler(1, TraceHandler);
    if (!g_veh) { snprintf(err, err_sz, "no exception handler"); return false; }
    g_active = 1;
    g_grace  = 1;
    if (!ApplyAll(a)) {
        g_active = 0;
        snprintf(err, err_sz, "could not set debug registers (%d failed)", a.failed);
        return false;
    }
    snprintf(err, err_sz, "trace on (thread %lu)", (unsigned long)a.tid);
    return true;
}

void HwTraceStop(void (*log)(const char*))
{
    if (!g_active) return;
    SetArgs a = {};
    a.tid = GetCurrentThreadId();
    ApplyAll(a);              /* all zero: breakpoints off */
    g_active = 0;

    char buf[256];
    snprintf(buf, sizeof(buf), "[jaws_mod] HW trace: %ld distinct writers, %ld dropped", (long)g_nhits, (long)g_dropped);
    log(buf);
    for (int i = 0; i < g_n; ++i) {
        snprintf(buf, sizeof(buf), "[jaws_mod]   DR%d = %08lX %s", i, (unsigned long)g_addr[i], g_label[i]);
        log(buf);
    }
    for (int i = 0; i < g_nhits; ++i) {
        const Hit& h = g_hits[i];
        float f; memcpy(&f, &h.sample, 4);
        snprintf(buf, sizeof(buf),
                 "[jaws_mod]   DR%d after %08lX x%lu  ret %08lX %08lX %08lX %08lX  last %.3f",
                 h.dr, (unsigned long)h.eip, (unsigned long)h.count,
                 (unsigned long)h.ret[0], (unsigned long)h.ret[1], (unsigned long)h.ret[2], (unsigned long)h.ret[3], f);
        log(buf);
    }
}

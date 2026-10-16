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

#include "debuglog.h"
#include "device_proxy.h"   /* log_msg */

#include <windows.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static const DWORD DBGPRINT_ADDR = 0x4549D0;  /* `ret` + 15 bytes of int3/nop padding */
static const char* DEBUG_FILE    = "C:\\jaws_debug.log";

static CRITICAL_SECTION g_lock;
static FILE*  g_file = nullptr;
static char   g_last[1024];
static int    g_repeat = 0;
static DWORD  g_t0 = 0;

/* The prints were never run in this build, so a format/argument mismatch is
 * possible. Walk the format once and check every %s pointer before letting
 * vsnprintf read it. */
static bool ArgsLookSafe(const char* fmt, va_list ap)
{
    va_list a;
    va_copy(a, ap);
    bool ok = true;
    for (const char* p = fmt; *p && ok; ++p) {
        if (*p != '%') continue;
        ++p;
        if (*p == '%') continue;
        while (*p && strchr("-+ #0", *p)) ++p;
        if (*p == '*') { (void)va_arg(a, int); ++p; } else while (*p >= '0' && *p <= '9') ++p;
        if (*p == '.') { ++p; if (*p == '*') { (void)va_arg(a, int); ++p; } else while (*p >= '0' && *p <= '9') ++p; }
        int longs = 0;
        while (*p && strchr("hlLqjzt", *p)) { if (*p == 'l' || *p == 'q' || *p == 'L') ++longs; ++p; }
        switch (*p) {
        case 'd': case 'i': case 'u': case 'x': case 'X': case 'o': case 'c':
            if (longs >= 2) (void)va_arg(a, long long); else (void)va_arg(a, int);
            break;
        case 'f': case 'F': case 'e': case 'E': case 'g': case 'G': case 'a': case 'A':
            (void)va_arg(a, double);
            break;
        case 'p': (void)va_arg(a, void*); break;
        case 's': {
            const char* s = va_arg(a, const char*);
            if (!s || IsBadStringPtrA(s, 512)) ok = false;
            break;
        }
        case 'n': ok = false; break;   /* never let it write */
        case 0: --p; break;
        default: break;
        }
    }
    va_end(a);
    return ok;
}

static void WriteLine(const char* line, DWORD t)
{
    fprintf(g_file, "%8.3f  %s\n", (t - g_t0) / 1000.0, line);
}

static void FlushRepeat(DWORD t)
{
    if (g_repeat > 0) {
        char buf[64];
        snprintf(buf, sizeof(buf), "  (previous line repeated %d more times)", g_repeat);
        WriteLine(buf, t);
        g_repeat = 0;
    }
}

extern "C" void __cdecl DebugPrintHook(const char* fmt, ...)
{
    if (!fmt || IsBadStringPtrA(fmt, 512)) return;
    char text[1024];
    va_list ap;
    va_start(ap, fmt);
    if (ArgsLookSafe(fmt, ap)) vsnprintf(text, sizeof(text), fmt, ap);
    else snprintf(text, sizeof(text), "[unformatted] %s", fmt);
    va_end(ap);

    /* One log line per printed line; leading/trailing newlines dropped. */
    char* s = text;
    while (*s == '\n' || *s == '\r') ++s;
    size_t n = strlen(s);
    while (n && (s[n - 1] == '\n' || s[n - 1] == '\r')) s[--n] = 0;
    if (!n) return;

    EnterCriticalSection(&g_lock);
    if (g_file) {
        DWORD t = GetTickCount();
        if (strcmp(s, g_last) == 0) {
            ++g_repeat;
        } else {
            FlushRepeat(t);
            WriteLine(s, t);
            snprintf(g_last, sizeof(g_last), "%s", s);
        }
        fflush(g_file);
    }
    LeaveCriticalSection(&g_lock);
}

bool InstallDebugPrint()
{
    static int state = 0;              /* 0 = not tried, 1 = ok, -1 = failed */
    if (state) return state > 0;
    state = -1;

    BYTE* p = (BYTE*)DBGPRINT_ADDR;
    BYTE cur[5];
    if (!ReadProcessMemory(GetCurrentProcess(), p, cur, 5, nullptr) || cur[0] != 0xC3) {
        log_msg("[jaws_mod] debug print: unexpected bytes at 0x4549D0, not hooked");
        return false;
    }
    for (int i = 1; i < 5; ++i)
        if (cur[i] != 0x90 && cur[i] != 0xCC) {
            log_msg("[jaws_mod] debug print: no padding after 0x4549D0, not hooked");
            return false;
        }

    InitializeCriticalSection(&g_lock);
    g_file = fopen(DEBUG_FILE, "w");   /* fresh log each game start */
    if (!g_file) { log_msg("[jaws_mod] debug print: cannot open C:\\jaws_debug.log"); return false; }
    g_t0 = GetTickCount();
    fprintf(g_file, "# Jaws.exe debug text (mod). Columns: seconds since start, message.\n");
    fflush(g_file);

    BYTE patch[5];
    patch[0] = 0xE9;                   /* jmp rel32 */
    DWORD rel = (DWORD)DebugPrintHook - (DBGPRINT_ADDR + 5);
    memcpy(patch + 1, &rel, 4);

    DWORD old;
    if (!VirtualProtect(p, 5, PAGE_EXECUTE_READWRITE, &old)) return false;
    memcpy(p, patch, 5);
    VirtualProtect(p, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), p, 5);
    log_msg("[jaws_mod] debug print hooked -> C:\\jaws_debug.log");
    state = 1;
    return true;
}

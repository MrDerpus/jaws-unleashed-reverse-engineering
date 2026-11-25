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

#include "gdtrace.h"
#include "modpath.h"
#include "device_proxy.h"   /* log_msg */

#include <windows.h>
#include <stdio.h>
#include <stdint.h>

typedef int (__thiscall *SeekFn)(void* self, int off, int origin);
typedef int (__thiscall *TellFn)(void* self);
typedef int (__thiscall *ReadFn)(void* self, void* buf, int n);

static const DWORD VTABLES[3] = {0x7F5C0C, 0x7F5CF4, 0x7F5DDC};
static const DWORD EXPECT_READ[3] = {0x6C1210, 0x6C1320, 0x6C1460};   /* slot 7 sanity check */

static SeekFn g_seek[3];
static TellFn g_tell[3];
static ReadFn g_read[3];
static FILE* g_file = nullptr;
static CRITICAL_SECTION g_lock;

static void Rec(uint32_t kind, void* self, void* ret, uint32_t pos, uint32_t a, uint32_t b)
{
    uint32_t r[6] = {kind, (uint32_t)(uintptr_t)self, (uint32_t)(uintptr_t)ret, pos, a, b};
    EnterCriticalSection(&g_lock);
    if (g_file) fwrite(r, sizeof(r), 1, g_file);
    LeaveCriticalSection(&g_lock);
}

template <int C>
static int __thiscall HookSeek(void* self, int off, int origin)
{
    void* ret = __builtin_return_address(0);
    uint32_t pos = (uint32_t)g_tell[C](self);
    Rec(1 | (C << 8), self, ret, pos, (uint32_t)off, (uint32_t)origin);
    return g_seek[C](self, off, origin);
}

template <int C>
static int __thiscall HookTell(void* self)
{
    void* ret = __builtin_return_address(0);
    int pos = g_tell[C](self);
    Rec(2 | (C << 8), self, ret, (uint32_t)pos, 0, 0);
    return pos;
}

template <int C>
static int __thiscall HookRead(void* self, void* buf, int n)
{
    void* ret = __builtin_return_address(0);
    uint32_t pos = (uint32_t)g_tell[C](self);
    int r = g_read[C](self, buf, n);
    Rec(0 | (C << 8), self, ret, pos, (uint32_t)n, (uint32_t)r);
    return r;
}

static void Patch(DWORD addr, void* fn)
{
    DWORD old;
    VirtualProtect((void*)addr, 4, PAGE_READWRITE, &old);
    *(void**)addr = fn;
    VirtualProtect((void*)addr, 4, old, &old);
}

void InstallGdTrace()
{
    static bool tried = false;
    if (tried) return;
    tried = true;
    if (GetFileAttributesA(MOD_PATH("jaws_gdfile_trace.on")) == INVALID_FILE_ATTRIBUTES) return;

    for (int c = 0; c < 3; ++c)
        if (*(DWORD*)(VTABLES[c] + 0x1C) != EXPECT_READ[c]) {
            log_msg("[jaws_mod] gdfile trace: unexpected vtable contents, not installed");
            return;
        }
    InitializeCriticalSection(&g_lock);
    g_file = fopen(MOD_PATH("jaws_gdfile_trace.bin"), "wb");
    if (!g_file) { log_msg("[jaws_mod] gdfile trace: cannot create jaws_gdfile_trace.bin"); return; }
    setvbuf(g_file, nullptr, _IOFBF, 1 << 20);

    void* seeks[3] = {(void*)HookSeek<0>, (void*)HookSeek<1>, (void*)HookSeek<2>};
    void* tells[3] = {(void*)HookTell<0>, (void*)HookTell<1>, (void*)HookTell<2>};
    void* reads[3] = {(void*)HookRead<0>, (void*)HookRead<1>, (void*)HookRead<2>};
    for (int c = 0; c < 3; ++c) {
        DWORD vt = VTABLES[c];
        g_seek[c] = *(SeekFn*)(vt + 0x0C);
        g_tell[c] = *(TellFn*)(vt + 0x10);
        g_read[c] = *(ReadFn*)(vt + 0x1C);
        Patch(vt + 0x0C, seeks[c]);
        Patch(vt + 0x10, tells[c]);
        Patch(vt + 0x1C, reads[c]);
    }
    log_msg("[jaws_mod] gdfile trace ON -> jaws_gdfile_trace.bin (game folder)");
}

void FlushGdTrace()
{
    if (!g_file) return;
    EnterCriticalSection(&g_lock);
    fflush(g_file);
    LeaveCriticalSection(&g_lock);
}

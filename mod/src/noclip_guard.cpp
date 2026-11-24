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

#include "noclip_guard.h"

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <math.h>

extern bool g_noclip;                         /* device_proxy.cpp (F7) */

#define THISCALL __attribute__((thiscall))

static const DWORD ENGINE_GLOBAL = 0x920E24;
static const DWORD SHARK_BRICK   = 0x90BC08;   /* as used by ANTol's tick */
static const DWORD FN_LOOKUP     = 0x6C3010;   /* engine->object by ID (live brick) */

static const DWORD SPHERE_TICK   = 0x43BF60, SPHERE_SLOT = 0x7D12E4;
static const DWORD SPHERE_TEST   = 0x43BDE0;   /* returns 1 = target outside */
static const DWORD TOL_TICK      = 0x43F6A0, TOL_SLOT = 0x7D18D4;
static const DWORD WHIRL_FORCE   = 0x63BD80;
static const DWORD WHIRL_SLOTS[] = {0x7F0AD0, 0x7D952C};

typedef void  (THISCALL *TickFn)(void* self);
typedef char  (THISCALL *TestFn)(void* self);
typedef int   (THISCALL *ForceFn)(void* self, const float* pos, float* out);
typedef DWORD (THISCALL *LookupFn)(DWORD engine, DWORD id, DWORD zero);

static bool rd(DWORD addr, void* out, SIZE_T n)
{
    return addr > 0x10000 && ReadProcessMemory(GetCurrentProcess(), (LPCVOID)addr, out, n, nullptr) != 0;
}

static DWORD shark_brick()
{
    DWORD b = 0;
    return rd(SHARK_BRICK, &b, 4) ? b : 0;
}

/* Brick world position = +0xA8 / +0xAC / +0xB0. */
static bool near_shark(const float* p)
{
    DWORD b = shark_brick();
    float s[3];
    if (!b || !p || !rd(b + 0xA8, s, sizeof(s)))
        return false;
    float dx = p[0] - s[0], dy = p[1] - s[1], dz = p[2] - s[2];
    return dx * dx + dy * dy + dz * dz < 4.0f;        /* within 2 units */
}

static bool sphere_targets_shark(void* self)
{
    DWORD engine = 0, id = 0, shark = shark_brick();
    if (!shark || !rd(ENGINE_GLOBAL, &engine, 4) || !engine || !rd((DWORD)self + 0x11C, &id, 4) || !id)
        return false;
    DWORD target = ((LookupFn)FN_LOOKUP)(engine, id, 0);
    return target && target == shark;
}

static void THISCALL SphereTickHook(void* self)
{
    if (g_noclip && sphere_targets_shark(self)) {
        /* track inside/outside without firing the enter/leave actions */
        *((char*)self + 0x100) = ((TestFn)SPHERE_TEST)(self);
        return;
    }
    ((TickFn)SPHERE_TICK)(self);
}

static void THISCALL TolTickHook(void* self)
{
    if (g_noclip)
        return;                                   /* buoys only push the shark */
    ((TickFn)TOL_TICK)(self);
}

static int THISCALL WhirlForceHook(void* self, const float* pos, float* out)
{
    if (g_noclip && near_shark(pos)) {
        if (out) *out = 0.0f;                     /* what the stock code does out of range */
        return 0;
    }
    return ((ForceFn)WHIRL_FORCE)(self, pos, out);
}

static bool patch_slot(DWORD slot, DWORD expect, void* hook)
{
    DWORD cur = 0, old;
    if (!rd(slot, &cur, 4) || cur != expect)
        return false;
    if (!VirtualProtect((LPVOID)slot, 4, PAGE_READWRITE, &old))
        return false;
    *(DWORD*)slot = (DWORD)hook;
    VirtualProtect((LPVOID)slot, 4, old, &old);
    return true;
}

bool InstallNoclipGuards()
{
    static int state = 0;
    if (state) return state > 0;
    bool ok = patch_slot(SPHERE_SLOT, SPHERE_TICK, (void*)&SphereTickHook);
    ok = patch_slot(TOL_SLOT, TOL_TICK, (void*)&TolTickHook) && ok;
    for (DWORD s : WHIRL_SLOTS)
        ok = patch_slot(s, WHIRL_FORCE, (void*)&WhirlForceHook) && ok;
    state = ok ? 1 : -1;
    return ok;
}

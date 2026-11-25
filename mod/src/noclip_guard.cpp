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
#include <stdio.h>
#include "modpath.h"

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

/* ── Air swim: water-height wrapper (see noclip_guard.h) ─────────────────── */

static const DWORD WATER_HEIGHT_PTR = 0x8B2E9C;
static const float NO_WATER         = -2147483648.0f;   /* 0x7D388C */
static const float AIR_LIFT         = 1000.0f;

/* Return addresses (call site + 6) that get the lifted surface. */
static const DWORD AIR_CALLERS[] = {
    0x67031E + 6, 0x67033C + 6,   /* shark tick: in-air flag 0x40000 */
    /* NOT 0x66DDC5/0x66DDFB: they raise [obj+0x28] to "surface - offset" and
     * the shark is pulled toward it, so a lifted surface flung it up ~1000
     * units per frame (user-tested 2026-11-25). */
};

typedef float (__cdecl *WaterFn)(const float* pos);
static WaterFn g_real_water = nullptr;

/* Debug (2026-11-25): log which callers ask about the shark's position
 * (every 2 s to jaws_mod.log while no-clip is on). Off in normal builds. */
#ifndef AIRSWIM_DEBUG
#define AIRSWIM_DEBUG 0
#endif
struct CallerCount { DWORD ret; int n; float y, h; char tag; };
static CallerCount g_callers[64];
static int g_ncallers = 0;

static void note_caller(DWORD ret, const float* pos, float h, char tag)
{
    if (!AIRSWIM_DEBUG) return;
    DWORD b = shark_brick();
    float s[3];
    if (!b || !rd(b + 0xA8, s, sizeof(s))) return;
    float dx = pos[0] - s[0], dy = pos[1] - s[1], dz = pos[2] - s[2];
    if (dx * dx + dy * dy + dz * dz > 30.0f * 30.0f) return;   /* within 30 units */
    for (int i = 0; i < g_ncallers; ++i)
        if (g_callers[i].ret == ret && g_callers[i].tag == tag) { ++g_callers[i].n; g_callers[i].y = pos[1]; g_callers[i].h = h; return; }
    if (g_ncallers < 64) g_callers[g_ncallers++] = {ret, 1, pos[1], h, tag};
}

/* Lifted surface for the shark's own checks. Also used where the level has
 * no water at that spot (h == NO_WATER: AQUARIUM away from the pools),
 * otherwise the shark counts as airborne there and falls. */
static float lifted_surface(const float* pos, float h)
{
    float lifted = pos[1] + AIR_LIFT;
    return (h == NO_WATER || lifted > h) ? lifted : h;
}

/* Above-water camera (0x676AC0) puts itself at water + cfg[0xDC] and only
 * aims at the shark, so it stayed down by the waves. At this site pos is
 * the camera's planned spot behind the shark: use its own height when that
 * is above the water, so the camera rises with the shark. */
static const DWORD CAM_FOLLOW_CALLER = 0x676C3B + 6;

static float __cdecl water_height_hook(const float* pos)
{
    float h = g_real_water ? g_real_water(pos) : NO_WATER;
    if (!g_noclip || !pos) return h;
    DWORD ret = (DWORD)__builtin_return_address(0);
    note_caller(ret, pos, h, 'F');
    for (DWORD a : AIR_CALLERS)
        if (ret == a) return lifted_surface(pos, h);
    if (ret == CAM_FOLLOW_CALLER && h != NO_WATER && pos[1] > h) return pos[1];
    return h;
}

/* Wave surface height, fn ptr 0x8B2E94 (same signature). This is the one
 * the shark's airborne physics uses (user-tested log 2026-11-25). */
static const DWORD WAVE_HEIGHT_PTR = 0x8B2E94;
static WaterFn g_real_wave = nullptr;

static const DWORD WAVE_AIR_CALLERS[] = {
    0x66D2E4 + 6,                 /* y <= surface: clear on-ground ctrl+0x5A8 */
    0x66D6FB + 6, 0x66D70E + 6,   /* head/tail vs surface: airborne ctrl+0x4A0,
                                     fraction out of water (air/water physics) */
    0x66D762 + 6,                 /* near-surface flag ctrl+0x828 */
    0x66E4A7 + 6,                 /* surface swim animation blend (m_felszineny) */
    0x6703A7 + 6, 0x6703EB + 6,   /* surface wake effect */
};

static float __cdecl wave_height_hook(const float* pos)
{
    float h = g_real_wave ? g_real_wave(pos) : NO_WATER;
    if (!g_noclip || !pos) return h;
    DWORD ret = (DWORD)__builtin_return_address(0);
    note_caller(ret, pos, h, 'W');
    for (DWORD a : WAVE_AIR_CALLERS)
        if (ret == a) return lifted_surface(pos, h);
    return h;
}

static void log_line(const char* s)
{
    FILE* f = fopen(MOD_PATH("jaws_mod.log"), "a");
    if (f) { fprintf(f, "%s\n", s); fclose(f); }
}

static void flush_caller_log()
{
    static DWORD last = 0;
    DWORD now = GetTickCount();
    if (now - last < 2000 || !g_ncallers) return;
    last = now;
    DWORD ctrl = 0, state = 0, brick = shark_brick();
    float sy = 0;
    rd(0x90BC04, &ctrl, 4);
    if (ctrl) rd(ctrl + 0x240, &state, 4);
    if (brick) rd(brick + 0xAC, &sy, 4);
    char buf[160];
    snprintf(buf, sizeof(buf), "[jaws_mod] air swim: shark y %.1f state %lu, water callers near shark:", sy, (unsigned long)state);
    log_line(buf);
    for (int i = 0; i < g_ncallers; ++i) {
        snprintf(buf, sizeof(buf), "[jaws_mod]   %s site 0x%06lX x%d (y %.1f, water %.1f)",
                 g_callers[i].tag == 'W' ? "wave" : "flat",
                 (unsigned long)(g_callers[i].ret - 6), g_callers[i].n, g_callers[i].y, g_callers[i].h);
        log_line(buf);
    }
    g_ncallers = 0;
}

void UpdateNoclipAirSwim()
{
    if (AIRSWIM_DEBUG && g_noclip) flush_caller_log();
    WaterFn* wslot = (WaterFn*)WAVE_HEIGHT_PTR;
    WaterFn wcur = *wslot;
    if (g_noclip) {
        if (wcur && wcur != wave_height_hook) { g_real_wave = wcur; *wslot = wave_height_hook; }
    } else if (wcur == wave_height_hook) {
        *wslot = g_real_wave;
    }

    WaterFn* slot = (WaterFn*)WATER_HEIGHT_PTR;
    WaterFn cur = *slot;
    if (g_noclip) {
        if (cur && cur != water_height_hook) {
            g_real_water = cur;        /* level load wrote a new one */
            *slot = water_height_hook;
        }
    } else if (cur == water_height_hook) {
        *slot = g_real_water;
    }
}

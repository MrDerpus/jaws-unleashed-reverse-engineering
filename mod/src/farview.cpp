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

#include "farview.h"

#include <windows.h>
#include <vector>

static const float FAR_PLANE      = 3000.0f;
static const float FOG_ABOVE[2]   = {1000.0f, 2900.0f};
static const float FOG_BELOW[2]   = {100.0f, 400.0f};

static const DWORD ENGINE_GLOBAL  = 0x920E24;
static const DWORD ENGINE_ID_MAP  = 0x50;
static const DWORD SHARK_CTRL     = 0x90BC04;   /* null outside gameplay */
static const DWORD VT_WATERYCAM   = 0x7F0120;
static const DWORD FN_CURRENT_CAM = 0x5519A0;
static const DWORD FN_LOOKUP      = 0x6C3010;

static const DWORD ENV_FOG_ABOVE_ID = 0x80;
static const DWORD ENV_UNDERWATER   = 0x150;
static const DWORD ENV_BELOW_FLOATS[4] = {0x90, 0x98, 0xB0, 0xB8};
static const DWORD FOG_START = 0x12C, FOG_END = 0x134;
static const DWORD CAM_FAR   = 0x11C;

typedef DWORD (__cdecl *CurrentCamFn)(unsigned mask);
typedef DWORD (__attribute__((thiscall)) *LookupFn)(DWORD engine, DWORD id, DWORD zero);

static bool rd(DWORD addr, void* out, SIZE_T n)
{
    return addr > 0x10000 && ReadProcessMemory(GetCurrentProcess(), (LPCVOID)addr, out, n, nullptr) != 0;
}

static DWORD vtable_of(DWORD obj)
{
    DWORD vt = 0;
    return rd(obj, &vt, 4) ? vt : 0;
}

/* A float the mod changed, with the level's own value to put back. */
struct Saved { DWORD obj, vt, off; float orig; };

static bool  g_enabled = false;
static DWORD g_env = 0;
static DWORD g_last_scan = 0;
static std::vector<Saved> g_saved;

bool FarViewEnabled() { return g_enabled; }

static DWORD engine_ptr()
{
    DWORD e = 0;
    return rd(ENGINE_GLOBAL, &e, 4) ? e : 0;
}

/* Walk the engine's ID registry for the NAWaterYCamera live instance. */
static DWORD find_water_camera(DWORD engine)
{
    DWORD nbuckets = 0, buckets = 0;
    if (!rd(engine + ENGINE_ID_MAP + 4, &nbuckets, 4) || !rd(engine + ENGINE_ID_MAP + 8, &buckets, 4) ||
        !nbuckets || nbuckets > 0x400000)
        return 0;
    std::vector<DWORD> table(nbuckets);
    if (!rd(buckets, table.data(), nbuckets * 4))
        return 0;
    for (DWORD b = 0; b < nbuckets; ++b)
        for (DWORD e = table[b], guard = 0; e && guard < 100000; ++guard) {
            DWORD ent[4];
            if (!rd(e, ent, sizeof(ent)))
                break;
            DWORD obj = ent[2];
            if (vtable_of(obj) == VT_WATERYCAM)
                return obj;
            for (DWORD off : {0x20u, 0x24u}) {   /* live instance of an action */
                DWORD live = 0;
                if (rd(obj + off, &live, 4) && vtable_of(live) == VT_WATERYCAM)
                    return live;
            }
            e = ent[3];
        }
    return 0;
}

/* Write `val` to obj+off, remembering the original the first time. */
static void set_float(DWORD obj, DWORD off, float val)
{
    float cur;
    if (!obj || !rd(obj + off, &cur, 4))
        return;
    bool known = false;
    for (const Saved& s : g_saved)
        if (s.obj == obj && s.off == off) { known = true; break; }
    if (!known)
        g_saved.push_back({obj, vtable_of(obj), off, cur});
    if (cur != val)
        *(float*)(obj + off) = val;
}

static void restore_all()
{
    for (const Saved& s : g_saved)
        if (vtable_of(s.obj) == s.vt)      /* object still alive */
            *(float*)(s.obj + s.off) = s.orig;
    g_saved.clear();
}

bool ToggleFarView()
{
    g_enabled = !g_enabled;
    if (!g_enabled)
        restore_all();
    return g_enabled;
}

void UpdateFarView()
{
    DWORD engine = engine_ptr(), ctrl = 0, world = 0;
    bool in_game = engine && rd(SHARK_CTRL, &ctrl, 4) && ctrl &&
                   rd(engine + 0x10, &world, 4) && world;
    if (!in_game) {
        /* level unloading or menus: the saved objects are going away */
        g_env = 0;
        g_saved.clear();
        return;
    }
    if (!g_enabled)
        return;

    if (g_env && vtable_of(g_env) != VT_WATERYCAM) {
        g_env = 0;
        g_saved.clear();
    }
    if (!g_env) {
        if (GetTickCount() - g_last_scan < 2000)
            return;
        g_last_scan = GetTickCount();
        g_env = find_water_camera(engine);
        if (!g_env)
            return;
    }

    /* Underwater: the game copies these into the fog and the far plane. */
    for (int i = 0; i < 4; ++i)
        set_float(g_env, ENV_BELOW_FLOATS[i], FOG_BELOW[i & 1]);

    DWORD underwater = 1, fog_above_id = 0;
    rd(g_env + ENV_UNDERWATER, &underwater, 4);
    rd(g_env + ENV_FOG_ABOVE_ID, &fog_above_id, 4);
    if (underwater != 0)
        return;

    /* Above water: nothing re-sets these until the next crossing. */
    DWORD cam = ((CurrentCamFn)FN_CURRENT_CAM)(3);
    if (cam)
        set_float(cam, CAM_FAR, FAR_PLANE);
    DWORD fog = fog_above_id ? ((LookupFn)FN_LOOKUP)(engine, fog_above_id, 0) : 0;
    if (fog) {
        set_float(fog, FOG_START, FOG_ABOVE[0]);
        set_float(fog, FOG_END, FOG_ABOVE[1]);
    }
}

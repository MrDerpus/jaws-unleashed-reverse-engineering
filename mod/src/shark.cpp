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

#include "shark.h"
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static const DWORD SHARK_CTRL_GLOBAL = 0x90BC04;
static const DWORD CTRL_BRICK        = 0x50;
static const DWORD BRICK_FLAGS       = 0x0C;
static const DWORD BRICK_PARENT      = 0x14;
static const DWORD BRICK_LOCAL       = 0x50;
static const DWORD BRICK_WORLD       = 0x84;
static const DWORD CTRL_LAST_POS     = 0x680;   /* collision sweep start, see TeleportShark */
static const DWORD FLAG_WORLD_STALE  = 0x20;
static const DWORD CTRL_HEALTH_MAX   = 0x2A8;
static const DWORD CTRL_HEALTH       = 0x2B0;
static const DWORD CTRL_HUNGER_MAX   = 0x2AC;
static const DWORD CTRL_HUNGER       = 0x2B4;

static bool rd(DWORD addr, void* out, SIZE_T n)
{
    return ReadProcessMemory(GetCurrentProcess(), (LPCVOID)addr, out, n, nullptr) != 0;
}

static bool wr(DWORD addr, const void* in, SIZE_T n)
{
    return WriteProcessMemory(GetCurrentProcess(), (LPVOID)addr, in, n, nullptr) != 0;
}

static bool SharkBrick(DWORD& brick)
{
    DWORD ctrl = 0;
    if (!rd(SHARK_CTRL_GLOBAL, &ctrl, 4) || !ctrl) return false;
    if (!rd(ctrl + CTRL_BRICK, &brick, 4) || !brick) return false;
    return true;
}

bool ReadShark(SharkState& out)
{
    DWORD brick;
    float w[12];
    if (!SharkBrick(brick) || !rd(brick + BRICK_WORLD, w, sizeof(w))) return false;

    out.x = w[9]; out.y = w[10]; out.z = w[11];

    /* Z basis row = forward; normalize away the model's scale (~2.1). */
    float fx = w[6], fy = w[7], fz = w[8];
    float len = sqrtf(fx*fx + fy*fy + fz*fz);
    if (len < 1e-6f) { out.yaw_deg = out.pitch_deg = 0; return true; }
    fx /= len; fy /= len; fz /= len;
    float yaw = atan2f(fx, fz) * 57.29578f;
    out.yaw_deg   = yaw < 0 ? yaw + 360.0f : yaw;
    out.pitch_deg = asinf(fmaxf(-1.0f, fminf(1.0f, fy))) * 57.29578f;
    return true;
}

bool TeleportShark(float x, float y, float z, char* err, size_t err_sz)
{
    DWORD brick, parent = 0, flags = 0;
    if (!SharkBrick(brick)) { snprintf(err, err_sz, "no shark"); return false; }
    if (!rd(brick + BRICK_PARENT, &parent, 4) || !rd(brick + BRICK_FLAGS, &flags, 4)) {
        snprintf(err, err_sz, "read failed"); return false;
    }

    /* world_t = local_t.x*R0 + local_t.y*R1 + local_t.z*R2 + parent_t, where
     * R0..R2 are the parent's world basis rows. Solve for local_t (Cramer). */
    float lt[3] = { x, y, z };
    if (parent) {
        float p[12];
        if (!rd(parent + BRICK_WORLD, p, sizeof(p))) { snprintf(err, err_sz, "parent read failed"); return false; }
        float d[3] = { x - p[9], y - p[10], z - p[11] };
        const float *r0 = p, *r1 = p + 3, *r2 = p + 6;
        auto det3 = [](const float* a, const float* b, const float* c) {
            return a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0]);
        };
        float det = det3(r0, r1, r2);
        if (fabsf(det) < 1e-9f) { snprintf(err, err_sz, "parent matrix singular"); return false; }
        lt[0] = det3(d,  r1, r2) / det;
        lt[1] = det3(r0, d,  r2) / det;
        lt[2] = det3(r0, r1, d ) / det;
    }

    float wt[3] = { x, y, z };
    float old[3] = {};
    rd(brick + BRICK_WORLD + 0x24, old, sizeof(old));
    flags |= FLAG_WORLD_STALE;
    if (!wr(brick + BRICK_LOCAL + 0x24, lt, sizeof(lt)) ||
        !wr(brick + BRICK_WORLD + 0x24, wt, sizeof(wt)) ||
        !wr(brick + BRICK_FLAGS, &flags, 4)) {
        snprintf(err, err_sz, "write failed"); return false;
    }

    /* The collision move sweeps each frame from the controller's stored
     * last position (ctrl+0x680, copied from the brick's world translation at
     * 0x666611 and set to the resolved position at 0x670485) to the brick's
     * new position, and stops at the first obstacle. Moving only the brick
     * therefore snaps back (or stops part-way) whenever terrain lies between
     * the old spot and the target. Move the stored copy too. */
    DWORD ctrl = 0;
    if (rd(SHARK_CTRL_GLOBAL, &ctrl, 4) && ctrl)
        wr(ctrl + CTRL_LAST_POS, wt, sizeof(wt));
    /* A second object at [ctrl+0x58] keeps the shark's world position at
     * +0xA8 too (seen by the 2026-10-04 scan); update it only if it really
     * mirrors the shark right now. */
    DWORD other = 0;
    float ow[3];
    if (ctrl && rd(ctrl + 0x58, &other, 4) && other && rd(other + BRICK_WORLD + 0x24, ow, sizeof(ow)) &&
        fabsf(ow[0] - old[0]) < 0.05f && fabsf(ow[1] - old[1]) < 0.05f && fabsf(ow[2] - old[2]) < 0.05f)
        wr(other + BRICK_WORLD + 0x24, wt, sizeof(wt));
    return true;
}

void ScanSharkPositionCopies(const float* want, float tol, char* out, size_t out_sz)
{
    out[0] = 0;
    DWORD ctrl = 0, brick = 0;
    float pos[3];
    if (!rd(SHARK_CTRL_GLOBAL, &ctrl, 4) || !ctrl || !SharkBrick(brick) ||
        !rd(brick + BRICK_WORLD + 0x24, pos, sizeof(pos))) {
        snprintf(out, out_sz, "scan: no shark");
        return;
    }
    if (want) memcpy(pos, want, sizeof(pos));
    size_t used = 0;
    int hits = 0;
    auto scan = [&](const char* label, DWORD base, DWORD len) {
        static unsigned char buf[0x2000];
        if (len > sizeof(buf) || !rd(base, buf, len)) return;
        for (DWORD o = 0; o + 12 <= len; o += 4) {
            float f[3];
            memcpy(f, buf + o, 12);
            if (fabsf(f[0] - pos[0]) < tol && fabsf(f[1] - pos[1]) < tol && fabsf(f[2] - pos[2]) < tol) {
                ++hits;
                if (used + 128 < out_sz)
                    used += snprintf(out + used, out_sz - used, "  %s+0x%lX (%08lX) = (%.2f, %.2f, %.2f)\n",
                                     label, (unsigned long)o, (unsigned long)(base + o), f[0], f[1], f[2]);
            }
        }
    };
    auto heap = [&](DWORD p) { return p >= 0x01000000 && !(p >= 0x400000 && p < 0xE70000); };
    if (used + 96 < out_sz)
        used += snprintf(out + used, out_sz - used, "scan for (%.2f, %.2f, %.2f) tol %.2f: ctrl %08lX brick %08lX\n",
                         pos[0], pos[1], pos[2], tol, (unsigned long)ctrl, (unsigned long)brick);
    scan("ctrl", ctrl, 0x2000);
    scan("brick", brick, 0x400);
    static DWORD words[0x2000 / 4];
    if (rd(ctrl, words, sizeof(words))) {
        for (DWORD i = 0; i < 0x2000 / 4; ++i) {
            DWORD p = words[i];
            if (!heap(p) || p == brick) continue;
            char label[32];
            snprintf(label, sizeof(label), "[ctrl+0x%lX]", (unsigned long)(i * 4));
            scan(label, p, 0x400);
        }
        /* one level deeper for the objects most likely to hold physics state */
        const DWORD deep[] = { 0x50, 0x54, 0x58 };
        for (DWORD off : deep) {
            DWORD obj = words[off / 4], sub[0x400 / 4];
            if (!heap(obj) || !rd(obj, sub, sizeof(sub))) continue;
            for (DWORD k = 0; k < 0x400 / 4; ++k) {
                if (!heap(sub[k]) || sub[k] == brick || sub[k] == ctrl) continue;
                char label[48];
                snprintf(label, sizeof(label), "[[ctrl+0x%lX]+0x%lX]", (unsigned long)off, (unsigned long)(k * 4));
                scan(label, sub[k], 0x400);
            }
        }
    }
    if (used + 64 < out_sz)
        snprintf(out + used, out_sz - used, "  %d hit(s)", hits);
}

static bool RefillPair(DWORD ctrl, DWORD max_off, DWORD cur_off)
{
    float max_v, cur;
    if (!rd(ctrl + max_off, &max_v, 4) || !rd(ctrl + cur_off, &cur, 4)) return false;
    if (!(max_v > 0.0f)) return false;   /* not set up yet (also rejects NaN) */
    if (cur < max_v) return wr(ctrl + cur_off, &max_v, 4);
    return true;
}

bool RefillSharkHealth()
{
    DWORD ctrl = 0;
    if (!rd(SHARK_CTRL_GLOBAL, &ctrl, 4) || !ctrl) return false;
    bool hp  = RefillPair(ctrl, CTRL_HEALTH_MAX, CTRL_HEALTH);
    bool hun = RefillPair(ctrl, CTRL_HUNGER_MAX, CTRL_HUNGER);
    return hp && hun;
}

/* ── Death block ───────────────────────────────────────────────────────── */

static const DWORD SETSTATE_ADDR   = 0x65EDA0;
static const DWORD SHARK_STATE_DEAD = 7;
/* Original first instruction: mov edx, [0x920E24] (6 bytes). */
static const BYTE  SETSTATE_ORIG[6] = { 0x8B, 0x15, 0x24, 0x0E, 0x92, 0x00 };

extern "C" {
volatile int g_block_shark_death = 0;
volatile int g_blocked_deaths    = 0;
DWORD        g_setstate_resume   = SETSTATE_ADDR + 6;
}

/* Entry hook. On entry [esp+4] is the requested state (thiscall: `this` in
 * ecx, args on the stack). If blocking and state == 7, return immediately,
 * popping the 3 args like the real function would; otherwise replay the
 * overwritten instruction and continue into the original. */
asm(
    ".text\n"
    ".globl _SetStateHook\n"
    "_SetStateHook:\n"
    "    cmpl  $0, _g_block_shark_death\n"
    "    je    1f\n"
    "    cmpl  $7, 4(%esp)\n"
    "    jne   1f\n"
    "    lock incl _g_blocked_deaths\n"
    "    ret   $12\n"
    "1:\n"
    "    movl  0x920E24, %edx\n"
    "    jmp   *_g_setstate_resume\n"
);
extern "C" void SetStateHook();

bool InstallDeathBlock()
{
    static int state = 0;              /* 0 = not tried, 1 = ok, -1 = failed */
    if (state) return state > 0;
    state = -1;

    BYTE* p = (BYTE*)SETSTATE_ADDR;
    BYTE cur[6];
    if (!rd(SETSTATE_ADDR, cur, 6) || memcmp(cur, SETSTATE_ORIG, 6) != 0) return false;

    BYTE patch[6];
    patch[0] = 0xE9;                   /* jmp rel32 */
    DWORD rel = (DWORD)SetStateHook - (SETSTATE_ADDR + 5);
    memcpy(patch + 1, &rel, 4);
    patch[5] = 0x90;                   /* nop out the 6th byte */

    DWORD old;
    if (!VirtualProtect(p, 6, PAGE_EXECUTE_READWRITE, &old)) return false;
    memcpy(p, patch, 6);
    VirtualProtect(p, 6, old, &old);
    FlushInstructionCache(GetCurrentProcess(), p, 6);
    state = 1;
    return true;
}

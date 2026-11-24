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

/*
 * Ecco DolphCtrl movement port, see ecco.h. Field names in comments are
 * the DolphCtrl offsets (`this+0x...`) and Ecco addresses they come from,
 * so the code can be checked against dolphctrl_annot.c.
 *
 * Coordinate frames. Both games use row-vector matrices (rows = local X, Y,
 * Z axes, then translation), Y up. The dolphin's nose points along its local
 * -Z, the Jaws shark's along +Z, so the Ecco frame is the Jaws frame turned
 * 180 degrees about Y: E0 = -J0, E1 = J1, E2 = -J2 (E2 = "back"). All Ecco
 * logic runs on E with Ecco's own rotation primitives and Euler angles
 * (pitch + = nose down, as in Ecco), in Ecco length units (Jaws / scale).
 * One tick = one frame; both games step their logic at 30 Hz, and Ecco's
 * dt (0x589684) is 1.0.
 */
#include "ecco.h"
#include "modpath.h"
#include "input_block.h"
#include "sonar.h"
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

/* ── Jaws addresses ────────────────────────────────────────────────────── */
static const DWORD SHARK_CTRL_GLOBAL = 0x90BC04;
static const DWORD TICK_SLOT         = 0x7F28FC + 0x48;   /* MLSharkCtrl vtable, per-frame tick */
static const DWORD TICK_ORIG         = 0x667FB0;
static const DWORD ENGINE_GLOBAL     = 0x920E24;          /* +0x88 -> +8 = pad */
static const DWORD WATER_HEIGHT_PTR  = 0x8B2E9C;          /* float cdecl f(const float* pos) */
static const DWORD INVERT_OPTION     = 0x8D1DC1;          /* byte; 0 = the game flips stick Y (0x65EAE0) */
static const DWORD WORLD_UPDATE      = 0x696EA0;          /* thiscall brick: recompute stale world matrix */
static const float NO_WATER          = -2147483648.0f;    /* 0x7D388C */
static const DWORD BRICK_FLAGS = 0x0C, BRICK_PARENT = 0x14, BRICK_LOCAL = 0x50, BRICK_WORLD = 0x84;
static const DWORD FLAG_WORLD_STALE  = 0x20;

typedef void  (__fastcall *TickFn)(void* self, void* edx);
typedef float (__cdecl    *WaterFn)(const float* pos);
typedef void  (__fastcall *UpdateFn)(DWORD brick, void* edx);

static bool rd(DWORD addr, void* out, SIZE_T n)
{
    return ReadProcessMemory(GetCurrentProcess(), (LPCVOID)addr, out, n, nullptr) != 0;
}

static bool wr(DWORD addr, const void* in, SIZE_T n)
{
    return WriteProcessMemory(GetCurrentProcess(), (LPVOID)addr, in, n, nullptr) != 0;
}

/* ── DolphConfig (120NORTH node 2337, the 3D one) ─────────────────────── */
struct Cfg {
    float Gravity = 0.04f, WaterDrag = 0.04f;
    float SideSpeedBase = 0.069813f, SideSpeedRel = 0.034907f, SideBend = 1.1f;
    float VertSpeedBase = 0.069813f, VertSpeedRel = 0.034907f, VertBend = 1.25f;
    float RollSpeedBase = 0.069813f, RollSpeedRel = 0.017453f, RollBend = 1.0f;
    float S1min = 0.4f, S1max = 3.9f, S1aa = 0.5f, S1ar = 0.007f;
    float ChargeLoopAnimSpeed = 2.0f, SupChargeAnimSpeed = 2.0f, ChargeAccelRatio = 1.5f;
    int   ChargePeriod = 30, ChargeGlide = 20, SupChargePeriod = 60, SupChargeGlide = 40;
    float JumpSideBend = 1.4f, JumpVertBend = 2.0f, JumpRollBend = 2.0f;
    float JumpSideSpeed = 0.069813f, JumpVertSpeed = 0.05236f, JumpRollSpeed = 0.069813f;
    float JumpCorrSpeed = 0.087266f;
    float JumpDisRatio = 0.0f, JumpSlowRatio = 1.0f, JumpFastRatio = 1.75f;
    float TWMaxYSpeed = 0.25f, TWAngleMin = -1.570796f, TWAngleMax = -1.047198f;
    float TWAnimMinSp = 0.9f, TWAnimMaxSp = 4.0f, TWAnimStartSp = 1.0f, TWAnimAccel = 1.5f;
    float TWMaxAscend = 1.5f, TWSpeed = -0.1f, TWSlowdown = 0.1f, TWDescendSpeed = 0.03f;
    float BackSpeed = 0.15f, BrakeSlowdown = 0.1f;
    float rsrr = 1.0f, asra = 0.174533f, rsrg = 0.1f;
    int   bTurnUp = 1, TurnUpDelayZ = 0, TurnUpDelayXY = 100;
};
static Cfg C;

/* Mod-side settings (jaws_ecco.txt). */
static float g_scale = 4.0f;          /* Jaws units per Ecco unit */
static float g_body_len = 3.2f;       /* Ecco dolphin mesh length */
static int   g_invert_x = 0, g_invert_y = 0, g_skip_tick = 0;

/* Ecco's 34-entry yaw table for the 180-degree turn (0x490208, sums to pi). */
static const float TURN180_TABLE[35] = {
    0.034907f, 0.069813f, 0.10472f, 0.10472f, 0.122173f, 0.122173f, 0.122173f, 0.122173f,
    0.122173f, 0.139626f, 0.139626f, 0.139626f, 0.139626f, 0.122173f, 0.122173f, 0.122173f,
    0.122173f, 0.10472f, 0.10472f, 0.10472f, 0.10472f, 0.087266f, 0.087266f, 0.087266f,
    0.087266f, 0.087266f, 0.069813f, 0.069813f, 0.05236f, 0.034907f, 0.034907f, 0.017453f,
    0.017453f, 0.017453f, 0.0f };

/* Ecco button bits (pad +0xC), mapped from Jaws input in ReadButtons. */
enum {
    B_SWIM = 0x1, B_CHARGE = 0x2, B_CRUISE = 0x8, B_CIRCLE = 0x100, B_BRAKE = 0x200,
    B_TURN = 0x400, B_TURN_M = 0x800, B_TURNUP = 0x1000,
};

/* Clip loop starts (Ecco.gdm frame pool, see docs/ecco_dolphin_controller.md). */
enum {
    CLIP_SLOW = 6, CLIP_MED = 0x26, CLIP_FAST = 0x46, CLIP_TW = 0x66, CLIP_IDLE = 0x86,
    CLIP_CHARGE = 0xA6, CLIP_BACK = 0xC5, CLIP_TURN = 0xD6, CLIP_TURN_M = 0xFA, CLIP_SUPCHARGE = 0x11E,
};

/* ── Dolphin state (DolphCtrl fields) ──────────────────────────────────── */
struct Dolph {
    float E[3][3];            /* orientation, Ecco frame (brick +0x40) */
    float pos[3];             /* Ecco units (brick +0x70) */
    float vel[3];             /* +0x260, units per frame */
    float jscale[3];          /* Jaws brick row lengths, kept as found */
    int   state, sub;         /* +0x228, +0x22C */
    float r230, r234, r238;   /* smoothed yaw / pitch / roll input */
    float r23c, r240, r244;   /* yaw / pitch / roll speed */
    float in54c, in550, in554;/* pitch / yaw / roll input */
    int   s558, s55c, s560;   /* stick deflected (sign) */
    float lvl490, tgt494;     /* swim speed level, target speed */
    int   c3b0, c3ac, c438;
    int   c530, c534, c538;   /* charge timer, glide end, super charge */
    float f53c;               /* charge: clip frame where the push starts */
    unsigned flags;           /* +0x40 bits used here: 4, 8, 0x80, 0x200 */
    int   f590, f2a4;         /* brake = back up; moving backwards */
    float r254;
    float spd4d0, t43c;       /* turn 180: entry speed, table position */
    float rad3c0, ang3c4;     /* circling */
    float off290[2], roll2a0; /* circling: model offset in local X/Y, model roll */
    int   i2c4, i2c8;         /* frames without stick (any / XY, swim counts as input) */
    int   i32c, i330, i334;   /* idle routine */
    float i338, save340[3];
    /* simulated animation (+0x3F8 frame, +0x3FC speed, +0x410/+0x41C loop) */
    float frame, aspeed;
    int   clip_start, clip_end;
    unsigned prev_buttons;
    float last_off[3];        /* circling offset added to the written position */
    bool  have_last;
    float last_written[3];
};
static Dolph D;

static volatile bool g_on = false, g_reinit = false;
static float g_cam[3]; static volatile bool g_have_cam = false;
static unsigned g_rand = 12345;
static char  g_status[96] = "";

static int RandEcco()   /* Ecco's LCG (0x5896A0), returns 0..0x7FFF */
{
    g_rand = g_rand * 0x343FD + 0x269EC3;
    return (g_rand >> 16) & 0x7FFF;
}

/* ── Math (Ecco primitives, ecco_math.c) ───────────────────────────────── */
static inline float dot3(const float* a, const float* b) { return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]; }
static inline float len3(const float* a) { return sqrtf(dot3(a, a)); }
static inline float absf(float v) { return v < 0 ? -v : v; }
static inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

/* FUN_0016e4c0: yaw about local Y. */
static void RotYaw(float E[3][3], float a)
{
    if (a == 0) return;
    float c = cosf(a), s = sinf(a);
    for (int i = 0; i < 3; ++i) {
        float r0 = E[0][i], r2 = E[2][i];
        E[2][i] = -r0 * s + c * r2;
        E[0][i] =  c * r0 + s * r2;
    }
}
/* FUN_0016e308: pitch about local X (+ = nose down). */
static void RotPitch(float E[3][3], float a)
{
    if (a == 0) return;
    float c = cosf(a), s = sinf(a);
    for (int i = 0; i < 3; ++i) {
        float r1 = E[1][i], r2 = E[2][i];
        E[2][i] = s * r1 + c * r2;
        E[1][i] = c * r1 - s * r2;
    }
}
/* FUN_0016e688: roll about local Z. */
static void RotRoll(float E[3][3], float a)
{
    if (a == 0) return;
    float c = cosf(a), s = sinf(a);
    for (int i = 0; i < 3; ++i) {
        float r0 = E[0][i], r1 = E[1][i];
        E[1][i] = s * r0 + c * r1;
        E[0][i] = c * r0 - s * r1;
    }
}
/* FUN_0016ef80: matrix from (pitch, yaw, roll). */
static void FromEuler(float E[3][3], float px, float py, float pr)
{
    float sx = sinf(px), cx = cosf(px), sy = sinf(py), cy = cosf(py), sr = sinf(pr), cr = cosf(pr);
    E[0][0] = cr*cy - sr*sx*sy; E[0][1] = -sr*cx; E[0][2] = cr*sy + sr*sx*cy;
    E[1][0] = sr*cy + cr*sx*sy; E[1][1] =  cr*cx; E[1][2] = sr*sy - cr*sx*cy;
    E[2][0] = -cx*sy;           E[2][1] =  sx;    E[2][2] = cx*cy;
}
/* FUN_0016ee78: (pitch, yaw, roll) from matrix. */
static void ToEuler(const float E[3][3], float& px, float& py, float& pr)
{
    py = atan2f(-E[2][0], E[2][2]);
    px = atan2f(E[2][1], sqrtf(E[2][0]*E[2][0] + E[2][2]*E[2][2]));
    pr = atan2f(-E[0][1], E[1][1]);
}
/* FUN_001b0ca8: b - a, wrapped to (-pi, pi]. */
static float AngDiff(float a, float b)
{
    const float PI = 3.14159265f;
    if (a < b) { if (b - a > PI) b -= 2*PI; }
    else if (a - b > PI) b += 2*PI;
    return b - a;
}
/* FUN_001b0a80 (dt = 1): approach with a proportional step clamped to [lo, hi]. */
static bool Approach(float target, float rate, float lo, float hi, float& v)
{
    float d = target - v;
    if (absf(d) <= lo) { v = target; return true; }
    d *= rate;
    if (d > 0) d = d > hi ? hi : (d < lo ? lo : d);
    else       d = d < -hi ? -hi : (d > -lo ? -lo : d);
    v += d;
    return false;
}
/* FUN_001b0b98: linear approach; true once reached. */
static bool ApproachLin(float target, float step, float& v)
{
    if (absf(target - v) >= step) { v += v < target ? step : -step; return false; }
    v = target;
    return true;
}
static void Orthonormalize(float E[3][3])
{
    float l = len3(E[2]); for (int i = 0; i < 3; ++i) E[2][i] /= l;
    float d = dot3(E[1], E[2]); for (int i = 0; i < 3; ++i) E[1][i] -= d * E[2][i];
    l = len3(E[1]); for (int i = 0; i < 3; ++i) E[1][i] /= l;
    E[0][0] = E[1][1]*E[2][2] - E[1][2]*E[2][1];
    E[0][1] = E[1][2]*E[2][0] - E[1][0]*E[2][2];
    E[0][2] = E[1][0]*E[2][1] - E[1][1]*E[2][0];
}

/* ── Animation (FUN_0019df80 / FUN_0019e150, no blending) ──────────────── */
static void SetClip(float speed, int entry, int start, int end)
{
    if (D.clip_start == start && D.clip_end == end) { D.aspeed = speed; return; }
    D.clip_start = start; D.clip_end = end; D.frame = (float)entry; D.aspeed = speed;
}
static void StopClip() { SetClip(0, 0, 0, 0); }
static bool ClipIsSwim() { return D.clip_start == CLIP_SLOW || D.clip_start == CLIP_MED || D.clip_start == CLIP_FAST; }
static void AnimTick()
{
    if (!D.clip_end) return;
    D.frame += D.aspeed;
    float len = (float)(D.clip_end + 1 - D.clip_start);
    while (D.frame >= D.clip_end + 1) D.frame -= len;
}
/* Clip for a swim level: medium above 2x speed scale, else slow. */
static void SetSwimClip(float speed, float level)
{
    if (level < 2.0f) SetClip(speed, 0x0F, CLIP_SLOW, 0x25);
    else              SetClip(speed, 0x32, CLIP_MED, 0x45);
}

static float TargetSpeed(float level) { return level * C.S1ar * (1.0f - C.WaterDrag) / C.WaterDrag; }

/* FUN_001a7de8 + FUN_001a7cc8: swim level that holds speed `v`. */
static void LevelFromSpeed(float v)
{
    D.flags &= ~8u;
    float level = (v * C.WaterDrag) / (1.0f - C.WaterDrag) / C.S1ar;
    if (level > C.S1max) level = C.S1max;
    if (level > 2.0f) SetClip(level, 0x32, CLIP_MED, 0x45);
    else if (level <= 0.0f) { StopClip(); level = 0; }
    else { if (level < C.S1min) level = C.S1min; SetClip(level, 0x0F, CLIP_SLOW, 0x25); }
    D.lvl490 = level;
    D.tgt494 = TargetSpeed(level);
}

/* FUN_001a7178: stick inputs that turn the back axis (E2) toward `dir`.
 * True once all three are below 0.05 (aligned). */
static bool SteerToward(float px, float py, float pr, const float* dir, bool set_roll)
{
    float ty = atan2f(-dir[0], dir[2]);
    float tp = atan2f(dir[1], sqrtf(dir[0]*dir[0] + dir[2]*dir[2]));
    float ep = clampf(AngDiff(px, tp) * 2, -1, 1);
    float ey = clampf(AngDiff(py, ty) * 2 * cosf(tp), -1, 1);
    float er = clampf(-pr - pr, -1, 1);
    float c = cosf(pr), s = sinf(pr);
    D.in54c = c * ep - s * ey;
    D.in550 = s * ep + c * ey;
    if (set_roll) D.in554 = er;
    return absf(D.in54c) < 0.05f && absf(D.in550) < 0.05f && absf(D.in554) < 0.05f;
}

/* ── Input ─────────────────────────────────────────────────────────────── */
static bool GameHasFocus()
{
    DWORD pid = 0;
    GetWindowThreadProcessId(GetForegroundWindow(), &pid);
    return pid == GetCurrentProcessId();
}
static inline bool Key(int vk) { return (GetAsyncKeyState(vk) & 0x8000) != 0; }

/* Swim comes from the game's own swim bits; the other Ecco buttons are keys
 * Jaws doesn't use: RMB charge (Jaws: charge too), R brake/back up, T / Y
 * 180-degree turn (left / right), C circle (barrel roll), B cruise,
 * Q / E roll, U level out ("turn up"). */
static unsigned ReadButtons(const unsigned* pad, int& roll)
{
    unsigned b = 0;
    roll = 0;
    if (pad && (pad[0] & 0x800002)) b |= B_SWIM;
    if (!GameHasFocus() || g_block_game_input) return b;
    if (Key(VK_RBUTTON)) b |= B_CHARGE;
    if (Key('R')) b |= B_BRAKE;
    if (Key('T')) b |= B_TURN;
    if (Key('Y')) b |= B_TURN_M;
    if (Key('C')) b |= B_CIRCLE;
    if (Key('B')) b |= B_CRUISE;
    if (Key('U')) b |= B_TURNUP;
    if (Key('Q')) roll -= 0x4000;    /* Ecco: 0x20000000 -> z = -0x4000 */
    if (Key('E')) roll += 0x4000;
    return b;
}

/* FUN_0019c8e0, player branch. */
static void ReadSteering(const unsigned* pad, int roll)
{
    D.in54c = D.in550 = D.in554 = 0;
    D.s558 = D.s55c = D.s560 = 0;
    if (D.state != 5 && pad) {
        /* Jaws's stick reader FUN_0065EAE0, re-implemented because it prints a
         * debug line on every call: deadzone 0x1000, rescale to +-0x4000,
         * digital directions, Y flipped unless the invert option is set. */
        auto axis = [](int v) { int a = v < 0 ? -v : v; return a < 0x1000 ? 0 : (a - 0x1000) * v / 0x3000; };
        int x = axis((int)pad[2]), y = axis((int)pad[3]);
        if (pad[0] & 0x100) x = -0x4000; else if (pad[0] & 0x200) x = 0x4000;
        if (pad[0] & 0x40)  y = -0x4000; else if (pad[0] & 0x80)  y = 0x4000;
        unsigned char inv = 1;
        rd(INVERT_OPTION, &inv, 1);
        if (!inv) y = -y;
        if (g_invert_x) x = -x;
        if (g_invert_y) y = -y;
        if (x) { D.s55c = x < 0 ? -1 : 1; D.in550 = clampf(-(float)x / 16384.0f, -1, 1); }
        if (y) { D.s558 = y < 0 ? -1 : 1; D.in54c = clampf(-(float)y / 16384.0f, -1, 1); }
        if (roll) { D.s560 = roll < 0 ? -1 : 1; D.in554 = -(float)(roll + (roll < 0 ? 0x1000 : -0x1000)) / 12288.0f; }
    }
    /* idle counters (end of FUN_0019c8e0) */
    bool input = D.s558 || D.s55c || D.s560;
    D.i2c4 = input ? 0 : D.i2c4 + 1;
    D.i2c8 = (input || D.state == 1) ? 0 : D.i2c8 + 1;
}

/* ── Jaws side ─────────────────────────────────────────────────────────── */
static void LoadSettings()
{
    g_scale = 4.0f; g_body_len = 3.2f; g_invert_x = g_invert_y = g_skip_tick = 0;
    FILE* f = fopen(MOD_PATH("jaws_ecco.txt"), "r");
    if (!f) return;
    char line[160];
    while (fgets(line, sizeof(line), f)) {
        char key[64]; float v;
        if (line[0] == '#' || sscanf(line, "%63s %f", key, &v) != 2) continue;
        if      (!strcmp(key, "scale") && v > 0.01f)       g_scale = v;
        else if (!strcmp(key, "body_length") && v > 0.1f)  g_body_len = v;
        else if (!strcmp(key, "invert_x"))                 g_invert_x = v != 0;
        else if (!strcmp(key, "invert_y"))                 g_invert_y = v != 0;
        else if (!strcmp(key, "skip_shark_tick"))          g_skip_tick = v != 0;
    }
    fclose(f);
}

/* Starts the simulation from the brick's current world transform. */
static void InitFromBrick(const float* w)
{
    memset(&D, 0, sizeof(D));
    for (int r = 0; r < 3; ++r) {
        float l = len3(w + 3*r);
        D.jscale[r] = l > 1e-6f ? l : 1.0f;
        float sgn = (r == 1) ? 1.0f : -1.0f;      /* E0 = -J0, E1 = J1, E2 = -J2 */
        for (int i = 0; i < 3; ++i) D.E[r][i] = sgn * w[3*r + i] / D.jscale[r];
    }
    Orthonormalize(D.E);
    for (int i = 0; i < 3; ++i) D.pos[i] = w[9 + i] / g_scale;
    D.ang3c4 = 3.14159265f;
}

/* Writes world (and local, solved through the parent) transform. */
static void WriteBrick(DWORD brick, const float E[3][3], const float* posJ)
{
    float w[12];
    for (int r = 0; r < 3; ++r) {
        float sgn = (r == 1) ? 1.0f : -1.0f;
        for (int i = 0; i < 3; ++i) w[3*r + i] = sgn * E[r][i] * D.jscale[r];
    }
    w[9] = posJ[0]; w[10] = posJ[1]; w[11] = posJ[2];

    float local[12];
    memcpy(local, w, sizeof(w));
    DWORD parent = 0;
    float p[12];
    if (rd(brick + BRICK_PARENT, &parent, 4) && parent && rd(parent + BRICK_WORLD, p, sizeof(p))) {
        /* world = local * P  =>  local = world * inv(P), P = [R | t] row-vector */
        float a = p[0], b = p[1], c = p[2], d = p[3], e = p[4], f = p[5], g = p[6], h = p[7], k = p[8];
        float det = a*(e*k - f*h) - b*(d*k - f*g) + c*(d*h - e*g);
        if (absf(det) > 1e-9f) {
            float inv[9] = {
                (e*k - f*h)/det, (c*h - b*k)/det, (b*f - c*e)/det,
                (f*g - d*k)/det, (a*k - c*g)/det, (c*d - a*f)/det,
                (d*h - e*g)/det, (b*g - a*h)/det, (a*e - b*d)/det };
            float t[3] = { w[9] - p[9], w[10] - p[10], w[11] - p[11] };
            for (int r = 0; r < 4; ++r) {
                const float* src = (r < 3) ? w + 3*r : t;
                for (int i = 0; i < 3; ++i)
                    local[3*r + i] = src[0]*inv[0*3 + i] + src[1]*inv[1*3 + i] + src[2]*inv[2*3 + i];
            }
        }
    }
    DWORD flags = 0;
    wr(brick + BRICK_LOCAL, local, sizeof(local));
    wr(brick + BRICK_WORLD, w, sizeof(w));
    if (rd(brick + BRICK_FLAGS, &flags, 4)) { flags |= FLAG_WORLD_STALE; wr(brick + BRICK_FLAGS, &flags, 4); }
}

/* ── The tick (DolphCtrl::vf_05C, 3D path) ─────────────────────────────── */
static void Step(const unsigned* pad, float water_ecco, bool have_water)
{
    const float s = 1.0f;                 /* +0x248 speed scale (no exhaustion) */
    int roll_key = 0;
    unsigned b = ReadButtons(pad, roll_key);
    unsigned nb = b & ~D.prev_buttons;    /* new presses */
    unsigned released = D.prev_buttons & ~b;
    D.prev_buttons = b;

    float* E2 = D.E[2];
    float spd  = len3(D.vel);             /* fVar31 */
    float fdot = dot3(E2, D.vel);         /* fVar34: + = moving backwards */
    float h    = have_water ? D.pos[1] - water_ecco : -100000.0f;   /* brick +0x228 */
    float px, py, pr;
    ToEuler(D.E, px, py, pr);

    ReadSteering(pad, roll_key);
    if (nb & B_BRAKE) D.f590 = fdot >= -0.02f;

    /* per-frame rotation amounts: J = body only (jump, turn 180), N = also turns the velocity */
    float yawJ = 0, yawN = 0, pitchJ = 0, pitchN = 0, rollA = 0;

    for (int guard = 0; guard < 4; ++guard) {      /* the Ecco code re-enters the switch (LAB_0019e66c) */
        bool again = false;
        switch (D.state) {
        case 0: {   /* idle / brake / back up */
            if (ClipIsSwim()) StopClip();
            if (D.clip_start == CLIP_BACK && D.frame >= 213.0f - D.aspeed) StopClip();
            if (D.clip_start == CLIP_BACK && (int)D.frame == 0xCD)
                for (int i = 0; i < 3; ++i) D.vel[i] += E2[i] * C.BackSpeed * s;
            if (!(b & B_BRAKE)) {
                Approach(0, 0.2f*s, 0.01f*s, 0.1f*s, D.r254);
            } else {
                if (D.f590 == 1 && (spd < 0.02f || (D.f2a4 == 1 && spd <= C.BackSpeed * 3)) && !D.clip_end)
                    SetClip(0.5f * s, CLIP_BACK, CLIP_BACK, 0xD5);
                float tgt = 0;
                if (D.f2a4 == 0 && D.f590 == 0) {
                    bool pos_ = (D.r254 == 0) ? fdot < -0.2f : D.r254 > 0;
                    tgt = pos_ ? 1.0f : -1.0f;
                    float k = fdot * C.BrakeSlowdown * s;
                    for (int i = 0; i < 3; ++i) D.vel[i] -= E2[i] * k;
                }
                Approach(tgt, 0.2f*s, 0.01f*s, 0.1f*s, D.r254);
            }
            if (!(b & B_SWIM)) {
                if ((b & B_CRUISE) && !(b & B_BRAKE) && D.f2a4 == 0 && spd > 0.02f) { D.state = 1; D.sub = 0; }
                else if ((nb & B_CHARGE) && D.c530 == 0) { D.state = 2; D.sub = 0; again = true; }
                break;
            }
            bool tap = false;
            if (nb & B_SWIM) { tap = D.c3b0 < 10; D.c3b0 = 0; }
            bool go = tap;
            if (!tap) {
                if (D.f2a4 == 1) {
                    float k = fdot * C.BrakeSlowdown;
                    for (int i = 0; i < 3; ++i) D.vel[i] -= E2[i] * k;
                }
                go = D.f2a4 == 0 || spd < 0.02f;
            }
            if (go) {
                D.state = 1;
                D.sub = ((nb & B_SWIM) && spd < TargetSpeed(0.05f)) ? 0xD : 0;
            }
            D.c3b0++;
            break;
        }
        case 1: {   /* swim */
            switch (D.sub) {
            case 0: case 0xD:
                LevelFromSpeed(spd);
                D.c3b0 = 0;
                D.sub = (D.sub == 0xD && (b & B_SWIM)) ? 2 : 1;
                break;
            case 2: case 1: {
                if (D.sub == 2) {   /* a new swim press: next speed level */
                    float base = (D.flags & 8) ? D.lvl490 : D.aspeed;
                    D.lvl490 = fminf(base * 1.5f + C.S1aa * s, C.S1max * s);
                    D.tgt494 = TargetSpeed(D.lvl490);
                    D.c3b0 = 0;
                    if (2*s <= D.lvl490 && base < 2*s) {
                        SetClip(D.lvl490, 0x52, CLIP_FAST, 0x65);   /* kick into the fast cycle */
                        D.flags &= ~8u;
                        D.c438 = 0;
                    } else {
                        SetSwimClip(D.lvl490, D.lvl490);
                        D.flags |= 8;
                    }
                    D.sub = 1;
                }
                float cap = C.S1max * s;
                if (cap < D.lvl490) { D.lvl490 = cap; D.tgt494 = TargetSpeed(cap); D.flags |= 8; }
                if (D.flags & 8) {
                    if (absf(D.tgt494 - spd) < s * 0.05f) {
                        SetSwimClip(D.lvl490, D.lvl490);
                        D.flags &= ~8u;
                    } else {
                        float a = (D.tgt494 - spd) * 4.0f * s + D.lvl490;
                        a = clampf(a, C.S1min * s, C.S1max * s);
                        SetSwimClip(a, D.lvl490);
                    }
                }
                D.c3b0++;
                if (b & B_BRAKE) { StopClip(); D.state = 0; break; }
                if (!(b & B_SWIM) && !(b & B_CRUISE)) { D.sub = 3; D.c3ac = 10; }
                break;
            }
            case 3:     /* swim released: coast, then slow the stroke down */
                if (b & B_SWIM) { D.sub = 2; break; }
                if (b & B_BRAKE) { StopClip(); D.state = 0; break; }
                if (b & B_CRUISE) { D.sub = 1; break; }
                if (D.c3ac == 0) {
                    if ((D.clip_start == CLIP_SLOW || D.clip_start == CLIP_MED) && D.aspeed > 1.0f) D.aspeed *= 0.9f;
                    else { StopClip(); D.state = 0; }
                } else D.c3ac--;
                D.c3b0++;
                break;
            default:
                break;
            }
            if (b & B_CIRCLE) { D.state = 6; D.sub = 0; break; }
            if ((nb & B_CHARGE) && D.c530 == 0) { D.state = 2; D.sub = 0; again = true; break; }
            if (D.clip_start == CLIP_FAST) {
                if (++D.c438 == 30) { SetClip(4.0f*s, 0x32, CLIP_MED, 0x45); D.flags |= 0x80; }
                else ApproachLin(4.0f*s, 0.08f*s, D.aspeed);
            } else if (D.flags & 0x80) {
                if (ApproachLin(D.lvl490, 0.08f*s, D.aspeed)) D.flags &= ~0x80u;
            }
            break;
        }
        case 2: {   /* charge */
            float K = TargetSpeed(C.S1max) * C.ChargeAccelRatio * s;
            if (D.sub == 0) {
                if (D.c530 != 0) { StopClip(); D.state = 0; break; }
                if (spd >= 0.02f && D.f2a4 != 1) {
                    SetClip(C.ChargeLoopAnimSpeed * s, CLIP_CHARGE, CLIP_CHARGE, 0xC4);
                    D.c530 = C.ChargePeriod; D.c534 = C.ChargePeriod - C.ChargeGlide; D.c538 = 0; D.f53c = 175.0f;
                } else {
                    SetClip(C.SupChargeAnimSpeed * s, CLIP_SUPCHARGE, CLIP_SUPCHARGE, 0x13E);
                    D.c530 = C.SupChargePeriod; D.c534 = C.SupChargePeriod - C.SupChargeGlide; D.c538 = 1; D.f53c = 310.0f;
                }
                D.sub = 4;
            } else if (D.sub == 4) {
                if (D.frame >= D.f53c)
                    for (int i = 0; i < 3; ++i) D.vel[i] = -E2[i] * K;
                if ((float)D.clip_end - D.aspeed <= D.frame) { D.frame = (float)D.clip_end; D.aspeed = 0; D.sub = 5; }
            } else if (D.sub == 5) {
                if (D.c530 < D.c534) { StopClip(); D.state = 0; break; }
                for (int i = 0; i < 3; ++i) D.vel[i] = -E2[i] * K;
            }
            break;
        }
        case 3: {   /* jump */
            if (h <= 0) {
                if (b & B_SWIM) { D.state = 1; D.sub = 0; } else D.state = 0;
                break;
            }
            if (spd > 0.02f && (D.s558 == 0 || (b & B_SWIM))) {
                /* nose follows the flight path */
                float tp = atan2f(-D.vel[1], sqrtf(D.vel[0]*D.vel[0] + D.vel[2]*D.vel[2]));
                float dp = AngDiff(px, tp);
                float ty = atan2f(D.vel[0], -D.vel[2]);
                float dy = AngDiff(py, ty);
                float tot = absf(dp) + absf(dy);
                float ratio = C.JumpSlowRatio;
                if (!(b & B_SWIM)) {
                    if (b & B_CHARGE) ratio = C.JumpFastRatio;
                    else if (b & B_CRUISE) ratio = C.JumpDisRatio;
                }
                float lim = ratio * C.JumpCorrSpeed;
                float k = (lim < tot) ? lim / tot : 1.0f;
                px += dp * k;
                py += dy * k;
                FromEuler(D.E, px, py, pr);
            }
            break;
        }
        case 4: {   /* tail walk */
            if (D.sub == 0) {
                if (D.clip_start == CLIP_TW) { D.c3ac = 0; D.sub = 6; }
                else SetClip(C.TWAnimStartSp, CLIP_TW, CLIP_TW, 0x85);
                break;
            }
            if (D.sub == 6) {
                float& p = D.aspeed;
                if (nb & B_SWIM) p = fminf(p + C.TWAnimAccel, C.TWAnimMaxSp);
                else if (released & B_SWIM) D.c3ac = 10;
                if (nb & B_CHARGE) p = C.TWAnimMaxSp + C.TWAnimAccel;
                if (!(b & B_SWIM)) { if (D.c3ac == 0) p -= C.TWSlowdown; else D.c3ac--; }
                if (p < C.TWAnimMinSp || s < 0.9f) { StopClip(); D.sub = 7; break; }
                if (C.TWAnimMaxSp < p) {   /* launch out of the tail walk */
                    float k = 2.0f * C.TWMaxYSpeed / E2[1];
                    for (int i = 0; i < 3; ++i) D.vel[i] = E2[i] * k;
                    StopClip(); D.state = 0;
                    break;
                }
                /* hold the tail end at the surface, higher the faster it beats */
                float k350 = C.TWMaxAscend / (C.TWAnimMaxSp - C.TWAnimMinSp);
                float avg = D.pos[1] + E2[1] * g_body_len * 0.3f, avg0 = avg;
                Approach((D.pos[1] - h) + (p - C.TWAnimMinSp) * k350, 0.1f, 0.01f, 0.1f, avg);
                D.vel[0] = C.TWSpeed * p * E2[0];
                D.vel[2] = C.TWSpeed * p * E2[2];
                D.vel[1] = avg - avg0;
                if (C.TWAngleMin <= px && px <= C.TWAngleMax) break;
                if (b & B_SWIM) { D.state = 1; D.sub = 0; break; }
                StopClip(); D.state = 0;
                break;
            }
            if (D.sub == 7) {   /* fall back into the water */
                float k = absf(px) * C.TWDescendSpeed / 3.14159265f;
                for (int i = 0; i < 3; ++i) D.vel[i] += E2[i] * k;
                ApproachLin(-1.0f, 0.2f, D.r234);
                if (absf(px) < 0.087266f || (nb & (B_SWIM | B_CHARGE)) || D.s558) { D.state = 0; again = true; }
            }
            break;
        }
        case 5: {   /* 180-degree turn */
            if (D.sub == 0 || D.sub == 0xB) {
                if (D.sub == 0) D.spd4d0 = spd;
                if (fdot >= -0.2f) {
                    if (D.flags & 0x200) SetClip(1.0f, CLIP_TURN_M, CLIP_TURN_M, 0x11D);
                    else                 SetClip(1.0f, CLIP_TURN, CLIP_TURN, 0xF9);
                    D.t43c = 0;
                    D.sub = 0xC;
                } else if (D.sub == 0) {
                    SetClip(C.S1max, 0x52, CLIP_FAST, 0x65);
                    D.sub = 0xB;
                }
                break;
            }
            if (D.sub != 0xC) break;
            if ((D.clip_start == CLIP_TURN || D.clip_start == CLIP_TURN_M) && D.t43c < 34.0f) {
                float nt = fminf(D.t43c + 1.0f, 34.0f);
                int i0 = (int)D.t43c, i1 = (int)nt;
                float a;
                if (i0 == i1) a = (nt - D.t43c) * TURN180_TABLE[i1];
                else {
                    a = ((float)(i0 + 1) - D.t43c) * TURN180_TABLE[i0];
                    for (int i = i0 + 1; i < i1; ++i) a += TURN180_TABLE[i];
                    if (i1 < 34) a += (nt - (float)i1) * TURN180_TABLE[i1];
                }
                yawJ = (D.flags & 0x200) ? -a : a;
                D.t43c = nt;
            }
            float end = (D.flags & 0x200) ? 285.0f : 249.0f;
            if (D.frame <= end - D.aspeed) break;
            if ((b & B_SWIM) && D.spd4d0 > 0.02f) {
                D.state = 1;
                LevelFromSpeed(D.spd4d0 * 0.9f);
                D.c3b0 = 0; D.flags |= 8; D.sub = 1;
            } else { StopClip(); D.state = 0; }
            break;
        }
        case 6: {   /* circling: the model loops around the brick (barrel roll) */
            if (D.sub == 0) { D.rad3c0 = 0; D.ang3c4 = 3.14159265f; D.sub = 8; }
            if (D.sub == 8) {
                if (!(b & B_CIRCLE)) D.sub = 10;
                else if ((D.rad3c0 += C.rsrg) >= C.rsrr) D.sub = 9;
            } else if (D.sub == 9) {
                if (!(b & B_CIRCLE)) D.sub = 10;
            } else if (D.sub == 10) {
                if (D.rad3c0 > 0) D.rad3c0 -= C.rsrg;
                else if (D.ang3c4 > 2*C.asra - 3.14159265f) { D.rad3c0 = 0; D.ang3c4 -= C.asra; }
                else {
                    StopClip(); D.state = 0; D.roll2a0 = 0; D.off290[0] = D.off290[1] = 0;
                    again = true;
                    break;
                }
            }
            float a = D.ang3c4;
            D.roll2a0 = 3.14159265f - a;
            D.off290[0] = sinf(a) * D.rad3c0;
            D.off290[1] = cosf(a) * D.rad3c0;
            a -= C.asra;
            D.ang3c4 = (a < -3.14159265f) ? a + 6.2831853f : a;
            break;
        }
        default:
            D.state = 0;
            break;
        }
        if (!again) break;
    }

    /* 180-degree turn buttons (0x400 / 0x800 mirrored) */
    if ((nb & (B_TURN | B_TURN_M)) && D.state != 3 && D.state != 4 && D.state != 5) {
        D.state = 5; D.sub = 0;
        if (nb & B_TURN_M) D.flags |= 0x200; else D.flags &= ~0x200u;
    }
    if (D.state != 0) ApproachLin(0, 0.1f, D.r254);
    if (D.c530) D.c530--;
    AnimTick();

    /* water: gravity on the part of the body above the surface, drag on the rest */
    {
        float frac = 0;
        if (have_water) {
            float depth = -h;
            float ya = -E2[1] * g_body_len * 0.5f;   /* head (local -Z) */
            float yb =  E2[1] * g_body_len * 0.5f;   /* tail */
            if (depth < ya) frac = (depth < yb) ? 1.0f : (ya - depth) / (ya - yb);
            else frac = (yb <= depth) ? 0.0f : (yb - depth) / (yb - ya);
        }
        if (D.state == 3 && frac < 0.1f) frac = 0.1f;
        D.vel[1] -= frac * C.Gravity;
        float dd = (1.0f - frac) * C.WaterDrag;
        if (spd != 0) dd *= (1.0f - absf(fdot) / spd) * 5.0f + 1.0f;
        float w = dd < 1.0f ? 1.0f - dd : 0.0f;
        for (int i = 0; i < 3; ++i) D.vel[i] *= w;
    }

    float vlen = len3(D.vel);
    if (D.state == 3 || (D.state == 4 && D.sub == 6)) D.f2a4 = 0;
    else D.f2a4 = dot3(E2, D.vel) > 0.02f;

    /* turning speeds: normal, or the overridden jump set */
    float bendP, bendY, bendR, spP, spY, spR;
    if (D.state != 3) {
        bendP = C.VertBend; bendY = C.SideBend; bendR = C.RollBend;
        spP = vlen * C.VertSpeedRel + C.VertSpeedBase;
        spY = vlen * C.SideSpeedRel + C.SideSpeedBase;
        spR = vlen * C.RollSpeedRel + C.RollSpeedBase;
    } else {
        float ratio = C.JumpSlowRatio;
        if (b & B_SWIM) ratio = C.JumpDisRatio;
        else if (b & B_CHARGE) ratio = C.JumpFastRatio;
        else if (b & B_CRUISE) ratio = C.JumpDisRatio;
        bendP = C.JumpVertBend; bendY = C.JumpSideBend; bendR = C.JumpRollBend;
        spP = ratio * C.JumpVertSpeed; spY = ratio * C.JumpSideSpeed; spR = ratio * C.JumpRollSpeed;
    }
    spR *= s;

    /* idle routine: after 600 quiet frames, turn to look at the camera */
    bool quiet = D.state == 0 && b == 0 && D.i2c4 != 0 && g_have_cam;
    if (!quiet) { D.i32c = 0; D.i330 = 0; }
    else {
        float dir[3] = { D.pos[0] - g_cam[0] / g_scale, D.pos[1] - g_cam[1] / g_scale, D.pos[2] - g_cam[2] / g_scale };
        int limit = -1;
        switch (D.i32c) {
        case 0:
            if (++D.i330 > 600) { D.i32c = (RandEcco() % 100 < 66) ? 1 : 4; D.i330 = 0; }
            break;
        case 1:
            if (D.i330 == 0) { memcpy(D.save340, E2, sizeof(D.save340)); D.i330++; }
            if (len3(dir) > 0.1f && SteerToward(px, py, pr, dir, true) && ++D.i330 == 9) {
                D.i32c = (RandEcco() % 100 < 66) ? 2 : 3; D.i330 = 0;
            }
            break;
        case 2:
            if (D.i330 == 0) D.i334 = 30;
            limit = 0x5B; D.i330++;
            break;
        case 3:
            limit = 0x5B; D.i330++;
            break;
        case 4:
            if (D.i330 == 0) {
                memcpy(D.save340, E2, sizeof(D.save340));
                float w = (float)RandEcco() * 3.0517578e-05f * 0.02f + 0.03f;
                D.i338 = (RandEcco() % 100 < 50) ? -w : w;
            }
            D.in554 = (float)(D.i330 < 0x4B ? D.i330 : 0x96 - D.i330) * D.i338;
            limit = 0x97; D.i330++;
            break;
        case 5:
            if (SteerToward(px, py, pr, D.save340, true) && ++D.i330 == 9) { D.i32c = 0; D.i330 = 150; }
            break;
        }
        if (limit > 0 && D.i330 == limit) { D.i32c = 5; D.i330 = 0; }
    }

    /* turn up: level out roll (and pitch after TurnUpDelayXY quiet frames) */
    if (D.state == 3 || D.state == 4 || D.i32c != 0) {
        D.flags &= ~4u;
    } else {
        if (C.bTurnUp && D.i2c4 > C.TurnUpDelayZ && absf(E2[1]) < 0.965992f &&
            (absf(px) > 0.087266f || absf(pr) > 0.087266f)) D.flags |= 4;
        else if (b & B_TURNUP) D.flags |= 4;
        else if (!((D.flags & 4) && D.i2c4 != 0)) D.flags &= ~4u;
        if (D.flags & 4) {
            float m = (b & B_TURNUP) ? -4.0f : -2.0f, lim = (b & B_TURNUP) ? 1.0f : 0.7f;
            auto shape = [&](float v, float lo) {
                v = clampf(v, -lim, lim);
                if (absf(v) < lo) v = v >= 0 ? lo : -lo;
                return v;
            };
            D.in554 = shape(m * pr, 0.02f);
            if ((C.bTurnUp && C.TurnUpDelayXY < D.i2c8) || (b & B_TURNUP)) {
                float v = shape(m * px, 0.02f);
                if (absf(v) > 0.04f) { D.in54c = cosf(pr) * v; D.in550 = sinf(pr) * v; }
            }
            if (absf(px) <= 0.020944f && absf(pr) <= 0.020944f) D.flags &= ~4u;
        }
    }

    /* rate smoothing */
    bool tw_fall = D.state == 4 && D.sub == 7;
    if (!tw_fall) Approach(bendP * D.in54c, 0.1f*s, 0.1f*s, s, D.r234);
    Approach(bendY * D.in550, 0.1f*s, 0.1f*s, s, D.r230);
    Approach(bendR * D.in554, 0.1f*s, 0.1f*s, s, D.r238);
    Approach(spP * s * D.r234, 0.1f, 0.025f, 0.1f, D.r240);
    Approach(spY * s * D.r230, 0.1f, 0.025f, 0.1f, D.r23c);
    Approach(spR * D.r238,     0.1f, 0.025f, 0.1f, D.r244);

    bool flip = tw_fall && D.f2a4 == 1;
    if (absf(D.r234) > 0.02f) { if (D.state == 3) pitchJ += D.r240; else pitchN += flip ? -D.r240 : D.r240; }
    if (absf(D.r230) > 0.02f) { if (D.state == 3) yawJ  += D.r23c; else yawN  += flip ? -D.r23c : D.r23c; }
    if (absf(D.r238) > 0.02f) rollA += D.r244;

    /* apply */
    if (D.state == 4 && D.sub == 6) {
        FromEuler(D.E, px, (yawJ + yawN) + py, pr - rollA);
        RotPitch(D.E, pitchJ + pitchN);
    } else {
        float old[3][3], coupled[3][3];
        memcpy(old, D.E, sizeof(old));
        memcpy(coupled, D.E, sizeof(coupled));
        RotYaw(coupled, yawN);
        RotPitch(coupled, pitchN);
        if (yawN != 0 || pitchN != 0) {   /* the velocity turns with the body */
            float vb[3] = { dot3(old[0], D.vel), dot3(old[1], D.vel), dot3(old[2], D.vel) };
            for (int i = 0; i < 3; ++i) D.vel[i] = vb[0]*coupled[0][i] + vb[1]*coupled[1][i] + vb[2]*coupled[2][i];
        }
        RotYaw(D.E, yawJ + yawN);
        RotPitch(D.E, pitchJ + pitchN);
        RotRoll(D.E, rollA);
    }
    Orthonormalize(D.E);

    for (int i = 0; i < 3; ++i) D.pos[i] += D.vel[i];

    /* breaking the surface: jump, or tail walk when coming up steep and slow */
    if (D.state != 3 && D.state != 4 && have_water) {
        bool out;
        if (D.state == 6) {
            out = h + D.off290[1] * D.E[1][1] >= 0;
            if (out) { D.roll2a0 = 0; D.off290[0] = D.off290[1] = 0; }
        } else if (D.state == 2 && D.c538 && D.frame < D.f53c + 4.0f) out = false;
        else out = h >= 0;
        if (out) {
            StopClip();
            if (s <= 0.9f || C.TWMaxYSpeed < D.vel[1] || px <= C.TWAngleMin || C.TWAngleMax <= px) D.state = 3;
            else { D.state = 4; D.sub = 0; }
        }
    }

    /* swim thrust (FUN_001a7a38), from the current clip */
    {
        float T = 0;
        if (D.clip_start == CLIP_FAST) T = C.S1ar * (D.state == 1 ? D.lvl490 : D.aspeed);
        else if (D.clip_start == CLIP_SLOW || D.clip_start == CLIP_MED) T = C.S1ar * D.aspeed;
        else if (D.clip_start == CLIP_CHARGE || (D.clip_start == CLIP_SUPCHARGE && D.frame >= 310.0f))
            T = C.S1ar * C.S1max * C.ChargeAccelRatio * s;
        if (D.state == 5) T *= 3.0f;
        for (int i = 0; i < 3; ++i) D.vel[i] -= E2[i] * T;
    }
}

/* ── Hook ──────────────────────────────────────────────────────────────── */
static const char* StateName(int st)
{
    static const char* n[] = { "idle", "swim", "charge", "jump", "tailwalk", "turn180", "circle" };
    return (st >= 0 && st < 7) ? n[st] : "?";
}

/* Phase B2: show the simulated Ecco clip on the dolphin model (custom level DOLPHIN,
 * scripts/build_ecco_dolphin.py). The shark controller's clip animator sits at
 * ctrl+0xBC (PlayClip 0x65E610 -> 0x4DCF70; per-tick update 0x4DD250, called by the
 * shark tick at 0x66DF91): +0x10 skeleton model, +0x14 frame, +0x1C/+0x20 clip
 * start/end, +0x24/+0x28 cross-fade length/remaining, +0x3C weight, +0x44 speed,
 * +0x58 reference frame, +0x60 flags (8 = loop; 1/2/4 pick special bone paths).
 * After the stock tick the animator's state is saved, our clip/frame written with
 * speed 0 and no cross-fade, the engine's own update poses the bones, and the saved
 * state is put back, so the shark logic's clip timing is untouched. Only for a
 * skeleton with Ecco.gdm's 319-frame pool (SKEL resource +0x20, loader 0x6F47D0; +0x24 = morph frames). */
static const DWORD ANIMATOR_OFF  = 0xBC;
static const DWORD ANIM_UPDATE   = 0x4DD250;   /* thiscall (animator, int reset), ret 4 */
static const int   ECCO_FRAMES   = 319;
typedef int   (__fastcall *AnimUpdateFn)(void* self, void* edx, int reset);
typedef DWORD (__fastcall *GetResFn)(void* self, void* edx);

static void PoseDolphin(DWORD ctrl)
{
    BYTE* A = (BYTE*)(ctrl + ANIMATOR_OFF);
    DWORD skel = 0, vt = 0, getres = 0;
    if (!rd((DWORD)A + 0x10, &skel, 4) || !skel || !rd(skel, &vt, 4) || !rd(vt + 0x84, &getres, 4)) return;
    DWORD res = ((GetResFn)getres)((void*)skel, nullptr);
    int frames = 0;
    if (!res || !rd(res + 0x20, &frames, 4) || frames != ECCO_FRAMES) return;

    BYTE saved[0x80];
    memcpy(saved, A, sizeof(saved));
    int start = D.clip_end ? D.clip_start : 0, end = D.clip_end ? D.clip_end : 5;
    float frame = D.clip_end ? D.frame : 0.0f, zero = 0.0f, one = 1.0f;
    DWORD flags = (*(DWORD*)(A + 0x60) & ~7u) | 8u;
    memcpy(A + 0x14, &frame, 4);
    memcpy(A + 0x1C, &start, 4);
    memcpy(A + 0x20, &end, 4);
    memset(A + 0x24, 0, 8);
    memcpy(A + 0x3C, &one, 4);
    memcpy(A + 0x44, &zero, 4);
    memcpy(A + 0x58, &start, 4);
    memcpy(A + 0x60, &flags, 4);
    ((AnimUpdateFn)ANIM_UPDATE)(A, nullptr, 0);
    memcpy(A, saved, sizeof(saved));
}

static void __fastcall TickHook(void* self, void* edx)
{
    DWORD ctrl = 0, brick = 0;
    bool mine = g_on && rd(SHARK_CTRL_GLOBAL, &ctrl, 4) && ctrl == (DWORD)self &&
                rd(ctrl + 0x50, &brick, 4) && brick;
    float w[12];
    if (mine) {
        DWORD flags = 0;
        rd(brick + BRICK_FLAGS, &flags, 4);
        if (flags & FLAG_WORLD_STALE) ((UpdateFn)WORLD_UPDATE)(brick, nullptr);   /* as the shark tick does */
        mine = rd(brick + BRICK_WORLD, w, sizeof(w));
    }
    if (!mine || !g_skip_tick) ((TickFn)TICK_ORIG)(self, edx);
    if (!mine) return;

    if (g_reinit) { InitFromBrick(w); g_reinit = false; }
    else {
        /* adopt the position the engine left us (collision push, teleport) */
        float posJ[3] = { w[9], w[10], w[11] };
        float dx = posJ[0] - D.last_written[0], dy = posJ[1] - D.last_written[1], dz = posJ[2] - D.last_written[2];
        if (D.have_last && dx*dx + dy*dy + dz*dz > 100.0f * 100.0f) memset(D.vel, 0, sizeof(D.vel));
        for (int i = 0; i < 3; ++i) D.pos[i] = posJ[i] / g_scale - D.last_off[i];
    }

    float posJ[3] = { D.pos[0] * g_scale, D.pos[1] * g_scale, D.pos[2] * g_scale };
    float wy = ((WaterFn)(*(DWORD*)WATER_HEIGHT_PTR))(posJ);
    bool have_water = wy != NO_WATER;

    DWORD pad_ptr = 0, eng = 0;
    const unsigned* pad = nullptr;
    if (rd(ENGINE_GLOBAL, &eng, 4) && eng && rd(eng + 0x88, &pad_ptr, 4) && pad_ptr &&
        rd(pad_ptr + 8, &pad_ptr, 4) && pad_ptr)
        pad = (const unsigned*)pad_ptr;

    Step(pad, wy / g_scale, have_water);

    /* render transform: circling adds a local offset and a roll to the model */
    float R[3][3];
    memcpy(R, D.E, sizeof(R));
    if (D.roll2a0 != 0) RotRoll(R, D.roll2a0);
    for (int i = 0; i < 3; ++i) D.last_off[i] = D.off290[0] * D.E[0][i] + D.off290[1] * D.E[1][i];
    float out[3];
    for (int i = 0; i < 3; ++i) out[i] = (D.pos[i] + D.last_off[i]) * g_scale;
    WriteBrick(brick, R, out);
    memcpy(D.last_written, out, sizeof(out));
    D.have_last = true;
    PoseDolphin(ctrl);

    /* sonar from the head: nose = brick +Z = -E2, up = E1 */
    {
        float fwd[3] = { -R[2][0], -R[2][1], -R[2][2] }, up[3] = { R[1][0], R[1][1], R[1][2] };
        bool pressed = GameHasFocus() && !g_block_game_input && (Key('F') || Key(VK_MBUTTON));
        float cam[3] = { g_cam[0], g_cam[1], g_cam[2] };
        if (!g_have_cam) for (int i = 0; i < 3; ++i) cam[i] = out[i] - fwd[i];
        SonarTick(pressed, out, fwd, up, cam, g_scale, (out[1] - wy) / g_scale, have_water);
    }

    snprintf(g_status, sizeof(g_status), "Ecco: %s.%d lvl %.1f v %.2f%s", StateName(D.state), D.sub,
             D.lvl490, len3(D.vel), have_water ? "" : " (no water)");
}

bool InstallEccoHook()
{
    static int state = 0;
    if (state) return state > 0;
    state = -1;
    DWORD cur = 0;
    if (!rd(TICK_SLOT, &cur, 4) || cur != TICK_ORIG) return false;
    DWORD hook = (DWORD)&TickHook, old;
    if (!VirtualProtect((LPVOID)TICK_SLOT, 4, PAGE_READWRITE, &old)) return false;
    memcpy((void*)TICK_SLOT, &hook, 4);
    VirtualProtect((LPVOID)TICK_SLOT, 4, old, &old);
    state = 1;
    return true;
}

bool ToggleEcco()
{
    if (!g_on) {
        LoadSettings();
        SonarLoad();
        g_reinit = true;
        g_on = true;
    } else {
        g_on = false;
        g_status[0] = 0;
        SonarClear();
    }
    return g_on;
}

bool EccoEnabled() { return g_on; }

void EccoSetCamera(float x, float y, float z)
{
    g_cam[0] = x; g_cam[1] = y; g_cam[2] = z;
    g_have_cam = true;
}

const char* EccoStatus() { return g_on ? g_status : ""; }

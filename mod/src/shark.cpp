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
    flags |= FLAG_WORLD_STALE;
    if (!wr(brick + BRICK_LOCAL + 0x24, lt, sizeof(lt)) ||
        !wr(brick + BRICK_WORLD + 0x24, wt, sizeof(wt)) ||
        !wr(brick + BRICK_FLAGS, &flags, 4)) {
        snprintf(err, err_sz, "write failed"); return false;
    }
    return true;
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

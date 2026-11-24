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
 * Ecco sonar, visual + sound (see sonar.h). Timings and easing rates are
 * Ecco's: cone 0x304E40 (scale +0x34 -> 1 at 0.25 per tick, +0x38 follows
 * it at 0.25, hidden after +0x54 = 32 ticks), wave 0x304220 (phase 0: alpha
 * +0x48 -> 1 at 0.2, scale +0x50 -> 1 at 0.05; phase 1, 6 ticks: scale -> 1
 * at 0.25; moves (0, 0, 2.4) per tick in its spawn frame), cooldown
 * m_rSonarFrequency 1.0 x 30 ticks. Choices of ours, not from the exe: the
 * cone's alpha is 1 - (+0x38), wave phase 0 lasts 24 ticks (the clone's
 * timer isn't set by the spawner), the wave fades out linearly in phase 1
 * (Ecco only eases alpha at 0.02 there, then pops it), the wave travels
 * along the dolphin's nose (Ecco moves it along its spawn frame's +Z, and
 * which way that frame faces isn't settled), colours and blending
 * (additive). The wave mesh's axis Y is its direction of travel, as in
 * 120NORTH, where node 2445's local rotation turns mesh Y onto the mover's Z.
 */
#include "sonar.h"
#include "modpath.h"
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <vector>

/* ── Meshes ────────────────────────────────────────────────────────────── */
struct Mesh { std::vector<float> v; std::vector<unsigned short> i; };
static Mesh g_cone, g_wave;

static bool LoadObj(const char* path, Mesh& m)
{
    FILE* f = fopen(path, "r");
    if (!f) return false;
    Mesh out;
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        float x, y, z;
        if (line[0] == 'v' && line[1] == ' ' && sscanf(line + 2, "%f %f %f", &x, &y, &z) == 3) {
            out.v.push_back(x); out.v.push_back(y); out.v.push_back(z);
        } else if (line[0] == 'f' && line[1] == ' ') {
            int idx[16], n = 0;
            char* p = line + 2;
            while (n < 16) {
                while (*p == ' ' || *p == '\t') ++p;
                if (*p < '0' || *p > '9') break;
                idx[n++] = (int)strtol(p, &p, 10) - 1;
                while (*p && *p != ' ' && *p != '\t' && *p != '\n' && *p != '\r') ++p;
            }
            for (int k = 2; k < n; ++k) {          /* fan */
                out.i.push_back((unsigned short)idx[0]);
                out.i.push_back((unsigned short)idx[k - 1]);
                out.i.push_back((unsigned short)idx[k]);
            }
        }
    }
    fclose(f);
    size_t nv = out.v.size() / 3;
    if (!nv || nv > 65535 || out.i.empty()) return false;
    for (unsigned short k : out.i) if (k >= nv) return false;
    m = out;
    return true;
}

/* Fallbacks with the Ecco meshes' sizes: cone length 6.22, radius 1.3 along
 * +Z (apex at the origin); ring radius 3.2, height 0.85 along Y. */
static void MakeCone(Mesh& m)
{
    const int N = 24;
    m.v = { 0, 0, 0 };
    for (int k = 0; k < N; ++k) {
        float a = 6.2831853f * k / N;
        m.v.push_back(1.3f * cosf(a)); m.v.push_back(1.3f * sinf(a)); m.v.push_back(6.22f);
    }
    m.i.clear();
    for (int k = 0; k < N; ++k) {
        m.i.push_back(0); m.i.push_back((unsigned short)(1 + k)); m.i.push_back((unsigned short)(1 + (k + 1) % N));
    }
}

static void MakeRing(Mesh& m)
{
    const int N = 32;
    m.v.clear(); m.i.clear();
    for (int k = 0; k < N; ++k) {
        float a = 6.2831853f * k / N, c = 3.2f * cosf(a), s = 3.2f * sinf(a);
        m.v.insert(m.v.end(), { c, 0.0f, s, c, 0.85f, s });
    }
    for (int k = 0; k < N; ++k) {
        unsigned short a = (unsigned short)(2 * k), b = (unsigned short)(2 * ((k + 1) % N));
        m.i.insert(m.i.end(), { a, b, (unsigned short)(a + 1), b, (unsigned short)(b + 1), (unsigned short)(a + 1) });
    }
}

/* ── Sound ─────────────────────────────────────────────────────────────── */
typedef BOOL (WINAPI* PlaySoundFn)(LPCSTR, HMODULE, DWORD);
static PlaySoundFn g_play = nullptr;
static std::vector<char> g_wav;

static void PlaySonar()
{
    if (!g_play || g_wav.empty()) return;
    g_play(g_wav.data(), nullptr, 0x0004 /* SND_MEMORY */ | 0x0001 /* SND_ASYNC */ | 0x0002 /* SND_NODEFAULT */);
}

/* ── Settings (shared jaws_ecco.txt) ────────────────────────────────── */
static float g_head = 1.3f;     /* head offset along the heading, Ecco units */
static int   g_ztest = 1;
static float g_alpha = 0.6f;

void SonarLoad()
{
    if (!LoadObj(MOD_PATH("jaws_sonar_cone.obj"), g_cone)) MakeCone(g_cone);
    if (!LoadObj(MOD_PATH("jaws_sonar_wave.obj"), g_wave)) MakeRing(g_wave);

    if (!g_play) {
        HMODULE w = LoadLibraryA("winmm.dll");
        if (w) g_play = (PlaySoundFn)GetProcAddress(w, "PlaySoundA");
    }
    if (g_play) g_play(nullptr, nullptr, 0);   /* stop anything still playing from the old buffer */
    g_wav.clear();
    if (FILE* f = fopen(MOD_PATH("jaws_sonar.wav"), "rb")) {
        fseek(f, 0, SEEK_END);
        long n = ftell(f);
        fseek(f, 0, SEEK_SET);
        if (n > 44 && n < 8 * 1024 * 1024) {
            g_wav.resize(n);
            if (fread(g_wav.data(), 1, n, f) != (size_t)n) g_wav.clear();
        }
        fclose(f);
    }

    g_head = 1.3f; g_ztest = 1; g_alpha = 0.6f;
    if (FILE* f = fopen(MOD_PATH("jaws_ecco.txt"), "r")) {
        char line[160];
        while (fgets(line, sizeof(line), f)) {
            char key[64]; float v;
            if (line[0] == '#' || sscanf(line, "%63s %f", key, &v) != 2) continue;
            if      (!strcmp(key, "sonar_head"))  g_head = v;
            else if (!strcmp(key, "sonar_ztest")) g_ztest = v != 0;
            else if (!strcmp(key, "sonar_alpha")) g_alpha = v;
        }
        fclose(f);
    }
}

/* ── Pulses ────────────────────────────────────────────────────────────── */
struct Pulse {
    bool  cone;
    int   age, phase, phase_end;
    float pos[3], axis[3], up[3];   /* cone: follows the head; wave: spawn frame */
    float s34, s38;                 /* cone scale / fade */
    float alpha, scale, fade0;      /* wave */
};
static const int MAX_PULSES = 16;
static Pulse g_p[MAX_PULSES];
static int   g_np = 0;
static float g_scale = 4.0f;
static bool  g_was_down = false;
static int   g_tick = 0, g_ready = 0;   /* g_ready = tick when the next pulse may fire */
static CRITICAL_SECTION g_cs;
static bool g_cs_init = false;

static void Lock()   { if (!g_cs_init) { InitializeCriticalSection(&g_cs); g_cs_init = true; } EnterCriticalSection(&g_cs); }
static void Unlock() { LeaveCriticalSection(&g_cs); }

static void norm3(float* a)
{
    float l = sqrtf(a[0]*a[0] + a[1]*a[1] + a[2]*a[2]);
    if (l > 1e-6f) { a[0] /= l; a[1] /= l; a[2] /= l; }
}

static void Add(const Pulse& p)
{
    if (g_np < MAX_PULSES) g_p[g_np++] = p;
}

void SonarClear()
{
    Lock();
    g_np = 0;
    g_was_down = false;
    Unlock();
}

void SonarTick(bool pressed, const float head[3], const float fwd[3], const float up[3],
               const float cam[3], float scale, float depth, bool have_water)
{
    Lock();
    ++g_tick;
    g_scale = scale;
    float hp[3];
    for (int i = 0; i < 3; ++i) hp[i] = head[i] + fwd[i] * g_head * scale;

    /* cone direction: camera -> head (0x304E40), heading if the camera sits on the head */
    float cdir[3] = { hp[0] - cam[0], hp[1] - cam[1], hp[2] - cam[2] };
    if (cdir[0]*cdir[0] + cdir[1]*cdir[1] + cdir[2]*cdir[2] < 1e-4f) memcpy(cdir, fwd, sizeof(cdir));
    norm3(cdir);

    /* FUN_001ABBE8: underwater (depth < -2, or no water info), new press, cooldown over */
    bool can = !have_water || depth < -2.0f;
    if (can && pressed) {
        if (g_was_down) g_ready = g_tick + 30;          /* held: keep re-arming */
        else if (g_tick >= g_ready) {
            Pulse c = {};
            c.cone = true;
            memcpy(c.pos, hp, sizeof(hp)); memcpy(c.axis, cdir, sizeof(cdir)); memcpy(c.up, up, 12);
            Add(c);
            Pulse w = {};
            w.cone = false;
            memcpy(w.pos, hp, sizeof(hp)); memcpy(w.axis, fwd, 12); memcpy(w.up, up, 12);
            w.scale = 0.2f; w.phase_end = 24;
            Add(w);
            PlaySonar();
            g_ready = g_tick + 30;
        }
    }
    g_was_down = can && pressed;

    int n = 0;
    for (int k = 0; k < g_np; ++k) {
        Pulse& p = g_p[k];
        ++p.age;
        bool alive = true;
        if (p.cone) {
            p.s34 += (1.0f - p.s34) * 0.25f;
            p.s38 += (p.s34 - p.s38) * 0.25f;
            memcpy(p.pos, hp, sizeof(hp)); memcpy(p.axis, cdir, sizeof(cdir)); memcpy(p.up, up, 12);
            alive = p.age < 32;
        } else {
            if (p.phase == 0) {
                p.alpha += (1.0f - p.alpha) * 0.2f;
                p.scale += (1.0f - p.scale) * 0.05f;
                if (p.age >= p.phase_end) { p.phase = 1; p.phase_end = p.age + 6; p.fade0 = p.alpha; }
            } else {
                p.scale += (1.0f - p.scale) * 0.25f;
                p.alpha = p.fade0 * (float)(p.phase_end - p.age) / 6.0f;
                alive = p.age < p.phase_end;
            }
            for (int i = 0; i < 3; ++i) p.pos[i] += p.axis[i] * 2.4f * scale;
        }
        if (alive) g_p[n++] = p;
    }
    g_np = n;
    Unlock();
}

/* ── Drawing ───────────────────────────────────────────────────────────── */
static const DWORD RS_IDS[] = {
    7 /* ZENABLE */, 8 /* FILLMODE */, 14 /* ZWRITEENABLE */, 15 /* ALPHATESTENABLE */,
    19 /* SRCBLEND */, 20 /* DESTBLEND */, 22 /* CULLMODE */, 23 /* ZFUNC */,
    27 /* ALPHABLENDENABLE */, 28 /* FOGENABLE */, 29 /* SPECULARENABLE */, 52 /* STENCILENABLE */,
    60 /* TEXTUREFACTOR */, 137 /* LIGHTING */, 141 /* COLORVERTEX */, 151 /* VERTEXBLEND */,
};
static const int N_RS = sizeof(RS_IDS) / sizeof(RS_IDS[0]);
static const DWORD TS_IDS[][2] = {
    { 0, 1 /* COLOROP */ }, { 0, 2 /* COLORARG1 */ }, { 0, 4 /* ALPHAOP */ }, { 0, 5 /* ALPHAARG1 */ },
    { 0, 24 /* TEXTURETRANSFORMFLAGS */ }, { 1, 1 }, { 1, 4 },
};
static const int N_TS = sizeof(TS_IDS) / sizeof(TS_IDS[0]);

/* Row-vector world matrix: rows local X, Y, Z, translation. */
static void Basis(D3DMATRIX& m, const float* fwd_axis, int fwd_row, const float* up_hint,
                  const float* pos, float s)
{
    float z[3] = { fwd_axis[0], fwd_axis[1], fwd_axis[2] };
    float u[3] = { up_hint[0], up_hint[1], up_hint[2] };
    if (fabsf(z[0]*u[0] + z[1]*u[1] + z[2]*u[2]) > 0.99f) { u[0] = 1; u[1] = 0; u[2] = 0; }
    float x[3] = { u[1]*z[2] - u[2]*z[1], u[2]*z[0] - u[0]*z[2], u[0]*z[1] - u[1]*z[0] };
    norm3(x);
    float y[3] = { z[1]*x[2] - z[2]*x[1], z[2]*x[0] - z[0]*x[2], z[0]*x[1] - z[1]*x[0] };
    /* fwd_row 2: mesh +Z along the axis (cone); 1: mesh +Y along the axis (wave disc) */
    const float* r0 = x;
    const float* r1 = fwd_row == 2 ? y : z;
    const float* r2 = fwd_row == 2 ? z : y;
    memset(&m, 0, sizeof(m));
    for (int i = 0; i < 3; ++i) { m.m[0][i] = r0[i] * s; m.m[1][i] = r1[i] * s; m.m[2][i] = r2[i] * s; m.m[3][i] = pos[i]; }
    m.m[3][3] = 1.0f;
}

void SonarDraw(IDirect3DDevice8* dev, const D3DMATRIX& view, const D3DMATRIX& proj)
{
    Lock();
    if (!g_np || g_cone.i.empty() || g_wave.i.empty()) { Unlock(); return; }

    DWORD rs[N_RS], ts[N_TS], vs = 0, ps = 0;
    for (int k = 0; k < N_RS; ++k) dev->GetRenderState(RS_IDS[k], &rs[k]);
    for (int k = 0; k < N_TS; ++k) dev->GetTextureStageState(TS_IDS[k][0], TS_IDS[k][1], &ts[k]);
    D3DMATRIX sw, sv, sp;
    dev->GetTransform(D3DTS_WORLD, &sw);
    dev->GetTransform(D3DTS_VIEW, &sv);
    dev->GetTransform(D3DTS_PROJECTION, &sp);
    dev->GetVertexShader(&vs);
    dev->GetPixelShader(&ps);
    IDirect3DBaseTexture8* tex = nullptr;
    dev->GetTexture(0, &tex);
    IDirect3DVertexBuffer8* vb = nullptr; UINT stride = 0;
    dev->GetStreamSource(0, &vb, &stride);
    IDirect3DIndexBuffer8* ib = nullptr; UINT base = 0;
    dev->GetIndices(&ib, &base);

    dev->SetTransform(D3DTS_VIEW, &view);
    dev->SetTransform(D3DTS_PROJECTION, &proj);
    dev->SetPixelShader(0);
    dev->SetVertexShader(0x002 /* D3DFVF_XYZ */);
    dev->SetTexture(0, nullptr);
    dev->SetTextureStageState(0, 1, 2 /* SELECTARG1 */);
    dev->SetTextureStageState(0, 2, 3 /* TFACTOR */);
    dev->SetTextureStageState(0, 4, 2);
    dev->SetTextureStageState(0, 5, 3);
    dev->SetTextureStageState(0, 24, 0);
    dev->SetTextureStageState(1, 1, 1 /* DISABLE */);
    dev->SetTextureStageState(1, 4, 1);
    dev->SetRenderState(7, g_ztest ? 1 : 0);
    dev->SetRenderState(8, 3 /* SOLID */);
    dev->SetRenderState(14, FALSE);
    dev->SetRenderState(15, FALSE);
    dev->SetRenderState(19, 5 /* SRCALPHA */);
    dev->SetRenderState(20, 2 /* ONE */);
    dev->SetRenderState(22, 1 /* CULL_NONE */);
    dev->SetRenderState(23, 4 /* LESSEQUAL */);
    dev->SetRenderState(27, TRUE);
    dev->SetRenderState(28, FALSE);
    dev->SetRenderState(29, FALSE);
    dev->SetRenderState(52, FALSE);
    dev->SetRenderState(137, FALSE);
    dev->SetRenderState(141, FALSE);
    dev->SetRenderState(151, 0);

    for (int k = 0; k < g_np; ++k) {
        const Pulse& p = g_p[k];
        const Mesh& m = p.cone ? g_cone : g_wave;
        float a = p.cone ? (1.0f - p.s38) : p.alpha;
        float s = (p.cone ? p.s34 : p.scale) * g_scale;
        a *= g_alpha;
        if (a <= 0.004f || s <= 1e-4f) continue;
        D3DMATRIX w;
        Basis(w, p.axis, p.cone ? 2 : 1, p.up, p.pos, s);
        dev->SetTransform(D3DTS_WORLD, &w);
        DWORD A = (DWORD)(a > 1.0f ? 255 : a * 255.0f);
        DWORD col = p.cone ? 0x0060C0FFu : 0x0090D8FFu;
        dev->SetRenderState(60, (A << 24) | col);
        dev->DrawIndexedPrimitiveUP((D3DPRIMITIVETYPE)4 /* TRIANGLELIST */, 0, (UINT)(m.v.size() / 3),
                                    (UINT)(m.i.size() / 3), m.i.data(), 101 /* D3DFMT_INDEX16 */,
                                    m.v.data(), 12);
    }

    dev->SetIndices(ib, base);
    if (ib) ib->Release();
    dev->SetStreamSource(0, vb, stride);
    if (vb) vb->Release();
    dev->SetTexture(0, tex);
    if (tex) tex->Release();
    dev->SetVertexShader(vs);
    dev->SetPixelShader(ps);
    dev->SetTransform(D3DTS_WORLD, &sw);
    dev->SetTransform(D3DTS_VIEW, &sv);
    dev->SetTransform(D3DTS_PROJECTION, &sp);
    for (int k = 0; k < N_TS; ++k) dev->SetTextureStageState(TS_IDS[k][0], TS_IDS[k][1], ts[k]);
    for (int k = 0; k < N_RS; ++k) dev->SetRenderState(RS_IDS[k], rs[k]);
    Unlock();
}

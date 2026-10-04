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

#include "device_proxy.h"
#include "shark.h"
#include "input_block.h"
#include "bookmarks.h"
#include "stage.h"
#include "messages.h"
#include "iddump.h"
#include "levels.h"
#include <math.h>
#include <stdio.h>
#include <stdarg.h>

/* Teleport hold state: process-wide, the device proxy is recreated often. */
static const int TP_HOLD_FRAMES = 45;     /* ~0.75 s; 20 was occasionally too short */
static const bool TP_DEBUG_SCAN = false;  /* log memory still holding the old position (see shark.h) */
static int   g_tp_late_check = 0;        /* frames until a second, later readback */
static int   g_tp_hold_frames = 0;
static int   g_tp_scan_frames = 0;
static float g_tp_hold_target[3];
static float g_tp_old[3];

/* F9 level picker state: process-wide for the same reason. */
static bool g_picker_open  = false;
static int  g_picker_sel   = 0;
static int  g_picker_count = 0;
static int  ScanCount() { return g_picker_count; }

static inline bool key_down(int vk)
{
    /* key_down can be unreliable under Wine when the window isn't
     * the foreground window. GetKeyState reads the thread message queue
     * state which is more consistent inside a hooked DX call. */
    return (GetKeyState(vk) & 0x8000) != 0;
}

#define VK_F2  0x71
#define VK_F3  0x72
#define VK_F4  0x73
#define VK_F5  0x74
#define VK_F6  0x75
#define VK_F7  0x76
#define VK_F8  0x77
#define VK_F9  0x78
#define VK_F10 0x79
#define VK_F11 0x7A
#define VK_F12 0x7B
#define VK_W   0x57
#define VK_A   0x41
#define VK_S   0x53
#define VK_D   0x44
#define VK_U   0x55
#define VK_I   0x49
#define VK_O   0x4F
#define VK_J   0x4A
#define VK_K   0x4B
#define VK_L   0x4C

static const float FC_SPEED  = 5.0f;    /* units per second */
static const float FC_SHIFT  = 45.5f;  /* held-shift speed multiplier */
static const float FC_SENS   = 0.003f; /* mouse radians per pixel */


/* ── IUnknown ────────────────────────────────────────────────────────────── */

DeviceProxy::DeviceProxy(IDirect3DDevice8* real, UINT w, UINT h)
    : real_(real), vp_w_(w), vp_h_(h)
{
    log_msg("[jaws_mod] DeviceProxy::ctor done");
    /* overlay Init is deferred to first BeginScene to avoid crashing
     * during device setup before the pipeline is ready */
}

HRESULT __stdcall DeviceProxy::QueryInterface(REFIID riid, void** ppv)
{
    return real_->QueryInterface(riid, ppv);
}

ULONG __stdcall DeviceProxy::AddRef()
{
    return ++refs_;
}

ULONG __stdcall DeviceProxy::Release()
{
    if (--refs_ == 0) { delete this; return 0; }
    return refs_;
}

/* ── Reset — reinitialise overlay after device reset ─────────────────────── */

HRESULT __stdcall DeviceProxy::Reset(D3DPRESENT_PARAMETERS* pp)
{
    overlay_.Release();
    if (backbuffer_surf_) { backbuffer_surf_->Release(); backbuffer_surf_ = nullptr; }
    HRESULT hr = real_->Reset(pp);
    if (SUCCEEDED(hr)) {
        vp_w_ = pp->BackBufferWidth;
        vp_h_ = pp->BackBufferHeight;
        overlay_.Init(real_, vp_w_, vp_h_);
    }
    return hr;
}

/* ── SetRenderTarget — track whether we're on the primary backbuffer ─────── */

HRESULT __stdcall DeviceProxy::SetRenderTarget(IDirect3DSurface8* rt, IDirect3DSurface8* ds)
{
    if (!backbuffer_surf_)
        real_->GetBackBuffer(0, 0, &backbuffer_surf_); /* AddRefs; held for the proxy's lifetime */

    on_primary_target_ = (rt == backbuffer_surf_);

    return real_->SetRenderTarget(rt, ds);
}

/* ── SetRenderState — suppress fog/wireframe when toggles are active ──────── */

HRESULT __stdcall DeviceProxy::SetRenderState(DWORD state, DWORD value)
{
    if (fog_off_   && state == 28) value = FALSE; /* D3DRS_FOGENABLE */
    /* wireframe_ toggle disabled — D3DRS_FILLMODE override not supported by DXVK */
    // if (wireframe_ && state ==  8) value = 2;

    /* Track whether alpha test is currently on so we can lock it when hiding foliage. */
    if (state == 15) /* D3DRS_ALPHATESTENABLE */
        alpha_test_enabled_ = (value != FALSE);

    if (hide_foliage_ && alpha_test_enabled_) {
        if (state == 15 && value != FALSE) {
            /* Enable alpha test but set an impossible condition: alpha > 255.
             * No pixel can ever pass, so all alpha-tested geometry (foliage,
             * plants, kelp cards) becomes invisible. */
            real_->SetRenderState(15, TRUE);
            real_->SetRenderState(24, 0xFF); /* D3DRS_ALPHAREF  = 255 */
            real_->SetRenderState(25, 5);    /* D3DRS_ALPHAFUNC = D3DCMP_GREATER */
            return S_OK;
        }
        if (state == 24) value = 0xFF; /* D3DRS_ALPHAREF  — keep locked */
        if (state == 25) value = 5;    /* D3DRS_ALPHAFUNC — keep locked */
    }

    return real_->SetRenderState(state, value);
}

/* ── Screenshot — grab front buffer and write BMP to C:\ ─────────────────── */

/* Process-wide (not per-DeviceProxy) so the numbering survives device
 * recreation — the game calls CreateDevice far more often than a fresh
 * DeviceProxy instance implies, which used to reset a per-instance counter
 * back to 0 and made screenshots overwrite each other. Seeded from existing
 * files on disk so it also survives across separate game launches. */
static int NextScreenshotIdx()
{
    static int next_idx = -1;
    if (next_idx == -1) {
        next_idx = 0;
        WIN32_FIND_DATAA fd;
        HANDLE h = FindFirstFileA("C:\\jaws_screenshot_*.bmp", &fd);
        if (h != INVALID_HANDLE_VALUE) {
            do {
                int n;
                if (sscanf(fd.cFileName, "jaws_screenshot_%d.bmp", &n) == 1 && n >= next_idx)
                    next_idx = n + 1;
            } while (FindNextFileA(h, &fd));
            FindClose(h);
        }
    }
    return next_idx++;
}

void DeviceProxy::TakeScreenshot()
{
    static const D3DFORMAT FMT_A8R8G8B8 = (D3DFORMAT)21;
    char dbg[160];
    snprintf(dbg, sizeof(dbg), "[jaws_mod] screenshot: attempt (vp=%ux%u)", vp_w_, vp_h_);
    log_msg(dbg);

    IDirect3DSurface8* surf = nullptr;
    HRESULT hr = real_->CreateImageSurface(vp_w_, vp_h_, FMT_A8R8G8B8, &surf);
    if (FAILED(hr)) {
        snprintf(dbg, sizeof(dbg), "[jaws_mod] screenshot: CreateImageSurface failed hr=0x%08lX", (unsigned long)hr);
        log_msg(dbg);
        return;
    }
    hr = real_->GetFrontBuffer(surf);
    if (FAILED(hr)) {
        snprintf(dbg, sizeof(dbg), "[jaws_mod] screenshot: GetFrontBuffer failed hr=0x%08lX", (unsigned long)hr);
        log_msg(dbg);
        surf->Release();
        return;
    }

    D3DLOCKED_RECT lr;
    hr = surf->LockRect(&lr, nullptr, 0);
    if (FAILED(hr)) {
        snprintf(dbg, sizeof(dbg), "[jaws_mod] screenshot: LockRect failed hr=0x%08lX", (unsigned long)hr);
        log_msg(dbg);
        surf->Release();
        return;
    }

    char path[MAX_PATH];
    snprintf(path, sizeof(path), "C:\\jaws_screenshot_%04d.bmp", NextScreenshotIdx());

    DWORD pixel_bytes = vp_w_ * vp_h_ * 4;
    BITMAPFILEHEADER fh = {};
    fh.bfType    = 0x4D42;
    fh.bfOffBits = sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER);
    fh.bfSize    = fh.bfOffBits + pixel_bytes;
    BITMAPINFOHEADER ih = {};
    ih.biSize        = sizeof(BITMAPINFOHEADER);
    ih.biWidth       = (LONG)vp_w_;
    ih.biHeight      = -(LONG)vp_h_; /* negative = top-down, matches D3D */
    ih.biPlanes      = 1;
    ih.biBitCount    = 32;
    ih.biCompression = BI_RGB;
    ih.biSizeImage   = pixel_bytes;

    HANDLE hf = CreateFileA(path, GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, 0, nullptr);
    if (hf != INVALID_HANDLE_VALUE) {
        DWORD n;
        WriteFile(hf, &fh, sizeof(fh), &n, nullptr);
        WriteFile(hf, &ih, sizeof(ih), &n, nullptr);
        BYTE* src = (BYTE*)lr.pBits;
        for (UINT y = 0; y < vp_h_; ++y)
            WriteFile(hf, src + y * lr.Pitch, vp_w_ * 4, &n, nullptr);
        CloseHandle(hf);
        char msg[MAX_PATH + 32];
        snprintf(msg, sizeof(msg), "[jaws_mod] screenshot: %s", path);
        log_msg(msg);
    } else {
        snprintf(dbg, sizeof(dbg), "[jaws_mod] screenshot: CreateFileA failed err=%lu", (unsigned long)GetLastError());
        log_msg(dbg);
    }
    surf->UnlockRect();
    surf->Release();
}

/* ── Extract world-space camera position from view matrix ────────────────── */

static float med5(float* a)
{
    float t[5]; for (int i=0;i<5;i++) t[i]=a[i];
    for (int i=0;i<5;i++) for (int j=i+1;j<5;j++) if (t[j]<t[i]) { float tmp=t[i];t[i]=t[j];t[j]=tmp; }
    return t[2];
}

void DeviceProxy::ExtractCamPos(const D3DMATRIX& v)
{
    /* The game calls SetTransform(D3DTS_VIEW,...) multiple times per frame:
     * the real player camera, plus at least one secondary camera (water
     * reflection/refraction). Two purely mathematical attempts to tell them
     * apart from the matrix data alone both failed: a velocity/position
     * gate can't handle a reflection that moves right along with the real
     * camera, and the reflection's rotation part turned out to have a
     * perfectly ordinary +1 determinant here (confirmed by logging) --
     * this engine must render the reflection via a genuinely different
     * (mirrored-position) camera rather than a flipped-handedness matrix.
     *
     * Track the actual mechanism instead of guessing from the numbers:
     * secondary passes render to an off-screen texture, not the primary
     * back buffer, so gate on which render target is active (tracked in
     * SetRenderTarget) rather than anything about the camera itself. */
    float tx = v._41, ty = v._42, tz = v._43;
    float cx = -(v._11*tx + v._21*ty + v._31*tz);
    float cy = -(v._12*tx + v._22*ty + v._32*tz);
    float cz = -(v._13*tx + v._23*ty + v._33*tz);

    if (!on_primary_target_)
        return;

    cam_x_ = cx;
    cam_y_ = cy;
    cam_z_ = cz;

    /* Rolling history for median-position seeding on F2 activation -- now only
     * ever fed accepted (gated) samples, so this stays a real-camera history. */
    cam_hx_[cam_hidx_] = cam_x_;
    cam_hy_[cam_hidx_] = cam_y_;
    cam_hz_[cam_hidx_] = cam_z_;
    /* Forward vector (col 3 of rotation): _13=F.x, _23=F.y, _33=F.z */
    cam_hyaw_  [cam_hidx_] = atan2f(v._13, v._33);
    cam_hpitch_[cam_hidx_] = asinf(fmaxf(-1.0f, fminf(1.0f, v._23)));
    cam_hidx_ = (cam_hidx_ + 1) % 5;
}

/* ── SetTransform — track view matrix; inject freecam ───────────────────── */

HRESULT __stdcall DeviceProxy::SetTransform(D3DTRANSFORMSTATETYPE state,
                                             const D3DMATRIX*      mat)
{
    if (state == D3DTS_VIEW && mat) {
        ExtractCamPos(*mat);

        if (freecam_) {
            UpdateFreecam();
            D3DMATRIX fc_view;
            BuildViewMatrix(fc_view);
            return real_->SetTransform(state, &fc_view);
        }
    }
    return real_->SetTransform(state, mat);
}

/* ── EndScene — draw overlay, then hand off to real device ───────────────── */

HRESULT __stdcall DeviceProxy::EndScene()
{
    UpdateMessageOverrides();

    if (!endscene_logged_) {
        log_msg("[jaws_mod] EndScene firing — proxy is active");
        endscene_logged_ = true;
    }

    /* Toggle freecam on F2 (rising edge) — moved off F1 so F1 is free for
     * the game's own map screen (freecam interferes with the map's 3D view). */
    bool freecam_now = key_down(VK_F2);
    if (freecam_now && !freecam_prev_) {
        log_msg("[jaws_mod] F2 toggled");
        freecam_ = !freecam_;
        if (freecam_) {
            /* Seed from median of last 5 view matrices — picks the main camera
             * even when the game alternates with a secondary shadow/reflection camera. */
            fc_x_     = med5(cam_hx_);
            fc_y_     = med5(cam_hy_);
            fc_z_     = med5(cam_hz_);
            fc_yaw_   = med5(cam_hyaw_);
            fc_pitch_ = med5(cam_hpitch_);
            char buf[128];
            snprintf(buf, sizeof(buf), "[jaws_mod] freecam seed pos=(%.1f, %.1f, %.1f) yaw=%.2f pitch=%.2f",
                     fc_x_, fc_y_, fc_z_, fc_yaw_, fc_pitch_);
            log_msg(buf);
            /* Capture mouse */
            POINT pt; GetCursorPos(&pt);
            last_mouse_ = pt;
            mouse_captured_ = true;
            ShowCursor(FALSE);
        } else {
            ShowCursor(TRUE);
            mouse_captured_ = false;
        }
    }
    freecam_prev_ = freecam_now;

    /* F7 — two-pass health scanner.
     * Pass 1 (press at full health): records all floats in [0.001, 20.0] across full .data.
     * Pass 2 (press after taking damage): logs addresses whose value changed. */
    bool f7_now = key_down(VK_F7);
    if (f7_now && !f7_prev_) {
        static int   scan_phase = 0;
        static DWORD scan_addr [16000];
        static float scan_val0 [16000];
        static int   scan_n    = 0;
        char buf[160];

        if (scan_phase == 0) {
            scan_n = 0;
            /* Exact match: 1.0f (0x3F800000) or 10.0f (0x41200000) — full range */
            for (DWORD va = 0x845000u; va < 0xE70000u && scan_n < 16000; va += 4) {
                DWORD raw = *reinterpret_cast<const DWORD*>(va);
                if (raw == 0x3F800000u || raw == 0x41200000u) {
                    scan_addr[scan_n] = va;
                    scan_val0[scan_n] = *reinterpret_cast<const float*>(va);
                    ++scan_n;
                }
            }
            snprintf(buf, sizeof(buf),
                "[jaws_mod] F7 scan1: %d exact-1.0/10.0 (0x845000-0xE70000) — take damage then F7", scan_n);
            log_msg(buf);
            scan_phase = 1;
        } else {
            int dec = 0, inc = 0;
            for (int i = 0; i < scan_n; ++i) {
                float v = *reinterpret_cast<const float*>(scan_addr[i]);
                if (v < scan_val0[i] - 0.005f) {
                    snprintf(buf, sizeof(buf),
                        "[jaws_mod] dec 0x%08lX  was=%.4f  now=%.4f",
                        scan_addr[i], scan_val0[i], v);
                    log_msg(buf);
                    if (++dec >= 40) { log_msg("[jaws_mod] dec (capped)"); break; }
                }
            }
            for (int i = 0; i < scan_n; ++i) {
                float v = *reinterpret_cast<const float*>(scan_addr[i]);
                if (v > scan_val0[i] + 0.005f && v < 20.0f) {
                    snprintf(buf, sizeof(buf),
                        "[jaws_mod] inc 0x%08lX  was=%.4f  now=%.4f",
                        scan_addr[i], scan_val0[i], v);
                    log_msg(buf);
                    if (++inc >= 20) { log_msg("[jaws_mod] inc (capped)"); break; }
                }
            }
            snprintf(buf, sizeof(buf), "[jaws_mod] F7 scan2: %d dec  %d inc", dec, inc);
            log_msg(buf);
            scan_phase = 0;
        }
    }
    f7_prev_ = f7_now;

    /* F9 — custom level picker (see levels.h). Up/Down select, Enter loads,
     * Esc/F9 closes. Game keyboard input is swallowed while it's open. */
    {
        static bool f9_prev = false;
        static bool key_prev[256];
        auto pressed = [](int vk) {
            bool now = key_down(vk), was = key_prev[vk];
            key_prev[vk] = now;
            return now && !was;
        };
        bool f9_now = key_down(VK_F9);
        if (g_picker_open) {
            int n = ScanCount();
            if (pressed(VK_UP)   && n) g_picker_sel = (g_picker_sel + n - 1) % n;
            if (pressed(VK_DOWN) && n) g_picker_sel = (g_picker_sel + 1) % n;
            if (pressed(VK_ESCAPE) || (f9_now && !f9_prev)) {
                g_picker_open = false;
            } else if (pressed(VK_RETURN) && n) {
                g_picker_open = false;
                char msg[96];
                const char* name = CustomLevelName(g_picker_sel);
                RequestStageLoad(name, msg, sizeof(msg));
                SetTpMsg("%s", msg);
                char buf[160];
                snprintf(buf, sizeof(buf), "[jaws_mod] F9: %s", msg);
                log_msg(buf);
            }
        } else if (f9_now && !f9_prev && !tp_active_) {
            int n = ScanCustomLevels();
            g_picker_count = n;
            if (g_picker_sel >= n) g_picker_sel = 0;
            g_picker_open = true;
            g_block_game_input = true;
            for (int vk = 0; vk < 256; ++vk) key_prev[vk] = key_down(vk);
            char buf[96];
            snprintf(buf, sizeof(buf), "[jaws_mod] F9: %d custom level(s)", n);
            log_msg(buf);
        }
        f9_prev = f9_now;
    }

    /* Screenshot (F3 — rising edge, captures the current front buffer) */
    bool f3_now = key_down(VK_F3);
    if (f3_now && !f3_prev_) TakeScreenshot();
    f3_prev_ = f3_now;

    /* Fog toggle (F4) — SetRenderState override keeps it suppressed each frame */
    bool f4_now = key_down(VK_F4);
    if (f4_now && !f4_prev_) {
        fog_off_ = !fog_off_;
        real_->SetRenderState(28, fog_off_ ? FALSE : TRUE); /* force immediate update */
        log_msg(fog_off_ ? "[jaws_mod] fog OFF" : "[jaws_mod] fog ON");
    }
    f4_prev_ = f4_now;

    /* F5 — simulation pause (wireframe left commented out — not supported by DXVK) */
    bool f5_now = key_down(VK_F5);
    if (f5_now && !f5_prev_) {
        sim_paused_ = !sim_paused_;
        g_sim_paused = sim_paused_;
        if (sim_paused_) {
            freeze_sim_time();
            log_msg("[jaws_mod] sim PAUSED");
        } else {
            thaw_sim_time();
            log_msg("[jaws_mod] sim RESUMED");
        }
    }
    f5_prev_ = f5_now;

    /* Foliage hide toggle (F6) — forces alpha test to always fail while active */
    bool f6_now = key_down(VK_F6);
    if (f6_now && !f6_prev_) {
        hide_foliage_ = !hide_foliage_;
        log_msg(hide_foliage_ ? "[jaws_mod] foliage HIDDEN" : "[jaws_mod] foliage VISIBLE");
    }
    f6_prev_ = f6_now;

    /* Confine cursor to game window — prevents drift to other monitors.
     * Releases automatically when the window loses focus (alt-tab etc.). */
    {
        HWND fg = GetForegroundWindow();
        DWORD fg_pid = 0;
        GetWindowThreadProcessId(fg, &fg_pid);
        if (fg_pid == GetCurrentProcessId()) {
            RECT r;
            GetClientRect(fg, &r);
            POINT tl = { r.left, r.top };
            POINT br = { r.right, r.bottom };
            ClientToScreen(fg, &tl);
            ClientToScreen(fg, &br);
            RECT sr = { tl.x, tl.y, br.x, br.y };
            ClipCursor(&sr);
        } else {
            ClipCursor(NULL);
        }
    }

    /* F11 — invincibility toggle. Health refill runs every frame while on;
     * the pointer chain is re-resolved each time, so it survives level
     * loads (unlike the old hardcoded-address god mode, which crashed). */
    bool f11_now = key_down(VK_F11);
    if (f11_now && !f11_prev_) {
        invincible_ = !invincible_;
        log_msg(invincible_ ? "[jaws_mod] invincible ON" : "[jaws_mod] invincible OFF");
    }
    f11_prev_ = f11_now;
    if (invincible_) RefillSharkHealth();
    /* Scripted / timer deaths bypass health and set the shark's "dead"
     * state directly -- block those too (see InstallDeathBlock). */
    {
        static bool tried = false;
        if (!tried) {
            tried = true;
            log_msg(InstallDeathBlock() ? "[jaws_mod] death block: SetState hook installed"
                                        : "[jaws_mod] death block: install FAILED (exe bytes differ?)");
        }
        g_block_shark_death = invincible_ ? 1 : 0;
        static int logged = 0;
        static DWORD last_log = 0;
        if (g_blocked_deaths != logged && GetTickCount() - last_log > 1000) {
            char buf[96];
            snprintf(buf, sizeof(buf), "[jaws_mod] death block: blocked %d death request(s) so far", g_blocked_deaths);
            log_msg(buf);
            logged = g_blocked_deaths;
            last_log = GetTickCount();
        }
    }

    /* F10 — reload the current stage from disk (engine's own deferred stage
     * request, see stage.h). Debounce and cooldown are process-wide statics:
     * the proxy is recreated during loads, and a per-instance "previous key"
     * would re-fire while the key is still held. Ignored while typing in F8. */
    {
        static bool  f10_prev = false;
        static DWORD last_reload = 0;
        bool f10_now = key_down(VK_F10);
        if (f10_now && !f10_prev && !tp_active_ && GetTickCount() - last_reload > 3000) {
            char msg[96];
            if (RequestStageReload(msg, sizeof(msg)))
                last_reload = GetTickCount();
            SetTpMsg("%s", msg);
            char buf[128];
            snprintf(buf, sizeof(buf), "[jaws_mod] F10: %s", msg);
            log_msg(buf);
        }
        f10_prev = f10_now;
    }

    /* F12 — dump the engine's object-ID registry for the IDs in C:\jaws_ids.txt
     * to C:\jaws_iddump.txt (read-only debug aid, see iddump.h). */
    {
        static bool  f12_prev = false;
        static DWORD last_dump = 0;
        bool f12_now = key_down(VK_F12);
        if (f12_now && !f12_prev && !tp_active_ && GetTickCount() - last_dump > 1000) {
            char msg[128];
            DumpIdRegistry(msg, sizeof(msg));
            last_dump = GetTickCount();
            SetTpMsg("%s", msg);
            char buf[160];
            snprintf(buf, sizeof(buf), "[jaws_mod] F12: %s", msg);
            log_msg(buf);
        }
        f12_prev = f12_now;
    }

    /* F8 — teleport text box. Game keyboard input is swallowed while open. */
    InstallInputBlock();
    bool f8_now = key_down(VK_F8);
    if (tp_active_) {
        HandleTeleportInput();
    } else if (f8_now && !f8_prev_ && !g_picker_open) {
        tp_active_ = true;
        tp_len_ = 0; tp_buf_[0] = 0;
        BookmarkReloadIfChanged();   /* pick up hand edits to the file */
        g_block_game_input = true;
        /* Seed edge detection with current key state so nothing held
         * at open time gets typed. */
        for (int vk = 0; vk < 256; ++vk) tp_key_prev_[vk] = key_down(vk);
    }
    f8_prev_ = f8_now;
    /* Keep blocking until Enter/Esc are released, so the game never sees
     * a lone key-up/down from closing the box. */
    if (!tp_active_ && !g_picker_open && g_block_game_input && !key_down(VK_RETURN) && !key_down(VK_ESCAPE))
        g_block_game_input = false;

    /* Teleport hold: keep re-writing the target for a few frames so every
     * "previous position" the physics keeps catches up. Without it a long
     * jump reads as a huge one-frame velocity and flings the shark into the
     * sky or under the map (2026-10-04). The first frames also log any
     * memory still holding the pre-teleport position (debug). */
    if (g_tp_hold_frames > 0) {
        char err[64];
        TeleportShark(g_tp_hold_target[0], g_tp_hold_target[1], g_tp_hold_target[2], err, sizeof(err));
        --g_tp_hold_frames;
        if (g_tp_scan_frames > 0) {
            static char scanbuf[8192];
            ScanSharkPositionCopies(g_tp_old, 2.0f, scanbuf, sizeof(scanbuf));
            char hdr[96];
            snprintf(hdr, sizeof(hdr), "[jaws_mod] TP hold frame %d, old-position scan:", 4 - g_tp_scan_frames);
            log_msg(hdr);
            for (char* line = strtok(scanbuf, "\n"); line; line = strtok(nullptr, "\n")) {
                char lb[200];
                snprintf(lb, sizeof(lb), "[jaws_mod]   %s", line);
                log_msg(lb);
            }
            --g_tp_scan_frames;
        }
    }

    /* Late readback (~2 s): catches the game pushing the shark away after
     * the hold ended, e.g. out of geometry it landed in. */
    if (g_tp_late_check > 0 && --g_tp_late_check == 0) {
        SharkState st;
        if (ReadShark(st)) {
            float dx = st.x - g_tp_hold_target[0], dy = st.y - g_tp_hold_target[1], dz = st.z - g_tp_hold_target[2];
            float dist = sqrtf(dx*dx + dy*dy + dz*dz);
            char buf[160];
            snprintf(buf, sizeof(buf), "[jaws_mod] TP late readback (2 s): now (%.1f, %.1f, %.1f), off by %.1f",
                     st.x, st.y, st.z, dist);
            log_msg(buf);
        }
    }

    /* Teleport readback: ~half a second later, check the shark is still
     * where we put it (physics/controller could snap it back). */
    if (tp_verify_frames_ > 0 && --tp_verify_frames_ == 0) {
        SharkState st;
        char buf[160];
        if (ReadShark(st)) {
            float dx = st.x - tp_target_[0], dy = st.y - tp_target_[1], dz = st.z - tp_target_[2];
            float dist = sqrtf(dx*dx + dy*dy + dz*dz);
            snprintf(buf, sizeof(buf), "[jaws_mod] TP readback: now (%.1f, %.1f, %.1f), target (%.1f, %.1f, %.1f), off by %.1f",
                     st.x, st.y, st.z, tp_target_[0], tp_target_[1], tp_target_[2], dist);
            log_msg(buf);
            if (dist > 25.0f) SetTpMsg("TP didn't stick (moved back %.0f)", dist);
        } else {
            log_msg("[jaws_mod] TP readback: shark gone");
        }
    }

    /* Draw HUD. Prefer the player shark's real world position (read from
     * game memory, see shark.h); fall back to the D3D camera-derived
     * position when the shark controller doesn't exist (menus, loading). */
    OverlayInfo info = {};
    SharkState st;
    info.pos_is_shark = ReadShark(st);
    if (info.pos_is_shark) {
        info.x = st.x; info.y = st.y; info.z = st.z;
        info.has_facing = true;
        info.yaw_deg = st.yaw_deg; info.pitch_deg = st.pitch_deg;
    } else {
        info.x = cam_x_; info.y = cam_y_; info.z = cam_z_;
    }
    info.freecam = freecam_; info.fog_off = fog_off_; info.wireframe = wireframe_;
    info.hide_foliage = hide_foliage_; info.sim_paused = sim_paused_;
    info.invincible = invincible_;
    info.tp_active = tp_active_;
    info.tp_text   = tp_buf_;
    char slot_text[BOOKMARK_SLOTS][40];
    if (tp_active_) {
        for (int i = 0; i < BOOKMARK_SLOTS; ++i) {
            float bx, by, bz;
            const char* label = "";
            if (BookmarkGet(i + 1, bx, by, bz, &label) && label[0])
                snprintf(slot_text[i], sizeof(slot_text[i]), "%d: %.22s", i + 1, label);
            else if (BookmarkGet(i + 1, bx, by, bz))
                snprintf(slot_text[i], sizeof(slot_text[i]), "%d: %.0f %.0f %.0f", i + 1, bx, by, bz);
            else                                snprintf(slot_text[i], sizeof(slot_text[i]), "%d: -", i + 1);
            info.tp_slots[i] = slot_text[i];
        }
    }
    info.picker_open  = g_picker_open;
    info.picker_count = g_picker_count;
    info.picker_sel   = g_picker_sel;
    for (int i = 0; i < g_picker_count && i < MAX_CUSTOM_LEVELS; ++i)
        info.picker_names[i] = CustomLevelName(i);
    info.tp_msg    = (tp_msg_[0] && GetTickCount() < tp_msg_until_) ? tp_msg_ : nullptr;
    overlay_.Draw(real_, info);

    return real_->EndScene();
}

/* ── Teleport text box (F8) ──────────────────────────────────────────────── */

void DeviceProxy::SetTpMsg(const char* fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(tp_msg_, sizeof(tp_msg_), fmt, ap);
    va_end(ap);
    tp_msg_until_ = GetTickCount() + 4000;
}

void DeviceProxy::HandleTeleportInput()
{
    /* Typed characters: main-row and numpad digits, minus, period; space
     * and comma both act as separators. */
    static const struct { int vk; char ch; } keys[] = {
        {'0','0'},{'1','1'},{'2','2'},{'3','3'},{'4','4'},{'5','5'},{'6','6'},{'7','7'},{'8','8'},{'9','9'},
        {0x60,'0'},{0x61,'1'},{0x62,'2'},{0x63,'3'},{0x64,'4'},{0x65,'5'},{0x66,'6'},{0x67,'7'},{0x68,'8'},{0x69,'9'},
        {0xBD,'-'},{0x6D,'-'},{0xBE,'.'},{0x6E,'.'},{0x20,' '},{0xBC,' '},
    };
    auto pressed = [this](int vk) {
        bool now = key_down(vk), was = tp_key_prev_[vk];
        tp_key_prev_[vk] = now;
        return now && !was;
    };

    bool ctrl = key_down(VK_CONTROL);
    for (const auto& k : keys) {
        if (!pressed(k.vk)) continue;
        /* Ctrl+1..9: bookmark the current position into that slot. */
        if (ctrl && k.ch >= '1' && k.ch <= '9') {
            SharkState cur;
            if (!ReadShark(cur)) { SetTpMsg("Bookmark failed: no shark"); continue; }
            BookmarkSet(k.ch - '0', cur.x, cur.y, cur.z);
            SetTpMsg("Saved slot %c: %.0f %.0f %.0f", k.ch, cur.x, cur.y, cur.z);
            char buf[96];
            snprintf(buf, sizeof(buf), "[jaws_mod] bookmark %c = (%.2f, %.2f, %.2f)", k.ch, cur.x, cur.y, cur.z);
            log_msg(buf);
            continue;
        }
        if (!ctrl && tp_len_ < (int)sizeof(tp_buf_) - 1) {
            tp_buf_[tp_len_++] = k.ch;
            tp_buf_[tp_len_] = 0;
        }
    }
    if (pressed(VK_BACK) && tp_len_ > 0) tp_buf_[--tp_len_] = 0;

    if (pressed(VK_ESCAPE)) {
        tp_active_ = false;
        SetTpMsg("Teleport cancelled");
        return;
    }
    if (!pressed(VK_RETURN)) return;

    tp_active_ = false;
    float v[3];
    int n = sscanf(tp_buf_, "%f %f %f", &v[0], &v[1], &v[2]);
    SharkState cur;
    if (!ReadShark(cur)) { SetTpMsg("TP failed: no shark"); return; }
    if (n == 1 && v[0] == floorf(v[0]) && v[0] >= 1 && v[0] <= BOOKMARK_SLOTS) {
        /* A lone slot number jumps to that bookmark (a coordinate entry
         * always has 2-3 numbers, so this can't be mistaken for one). */
        int slot = (int)v[0];
        if (!BookmarkGet(slot, v[0], v[1], v[2])) { SetTpMsg("Slot %d is empty", slot); return; }
    }
    else if (n == 2) { v[2] = v[1]; v[1] = cur.y; }     /* "X Z" keeps current depth */
    else if (n != 3) { SetTpMsg("TP: need X Y Z, X Z, or slot 1-9"); return; }

    char err[64];
    char buf[160];
    if (!TeleportShark(v[0], v[1], v[2], err, sizeof(err))) {
        SetTpMsg("TP failed: %s", err);
        snprintf(buf, sizeof(buf), "[jaws_mod] TP failed: %s", err);
        log_msg(buf);
        return;
    }
    snprintf(buf, sizeof(buf), "[jaws_mod] TP from (%.1f, %.1f, %.1f) to (%.1f, %.1f, %.1f)",
             cur.x, cur.y, cur.z, v[0], v[1], v[2]);
    log_msg(buf);
    SetTpMsg("TP -> %.0f %.0f %.0f", v[0], v[1], v[2]);
    tp_target_[0] = v[0]; tp_target_[1] = v[1]; tp_target_[2] = v[2];
    tp_verify_frames_ = 30;
    for (int k = 0; k < 3; ++k) { g_tp_hold_target[k] = v[k]; }
    g_tp_old[0] = cur.x; g_tp_old[1] = cur.y; g_tp_old[2] = cur.z;
    g_tp_hold_frames = TP_HOLD_FRAMES;
    g_tp_scan_frames = TP_DEBUG_SCAN ? 3 : 0;
    g_tp_late_check = 120;
}

/* ── Freecam movement (called from SetTransform every view update) ────────── */

void DeviceProxy::UpdateFreecam()
{
    if (!freecam_) return;

    /* Real wall-clock dt via the unhooked GetTickCount pointer — bypasses
     * the sim-pause fake tick so camera speed is independent of the game
     * loop rate whether paused or not. Clamped to 100ms to avoid a large
     * jump on first call or after the window loses focus. */
    DWORD real_now = g_real_GetTickCount();
    float dt = fc_time_init_
        ? fminf((float)(real_now - fc_last_real_ms_) / 1000.0f, 0.5f)
        : 0.0f;
    fc_last_real_ms_ = real_now;
    fc_time_init_    = true;

    /* Mouse look — per-pixel, already frame-rate independent */
    if (mouse_captured_) {
        POINT cur; GetCursorPos(&cur);
        float dx = (float)(cur.x - last_mouse_.x);
        float dy = (float)(cur.y - last_mouse_.y);
        fc_yaw_   += dx * FC_SENS;
        fc_pitch_ -= dy * FC_SENS;
        if (fc_pitch_ >  1.4f) fc_pitch_ =  1.4f;
        if (fc_pitch_ < -1.4f) fc_pitch_ = -1.4f;
        POINT centre = { (LONG)vp_w_ / 2, (LONG)vp_h_ / 2 };
        SetCursorPos(centre.x, centre.y);
        last_mouse_ = centre;
    }

    /* Keyboard movement scaled by real dt */
    float speed = FC_SPEED * dt;
    if (key_down(VK_MENU)) speed *= FC_SHIFT;

    float sy = sinf(fc_yaw_),  cy = cosf(fc_yaw_);
    float sp = sinf(fc_pitch_), cp = cosf(fc_pitch_);

    float fx = sy * cp, fy = sp, fz = cy * cp;
    float rx = cy, ry = 0.0f, rz = -sy;

    if (key_down(VK_I)) { fc_x_ += fx*speed; fc_y_ += fy*speed; fc_z_ += fz*speed; }
    if (key_down(VK_K)) { fc_x_ -= fx*speed; fc_y_ -= fy*speed; fc_z_ -= fz*speed; }
    if (key_down(VK_L)) { fc_x_ += rx*speed; fc_y_ += ry*speed; fc_z_ += rz*speed; }
    if (key_down(VK_J)) { fc_x_ -= rx*speed; fc_y_ -= ry*speed; fc_z_ -= rz*speed; }
    if (key_down(VK_U)) fc_y_ += speed;
    if (key_down(VK_O)) fc_y_ -= speed;
}

/* ── Build view matrix from freecam position + yaw/pitch ─────────────────── */

void DeviceProxy::BuildViewMatrix(D3DMATRIX& v) const
{
    float sy = sinf(fc_yaw_),  cy = cosf(fc_yaw_);
    float sp = sinf(fc_pitch_), cp = cosf(fc_pitch_);

    /* Basis vectors in world space */
    float fx = sy*cp, fy = sp,  fz = cy*cp;  /* forward */
    float rx = cy,    ry = 0.f, rz = -sy;     /* right   */
    /* Up = cross(forward, right)  [D3D left-handed: fwd × right gives world-up] */
    float ux = fy*rz - fz*ry;
    float uy = fz*rx - fx*rz;
    float uz = fx*ry - fy*rx;

    /* Normalise up */
    float ulen = sqrtf(ux*ux + uy*uy + uz*uz);
    if (ulen > 0.0001f) { ux/=ulen; uy/=ulen; uz/=ulen; }

    /* View = R^T * T  (dot-products into translation row) */
    v._11 = rx; v._12 = ux; v._13 = fx; v._14 = 0;
    v._21 = ry; v._22 = uy; v._23 = fy; v._24 = 0;
    v._31 = rz; v._32 = uz; v._33 = fz; v._34 = 0;
    v._41 = -(rx*fc_x_ + ry*fc_y_ + rz*fc_z_);
    v._42 = -(ux*fc_x_ + uy*fc_y_ + uz*fc_z_);
    v._43 = -(fx*fc_x_ + fy*fc_y_ + fz*fc_z_);
    v._44 = 1;
}

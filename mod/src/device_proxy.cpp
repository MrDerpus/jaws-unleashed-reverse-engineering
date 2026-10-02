#include "device_proxy.h"
#include "shark.h"
#include "input_block.h"
#include "bookmarks.h"
#include "stage.h"
#include <math.h>
#include <stdio.h>
#include <stdarg.h>

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

    /* F9 — three-pass player-position memory scanner. Sidesteps the D3D
     * camera transform ambiguity entirely (see mod dev log: the game
     * interleaves several camera identities per frame across off-screen
     * render targets, none of which map cleanly to "the real player
     * camera") by reading the game's actual position state directly, the
     * same way the god-mode health addresses were originally found.
     *
     * A 2-pass "did it move" version was tried first and found a false
     * positive: some oscillating/animation value (swim-cycle bob, most
     * likely) that happened to be a different value between the two
     * snapshots, without actually being a moving world position. Fixed by
     * requiring a THIRD snapshot and checking that the two displacement
     * vectors point in a consistent direction (cosine similarity > 0.5) --
     * real position moving in a straight line satisfies this; a value
     * that's merely "different by chance" twice in a row generally won't.
     *
     * Pass 1 (press while stationary): records every 4-byte-aligned XYZ
     * float triplet in a plausible coordinate range across the same address
     * range the F7 health scan already reads safely.
     * Pass 2 (press after swimming a distance in a straight line): keeps
     * triplets that moved a meaningful amount.
     * Pass 3 (press after continuing to swim in the SAME direction): keeps
     * survivors whose second displacement direction roughly matches the
     * first, and logs them. */
    bool f9_now = key_down(VK_F9);
    if (f9_now && !f9_prev_) {
        static int   pscan_phase = 0;
        static DWORD pscan_addr[4000];
        static float pscan_x0[4000], pscan_y0[4000], pscan_z0[4000];
        static float pscan_x1[4000], pscan_y1[4000], pscan_z1[4000];
        static int   pscan_n = 0;
        char buf[192];

        auto plausible = [](float v) {
            float a = fabsf(v);
            return a > 0.5f && a < 6000.0f;
        };

        if (pscan_phase == 0) {
            pscan_n = 0;
            for (DWORD va = 0x845000u; va < 0xE70000u - 8 && pscan_n < 4000; va += 4) {
                float x = *reinterpret_cast<const float*>(va);
                float y = *reinterpret_cast<const float*>(va + 4);
                float z = *reinterpret_cast<const float*>(va + 8);
                if (plausible(x) && plausible(y) && plausible(z)) {
                    pscan_addr[pscan_n] = va;
                    pscan_x0[pscan_n] = x; pscan_y0[pscan_n] = y; pscan_z0[pscan_n] = z;
                    ++pscan_n;
                }
            }
            snprintf(buf, sizeof(buf),
                "[jaws_mod] F9 scan1: %d plausible XYZ triplets (0x845000-0xE70000) — swim a good distance in a straight line, then F9",
                pscan_n);
            log_msg(buf);
            pscan_phase = 1;

        } else if (pscan_phase == 1) {
            int kept = 0;
            for (int i = 0; i < pscan_n; ++i) {
                float x = *reinterpret_cast<const float*>(pscan_addr[i]);
                float y = *reinterpret_cast<const float*>(pscan_addr[i] + 4);
                float z = *reinterpret_cast<const float*>(pscan_addr[i] + 8);
                if (!plausible(x) || !plausible(y) || !plausible(z)) continue;
                float dx = x - pscan_x0[i], dy = y - pscan_y0[i], dz = z - pscan_z0[i];
                if (sqrtf(dx*dx + dy*dy + dz*dz) > 3.0f) {
                    pscan_addr[kept] = pscan_addr[i];
                    pscan_x0[kept] = pscan_x0[i]; pscan_y0[kept] = pscan_y0[i]; pscan_z0[kept] = pscan_z0[i];
                    pscan_x1[kept] = x; pscan_y1[kept] = y; pscan_z1[kept] = z;
                    ++kept;
                }
            }
            pscan_n = kept;
            snprintf(buf, sizeof(buf),
                "[jaws_mod] F9 scan2: %d survivors — keep swimming the SAME direction, then F9 again", pscan_n);
            log_msg(buf);
            pscan_phase = 2;

        } else {
            int hits = 0;
            for (int i = 0; i < pscan_n; ++i) {
                float x = *reinterpret_cast<const float*>(pscan_addr[i]);
                float y = *reinterpret_cast<const float*>(pscan_addr[i] + 4);
                float z = *reinterpret_cast<const float*>(pscan_addr[i] + 8);
                if (!plausible(x) || !plausible(y) || !plausible(z)) continue;
                float d1x = pscan_x1[i]-pscan_x0[i], d1y = pscan_y1[i]-pscan_y0[i], d1z = pscan_z1[i]-pscan_z0[i];
                float d2x = x-pscan_x1[i],           d2y = y-pscan_y1[i],           d2z = z-pscan_z1[i];
                float m1 = sqrtf(d1x*d1x + d1y*d1y + d1z*d1z);
                float m2 = sqrtf(d2x*d2x + d2y*d2y + d2z*d2z);
                if (m1 < 3.0f || m2 < 3.0f) continue;
                float cos_sim = (d1x*d2x + d1y*d2y + d1z*d2z) / (m1 * m2);
                if (cos_sim > 0.5f) {
                    snprintf(buf, sizeof(buf),
                        "[jaws_mod] F9 hit 0x%08lX  (%.2f,%.2f,%.2f) -> (%.2f,%.2f,%.2f) -> (%.2f,%.2f,%.2f)  cos=%.2f",
                        pscan_addr[i], pscan_x0[i], pscan_y0[i], pscan_z0[i],
                        pscan_x1[i], pscan_y1[i], pscan_z1[i], x, y, z, cos_sim);
                    log_msg(buf);
                    if (++hits >= 40) { log_msg("[jaws_mod] F9 hits (capped)"); break; }
                }
            }
            snprintf(buf, sizeof(buf), "[jaws_mod] F9 scan3: %d direction-consistent hits", hits);
            log_msg(buf);
            pscan_phase = 0;
        }
    }
    f9_prev_ = f9_now;

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

    /* F8 — teleport text box. Game keyboard input is swallowed while open. */
    InstallInputBlock();
    bool f8_now = key_down(VK_F8);
    if (tp_active_) {
        HandleTeleportInput();
    } else if (f8_now && !f8_prev_) {
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
    if (!tp_active_ && g_block_game_input && !key_down(VK_RETURN) && !key_down(VK_ESCAPE))
        g_block_game_input = false;

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

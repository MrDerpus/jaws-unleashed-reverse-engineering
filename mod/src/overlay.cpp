#include "overlay.h"
#include <stdio.h>

static inline void ov_log(const char* msg)
{
    FILE* f = fopen("C:\\jaws_mod.log", "a");
    if (f) { fprintf(f, "%s\n", msg); fclose(f); }
}

/* ── Textured quad vertex ────────────────────────────────────────────────── */
/* D3DFVF_XYZ=0x002, D3DFVF_XYZRHW=0x004, D3DFVF_DIFFUSE=0x040, D3DFVF_TEX1=0x100.
 * XYZ and XYZRHW are alternatives in the position-type field, not combinable flags —
 * the previous (0x002|0x004|0x100) actually evaluated to 0x106, which decodes as
 * D3DFVF_XYZB1 (position + 1 blend weight) | D3DFVF_TEX1: no diffuse-color component
 * at all, and *not* pretransformed (XYZRHW), so these vertices were being run back
 * through the full world/view/projection + lighting pipeline using the game's own
 * camera matrices instead of being drawn as a fixed screen-space quad. That's almost
 * certainly why the overlay never appeared. */
#define D3DFVF_TLVERTEX (0x004 | 0x040 | 0x100)  /* D3DFVF_XYZRHW | D3DFVF_DIFFUSE | D3DFVF_TEX1 */

struct TLVertex {
    float x, y, z, rhw;
    DWORD color;
    float u, v;
};

/* ── D3DFORMAT constants we need ─────────────────────────────────────────── */
static const D3DFORMAT FMT_A8R8G8B8 = (D3DFORMAT)21;
static const D3DPOOL   POOL_MANAGED  = (D3DPOOL)1;
static const DWORD     LOCK_DISCARD  = 0x2000;
static const DWORD     RS_ALPHABLENDENABLE = 27;
static const DWORD     RS_SRCBLEND        = 19;
static const DWORD     RS_DESTBLEND       = 20;
static const DWORD     RS_ZENABLE         = 7;
static const DWORD     RS_ZWRITEENABLE    = 14;
static const DWORD     RS_CULLMODE        = 22;
static const DWORD     RS_LIGHTING        = 137;
static const DWORD     RS_COLORVERTEX     = 141;
static const DWORD     BLEND_SRCALPHA     = 5;
static const DWORD     BLEND_INVSRCALPHA  = 6;
static const DWORD     CULL_NONE          = 1;
static const DWORD     ZENABLE_FALSE      = 0;
static const DWORD     TS_COLOROP        = 0;   /* D3DTSS_COLOROP */
static const DWORD     TS_COLORARG1      = 1;   /* D3DTSS_COLORARG1 */
static const DWORD     TS_ALPHAOP        = 3;   /* D3DTSS_ALPHAOP */
static const DWORD     TS_ALPHAARG1      = 4;   /* D3DTSS_ALPHAARG1 */
static const DWORD     TOP_MODULATE      = 4;
static const DWORD     TOP_SELECTARG1    = 2;
static const DWORD     TA_TEXTURE        = 2;
static const DWORD     TA_DIFFUSE        = 0;

Overlay::Overlay()  = default;
Overlay::~Overlay() { Release(); }

void Overlay::Init(IDirect3DDevice8* dev, UINT vp_w, UINT vp_h)
{
    Release();
    vp_w_ = vp_w;
    vp_h_ = vp_h;

    HRESULT hr = dev->CreateTexture(tex_w_, tex_h_, 1, 0,
                                     FMT_A8R8G8B8, POOL_MANAGED, &tex_);
    char buf[96];
    snprintf(buf, sizeof(buf), "[jaws_mod] Overlay::Init CreateTexture hr=0x%08lX tex_=%p", (long)hr, (void*)tex_);
    ov_log(buf);
}

void Overlay::Release()
{
    if (tex_) { tex_->Release(); tex_ = nullptr; }
}

/* ── Update the CPU-side texture via GDI ────────────────────────────────── */
void Overlay::UpdateTexture(float cx, float cy, float cz,
                             bool freecam, bool god,
                             bool fog_off, bool wireframe, bool hide_foliage,
                             bool sim_paused)
{
    if (!tex_) return;

    /* D3DLOCK_DISCARD is only valid for DYNAMIC-usage resources; this texture
     * is POOL_MANAGED with no usage flags, so DISCARD is invalid here and
     * some drivers (DXVK included) can fail the lock outright instead of
     * silently ignoring it like old native D3D8 drivers did. Use a plain lock. */
    D3DLOCKED_RECT lr;
    HRESULT lock_hr = tex_->LockRect(0, &lr, nullptr, 0);
    if (FAILED(lock_hr)) {
        static bool logged_once = false;
        if (!logged_once) {
            char buf[64];
            snprintf(buf, sizeof(buf), "[jaws_mod] Overlay LockRect FAILED hr=0x%08lX", (long)lock_hr);
            ov_log(buf);
            logged_once = true;
        }
        return;
    }

    /* Create a GDI DIB section the same size as the texture. */
    BITMAPINFO bmi = {};
    bmi.bmiHeader.biSize        = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth       = (LONG)tex_w_;
    bmi.bmiHeader.biHeight      = -(LONG)tex_h_; /* top-down */
    bmi.bmiHeader.biPlanes      = 1;
    bmi.bmiHeader.biBitCount    = 32;
    bmi.bmiHeader.biCompression = BI_RGB;

    void* dibBits = nullptr;
    HDC   memDC   = CreateCompatibleDC(nullptr);
    HBITMAP hBmp  = CreateDIBSection(memDC, &bmi, DIB_RGB_COLORS, &dibBits, nullptr, 0);
    HBITMAP hOld  = (HBITMAP)SelectObject(memDC, hBmp);

    /* Background: transparent black */
    HBRUSH bgBrush = CreateSolidBrush(RGB(0, 0, 0));
    RECT   rc      = { 0, 0, (LONG)tex_w_, (LONG)tex_h_ };
    FillRect(memDC, &rc, bgBrush);
    DeleteObject(bgBrush);

    /* Text style */
    HFONT hFont = CreateFontA(
        16, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE,
        ANSI_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
        ANTIALIASED_QUALITY, FIXED_PITCH | FF_MODERN, "Courier New");
    HFONT hOldFont = (HFONT)SelectObject(memDC, hFont);
    SetBkMode(memDC, TRANSPARENT);
    SetTextColor(memDC, RGB(0, 255, 0)); /* green */

    char buf[64];
    snprintf(buf, sizeof(buf), "X: %8.1f", cx);
    TextOutA(memDC, 6, 4,  buf, (int)strlen(buf));
    snprintf(buf, sizeof(buf), "Y: %8.1f", cy);
    TextOutA(memDC, 6, 22, buf, (int)strlen(buf));
    snprintf(buf, sizeof(buf), "Z: %8.1f", cz);
    TextOutA(memDC, 6, 40, buf, (int)strlen(buf));

    /* Status lines */
    SetTextColor(memDC, freecam ? RGB(255,255,0) : RGB(150,150,150));
    TextOutA(memDC, 6, 58, freecam ? "[F1] FreeCam  ON" : "[F1] FreeCam OFF", 16);

    SetTextColor(memDC, god ? RGB(255,255,0) : RGB(150,150,150));
    TextOutA(memDC, 6, 74, god ? "[F2] GodMode  ON" : "[F2] GodMode OFF", 16);

    SetTextColor(memDC, fog_off ? RGB(255,255,0) : RGB(150,150,150));
    TextOutA(memDC, 6, 90, fog_off ? "[F4] Fog      OFF" : "[F4] Fog       ON", 17);

    SetTextColor(memDC, sim_paused ? RGB(255,255,0) : RGB(150,150,150));
    TextOutA(memDC, 6, 106, sim_paused ? "[F5] Sim Pause ON " : "[F5] Sim Pause OFF", 18);

    SetTextColor(memDC, hide_foliage ? RGB(255,255,0) : RGB(150,150,150));
    TextOutA(memDC, 6, 122, hide_foliage ? "[F6] Foliage  OFF" : "[F6] Foliage   ON", 17);

    SelectObject(memDC, hOldFont);
    DeleteObject(hFont);
    GdiFlush();

    /*
     * Copy DIB bits into the D3D texture. DIB is 32-bit BGRA;
     * D3D A8R8G8B8 is also BGRA in memory — direct copy works.
     * Set alpha=255 for text pixels (non-black), 0 for background.
     */
    DWORD* src = (DWORD*)dibBits;
    DWORD* dst = (DWORD*)lr.pBits;
    for (UINT y = 0; y < tex_h_; ++y) {
        for (UINT x = 0; x < tex_w_; ++x) {
            DWORD px = src[y * tex_w_ + x];
            BYTE  r  = (px >> 16) & 0xFF;
            BYTE  g  = (px >>  8) & 0xFF;
            BYTE  b  =  px        & 0xFF;
            BYTE  a  = (r | g | b) ? 255 : 0; /* transparent background */
            dst[y * (lr.Pitch / 4) + x] = (a << 24) | (r << 16) | (g << 8) | b;
        }
    }

    SelectObject(memDC, hOld);
    DeleteObject(hBmp);
    DeleteDC(memDC);

    tex_->UnlockRect(0);
}

/* ── Draw a screen-aligned quad with the overlay texture ─────────────────── */
void Overlay::DrawQuad(IDirect3DDevice8* dev)
{
    if (!tex_) return;

    /* Save every state we're about to touch. GetTexture adds a ref. */
    IDirect3DBaseTexture8* saved_tex = nullptr;
    dev->GetTexture(0, &saved_tex);

    DWORD s_colorop, s_colorarg1, s_alphaop, s_alphaarg1;
    dev->GetTextureStageState(0, TS_COLOROP,   &s_colorop);
    dev->GetTextureStageState(0, TS_COLORARG1, &s_colorarg1);
    dev->GetTextureStageState(0, TS_ALPHAOP,   &s_alphaop);
    dev->GetTextureStageState(0, TS_ALPHAARG1, &s_alphaarg1);

    DWORD s_blend, s_src, s_dst, s_ze, s_zw, s_cull, s_light, s_cvert;
    dev->GetRenderState(RS_ALPHABLENDENABLE, &s_blend);
    dev->GetRenderState(RS_SRCBLEND,         &s_src);
    dev->GetRenderState(RS_DESTBLEND,        &s_dst);
    dev->GetRenderState(RS_ZENABLE,          &s_ze);
    dev->GetRenderState(RS_ZWRITEENABLE,     &s_zw);
    dev->GetRenderState(RS_CULLMODE,         &s_cull);
    dev->GetRenderState(RS_LIGHTING,         &s_light);
    dev->GetRenderState(RS_COLORVERTEX,      &s_cvert);

    DWORD s_vshader;
    dev->GetVertexShader(&s_vshader);

    /* DrawPrimitiveUP internally rebinds stream 0 and may clear the index buffer. */
    IDirect3DVertexBuffer8* s_vbuf   = nullptr;
    UINT                    s_vstride = 0;
    dev->GetStreamSource(0, &s_vbuf, &s_vstride);

    IDirect3DIndexBuffer8* s_ibuf = nullptr;
    UINT                   s_bv   = 0;
    dev->GetIndices(&s_ibuf, &s_bv);

    /* Draw */
    float x0 = 8.0f,          y0 = 8.0f;
    float x1 = x0 + tex_w_,   y1 = y0 + tex_h_;

    TLVertex verts[4] = {
        { x0, y0, 0.0f, 1.0f, 0xFFFFFFFF, 0.0f, 0.0f },
        { x1, y0, 0.0f, 1.0f, 0xFFFFFFFF, 1.0f, 0.0f },
        { x0, y1, 0.0f, 1.0f, 0xFFFFFFFF, 0.0f, 1.0f },
        { x1, y1, 0.0f, 1.0f, 0xFFFFFFFF, 1.0f, 1.0f },
    };

    dev->SetTexture(0, tex_);
    dev->SetTextureStageState(0, TS_COLOROP,   TOP_MODULATE);
    dev->SetTextureStageState(0, TS_COLORARG1, TA_TEXTURE);
    dev->SetTextureStageState(0, TS_ALPHAOP,   TOP_SELECTARG1);
    dev->SetTextureStageState(0, TS_ALPHAARG1, TA_TEXTURE);

    dev->SetRenderState(RS_ALPHABLENDENABLE, TRUE);
    dev->SetRenderState(RS_SRCBLEND,         BLEND_SRCALPHA);
    dev->SetRenderState(RS_DESTBLEND,        BLEND_INVSRCALPHA);
    dev->SetRenderState(RS_ZENABLE,          ZENABLE_FALSE);
    dev->SetRenderState(RS_ZWRITEENABLE,     FALSE);
    dev->SetRenderState(RS_CULLMODE,         CULL_NONE);
    dev->SetRenderState(RS_LIGHTING,         FALSE);
    dev->SetRenderState(RS_COLORVERTEX,      FALSE);

    dev->SetVertexShader(D3DFVF_TLVERTEX);
    dev->DrawPrimitiveUP((D3DPRIMITIVETYPE)5 /* D3DPT_TRIANGLESTRIP */, 2, verts, sizeof(TLVertex));

    /* Restore */
    dev->SetIndices(s_ibuf, s_bv);
    if (s_ibuf) s_ibuf->Release();
    dev->SetStreamSource(0, s_vbuf, s_vstride);
    if (s_vbuf) s_vbuf->Release();
    dev->SetVertexShader(s_vshader);
    dev->SetRenderState(RS_ALPHABLENDENABLE, s_blend);
    dev->SetRenderState(RS_SRCBLEND,         s_src);
    dev->SetRenderState(RS_DESTBLEND,        s_dst);
    dev->SetRenderState(RS_ZENABLE,          s_ze);
    dev->SetRenderState(RS_ZWRITEENABLE,     s_zw);
    dev->SetRenderState(RS_CULLMODE,         s_cull);
    dev->SetRenderState(RS_LIGHTING,         s_light);
    dev->SetRenderState(RS_COLORVERTEX,      s_cvert);
    dev->SetTextureStageState(0, TS_COLOROP,   s_colorop);
    dev->SetTextureStageState(0, TS_COLORARG1, s_colorarg1);
    dev->SetTextureStageState(0, TS_ALPHAOP,   s_alphaop);
    dev->SetTextureStageState(0, TS_ALPHAARG1, s_alphaarg1);
    dev->SetTexture(0, saved_tex);
    if (saved_tex) saved_tex->Release(); /* GetTexture added a ref */
}

void Overlay::Draw(IDirect3DDevice8* dev,
                   float cx, float cy, float cz,
                   bool freecam, bool god,
                   bool fog_off, bool wireframe, bool hide_foliage,
                   bool sim_paused)
{
    UpdateTexture(cx, cy, cz, freecam, god, fog_off, wireframe, hide_foliage, sim_paused);
    DrawQuad(dev);
}

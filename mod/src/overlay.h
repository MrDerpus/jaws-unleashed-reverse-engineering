#pragma once
#include "d3d8_iface.h"

/* Everything the HUD shows, filled in by DeviceProxy::EndScene each frame. */
struct OverlayInfo {
    float x, y, z;
    bool  pos_is_shark;      /* true: shark world pos from memory; false: camera fallback */
    bool  has_facing;
    float yaw_deg, pitch_deg;
    bool  freecam, fog_off, wireframe, hide_foliage, sim_paused, invincible;
    bool  tp_active;         /* teleport text box open */
    const char* tp_text;     /* text typed so far */
    const char* tp_msg;      /* transient result/error line, or nullptr */
    const char* tp_slots[9]; /* bookmark slot lines, shown while the box is open */
};

/*
 * Bitmap-font overlay — renders XYZ coords and mod status using GDI text
 * drawn into a D3D texture each frame. No d3dx dependency.
 */
class Overlay {
public:
    Overlay();
    ~Overlay();

    /* Call once after device is created / reset. */
    void Init(IDirect3DDevice8* dev, UINT viewport_w, UINT viewport_h);

    /* Call once before device is lost / reset. */
    void Release();

    /* Draw the HUD. Call from EndScene hook, before the real EndScene. */
    void Draw(IDirect3DDevice8* dev, const OverlayInfo& info);

private:
    void UpdateTexture(const OverlayInfo& info);
    void DrawQuad(IDirect3DDevice8* dev);

    IDirect3DTexture8* tex_     = nullptr;
    UINT               tex_w_   = 512;
    UINT               tex_h_   = 512;
    UINT               vp_w_    = 640;
    UINT               vp_h_    = 480;
};

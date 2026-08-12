#pragma once
#include "d3d8_iface.h"

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
    void Draw(IDirect3DDevice8* dev,
              float cam_x, float cam_y, float cam_z,
              bool freecam_on,
              bool fog_off, bool wireframe, bool hide_foliage,
              bool sim_paused);

private:
    void UpdateTexture(float cam_x, float cam_y, float cam_z,
                       bool freecam_on,
                       bool fog_off, bool wireframe, bool hide_foliage,
                       bool sim_paused);
    void DrawQuad(IDirect3DDevice8* dev);

    IDirect3DTexture8* tex_     = nullptr;
    UINT               tex_w_   = 256;
    UINT               tex_h_   = 160;
    UINT               vp_w_    = 640;
    UINT               vp_h_    = 480;
};

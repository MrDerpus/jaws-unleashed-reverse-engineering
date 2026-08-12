#pragma once
#include "d3d8_iface.h"
#include "overlay.h"
#include <stdio.h>

extern bool g_sim_paused;
extern void freeze_sim_time();
extern void thaw_sim_time();
extern DWORD (WINAPI *g_real_GetTickCount)();

inline void log_msg(const char* msg) {
    FILE* f = fopen("C:\\jaws_mod.log", "a");
    if (f) { fprintf(f, "%s\n", msg); fclose(f); }
}

/*
 * Wraps IDirect3DDevice8. Intercepts:
 *   SetTransform  — tracks view matrix, injects freecam override
 *   EndScene      — draws XYZ / status overlay before the real call
 */
class DeviceProxy : public IDirect3DDevice8 {
public:
    DeviceProxy(IDirect3DDevice8* real, UINT w, UINT h);

    /* ── IUnknown ─────────────────────────────────────────────────────────── */
    HRESULT __stdcall QueryInterface(REFIID riid, void** ppv) override;
    ULONG   __stdcall AddRef()  override;
    ULONG   __stdcall Release() override;

    /* ── Intercepted methods ─────────────────────────────────────────────── */
    HRESULT __stdcall SetTransform(D3DTRANSFORMSTATETYPE, const D3DMATRIX*) override;
    HRESULT __stdcall EndScene() override;
    HRESULT __stdcall Reset(D3DPRESENT_PARAMETERS*) override;

    /* ── Pass-through boilerplate ────────────────────────────────────────── */
    HRESULT __stdcall TestCooperativeLevel() override                              { log_once("TestCooperativeLevel"); return real_->TestCooperativeLevel(); }
    UINT    __stdcall GetAvailableTextureMem() override                            { log_once("GetAvailableTextureMem"); return real_->GetAvailableTextureMem(); }
    HRESULT __stdcall ResourceManagerDiscardBytes(DWORD b) override                { log_once("ResourceManagerDiscardBytes"); return real_->ResourceManagerDiscardBytes(b); }
    HRESULT __stdcall GetDirect3D(IDirect3D8** p) override                         { log_once("GetDirect3D"); return real_->GetDirect3D(p); }
    HRESULT __stdcall GetDeviceCaps(D3DCAPS8* p) override                          { log_once("GetDeviceCaps"); return real_->GetDeviceCaps(p); }
    HRESULT __stdcall GetDisplayMode(D3DDISPLAYMODE* p) override                   { log_once("GetDisplayMode"); return real_->GetDisplayMode(p); }
    HRESULT __stdcall GetCreationParameters(void* p) override                      { log_once("GetCreationParameters"); return real_->GetCreationParameters(p); }
    HRESULT __stdcall SetCursorProperties(UINT x,UINT y,IDirect3DSurface8* s) override { log_once("SetCursorProperties"); return real_->SetCursorProperties(x,y,s); }
    void    __stdcall SetCursorPosition(int x,int y,DWORD f) override              { log_once("SetCursorPosition"); real_->SetCursorPosition(x,y,f); }
    BOOL    __stdcall ShowCursor(BOOL b) override                                  { log_once("ShowCursor"); return real_->ShowCursor(b); }
    HRESULT __stdcall CreateAdditionalSwapChain(D3DPRESENT_PARAMETERS* p,IDirect3DSwapChain8** s) override { log_once("CreateAdditionalSwapChain"); return real_->CreateAdditionalSwapChain(p,s); }
    HRESULT __stdcall Present(const RECT* s,const RECT* d,HWND h,const RGNDATA* r) override { return real_->Present(s,d,h,r); }
    HRESULT __stdcall GetBackBuffer(UINT i,DWORD t,IDirect3DSurface8** p) override { return real_->GetBackBuffer(i,t,p); }
    HRESULT __stdcall GetRasterStatus(void* p) override                            { return real_->GetRasterStatus(p); }
    void    __stdcall SetGammaRamp(DWORD f,const D3DGAMMARAMP* r) override         { real_->SetGammaRamp(f,r); }
    void    __stdcall GetGammaRamp(D3DGAMMARAMP* r) override                       { real_->GetGammaRamp(r); }
    HRESULT __stdcall CreateTexture(UINT w,UINT h,UINT l,DWORD u,D3DFORMAT f,D3DPOOL p,IDirect3DTexture8** t) override { return real_->CreateTexture(w,h,l,u,f,p,t); }
    HRESULT __stdcall CreateVolumeTexture(UINT w,UINT h,UINT d,UINT l,DWORD u,D3DFORMAT f,D3DPOOL p,IDirect3DVolumeTexture8** t) override { return real_->CreateVolumeTexture(w,h,d,l,u,f,p,t); }
    HRESULT __stdcall CreateCubeTexture(UINT s,UINT l,DWORD u,D3DFORMAT f,D3DPOOL p,IDirect3DCubeTexture8** t) override { return real_->CreateCubeTexture(s,l,u,f,p,t); }
    HRESULT __stdcall CreateVertexBuffer(UINT s,DWORD u,DWORD fvf,D3DPOOL p,IDirect3DVertexBuffer8** b) override { return real_->CreateVertexBuffer(s,u,fvf,p,b); }
    HRESULT __stdcall CreateIndexBuffer(UINT s,DWORD u,D3DFORMAT f,D3DPOOL p,IDirect3DIndexBuffer8** b) override { return real_->CreateIndexBuffer(s,u,f,p,b); }
    HRESULT __stdcall CreateRenderTarget(UINT w,UINT h,D3DFORMAT f,D3DMULTISAMPLE_TYPE m,BOOL l,IDirect3DSurface8** s) override { return real_->CreateRenderTarget(w,h,f,m,l,s); }
    HRESULT __stdcall CreateDepthStencilSurface(UINT w,UINT h,D3DFORMAT f,D3DMULTISAMPLE_TYPE m,IDirect3DSurface8** s) override { return real_->CreateDepthStencilSurface(w,h,f,m,s); }
    HRESULT __stdcall CreateImageSurface(UINT w,UINT h,D3DFORMAT f,IDirect3DSurface8** s) override { return real_->CreateImageSurface(w,h,f,s); }
    HRESULT __stdcall CopyRects(IDirect3DSurface8* s,const RECT* r,UINT c,IDirect3DSurface8* d,const POINT* p) override { return real_->CopyRects(s,r,c,d,p); }
    HRESULT __stdcall UpdateTexture(IDirect3DBaseTexture8* s,IDirect3DBaseTexture8* d) override { return real_->UpdateTexture(s,d); }
    HRESULT __stdcall GetFrontBuffer(IDirect3DSurface8* s) override                { return real_->GetFrontBuffer(s); }
    HRESULT __stdcall SetRenderTarget(IDirect3DSurface8* rt,IDirect3DSurface8* ds) override;
    HRESULT __stdcall GetRenderTarget(IDirect3DSurface8** p) override              { return real_->GetRenderTarget(p); }
    HRESULT __stdcall GetDepthStencilSurface(IDirect3DSurface8** p) override       { return real_->GetDepthStencilSurface(p); }
    HRESULT __stdcall BeginScene() override {
        log_once_begin();
        return real_->BeginScene();
    }
    HRESULT __stdcall Clear(DWORD c,const D3DRECT* r,DWORD f,D3DCOLOR col,float z,DWORD s) override { return real_->Clear(c,r,f,col,z,s); }
    HRESULT __stdcall GetTransform(D3DTRANSFORMSTATETYPE t,D3DMATRIX* m) override  { return real_->GetTransform(t,m); }
    HRESULT __stdcall MultiplyTransform(D3DTRANSFORMSTATETYPE t,const D3DMATRIX* m) override { return real_->MultiplyTransform(t,m); }
    HRESULT __stdcall SetViewport(const D3DVIEWPORT8* v) override                  { return real_->SetViewport(v); }
    HRESULT __stdcall GetViewport(D3DVIEWPORT8* v) override                        { return real_->GetViewport(v); }
    HRESULT __stdcall SetMaterial(const D3DMATERIAL8* m) override                  { return real_->SetMaterial(m); }
    HRESULT __stdcall GetMaterial(D3DMATERIAL8* m) override                        { return real_->GetMaterial(m); }
    HRESULT __stdcall SetLight(DWORD i,const D3DLIGHT8* l) override                { return real_->SetLight(i,l); }
    HRESULT __stdcall GetLight(DWORD i,D3DLIGHT8* l) override                      { return real_->GetLight(i,l); }
    HRESULT __stdcall LightEnable(DWORD i,BOOL e) override                         { return real_->LightEnable(i,e); }
    HRESULT __stdcall GetLightEnable(DWORD i,BOOL* e) override                     { return real_->GetLightEnable(i,e); }
    HRESULT __stdcall SetClipPlane(DWORD i,const float* p) override                { return real_->SetClipPlane(i,p); }
    HRESULT __stdcall GetClipPlane(DWORD i,float* p) override                      { return real_->GetClipPlane(i,p); }
    HRESULT __stdcall SetRenderState(DWORD s,DWORD v) override;
    HRESULT __stdcall GetRenderState(DWORD s,DWORD* v) override                    { return real_->GetRenderState(s,v); }
    HRESULT __stdcall BeginStateBlock() override                                   { return real_->BeginStateBlock(); }
    HRESULT __stdcall EndStateBlock(DWORD* p) override                             { return real_->EndStateBlock(p); }
    HRESULT __stdcall ApplyStateBlock(DWORD h) override                            { return real_->ApplyStateBlock(h); }
    HRESULT __stdcall CaptureStateBlock(DWORD h) override                          { return real_->CaptureStateBlock(h); }
    HRESULT __stdcall DeleteStateBlock(DWORD h) override                           { return real_->DeleteStateBlock(h); }
    HRESULT __stdcall CreateStateBlock(D3DSTATEBLOCKTYPE t,DWORD* p) override      { return real_->CreateStateBlock(t,p); }
    HRESULT __stdcall SetClipStatus(const D3DCLIPSTATUS8* c) override              { return real_->SetClipStatus(c); }
    HRESULT __stdcall GetClipStatus(D3DCLIPSTATUS8* c) override                    { return real_->GetClipStatus(c); }
    HRESULT __stdcall GetTexture(DWORD s,IDirect3DBaseTexture8** t) override        { return real_->GetTexture(s,t); }
    HRESULT __stdcall SetTexture(DWORD s,IDirect3DBaseTexture8* t) override         { return real_->SetTexture(s,t); }
    HRESULT __stdcall GetTextureStageState(DWORD s,DWORD t,DWORD* v) override      { return real_->GetTextureStageState(s,t,v); }
    HRESULT __stdcall SetTextureStageState(DWORD s,DWORD t,DWORD v) override       { return real_->SetTextureStageState(s,t,v); }
    HRESULT __stdcall ValidateDevice(DWORD* p) override                            { return real_->ValidateDevice(p); }
    HRESULT __stdcall GetInfo(DWORD id,void* p,DWORD s) override                   { return real_->GetInfo(id,p,s); }
    HRESULT __stdcall SetPaletteEntries(UINT p,const PALETTEENTRY* e) override     { return real_->SetPaletteEntries(p,e); }
    HRESULT __stdcall GetPaletteEntries(UINT p,PALETTEENTRY* e) override           { return real_->GetPaletteEntries(p,e); }
    HRESULT __stdcall SetCurrentTexturePalette(UINT p) override                    { return real_->SetCurrentTexturePalette(p); }
    HRESULT __stdcall GetCurrentTexturePalette(UINT* p) override                   { return real_->GetCurrentTexturePalette(p); }
    HRESULT __stdcall DrawPrimitive(D3DPRIMITIVETYPE t,UINT s,UINT c) override     { return real_->DrawPrimitive(t,s,c); }
    HRESULT __stdcall DrawIndexedPrimitive(D3DPRIMITIVETYPE t,UINT mn,UINT mv,UINT sv,UINT pc) override { return real_->DrawIndexedPrimitive(t,mn,mv,sv,pc); }
    HRESULT __stdcall DrawPrimitiveUP(D3DPRIMITIVETYPE t,UINT c,const void* d,UINT s) override { return real_->DrawPrimitiveUP(t,c,d,s); }
    HRESULT __stdcall DrawIndexedPrimitiveUP(D3DPRIMITIVETYPE t,UINT mn,UINT mv,UINT pc,const void* id,D3DFORMAT idf,const void* vd,UINT vs) override { return real_->DrawIndexedPrimitiveUP(t,mn,mv,pc,id,idf,vd,vs); }
    HRESULT __stdcall ProcessVertices(UINT ss,UINT ds,UINT vc,IDirect3DVertexBuffer8* b,DWORD f) override { return real_->ProcessVertices(ss,ds,vc,b,f); }
    HRESULT __stdcall CreateVertexShader(const DWORD* d,const DWORD* c,DWORD* h,DWORD u) override { return real_->CreateVertexShader(d,c,h,u); }
    HRESULT __stdcall SetVertexShader(DWORD h) override                            { return real_->SetVertexShader(h); }
    HRESULT __stdcall GetVertexShader(DWORD* h) override                           { return real_->GetVertexShader(h); }
    HRESULT __stdcall DeleteVertexShader(DWORD h) override                         { return real_->DeleteVertexShader(h); }
    HRESULT __stdcall SetVertexShaderConstant(DWORD r,const void* d,DWORD c) override { return real_->SetVertexShaderConstant(r,d,c); }
    HRESULT __stdcall GetVertexShaderConstant(DWORD r,void* d,DWORD c) override    { return real_->GetVertexShaderConstant(r,d,c); }
    HRESULT __stdcall GetVertexShaderDeclaration(DWORD h,void* d,DWORD* s) override { return real_->GetVertexShaderDeclaration(h,d,s); }
    HRESULT __stdcall GetVertexShaderFunction(DWORD h,void* d,DWORD* s) override   { return real_->GetVertexShaderFunction(h,d,s); }
    HRESULT __stdcall SetStreamSource(UINT n,IDirect3DVertexBuffer8* b,UINT s) override { return real_->SetStreamSource(n,b,s); }
    HRESULT __stdcall GetStreamSource(UINT n,IDirect3DVertexBuffer8** b,UINT* s) override { return real_->GetStreamSource(n,b,s); }
    HRESULT __stdcall SetIndices(IDirect3DIndexBuffer8* b,UINT bv) override        { return real_->SetIndices(b,bv); }
    HRESULT __stdcall GetIndices(IDirect3DIndexBuffer8** b,UINT* bv) override      { return real_->GetIndices(b,bv); }
    HRESULT __stdcall CreatePixelShader(const DWORD* f,DWORD* h) override          { return real_->CreatePixelShader(f,h); }
    HRESULT __stdcall SetPixelShader(DWORD h) override                             { return real_->SetPixelShader(h); }
    HRESULT __stdcall GetPixelShader(DWORD* h) override                            { return real_->GetPixelShader(h); }
    HRESULT __stdcall DeletePixelShader(DWORD h) override                          { return real_->DeletePixelShader(h); }
    HRESULT __stdcall SetPixelShaderConstant(DWORD r,const void* d,DWORD c) override { return real_->SetPixelShaderConstant(r,d,c); }
    HRESULT __stdcall GetPixelShaderConstant(DWORD r,void* d,DWORD c) override     { return real_->GetPixelShaderConstant(r,d,c); }
    HRESULT __stdcall GetPixelShaderFunction(DWORD h,void* d,DWORD* s) override    { return real_->GetPixelShaderFunction(h,d,s); }
    HRESULT __stdcall DrawRectPatch(UINT h,const float* n,const void* i) override  { return real_->DrawRectPatch(h,n,i); }
    HRESULT __stdcall DrawTriPatch(UINT h,const float* n,const void* i) override   { return real_->DrawTriPatch(h,n,i); }
    HRESULT __stdcall DeletePatch(UINT h) override                                 { return real_->DeletePatch(h); }

private:
    void UpdateFreecam();
    void BuildViewMatrix(D3DMATRIX& out) const;
    void ExtractCamPos(const D3DMATRIX& v);
    void TakeScreenshot();

    IDirect3DDevice8* real_    = nullptr;
    ULONG             refs_    = 1;

    /* Overlay */
    Overlay           overlay_;
    UINT              vp_w_    = 640;
    UINT              vp_h_    = 480;

    /* Render-target tracking -- lets us tell the primary backbuffer pass
     * apart from secondary passes (water reflection/refraction etc) that
     * render to an off-screen texture first, each with their own camera. */
    IDirect3DSurface8* backbuffer_surf_    = nullptr;
    bool                on_primary_target_ = true;

    /* Camera state extracted from the view matrix */
    float cam_x_ = 0, cam_y_ = 0, cam_z_ = 0;
    float cam_hx_[5] = {}, cam_hy_[5] = {}, cam_hz_[5] = {};
    float cam_hyaw_[5] = {}, cam_hpitch_[5] = {};
    int   cam_hidx_ = 0;

    /* Freecam */
    bool  freecam_       = false;
    float fc_x_          = 0, fc_y_ = 0, fc_z_ = 0;
    float fc_yaw_        = 0;   /* radians */
    float fc_pitch_      = 0;
    DWORD fc_last_real_ms_ = 0;
    bool  fc_time_init_    = false;

    /* Simulation pause — freezes game time while freecam remains live */
    bool  sim_paused_ = false;

    /* Render state overrides */
    bool  fog_off_          = false;
    bool  wireframe_        = false;
    bool  hide_foliage_     = false;
    bool  alpha_test_enabled_ = false; /* tracks D3DRS_ALPHATESTENABLE for foliage hide */

    /* Screenshot counter */
    int   screenshot_idx_ = 0;

    /* Input debounce */
    bool  freecam_prev_   = false;
    bool  f3_prev_        = false;
    bool  f4_prev_        = false;
    bool  f5_prev_        = false;
    bool  f6_prev_        = false;
    bool  f7_prev_        = false;
    bool  f9_prev_        = false;
    bool  endscene_logged_   = false;
    bool  beginscene_logged_ = false;
    int   call_count_        = 0;
    void  log_once(const char* method) {
        if (call_count_ < 30) {
            char buf[64]; snprintf(buf, sizeof(buf), "[jaws_mod]   call[%d] %s", call_count_, method);
            log_msg(buf); ++call_count_;
        }
    }
    void  log_once_begin() {
        if (!beginscene_logged_) {
            log_msg("[jaws_mod] BeginScene first call — init overlay");
            overlay_.Init(real_, vp_w_, vp_h_);
            beginscene_logged_ = true;
        }
    }
    POINT last_mouse_ = {};
    bool  mouse_captured_ = false;
};

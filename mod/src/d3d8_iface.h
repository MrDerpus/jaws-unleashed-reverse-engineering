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
 * Minimal hand-rolled Direct3D 8 interface definitions.
 * Avoids needing the DXSDK or wine-dev headers — defines only what we use.
 */
#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

/* ── D3D types ───────────────────────────────────────────────────────────── */
typedef DWORD D3DCOLOR;
typedef DWORD D3DFORMAT;
typedef DWORD D3DRESOURCETYPE;
typedef DWORD D3DMULTISAMPLE_TYPE;
typedef DWORD D3DPOOL;
typedef DWORD D3DPRIMITIVETYPE;
typedef DWORD D3DSTATEBLOCKTYPE;

#define D3DADAPTER_DEFAULT 0
#define D3DDEVTYPE_HAL     1
#define D3DCREATE_SOFTWARE_VERTEXPROCESSING 0x00000020
#define D3DCREATE_HARDWARE_VERTEXPROCESSING 0x00000040

typedef enum _D3DTRANSFORMSTATETYPE {
    D3DTS_VIEW       = 2,
    D3DTS_PROJECTION = 3,
    D3DTS_WORLD      = 256,
} D3DTRANSFORMSTATETYPE;

typedef struct _D3DMATRIX {
    union {
        struct { float _11,_12,_13,_14, _21,_22,_23,_24,
                       _31,_32,_33,_34, _41,_42,_43,_44; };
        float m[4][4];
    };
} D3DMATRIX;

typedef struct _D3DVECTOR { float x, y, z; } D3DVECTOR;

typedef struct _D3DRECT { LONG x1, y1, x2, y2; } D3DRECT;

typedef struct _D3DVIEWPORT8 {
    DWORD X, Y, Width, Height;
    float MinZ, MaxZ;
} D3DVIEWPORT8;

typedef struct _D3DDISPLAYMODE {
    UINT Width, Height, RefreshRate;
    D3DFORMAT Format;
} D3DDISPLAYMODE;

typedef struct _D3DCAPS8 { BYTE _pad[512]; } D3DCAPS8;

typedef struct _D3DPRESENT_PARAMETERS {
    UINT  BackBufferWidth, BackBufferHeight;
    D3DFORMAT BackBufferFormat;
    UINT  BackBufferCount;
    D3DMULTISAMPLE_TYPE MultiSampleType;
    BOOL  SwapEffect;             /* actually D3DSWAPEFFECT */
    HWND  hDeviceWindow;
    BOOL  Windowed;
    BOOL  EnableAutoDepthStencil;
    D3DFORMAT AutoDepthStencilFormat;
    DWORD Flags;
    UINT  FullScreen_RefreshRateInHz;
    UINT  FullScreen_PresentationInterval;
} D3DPRESENT_PARAMETERS;

typedef struct _D3DSURFACE_DESC {
    D3DFORMAT Format;
    D3DRESOURCETYPE Type;
    DWORD Usage;
    D3DPOOL Pool;
    UINT Size;
    D3DMULTISAMPLE_TYPE MultiSampleType;
    UINT Width, Height;
} D3DSURFACE_DESC;

typedef struct _D3DLOCKED_RECT { INT Pitch; void* pBits; } D3DLOCKED_RECT;
typedef struct _D3DLOCKED_BOX  { INT RowPitch, SlicePitch; void* pBits; } D3DLOCKED_BOX;
typedef struct _D3DRANGE        { UINT Offset, Size; } D3DRANGE;
typedef struct _D3DBOX { UINT Left,Top,Right,Bottom,Front,Back; } D3DBOX;
typedef struct _D3DLIGHT8       { BYTE _pad[256]; } D3DLIGHT8;
typedef struct _D3DMATERIAL8    { BYTE _pad[80];  } D3DMATERIAL8;
typedef struct _D3DCLIPSTATUS8  { DWORD ClipUnion, ClipIntersection; } D3DCLIPSTATUS8;
typedef struct _D3DINDEXBUFFER_DESC { D3DFORMAT Format; D3DRESOURCETYPE Type; DWORD Usage; D3DPOOL Pool; UINT Size; } D3DINDEXBUFFER_DESC;
typedef struct _D3DVERTEXBUFFER_DESC { D3DFORMAT Format; D3DRESOURCETYPE Type; DWORD Usage; D3DPOOL Pool; DWORD FVF; UINT Size; } D3DVERTEXBUFFER_DESC;
typedef struct _D3DGAMMARAMP { WORD red[256], green[256], blue[256]; } D3DGAMMARAMP;

/* ── COM IUnknown ────────────────────────────────────────────────────────── */
struct IUnknown {
    virtual HRESULT __stdcall QueryInterface(REFIID, void**) = 0;
    virtual ULONG   __stdcall AddRef()  = 0;
    virtual ULONG   __stdcall Release() = 0;
};

/* ── Forward declarations ────────────────────────────────────────────────── */
struct IDirect3D8;
struct IDirect3DDevice8;
struct IDirect3DSwapChain8;
struct IDirect3DResource8;
struct IDirect3DBaseTexture8;
struct IDirect3DTexture8;
struct IDirect3DVolumeTexture8;
struct IDirect3DCubeTexture8;
struct IDirect3DVertexBuffer8;
struct IDirect3DIndexBuffer8;
struct IDirect3DSurface8;
struct IDirect3DVolume8;

/* ── IDirect3DResource8 ──────────────────────────────────────────────────── */
struct IDirect3DResource8 : IUnknown {
    virtual HRESULT __stdcall GetDevice(IDirect3DDevice8**) = 0;
    virtual HRESULT __stdcall SetPrivateData(REFIID,const void*,DWORD,DWORD) = 0;
    virtual HRESULT __stdcall GetPrivateData(REFIID,void*,DWORD*) = 0;
    virtual HRESULT __stdcall FreePrivateData(REFIID) = 0;
    virtual DWORD   __stdcall SetPriority(DWORD) = 0;
    virtual DWORD   __stdcall GetPriority() = 0;
    virtual void    __stdcall PreLoad() = 0;
    virtual D3DRESOURCETYPE __stdcall GetType() = 0;
};

/* ── IDirect3DBaseTexture8 ───────────────────────────────────────────────── */
struct IDirect3DBaseTexture8 : IDirect3DResource8 {
    virtual DWORD   __stdcall SetLOD(DWORD) = 0;
    virtual DWORD   __stdcall GetLOD() = 0;
    virtual DWORD   __stdcall GetLevelCount() = 0;
};

/* ── IDirect3DTexture8 ───────────────────────────────────────────────────── */
struct IDirect3DTexture8 : IDirect3DBaseTexture8 {
    virtual HRESULT __stdcall GetLevelDesc(UINT,D3DSURFACE_DESC*) = 0;
    virtual HRESULT __stdcall GetSurfaceLevel(UINT,IDirect3DSurface8**) = 0;
    virtual HRESULT __stdcall LockRect(UINT,D3DLOCKED_RECT*,const RECT*,DWORD) = 0;
    virtual HRESULT __stdcall UnlockRect(UINT) = 0;
    virtual HRESULT __stdcall AddDirtyRect(const RECT*) = 0;
};

/* ── IDirect3DSurface8 ───────────────────────────────────────────────────── */
struct IDirect3DSurface8 : IUnknown {
    virtual HRESULT __stdcall GetDevice(IDirect3DDevice8**) = 0;
    virtual HRESULT __stdcall SetPrivateData(REFIID,const void*,DWORD,DWORD) = 0;
    virtual HRESULT __stdcall GetPrivateData(REFIID,void*,DWORD*) = 0;
    virtual HRESULT __stdcall FreePrivateData(REFIID) = 0;
    virtual HRESULT __stdcall GetContainer(REFIID,void**) = 0;
    virtual HRESULT __stdcall GetDesc(D3DSURFACE_DESC*) = 0;
    virtual HRESULT __stdcall LockRect(D3DLOCKED_RECT*,const RECT*,DWORD) = 0;
    virtual HRESULT __stdcall UnlockRect() = 0;
};

/* ── IDirect3DVertexBuffer8 ──────────────────────────────────────────────── */
struct IDirect3DVertexBuffer8 : IDirect3DResource8 {
    virtual HRESULT __stdcall Lock(UINT,UINT,BYTE**,DWORD) = 0;
    virtual HRESULT __stdcall Unlock() = 0;
    virtual HRESULT __stdcall GetDesc(D3DVERTEXBUFFER_DESC*) = 0;
};

/* ── IDirect3DIndexBuffer8 ───────────────────────────────────────────────── */
struct IDirect3DIndexBuffer8 : IDirect3DResource8 {
    virtual HRESULT __stdcall Lock(UINT,UINT,BYTE**,DWORD) = 0;
    virtual HRESULT __stdcall Unlock() = 0;
    virtual HRESULT __stdcall GetDesc(D3DINDEXBUFFER_DESC*) = 0;
};

/* ── IDirect3DSwapChain8 ─────────────────────────────────────────────────── */
struct IDirect3DSwapChain8 : IUnknown {
    virtual HRESULT __stdcall Present(const RECT*,const RECT*,HWND,const RGNDATA*) = 0;
    virtual HRESULT __stdcall GetBackBuffer(UINT,DWORD,IDirect3DSurface8**) = 0;
};

/* ── IDirect3DDevice8 ────────────────────────────────────────────────────── */
struct IDirect3DDevice8 : IUnknown {
    virtual HRESULT __stdcall TestCooperativeLevel() = 0;
    virtual UINT    __stdcall GetAvailableTextureMem() = 0;
    virtual HRESULT __stdcall ResourceManagerDiscardBytes(DWORD) = 0;
    virtual HRESULT __stdcall GetDirect3D(IDirect3D8**) = 0;
    virtual HRESULT __stdcall GetDeviceCaps(D3DCAPS8*) = 0;
    virtual HRESULT __stdcall GetDisplayMode(D3DDISPLAYMODE*) = 0;
    virtual HRESULT __stdcall GetCreationParameters(void*) = 0;
    virtual HRESULT __stdcall SetCursorProperties(UINT,UINT,IDirect3DSurface8*) = 0;
    virtual void    __stdcall SetCursorPosition(int,int,DWORD) = 0;
    virtual BOOL    __stdcall ShowCursor(BOOL) = 0;
    virtual HRESULT __stdcall CreateAdditionalSwapChain(D3DPRESENT_PARAMETERS*,IDirect3DSwapChain8**) = 0;
    virtual HRESULT __stdcall Reset(D3DPRESENT_PARAMETERS*) = 0;
    virtual HRESULT __stdcall Present(const RECT*,const RECT*,HWND,const RGNDATA*) = 0;
    virtual HRESULT __stdcall GetBackBuffer(UINT,DWORD,IDirect3DSurface8**) = 0;
    virtual HRESULT __stdcall GetRasterStatus(void*) = 0;
    virtual void    __stdcall SetGammaRamp(DWORD,const D3DGAMMARAMP*) = 0;
    virtual void    __stdcall GetGammaRamp(D3DGAMMARAMP*) = 0;
    virtual HRESULT __stdcall CreateTexture(UINT,UINT,UINT,DWORD,D3DFORMAT,D3DPOOL,IDirect3DTexture8**) = 0;
    virtual HRESULT __stdcall CreateVolumeTexture(UINT,UINT,UINT,UINT,DWORD,D3DFORMAT,D3DPOOL,IDirect3DVolumeTexture8**) = 0;
    virtual HRESULT __stdcall CreateCubeTexture(UINT,UINT,DWORD,D3DFORMAT,D3DPOOL,IDirect3DCubeTexture8**) = 0;
    virtual HRESULT __stdcall CreateVertexBuffer(UINT,DWORD,DWORD,D3DPOOL,IDirect3DVertexBuffer8**) = 0;
    virtual HRESULT __stdcall CreateIndexBuffer(UINT,DWORD,D3DFORMAT,D3DPOOL,IDirect3DIndexBuffer8**) = 0;
    virtual HRESULT __stdcall CreateRenderTarget(UINT,UINT,D3DFORMAT,D3DMULTISAMPLE_TYPE,BOOL,IDirect3DSurface8**) = 0;
    virtual HRESULT __stdcall CreateDepthStencilSurface(UINT,UINT,D3DFORMAT,D3DMULTISAMPLE_TYPE,IDirect3DSurface8**) = 0;
    virtual HRESULT __stdcall CreateImageSurface(UINT,UINT,D3DFORMAT,IDirect3DSurface8**) = 0;
    virtual HRESULT __stdcall CopyRects(IDirect3DSurface8*,const RECT*,UINT,IDirect3DSurface8*,const POINT*) = 0;
    virtual HRESULT __stdcall UpdateTexture(IDirect3DBaseTexture8*,IDirect3DBaseTexture8*) = 0;
    virtual HRESULT __stdcall GetFrontBuffer(IDirect3DSurface8*) = 0;
    virtual HRESULT __stdcall SetRenderTarget(IDirect3DSurface8*,IDirect3DSurface8*) = 0;
    virtual HRESULT __stdcall GetRenderTarget(IDirect3DSurface8**) = 0;
    virtual HRESULT __stdcall GetDepthStencilSurface(IDirect3DSurface8**) = 0;
    virtual HRESULT __stdcall BeginScene() = 0;
    virtual HRESULT __stdcall EndScene() = 0;
    virtual HRESULT __stdcall Clear(DWORD,const D3DRECT*,DWORD,D3DCOLOR,float,DWORD) = 0;
    virtual HRESULT __stdcall SetTransform(D3DTRANSFORMSTATETYPE,const D3DMATRIX*) = 0;
    virtual HRESULT __stdcall GetTransform(D3DTRANSFORMSTATETYPE,D3DMATRIX*) = 0;
    virtual HRESULT __stdcall MultiplyTransform(D3DTRANSFORMSTATETYPE,const D3DMATRIX*) = 0;
    virtual HRESULT __stdcall SetViewport(const D3DVIEWPORT8*) = 0;
    virtual HRESULT __stdcall GetViewport(D3DVIEWPORT8*) = 0;
    virtual HRESULT __stdcall SetMaterial(const D3DMATERIAL8*) = 0;
    virtual HRESULT __stdcall GetMaterial(D3DMATERIAL8*) = 0;
    virtual HRESULT __stdcall SetLight(DWORD,const D3DLIGHT8*) = 0;
    virtual HRESULT __stdcall GetLight(DWORD,D3DLIGHT8*) = 0;
    virtual HRESULT __stdcall LightEnable(DWORD,BOOL) = 0;
    virtual HRESULT __stdcall GetLightEnable(DWORD,BOOL*) = 0;
    virtual HRESULT __stdcall SetClipPlane(DWORD,const float*) = 0;
    virtual HRESULT __stdcall GetClipPlane(DWORD,float*) = 0;
    virtual HRESULT __stdcall SetRenderState(DWORD,DWORD) = 0;
    virtual HRESULT __stdcall GetRenderState(DWORD,DWORD*) = 0;
    virtual HRESULT __stdcall BeginStateBlock() = 0;
    virtual HRESULT __stdcall EndStateBlock(DWORD*) = 0;
    virtual HRESULT __stdcall ApplyStateBlock(DWORD) = 0;
    virtual HRESULT __stdcall CaptureStateBlock(DWORD) = 0;
    virtual HRESULT __stdcall DeleteStateBlock(DWORD) = 0;
    virtual HRESULT __stdcall CreateStateBlock(D3DSTATEBLOCKTYPE,DWORD*) = 0;
    virtual HRESULT __stdcall SetClipStatus(const D3DCLIPSTATUS8*) = 0;
    virtual HRESULT __stdcall GetClipStatus(D3DCLIPSTATUS8*) = 0;
    virtual HRESULT __stdcall GetTexture(DWORD,IDirect3DBaseTexture8**) = 0;
    virtual HRESULT __stdcall SetTexture(DWORD,IDirect3DBaseTexture8*) = 0;
    virtual HRESULT __stdcall GetTextureStageState(DWORD,DWORD,DWORD*) = 0;
    virtual HRESULT __stdcall SetTextureStageState(DWORD,DWORD,DWORD) = 0;
    virtual HRESULT __stdcall ValidateDevice(DWORD*) = 0;
    virtual HRESULT __stdcall GetInfo(DWORD,void*,DWORD) = 0;
    virtual HRESULT __stdcall SetPaletteEntries(UINT,const PALETTEENTRY*) = 0;
    virtual HRESULT __stdcall GetPaletteEntries(UINT,PALETTEENTRY*) = 0;
    virtual HRESULT __stdcall SetCurrentTexturePalette(UINT) = 0;
    virtual HRESULT __stdcall GetCurrentTexturePalette(UINT*) = 0;
    virtual HRESULT __stdcall DrawPrimitive(D3DPRIMITIVETYPE,UINT,UINT) = 0;
    virtual HRESULT __stdcall DrawIndexedPrimitive(D3DPRIMITIVETYPE,UINT,UINT,UINT,UINT) = 0;
    virtual HRESULT __stdcall DrawPrimitiveUP(D3DPRIMITIVETYPE,UINT,const void*,UINT) = 0;
    virtual HRESULT __stdcall DrawIndexedPrimitiveUP(D3DPRIMITIVETYPE,UINT,UINT,UINT,const void*,D3DFORMAT,const void*,UINT) = 0;
    virtual HRESULT __stdcall ProcessVertices(UINT,UINT,UINT,IDirect3DVertexBuffer8*,DWORD) = 0;
    virtual HRESULT __stdcall CreateVertexShader(const DWORD*,const DWORD*,DWORD*,DWORD) = 0;
    virtual HRESULT __stdcall SetVertexShader(DWORD) = 0;
    virtual HRESULT __stdcall GetVertexShader(DWORD*) = 0;
    virtual HRESULT __stdcall DeleteVertexShader(DWORD) = 0;
    virtual HRESULT __stdcall SetVertexShaderConstant(DWORD,const void*,DWORD) = 0;
    virtual HRESULT __stdcall GetVertexShaderConstant(DWORD,void*,DWORD) = 0;
    virtual HRESULT __stdcall GetVertexShaderDeclaration(DWORD,void*,DWORD*) = 0;
    virtual HRESULT __stdcall GetVertexShaderFunction(DWORD,void*,DWORD*) = 0;
    virtual HRESULT __stdcall SetStreamSource(UINT,IDirect3DVertexBuffer8*,UINT) = 0;
    virtual HRESULT __stdcall GetStreamSource(UINT,IDirect3DVertexBuffer8**,UINT*) = 0;
    virtual HRESULT __stdcall SetIndices(IDirect3DIndexBuffer8*,UINT) = 0;
    virtual HRESULT __stdcall GetIndices(IDirect3DIndexBuffer8**,UINT*) = 0;
    virtual HRESULT __stdcall CreatePixelShader(const DWORD*,DWORD*) = 0;
    virtual HRESULT __stdcall SetPixelShader(DWORD) = 0;
    virtual HRESULT __stdcall GetPixelShader(DWORD*) = 0;
    virtual HRESULT __stdcall DeletePixelShader(DWORD) = 0;
    virtual HRESULT __stdcall SetPixelShaderConstant(DWORD,const void*,DWORD) = 0;
    virtual HRESULT __stdcall GetPixelShaderConstant(DWORD,void*,DWORD) = 0;
    virtual HRESULT __stdcall GetPixelShaderFunction(DWORD,void*,DWORD*) = 0;
    virtual HRESULT __stdcall DrawRectPatch(UINT,const float*,const void*) = 0;
    virtual HRESULT __stdcall DrawTriPatch(UINT,const float*,const void*) = 0;
    virtual HRESULT __stdcall DeletePatch(UINT) = 0;
};

/* ── IDirect3D8 ──────────────────────────────────────────────────────────── */
struct IDirect3D8 : IUnknown {
    virtual HRESULT __stdcall RegisterSoftwareDevice(void*) = 0;
    virtual UINT    __stdcall GetAdapterCount() = 0;
    virtual HRESULT __stdcall GetAdapterIdentifier(UINT,DWORD,void*) = 0;
    virtual UINT    __stdcall GetAdapterModeCount(UINT) = 0;
    virtual HRESULT __stdcall EnumAdapterModes(UINT,UINT,D3DDISPLAYMODE*) = 0;
    virtual HRESULT __stdcall GetAdapterDisplayMode(UINT,D3DDISPLAYMODE*) = 0;
    virtual HRESULT __stdcall CheckDeviceType(UINT,DWORD,D3DFORMAT,D3DFORMAT,BOOL) = 0;
    virtual HRESULT __stdcall CheckDeviceFormat(UINT,DWORD,D3DFORMAT,DWORD,D3DRESOURCETYPE,D3DFORMAT) = 0;
    virtual HRESULT __stdcall CheckDeviceMultiSampleType(UINT,DWORD,D3DFORMAT,BOOL,D3DMULTISAMPLE_TYPE) = 0;
    virtual HRESULT __stdcall CheckDepthStencilMatch(UINT,DWORD,D3DFORMAT,D3DFORMAT,D3DFORMAT) = 0;
    virtual HRESULT __stdcall GetDeviceCaps(UINT,DWORD,D3DCAPS8*) = 0;
    virtual HMONITOR __stdcall GetAdapterMonitor(UINT) = 0;
    virtual HRESULT __stdcall CreateDevice(UINT,DWORD,HWND,DWORD,D3DPRESENT_PARAMETERS*,IDirect3DDevice8**) = 0;
};

typedef IDirect3D8* (WINAPI *PFN_Direct3DCreate8)(UINT);

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
 * winmm.dll proxy — injection point for the Jaws Unleashed mod.
 *
 * Strategy:
 *   1. Forward the four WINMM exports the game actually uses to the real winmm.dll.
 *      (winmm is fully implemented in Wine — no stub issue unlike dinput8.)
 *   2. In DllMain, patch Jaws.exe's IAT to redirect Direct3DCreate8 → our hook.
 *   3. Our hook wraps the DXVK device in DeviceProxy for freecam/overlay/god mode.
 *
 * Deploy: drop winmm.dll next to Jaws.exe (remove old dinput8.dll from game dir).
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "d3d8_iface.h"
#include "device_proxy.h"

/* ── Real WINMM forwarding ───────────────────────────────────────────────── */

static HMODULE g_real_winmm = nullptr;

static HMODULE get_winmm() {
    if (!g_real_winmm) {
        char path[MAX_PATH];
        GetSystemDirectoryA(path, MAX_PATH);
        strcat(path, "\\winmm.dll");
        g_real_winmm = LoadLibraryA(path);
    }
    return g_real_winmm;
}

extern "C" {

__declspec(dllexport) UINT WINAPI joyGetNumDevs(void)
{
    auto fn = (UINT (WINAPI*)())GetProcAddress(get_winmm(), "joyGetNumDevs");
    return fn ? fn() : 0;
}

__declspec(dllexport) UINT WINAPI joyGetDevCapsA(UINT id, void* caps, UINT sz)
{
    auto fn = (UINT (WINAPI*)(UINT, void*, UINT))GetProcAddress(get_winmm(), "joyGetDevCapsA");
    return fn ? fn(id, caps, sz) : 1; /* JOYERR_NOCANDO */
}

__declspec(dllexport) UINT WINAPI joyGetPosEx(UINT id, void* info)
{
    auto fn = (UINT (WINAPI*)(UINT, void*))GetProcAddress(get_winmm(), "joyGetPosEx");
    return fn ? fn(id, info) : 1;
}

__declspec(dllexport) DWORD WINAPI mciSendCommandA(DWORD id, UINT msg, DWORD p1, DWORD p2)
{
    auto fn = (DWORD (WINAPI*)(DWORD, UINT, DWORD, DWORD))GetProcAddress(get_winmm(), "mciSendCommandA");
    return fn ? fn(id, msg, p1, p2) : 1;
}

} /* extern "C" */

/* ── Exception observer ─────────────────────────────────────────────────── */

static LONG WINAPI OurVEH(EXCEPTION_POINTERS* ep)
{
    DWORD code = ep->ExceptionRecord->ExceptionCode;
    if (code == EXCEPTION_BREAKPOINT || code == EXCEPTION_SINGLE_STEP)
        return EXCEPTION_CONTINUE_SEARCH;
    char buf[128];
    snprintf(buf, sizeof(buf),
        "[jaws_mod] VEH code=0x%08lX addr=0x%08lX tid=%lu",
        (unsigned long)code,
        (unsigned long)ep->ExceptionRecord->ExceptionAddress,
        (unsigned long)GetCurrentThreadId());
    log_msg(buf);
    return EXCEPTION_CONTINUE_SEARCH;
}

/* ── IAT patch ───────────────────────────────────────────────────────────── */

static void PatchIAT(HMODULE module, const char* target_dll,
                     const char* func_name, void* hook)
{
    auto base = (BYTE*)module;
    auto dos  = (PIMAGE_DOS_HEADER)base;
    auto nt   = (PIMAGE_NT_HEADERS)(base + dos->e_lfanew);
    auto imp  = (PIMAGE_IMPORT_DESCRIPTOR)(base +
        nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress);

    for (; imp->Name; ++imp) {
        const char* dll = (const char*)(base + imp->Name);
        if (_stricmp(dll, target_dll) != 0) continue;

        auto thunk = (PIMAGE_THUNK_DATA)(base + imp->FirstThunk);
        auto orig  = (PIMAGE_THUNK_DATA)(base + imp->OriginalFirstThunk);

        for (; thunk->u1.Function; ++thunk, ++orig) {
            if (IMAGE_SNAP_BY_ORDINAL(orig->u1.Ordinal)) continue;
            auto ibn = (PIMAGE_IMPORT_BY_NAME)(base + orig->u1.AddressOfData);
            if (strcmp((char*)ibn->Name, func_name) != 0) continue;

            DWORD old_prot;
            VirtualProtect(&thunk->u1.Function, sizeof(void*), PAGE_READWRITE, &old_prot);
            thunk->u1.Function = (ULONG_PTR)hook;
            VirtualProtect(&thunk->u1.Function, sizeof(void*), old_prot, &old_prot);

            char msg[128];
            snprintf(msg, sizeof(msg), "[jaws_mod] IAT patched: %s!%s", target_dll, func_name);
            log_msg(msg);
            return;
        }
    }
    log_msg("[jaws_mod] WARNING: IAT entry not found");
}

/* ── D3D8Proxy ───────────────────────────────────────────────────────────── */

class D3D8Proxy : public IDirect3D8 {
public:
    explicit D3D8Proxy(IDirect3D8* real) : real_(real), refs_(1) {}

    HRESULT __stdcall QueryInterface(REFIID r, void** p) override { return real_->QueryInterface(r,p); }
    ULONG   __stdcall AddRef()  override { real_->AddRef();  return ++refs_; }
    ULONG   __stdcall Release() override {
        real_->Release();
        if (--refs_ == 0) { delete this; return 0; }
        return refs_;
    }

    HRESULT __stdcall RegisterSoftwareDevice(void* p) override                         { return real_->RegisterSoftwareDevice(p); }
    UINT    __stdcall GetAdapterCount() override                                        { return real_->GetAdapterCount(); }
    HRESULT __stdcall GetAdapterIdentifier(UINT a,DWORD f,void* p) override            { return real_->GetAdapterIdentifier(a,f,p); }
    UINT    __stdcall GetAdapterModeCount(UINT a) override                              { return real_->GetAdapterModeCount(a); }
    HRESULT __stdcall EnumAdapterModes(UINT a,UINT m,D3DDISPLAYMODE* p) override       { return real_->EnumAdapterModes(a,m,p); }
    HRESULT __stdcall GetAdapterDisplayMode(UINT a,D3DDISPLAYMODE* p) override         { return real_->GetAdapterDisplayMode(a,p); }
    HRESULT __stdcall CheckDeviceType(UINT a,DWORD t,D3DFORMAT af,D3DFORMAT bf,BOOL w) override { return real_->CheckDeviceType(a,t,af,bf,w); }
    HRESULT __stdcall CheckDeviceFormat(UINT a,DWORD t,D3DFORMAT af,DWORD u,D3DRESOURCETYPE r,D3DFORMAT cf) override { return real_->CheckDeviceFormat(a,t,af,u,r,cf); }
    HRESULT __stdcall CheckDeviceMultiSampleType(UINT a,DWORD t,D3DFORMAT f,BOOL w,D3DMULTISAMPLE_TYPE m) override { return real_->CheckDeviceMultiSampleType(a,t,f,w,m); }
    HRESULT __stdcall CheckDepthStencilMatch(UINT a,DWORD t,D3DFORMAT af,D3DFORMAT rf,D3DFORMAT df) override { return real_->CheckDepthStencilMatch(a,t,af,rf,df); }
    HRESULT __stdcall GetDeviceCaps(UINT a,DWORD t,D3DCAPS8* c) override               { return real_->GetDeviceCaps(a,t,c); }
    HMONITOR __stdcall GetAdapterMonitor(UINT a) override                              { return real_->GetAdapterMonitor(a); }

    HRESULT __stdcall CreateDevice(UINT adapter, DWORD devtype, HWND hwnd,
                                   DWORD flags, D3DPRESENT_PARAMETERS* pp,
                                   IDirect3DDevice8** ppdev) override
    {
        log_msg("[jaws_mod] CreateDevice called");
        IDirect3DDevice8* real_dev = nullptr;
        HRESULT hr = real_->CreateDevice(adapter, devtype, hwnd, flags, pp, &real_dev);
        if (SUCCEEDED(hr) && real_dev) {
            char buf[128];
            snprintf(buf, sizeof(buf), "[jaws_mod] DeviceProxy created %ux%u",
                     pp->BackBufferWidth, pp->BackBufferHeight);
            log_msg(buf);
            *ppdev = new DeviceProxy(real_dev,
                                     pp->BackBufferWidth  ? pp->BackBufferWidth  : 640,
                                     pp->BackBufferHeight ? pp->BackBufferHeight : 480);
        } else {
            char buf[64];
            snprintf(buf, sizeof(buf), "[jaws_mod] CreateDevice FAILED hr=0x%08lX", (unsigned long)hr);
            log_msg(buf);
        }
        return hr;
    }

private:
    IDirect3D8* real_;
    ULONG       refs_;
};

/* ── Our Direct3DCreate8 hook ────────────────────────────────────────────── */

static IDirect3D8* WINAPI OurDirect3DCreate8(UINT sdk_version)
{
    log_msg("[jaws_mod] Direct3DCreate8 hooked");
    HMODULE d3d8 = GetModuleHandleA("d3d8.dll");
    if (!d3d8) { log_msg("[jaws_mod] ERROR: d3d8.dll not loaded"); return nullptr; }

    auto real_fn = (PFN_Direct3DCreate8)GetProcAddress(d3d8, "Direct3DCreate8");
    if (!real_fn) { log_msg("[jaws_mod] ERROR: Direct3DCreate8 not found"); return nullptr; }

    IDirect3D8* real = real_fn(sdk_version);
    if (!real)  { log_msg("[jaws_mod] ERROR: real Direct3DCreate8 returned null"); return nullptr; }

    log_msg("[jaws_mod] D3D8Proxy wrapping");
    return new D3D8Proxy(real);
}

/* ── DllMain ─────────────────────────────────────────────────────────────── */

BOOL WINAPI DllMain(HINSTANCE hInst, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hInst);
        AddVectoredExceptionHandler(1, OurVEH);
        log_msg("[jaws_mod] winmm proxy loaded");

        /* Pre-load real winmm now so forwarded calls never block */
        get_winmm();
        if (g_real_winmm) log_msg("[jaws_mod] real winmm.dll loaded");
        else              log_msg("[jaws_mod] WARNING: real winmm.dll not found");

        /* Patch Jaws.exe's IAT to intercept Direct3DCreate8 */
        PatchIAT(GetModuleHandleA(nullptr), "d3d8.dll", "Direct3DCreate8",
                 (void*)OurDirect3DCreate8);
    }
    return TRUE;
}

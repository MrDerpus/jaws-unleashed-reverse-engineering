/*
 * dinput8.dll proxy — injection point for the Jaws Unleashed mod.
 *
 * Strategy:
 *   1. Forward the one DINPUT8 export (DirectInput8Create) to the real DLL.
 *   2. In DllMain, patch Jaws.exe's Import Address Table to redirect
 *      Direct3DCreate8 → OurDirect3DCreate8.
 *   3. When the game calls Direct3DCreate8, wrap the returned device in
 *      DeviceProxy for freecam, XYZ overlay, and god mode.
 *
 * Deploy: drop dinput8.dll next to Jaws.exe.
 * No WINEDLLOVERRIDES needed — DINPUT8 is not overridden by Proton.
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "d3d8_iface.h"
#include "device_proxy.h"

/* ── Logging ─────────────────────────────────────────────────────────────── */
/* log_msg() defined in device_proxy.h as inline */

/* ── Exception observer (VEH — logs without stealing from Wine's handlers) ── */

static LONG WINAPI OurVEH(EXCEPTION_POINTERS* ep)
{
    DWORD code = ep->ExceptionRecord->ExceptionCode;
    if (code == EXCEPTION_BREAKPOINT || code == EXCEPTION_SINGLE_STEP)
        return EXCEPTION_CONTINUE_SEARCH;
    char buf[256];
    snprintf(buf, sizeof(buf),
        "[jaws_mod] VEH code=0x%08lX addr=0x%08lX tid=%lu flags=0x%lX",
        (unsigned long)code,
        (unsigned long)ep->ExceptionRecord->ExceptionAddress,
        (unsigned long)GetCurrentThreadId(),
        (unsigned long)ep->ExceptionRecord->ExceptionFlags);
    log_msg(buf);
    /* Wine EXCEPTION_WINE_STUB packs two string pointers in ExceptionInformation */
    ULONG n = ep->ExceptionRecord->NumberParameters;
    for (ULONG i = 0; i < n && i < 2; i++) {
        const char* s = (const char*)ep->ExceptionRecord->ExceptionInformation[i];
        if (!IsBadReadPtr(s, 1)) {
            char line[128];
            snprintf(line, sizeof(line), "[jaws_mod]   info[%lu]='%.80s'", i, s);
            log_msg(line);
        }
    }
    /* Stack words past the EXCEPTION_RECORD may hold return addresses */
    DWORD* stk = (DWORD*)ep->ContextRecord->Esp;
    for (int i = 0; i < 16; i++) {
        char line[64];
        snprintf(line, sizeof(line), "[jaws_mod]   stk[%02d]=0x%08lX", i, (unsigned long)stk[i]);
        log_msg(line);
    }
    return EXCEPTION_CONTINUE_SEARCH;
}

/* ── Real DINPUT8 forwarding ─────────────────────────────────────────────── */

static HMODULE g_dinput8_real = nullptr;

extern "C" __declspec(dllexport)
HRESULT WINAPI DirectInput8Create(HINSTANCE inst, DWORD ver, REFIID riid,
                                   void** out, IUnknown* outer)
{
    if (!g_dinput8_real) return E_FAIL;
    auto fn = (decltype(&DirectInput8Create))
        GetProcAddress(g_dinput8_real, "DirectInput8Create");
    if (!fn) return E_FAIL;
    return fn(inst, ver, riid, out, outer);
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

            char buf[128];
            snprintf(buf, sizeof(buf), "[jaws_mod] IAT patched: %s!%s", target_dll, func_name);
            log_msg(buf);
            return;
        }
    }
    log_msg("[jaws_mod] WARNING: IAT entry not found");
}

/* ── D3D8Proxy (thin IDirect3D8 wrapper) ────────────────────────────────── */

class D3D8Proxy : public IDirect3D8 {
public:
    explicit D3D8Proxy(IDirect3D8* real) : real_(real), refs_(1) {
        log_msg("[jaws_mod] D3D8Proxy::ctor");
    }

    HRESULT __stdcall QueryInterface(REFIID r, void** p) override {
        log_msg("[jaws_mod] D3D8Proxy::QueryInterface");
        return real_->QueryInterface(r, p);
    }
    ULONG __stdcall AddRef() override {
        log_msg("[jaws_mod] D3D8Proxy::AddRef");
        real_->AddRef();
        return ++refs_;
    }
    ULONG __stdcall Release() override {
        log_msg("[jaws_mod] D3D8Proxy::Release");
        real_->Release();
        ULONG n = --refs_;
        if (n == 0) { log_msg("[jaws_mod] D3D8Proxy::Release — deleting"); delete this; }
        return n;
    }

    HRESULT __stdcall RegisterSoftwareDevice(void* p) override                         { log_msg("[jaws_mod] D3D8P::RegisterSoftwareDevice"); return real_->RegisterSoftwareDevice(p); }
    UINT    __stdcall GetAdapterCount() override                                        { log_msg("[jaws_mod] D3D8P::GetAdapterCount"); return real_->GetAdapterCount(); }
    HRESULT __stdcall GetAdapterIdentifier(UINT a,DWORD f,void* p) override            { log_msg("[jaws_mod] D3D8P::GetAdapterIdentifier"); return real_->GetAdapterIdentifier(a,f,p); }
    UINT    __stdcall GetAdapterModeCount(UINT a) override                              { log_msg("[jaws_mod] D3D8P::GetAdapterModeCount"); return real_->GetAdapterModeCount(a); }
    HRESULT __stdcall EnumAdapterModes(UINT a,UINT m,D3DDISPLAYMODE* p) override       { log_msg("[jaws_mod] D3D8P::EnumAdapterModes"); return real_->EnumAdapterModes(a,m,p); }
    HRESULT __stdcall GetAdapterDisplayMode(UINT a,D3DDISPLAYMODE* p) override         { log_msg("[jaws_mod] D3D8P::GetAdapterDisplayMode"); return real_->GetAdapterDisplayMode(a,p); }
    HRESULT __stdcall CheckDeviceType(UINT a,DWORD t,D3DFORMAT af,D3DFORMAT bf,BOOL w) override { log_msg("[jaws_mod] D3D8P::CheckDeviceType"); return real_->CheckDeviceType(a,t,af,bf,w); }
    HRESULT __stdcall CheckDeviceFormat(UINT a,DWORD t,D3DFORMAT af,DWORD u,D3DRESOURCETYPE r,D3DFORMAT cf) override { log_msg("[jaws_mod] D3D8P::CheckDeviceFormat"); return real_->CheckDeviceFormat(a,t,af,u,r,cf); }
    HRESULT __stdcall CheckDeviceMultiSampleType(UINT a,DWORD t,D3DFORMAT f,BOOL w,D3DMULTISAMPLE_TYPE m) override { log_msg("[jaws_mod] D3D8P::CheckDeviceMultiSampleType"); return real_->CheckDeviceMultiSampleType(a,t,f,w,m); }
    HRESULT __stdcall CheckDepthStencilMatch(UINT a,DWORD t,D3DFORMAT af,D3DFORMAT rf,D3DFORMAT df) override { log_msg("[jaws_mod] D3D8P::CheckDepthStencilMatch"); return real_->CheckDepthStencilMatch(a,t,af,rf,df); }
    HRESULT __stdcall GetDeviceCaps(UINT a,DWORD t,D3DCAPS8* c) override               { log_msg("[jaws_mod] D3D8P::GetDeviceCaps"); return real_->GetDeviceCaps(a,t,c); }
    HMONITOR __stdcall GetAdapterMonitor(UINT a) override                              { log_msg("[jaws_mod] D3D8P::GetAdapterMonitor"); return real_->GetAdapterMonitor(a); }

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
            log_msg("[jaws_mod] CreateDevice returning OK");
        } else {
            char buf[64];
            snprintf(buf, sizeof(buf), "[jaws_mod] ERROR: CreateDevice failed hr=0x%08lX", (unsigned long)hr);
            log_msg(buf);
        }
        return hr;
    }

private:
    IDirect3D8* real_;
    ULONG       refs_;
};

/* ── Our Direct3DCreate8 hook (defined after D3D8Proxy) ─────────────────── */

static IDirect3D8* WINAPI OurDirect3DCreate8(UINT sdk_version)
{
    log_msg("[jaws_mod] Direct3DCreate8 hooked — creating proxy");

    HMODULE d3d8 = GetModuleHandleA("d3d8.dll");
    if (!d3d8) { log_msg("[jaws_mod] ERROR: d3d8.dll not in process"); return nullptr; }

    auto real_fn = (PFN_Direct3DCreate8)GetProcAddress(d3d8, "Direct3DCreate8");
    if (!real_fn) { log_msg("[jaws_mod] ERROR: Direct3DCreate8 not found"); return nullptr; }

    IDirect3D8* real = real_fn(sdk_version);
    if (!real) { log_msg("[jaws_mod] ERROR: real Direct3DCreate8 returned null"); return nullptr; }

    log_msg("[jaws_mod] D3D8Proxy wrapping real object");
    return new D3D8Proxy(real);
}

/* ── DllMain ─────────────────────────────────────────────────────────────── */

BOOL WINAPI DllMain(HINSTANCE hInst, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hInst);

        /* VEH observer — logs exceptions without replacing Wine's own handlers */
        AddVectoredExceptionHandler(1, OurVEH);

        log_msg("[jaws_mod] dinput8 proxy loaded");

        /* Load real dinput8 from system (safe — no DXVK complications) */
        char path[MAX_PATH];
        GetSystemDirectoryA(path, MAX_PATH);
        strcat(path, "\\dinput8.dll");
        g_dinput8_real = LoadLibraryA(path);
        if (g_dinput8_real) log_msg("[jaws_mod] real dinput8.dll loaded");
        else                log_msg("[jaws_mod] WARNING: could not load real dinput8.dll");

        /* Patch Jaws.exe's IAT — safe here, just VirtualProtect + pointer write */
        HMODULE game = GetModuleHandleA(nullptr);
        PatchIAT(game, "d3d8.dll", "Direct3DCreate8", (void*)OurDirect3DCreate8);
    }
    return TRUE;
}

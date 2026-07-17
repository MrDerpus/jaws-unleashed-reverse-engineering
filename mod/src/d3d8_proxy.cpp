/*
 * d3d8.dll proxy — injection point for the Jaws Unleashed mod.
 *
 * Place this d3d8.dll in the game directory. Wine's DLL search finds it
 * before DXVK's system32 copy, so all Direct3DCreate8 calls come here.
 *
 * DXVK's d3d8 is loaded lazily (not in DllMain) to avoid loader-lock
 * deadlocks. By the time Direct3DCreate8 is first called, all DLLs have
 * finished loading and it is safe to call LoadLibraryA.
 *
 * dinput8.dll is never proxied → Wine loads its own real builtin → no crash.
 *
 * Deploy: drop d3d8.dll next to Jaws.exe (remove winmm.dll from game dir).
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "d3d8_iface.h"
#include "device_proxy.h"

static HMODULE g_dxvk = nullptr;

/* ── Simulation time freeze — IAT hooks for GetTickCount / QPC ──────────────
 *
 * When g_sim_paused is true, both hooks return a captured frozen timestamp.
 * g_tick_offset / g_qpc_offset accumulate total paused duration so that when
 * the sim resumes the game sees no time jump — dt on the first post-pause
 * frame is ~0 rather than the entire paused wall-clock duration.
 * ─────────────────────────────────────────────────────────────────────────── */

bool g_sim_paused = false;

DWORD (WINAPI *g_real_GetTickCount)() = ::GetTickCount;
static BOOL  (WINAPI *g_real_QPC)(LARGE_INTEGER*) = ::QueryPerformanceCounter;

/* Divisor used while paused.  Both GTC and QPC must be slowed together —
 * the game uses QPC (not just GTC) to gate its render loop, so freezing
 * either one stops EndScene from firing and makes F5 undetectable.
 * Divisor=4 → fake dt ≈ 4 ms per real 16 ms frame → game renders every
 * ~4 real frames (~15 fps) while simulation advances at 25% speed. */
static const DWORD SIM_DIVISOR = 4;

static DWORD    g_tick_offset     = 0;
static DWORD    g_tick_pause_real = 0;
static DWORD    g_frozen_tick     = 0;
static LONGLONG g_qpc_offset      = 0;
static LONGLONG g_qpc_pause_real  = 0;
static LONGLONG g_frozen_qpc      = 0;

void freeze_sim_time()
{
    g_tick_pause_real = g_real_GetTickCount();
    g_frozen_tick     = g_tick_pause_real - g_tick_offset;
    LARGE_INTEGER q; g_real_QPC(&q);
    g_qpc_pause_real  = q.QuadPart;
    g_frozen_qpc      = q.QuadPart - g_qpc_offset;
}

void thaw_sim_time()
{
    DWORD real_now = g_real_GetTickCount();
    DWORD fake_at_unpause = g_frozen_tick + (real_now - g_tick_pause_real) / SIM_DIVISOR;
    g_tick_offset = real_now - fake_at_unpause;
    LARGE_INTEGER q; g_real_QPC(&q);
    LONGLONG fake_qpc_at_unpause = g_frozen_qpc + (q.QuadPart - g_qpc_pause_real) / SIM_DIVISOR;
    g_qpc_offset = q.QuadPart - fake_qpc_at_unpause;
}

static DWORD WINAPI Hook_GetTickCount()
{
    DWORD real_now = g_real_GetTickCount();
    if (g_sim_paused)
        return g_frozen_tick + (real_now - g_tick_pause_real) / SIM_DIVISOR;
    return real_now - g_tick_offset;
}

static BOOL WINAPI Hook_QPC(LARGE_INTEGER* out)
{
    LARGE_INTEGER real_now; g_real_QPC(&real_now);
    if (g_sim_paused) {
        if (out) out->QuadPart = g_frozen_qpc + (real_now.QuadPart - g_qpc_pause_real) / SIM_DIVISOR;
        return TRUE;
    }
    if (out) out->QuadPart = real_now.QuadPart - g_qpc_offset;
    return TRUE;
}

static bool PatchIATEntry(HMODULE hMod, const char* dll_name, const char* fn_name,
                           void* hook_fn, void** real_out)
{
    BYTE* base = (BYTE*)hMod;
    auto* dos = (IMAGE_DOS_HEADER*)base;
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) return false;
    auto* nt  = (IMAGE_NT_HEADERS*)(base + dos->e_lfanew);
    auto& dir = nt->OptionalHeader.DataDirectory[1]; /* IMAGE_DIRECTORY_ENTRY_IMPORT */
    if (!dir.VirtualAddress) return false;

    auto* desc = (IMAGE_IMPORT_DESCRIPTOR*)(base + dir.VirtualAddress);
    for (; desc->Name; ++desc) {
        if (_stricmp((char*)(base + desc->Name), dll_name) != 0) continue;
        if (!desc->OriginalFirstThunk) continue;
        auto* orig  = (IMAGE_THUNK_DATA*)(base + desc->OriginalFirstThunk);
        auto* thunk = (IMAGE_THUNK_DATA*)(base + desc->FirstThunk);
        for (; orig->u1.AddressOfData; ++orig, ++thunk) {
            if (orig->u1.Ordinal & IMAGE_ORDINAL_FLAG) continue;
            auto* ibn = (IMAGE_IMPORT_BY_NAME*)(base + (DWORD)orig->u1.AddressOfData);
            if (strcmp((char*)ibn->Name, fn_name) != 0) continue;
            *real_out = (void*)thunk->u1.Function;
            DWORD old;
            VirtualProtect(&thunk->u1.Function, sizeof(void*), PAGE_READWRITE, &old);
            thunk->u1.Function = (DWORD_PTR)hook_fn;
            VirtualProtect(&thunk->u1.Function, sizeof(void*), old, &old);
            return true;
        }
    }
    return false;
}

static void InstallTimeHooks()
{
    static bool done = false;
    if (done) return;
    done = true;

    HMODULE exe = GetModuleHandleA(nullptr);
    bool ok1 = PatchIATEntry(exe, "KERNEL32.dll", "GetTickCount",
                              (void*)Hook_GetTickCount, (void**)&g_real_GetTickCount);
    bool ok2 = PatchIATEntry(exe, "KERNEL32.dll", "QueryPerformanceCounter",
                              (void*)Hook_QPC, (void**)&g_real_QPC);
    char buf[80];
    snprintf(buf, sizeof(buf), "[jaws_mod] time hooks: GTC=%s QPC=%s",
             ok1 ? "ok" : "MISS", ok2 ? "ok" : "MISS");
    log_msg(buf);
}

/* ── Exception observer ─────────────────────────────────────────────────── */

static void mod_name_for_addr(void* addr, char* out, size_t out_sz)
{
    HMODULE hmod = nullptr;
    if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                           GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           (LPCSTR)addr, &hmod) && hmod)
        GetModuleFileNameA(hmod, out, (DWORD)out_sz);
    else
        strncpy(out, "<unknown>", out_sz);
}

static LONG WINAPI OurVEH(EXCEPTION_POINTERS* ep)
{
    DWORD code = ep->ExceptionRecord->ExceptionCode;
    if (code == EXCEPTION_BREAKPOINT || code == EXCEPTION_SINGLE_STEP)
        return EXCEPTION_CONTINUE_SEARCH;

    void* addr = ep->ExceptionRecord->ExceptionAddress;
    char modname[MAX_PATH];
    mod_name_for_addr(addr, modname, sizeof(modname));

    char buf[MAX_PATH + 128];
    snprintf(buf, sizeof(buf),
        "[jaws_mod] VEH code=0x%08lX addr=0x%08lX tid=%lu mod=%s",
        (unsigned long)code, (unsigned long)addr,
        (unsigned long)GetCurrentThreadId(), modname);
    log_msg(buf);

    /* Wine stub exceptions: info[0]=dll name, info[1]=function name. */
    if (code == 0x80000100 && ep->ExceptionRecord->NumberParameters >= 1) {
        const char* dll_name  = (const char*)ep->ExceptionRecord->ExceptionInformation[0];
        const char* func_name = ep->ExceptionRecord->NumberParameters >= 2
                              ? (const char*)ep->ExceptionRecord->ExceptionInformation[1]
                              : "(no func)";
        snprintf(buf, sizeof(buf), "[jaws_mod]   wine_stub: %s!%s",
                 dll_name ? dll_name : "(null)", func_name ? func_name : "(null)");
        log_msg(buf);
    }

    /* Simple EBP-chain stack walk — identifies calling modules. */
    DWORD* ebp = (DWORD*)ep->ContextRecord->Ebp;
    for (int i = 0; i < 8; i++) {
        if (IsBadReadPtr(ebp, 8)) break;
        DWORD ret_addr = ebp[1];
        char frame_mod[MAX_PATH];
        mod_name_for_addr((void*)(DWORD_PTR)ret_addr, frame_mod, sizeof(frame_mod));
        snprintf(buf, sizeof(buf), "[jaws_mod]   frame[%d] ret=0x%08lX mod=%s",
                 i, (unsigned long)ret_addr, frame_mod);
        log_msg(buf);
        ebp = (DWORD*)ebp[0];
    }

    return EXCEPTION_CONTINUE_SEARCH;
}

/* ── IDirect3D8 proxy ────────────────────────────────────────────────────── */

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

/* ── DllMain ─────────────────────────────────────────────────────────────── */

BOOL WINAPI DllMain(HINSTANCE hInst, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hInst);
        AddVectoredExceptionHandler(1, OurVEH);
        log_msg("[jaws_mod] d3d8 proxy loaded");
        /* DXVK d3d8 is loaded lazily in Direct3DCreate8, not here.
         * Loading DXVK inside DllMain causes loader-lock deadlocks. */
    }
    return TRUE;
}

/* ── Direct3DCreate8 export ─────────────────────────────────────────────── */

extern "C" __declspec(dllexport)
IDirect3D8* WINAPI Direct3DCreate8(UINT sdk_version)
{
    log_msg("[jaws_mod] Direct3DCreate8 called");
    InstallTimeHooks();

    if (!g_dxvk) {
        /* Lazy-load DXVK's d3d8 via system32 path. For a 32-bit process,
         * WOW64 redirects system32 → syswow64, so we get DXVK's genuine
         * 32-bit PE (not a Wine stub — DXVK is a real native implementation). */
        char path[MAX_PATH];
        GetSystemDirectoryA(path, MAX_PATH);
        strcat(path, "\\d3d8.dll");
        char logbuf[MAX_PATH + 32];
        snprintf(logbuf, sizeof(logbuf), "[jaws_mod] loading DXVK from: %s", path);
        log_msg(logbuf);
        g_dxvk = LoadLibraryA(path);
        if (g_dxvk) log_msg("[jaws_mod] DXVK d3d8.dll loaded");
        else       { log_msg("[jaws_mod] ERROR: DXVK d3d8.dll not found"); return nullptr; }
    }

    auto fn = (PFN_Direct3DCreate8)GetProcAddress(g_dxvk, "Direct3DCreate8");
    if (!fn) { log_msg("[jaws_mod] ERROR: GetProcAddress failed"); return nullptr; }

    IDirect3D8* real = fn(sdk_version);
    if (!real) { log_msg("[jaws_mod] ERROR: real Direct3DCreate8 returned null"); return nullptr; }

    log_msg("[jaws_mod] D3D8Proxy wrapping");
    return new D3D8Proxy(real);
}

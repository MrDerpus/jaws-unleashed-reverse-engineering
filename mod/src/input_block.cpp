#include "input_block.h"
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>
#include <stdio.h>

static void log_msg(const char* msg)
{
    FILE* f = fopen("C:\\jaws_mod.log", "a");
    if (f) { fprintf(f, "%s\n", msg); fclose(f); }
}

bool g_block_game_input = false;

static const GUID IID_IDirectInput8A_ = { 0xBF798030, 0x483A, 0x4DA2, { 0xAA,0x99,0x5D,0x64,0xED,0x36,0x97,0x00 } };
static const GUID GUID_SysKeyboard_   = { 0x6F1D2B61, 0xD5A0, 0x11CF, { 0xBF,0xC7,0x44,0x45,0x53,0x54,0x00,0x00 } };

/* IDirectInputDevice8A vtable slots */
static const int SLOT_GETDEVICESTATE = 9;
static const int SLOT_GETDEVICEDATA  = 10;

typedef HRESULT (__stdcall *PFN_GetDeviceState)(void* self, DWORD cb, void* data);
typedef HRESULT (__stdcall *PFN_GetDeviceData)(void* self, DWORD cb_obj, void* rgdod, DWORD* inout, DWORD flags);
typedef HRESULT (WINAPI *PFN_DirectInput8Create)(HINSTANCE, DWORD, const GUID&, void**, void*);

static PFN_GetDeviceState g_real_gds = nullptr;
static PFN_GetDeviceData  g_real_gdd = nullptr;

static HRESULT __stdcall Hook_GetDeviceState(void* self, DWORD cb, void* data)
{
    HRESULT hr = g_real_gds(self, cb, data);
    /* Only blank keyboard-sized state (256 bytes) so a mouse sharing this
     * vtable keeps working. */
    if (g_block_game_input && SUCCEEDED(hr) && data && cb == 256) memset(data, 0, cb);
    return hr;
}

static HRESULT __stdcall Hook_GetDeviceData(void* self, DWORD cb_obj, void* rgdod, DWORD* inout, DWORD flags)
{
    HRESULT hr = g_real_gdd(self, cb_obj, rgdod, inout, flags);
    /* Real call still runs so the buffer drains; the game just gets 0 events. */
    if (g_block_game_input && SUCCEEDED(hr) && inout) *inout = 0;
    return hr;
}

static bool PatchSlot(void** vtbl, int slot, void* hook, void** real_out)
{
    if (vtbl[slot] == hook) return true;
    DWORD old;
    if (!VirtualProtect(&vtbl[slot], sizeof(void*), PAGE_EXECUTE_READWRITE, &old)) return false;
    *real_out = vtbl[slot];
    vtbl[slot] = hook;
    VirtualProtect(&vtbl[slot], sizeof(void*), old, &old);
    return true;
}

void InstallInputBlock()
{
    static bool done = false;
    if (done) return;
    done = true;

    HMODULE di = GetModuleHandleA("dinput8.dll");
    auto create = di ? (PFN_DirectInput8Create)GetProcAddress(di, "DirectInput8Create") : nullptr;
    if (!create) { log_msg("[jaws_mod] input block: dinput8 not loaded"); return; }

    void* dinput = nullptr;
    if (FAILED(create(GetModuleHandleA(nullptr), 0x0800, IID_IDirectInput8A_, &dinput, nullptr)) || !dinput) {
        log_msg("[jaws_mod] input block: DirectInput8Create failed"); return;
    }
    void** di_vtbl = *(void***)dinput;
    typedef HRESULT (__stdcall *PFN_CreateDevice)(void*, const GUID&, void**, void*);
    typedef ULONG   (__stdcall *PFN_Release)(void*);

    void* kbd = nullptr;
    bool ok = false;
    if (SUCCEEDED(((PFN_CreateDevice)di_vtbl[3])(dinput, GUID_SysKeyboard_, &kbd, nullptr)) && kbd) {
        void** dev_vtbl = *(void***)kbd;
        ok = PatchSlot(dev_vtbl, SLOT_GETDEVICESTATE, (void*)Hook_GetDeviceState, (void**)&g_real_gds) &&
             PatchSlot(dev_vtbl, SLOT_GETDEVICEDATA,  (void*)Hook_GetDeviceData,  (void**)&g_real_gdd);
        ((PFN_Release)dev_vtbl[2])(kbd);
    }
    ((PFN_Release)di_vtbl[2])(dinput);
    log_msg(ok ? "[jaws_mod] input block: keyboard vtable patched" : "[jaws_mod] input block: patch FAILED");
}

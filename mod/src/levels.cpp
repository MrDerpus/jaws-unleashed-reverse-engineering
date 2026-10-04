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

#include "levels.h"
#include "device_proxy.h"   /* log_msg */

#include <windows.h>
#include <stdio.h>
#include <string.h>

static const char* CUSTOM_DIR = "custom_levels";
static const char* DATA_DIR   = "data";
static const int   NAME_MAX_LEN = 31;

typedef HANDLE (WINAPI *CreateFileAFn)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
typedef DWORD  (WINAPI *GetFileAttributesAFn)(LPCSTR);

static CreateFileAFn        g_real_CreateFileA        = ::CreateFileA;
static GetFileAttributesAFn g_real_GetFileAttributesA = ::GetFileAttributesA;

static char g_exe_dir[MAX_PATH];          /* with trailing backslash */
static char g_names[MAX_CUSTOM_LEVELS][NAME_MAX_LEN + 1];
static int  g_count = 0;

static bool EndsWithGdw(const char* path)
{
    size_t n = strlen(path);
    return n > 4 && _stricmp(path + n - 4, ".GDW") == 0;
}

static const char* BaseName(const char* path)
{
    const char* b = path;
    for (const char* c = path; *c; ++c)
        if (*c == '\\' || *c == '/' || *c == ':') b = c + 1;
    return b;
}

/* If `path` is a .GDW that doesn't exist but custom_levels\ has one by that
 * name, writes the custom path to `out` and returns true. */
static bool Redirect(const char* path, char* out, size_t out_sz)
{
    if (!path || !EndsWithGdw(path) || !g_exe_dir[0]) return false;
    if (g_real_GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES) return false;
    snprintf(out, out_sz, "%s%s\\%s", g_exe_dir, CUSTOM_DIR, BaseName(path));
    return g_real_GetFileAttributesA(out) != INVALID_FILE_ATTRIBUTES;
}

/* Logs the first few .GDW paths the game touches, so the log shows what the
 * engine actually asks for. */
static void LogGdw(const char* fn, const char* path, const char* redirected)
{
    static LONG logged = 0;
    if (InterlockedIncrement(&logged) > 40) return;
    char buf[MAX_PATH * 2 + 64];
    if (redirected)
        snprintf(buf, sizeof(buf), "[jaws_mod] %s %s -> %s", fn, path, redirected);
    else
        snprintf(buf, sizeof(buf), "[jaws_mod] %s %s", fn, path);
    log_msg(buf);
}

static HANDLE WINAPI Hook_CreateFileA(LPCSTR path, DWORD access, DWORD share, LPSECURITY_ATTRIBUTES sa,
                                      DWORD disp, DWORD flags, HANDLE tmpl)
{
    char alt[MAX_PATH];
    if (Redirect(path, alt, sizeof(alt))) {
        LogGdw("CreateFileA", path, alt);
        return g_real_CreateFileA(alt, access, share, sa, disp, flags, tmpl);
    }
    if (path && EndsWithGdw(path)) LogGdw("CreateFileA", path, nullptr);
    return g_real_CreateFileA(path, access, share, sa, disp, flags, tmpl);
}

static DWORD WINAPI Hook_GetFileAttributesA(LPCSTR path)
{
    char alt[MAX_PATH];
    if (Redirect(path, alt, sizeof(alt))) {
        LogGdw("GetFileAttributesA", path, alt);
        return g_real_GetFileAttributesA(alt);
    }
    return g_real_GetFileAttributesA(path);
}

static bool PatchImport(HMODULE mod, const char* dll, const char* fn, void* hook, void** real)
{
    BYTE* base = (BYTE*)mod;
    auto* dos = (IMAGE_DOS_HEADER*)base;
    auto* nt  = (IMAGE_NT_HEADERS*)(base + dos->e_lfanew);
    auto& dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!dir.VirtualAddress) return false;
    for (auto* d = (IMAGE_IMPORT_DESCRIPTOR*)(base + dir.VirtualAddress); d->Name; ++d) {
        if (_stricmp((char*)(base + d->Name), dll) != 0 || !d->OriginalFirstThunk) continue;
        auto* orig  = (IMAGE_THUNK_DATA*)(base + d->OriginalFirstThunk);
        auto* thunk = (IMAGE_THUNK_DATA*)(base + d->FirstThunk);
        for (; orig->u1.AddressOfData; ++orig, ++thunk) {
            if (orig->u1.Ordinal & IMAGE_ORDINAL_FLAG) continue;
            auto* ibn = (IMAGE_IMPORT_BY_NAME*)(base + (DWORD)orig->u1.AddressOfData);
            if (strcmp((char*)ibn->Name, fn) != 0) continue;
            *real = (void*)thunk->u1.Function;
            DWORD old;
            VirtualProtect(&thunk->u1.Function, sizeof(void*), PAGE_READWRITE, &old);
            thunk->u1.Function = (DWORD_PTR)hook;
            VirtualProtect(&thunk->u1.Function, sizeof(void*), old, &old);
            return true;
        }
    }
    return false;
}

void InstallLevelFileHooks()
{
    static bool done = false;
    if (done) return;
    done = true;

    DWORD n = GetModuleFileNameA(nullptr, g_exe_dir, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) { g_exe_dir[0] = 0; log_msg("[jaws_mod] levels: no exe path"); return; }
    char* slash = strrchr(g_exe_dir, '\\');
    if (slash) slash[1] = 0;

    HMODULE exe = GetModuleHandleA(nullptr);
    bool ok1 = PatchImport(exe, "KERNEL32.dll", "CreateFileA",
                           (void*)Hook_CreateFileA, (void**)&g_real_CreateFileA);
    bool ok2 = PatchImport(exe, "KERNEL32.dll", "GetFileAttributesA",
                           (void*)Hook_GetFileAttributesA, (void**)&g_real_GetFileAttributesA);
    char buf[MAX_PATH + 96];
    snprintf(buf, sizeof(buf), "[jaws_mod] level hooks: CreateFileA=%s GetFileAttributesA=%s, folder %s%s",
             ok1 ? "ok" : "MISS", ok2 ? "ok" : "MISS", g_exe_dir, CUSTOM_DIR);
    log_msg(buf);
}

int ScanCustomLevels()
{
    g_count = 0;
    if (!g_exe_dir[0]) return 0;
    char pattern[MAX_PATH];
    snprintf(pattern, sizeof(pattern), "%s%s\\*.GDW", g_exe_dir, CUSTOM_DIR);
    WIN32_FIND_DATAA fd;
    HANDLE h = FindFirstFileA(pattern, &fd);
    if (h == INVALID_HANDLE_VALUE) return 0;
    do {
        if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) continue;
        /* Stem must be a plain name: the engine appends .GDW only when the
         * name has no '.', and keeps it in fixed-size buffers. */
        char stem[MAX_PATH];
        snprintf(stem, sizeof(stem), "%s", fd.cFileName);
        stem[strlen(stem) - 4] = 0;
        size_t len = strlen(stem);
        bool ok = len > 0 && len <= (size_t)NAME_MAX_LEN;
        for (const char* c = stem; ok && *c; ++c)
            ok = (*c >= 'A' && *c <= 'Z') || (*c >= 'a' && *c <= 'z') || (*c >= '0' && *c <= '9') || *c == '_';
        char stock[MAX_PATH];
        snprintf(stock, sizeof(stock), "%s%s\\%s", g_exe_dir, DATA_DIR, fd.cFileName);
        if (ok && g_real_GetFileAttributesA(stock) != INVALID_FILE_ATTRIBUTES) {
            char buf[MAX_PATH + 64];
            snprintf(buf, sizeof(buf), "[jaws_mod] levels: skipping %s (a stock level has that name)", fd.cFileName);
            log_msg(buf);
            continue;
        }
        if (!ok) {
            char buf[MAX_PATH + 64];
            snprintf(buf, sizeof(buf), "[jaws_mod] levels: skipping %s (name: letters, digits, _ only, max %d)",
                     fd.cFileName, NAME_MAX_LEN);
            log_msg(buf);
            continue;
        }
        for (char* c = stem; *c; ++c) if (*c >= 'a' && *c <= 'z') *c -= 32;
        snprintf(g_names[g_count], sizeof(g_names[g_count]), "%s", stem);
        ++g_count;
    } while (g_count < MAX_CUSTOM_LEVELS && FindNextFileA(h, &fd));
    FindClose(h);
    return g_count;
}

const char* CustomLevelName(int i)
{
    return (i >= 0 && i < g_count) ? g_names[i] : "";
}

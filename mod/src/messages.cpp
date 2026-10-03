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

#include "messages.h"
#include "device_proxy.h"   /* log_msg */

#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <string>
#include <vector>

static const char*  MSG_FILE          = "C:\\jaws_messages.txt";
static const DWORD  LANG_TABLES       = 0x854D14;   /* 5 pointers, English first */
static const DWORD  ENGLISH_TABLE     = 0x84FEF0;   /* sanity check: exe version */
static const int    LANGS = 5, SLOTS  = 1000;
static const DWORD  ENGINE_GLOBAL     = 0x920E24;
static const DWORD  ENGINE_STAGE_NAME = 0xB8;
static const int    CHECK_EVERY       = 30;         /* frames between file checks */

struct Override { std::string stage; int slot; std::string text; };

/* Process-wide: the D3D device (and DeviceProxy) is recreated constantly. */
static std::vector<Override> g_overrides;
static std::vector<std::string*> g_keep;   /* strings the game may still point at: never freed */
static DWORD    g_orig[LANGS][SLOTS];
static bool     g_saved = false, g_bad_exe = false;
static FILETIME g_mtime = {};
static bool     g_have_file = false;
static char     g_applied_stage[64] = "\x01";   /* forces the first apply */
static int      g_tick = 0;

static bool rd(DWORD addr, void* out, SIZE_T n)
{
    return ReadProcessMemory(GetCurrentProcess(), (LPCVOID)addr, out, n, nullptr) != 0;
}

static void LoadFile()
{
    g_overrides.clear();
    FILE* f = fopen(MSG_FILE, "r");
    if (!f) return;
    char line[2048];
    while (fgets(line, sizeof(line), f)) {
        char* p = line;
        while (*p == ' ' || *p == '\t') ++p;
        if (*p == '#' || *p == '\n' || *p == '\r' || !*p) continue;
        char stage[64]; int slot, used = 0;
        if (sscanf(p, "%63s %d %n", stage, &slot, &used) < 2 || slot < 0 || slot >= SLOTS) continue;
        std::string text;
        for (const char* c = p + used; *c && *c != '\n' && *c != '\r'; ++c) {
            if (c[0] == '\\' && c[1] == 'n') { text += '\n'; ++c; }
            else text += *c;
        }
        g_overrides.push_back({stage, slot, text});
    }
    fclose(f);
    char msg[128];
    snprintf(msg, sizeof(msg), "[jaws_mod] messages: %u overrides loaded", (unsigned)g_overrides.size());
    log_msg(msg);
}

static bool FileChanged()
{
    WIN32_FILE_ATTRIBUTE_DATA a;
    bool have = GetFileAttributesExA(MSG_FILE, GetFileExInfoStandard, &a) != 0;
    if (have == g_have_file && (!have || CompareFileTime(&a.ftLastWriteTime, &g_mtime) == 0))
        return false;
    g_have_file = have;
    if (have) g_mtime = a.ftLastWriteTime;
    return true;
}

static void CurrentStage(char* out, size_t n)
{
    out[0] = 0;
    DWORD engine = 0;
    if (!rd(ENGINE_GLOBAL, &engine, 4) || !engine) return;
    char name[64] = {};
    if (!rd(engine + ENGINE_STAGE_NAME, name, sizeof(name) - 1)) return;
    /* engine+0xB8 holds what the loader was given; may include a path */
    const char* base = name;
    for (const char* c = name; *c; ++c)
        if (*c == '\\' || *c == '/') base = c + 1;
    snprintf(out, n, "%s", base);
    char* dot = strrchr(out, '.');
    if (dot) *dot = 0;
}

static void Apply(const char* stage)
{
    DWORD tables[LANGS];
    if (!rd(LANG_TABLES, tables, sizeof(tables)))
        return;
    if (!g_saved) {
        for (int l = 0; l < LANGS; ++l)
            if (!rd(tables[l], g_orig[l], sizeof(g_orig[l]))) return;
        g_saved = true;
    }
    int n = 0;
    for (int l = 0; l < LANGS; ++l) {
        DWORD cur[SLOTS];
        memcpy(cur, g_orig[l], sizeof(cur));
        for (const Override& o : g_overrides)
            if (o.stage == "*" || _stricmp(o.stage.c_str(), stage) == 0) {
                std::string* s = new std::string(o.text);
                g_keep.push_back(s);
                cur[o.slot] = (DWORD)(uintptr_t)s->c_str();
                if (l == 0) ++n;
            }
        /* .data is writable; WriteProcessMemory also copes if it weren't */
        WriteProcessMemory(GetCurrentProcess(), (LPVOID)tables[l], cur, sizeof(cur), nullptr);
    }
    char msg[160];
    snprintf(msg, sizeof(msg), "[jaws_mod] messages: stage '%s', %d slot(s) replaced", stage, n);
    log_msg(msg);
}

void UpdateMessageOverrides()
{
    if (g_bad_exe) return;
    if (!g_saved) {
        DWORD en = 0;
        if (!rd(LANG_TABLES, &en, 4) || en != ENGLISH_TABLE) {
            g_bad_exe = true;
            log_msg("[jaws_mod] messages: unexpected message table (exe differs?), disabled");
            return;
        }
    }
    bool reload = false;
    if (++g_tick >= CHECK_EVERY) {
        g_tick = 0;
        if (FileChanged()) { LoadFile(); reload = true; }
    }
    char stage[64];
    CurrentStage(stage, sizeof(stage));
    if (!reload && strcmp(stage, g_applied_stage) == 0) return;
    snprintf(g_applied_stage, sizeof(g_applied_stage), "%s", stage);
    if (g_overrides.empty() && !g_saved) return;   /* nothing to do, nothing to restore */
    Apply(stage);
}

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

#include "stage.h"

#include <windows.h>
#include <stdio.h>
#include <string.h>

static const DWORD ENGINE_GLOBAL      = 0x920E24;
static const DWORD ENGINE_STAGE_NAME  = 0xB8;
static const DWORD VT_REQUEST_STAGE   = 0x80;
static const DWORD REQUEST_STAGE_FUNC = 0x6C3C50;
static const unsigned STAGE_FLAG_LOAD = 1;

typedef void (__attribute__((thiscall)) *RequestStageFn)(void* engine, unsigned flags, const char* name);

static bool rd(DWORD addr, void* out, SIZE_T n)
{
    return ReadProcessMemory(GetCurrentProcess(), (LPCVOID)addr, out, n, nullptr) != 0;
}

bool RequestStageReload(char* msg, size_t msg_sz)
{
    DWORD engine = 0, vtable = 0, fn = 0;
    if (!rd(ENGINE_GLOBAL, &engine, 4) || !engine) {
        snprintf(msg, msg_sz, "Reload: no engine yet");
        return false;
    }
    /* Only call through the vtable if it holds the function we decompiled. */
    if (!rd(engine, &vtable, 4) || !rd(vtable + VT_REQUEST_STAGE, &fn, 4) || fn != REQUEST_STAGE_FUNC) {
        snprintf(msg, msg_sz, "Reload: unexpected engine vtable (exe differs?)");
        return false;
    }
    char name[256] = {};
    if (!rd(engine + ENGINE_STAGE_NAME, name, sizeof(name) - 1) || !name[0]) {
        snprintf(msg, msg_sz, "Reload: no stage loaded");
        return false;
    }
    for (const char* c = name; *c; ++c)
        if ((unsigned char)*c < 0x20 || (unsigned char)*c > 0x7E) {
            snprintf(msg, msg_sz, "Reload: stage name unreadable");
            return false;
        }
    ((RequestStageFn)fn)((void*)engine, STAGE_FLAG_LOAD, name);
    snprintf(msg, msg_sz, "Reloading %s ...", name);
    return true;
}

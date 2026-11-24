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

#pragma once
/*
 * All mod files (settings, logs, bookmarks, dumps, screenshots, sonar
 * assets) live in the game folder next to Jaws.exe (since 2026-11-25;
 * before that they were in C:\).
 */
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <string.h>
#include <string>

/* Game folder with a trailing backslash. */
inline const std::string& mod_dir()
{
    static const std::string dir = [] {
        char p[MAX_PATH] = "";
        GetModuleFileNameA(nullptr, p, sizeof(p));
        char* slash = strrchr(p, '\\');
        if (slash) slash[1] = 0; else p[0] = 0;
        return std::string(p);
    }();
    return dir;
}

inline std::string mod_path(const char* name) { return mod_dir() + name; }

/* For use inside one call's arguments: fopen(MOD_PATH("jaws_x.txt"), "r"). */
#define MOD_PATH(name) (mod_path(name).c_str())

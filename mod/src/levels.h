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
 * Custom levels without editing any game file (2026-10-04).
 *
 * Custom levels are .GDW files in a `custom_levels` folder next to
 * Jaws.exe. The mod hooks Jaws.exe's imports of CreateFileA and
 * GetFileAttributesA: when the game asks for a .GDW that doesn't exist where
 * it looks (data\), and custom_levels\ has a file with that name, the call
 * is pointed there instead. Stock levels always win, so a custom level can
 * never replace one. Loading a custom level is then just the engine's own
 * stage request with its name (see stage.h); the F9 picker does that.
 */
#include <stddef.h>

static const int MAX_CUSTOM_LEVELS = 16;

/* Patches the imports. Safe to call more than once. */
void InstallLevelFileHooks();

/* Re-reads custom_levels\*.GDW. Returns how many were found; names (file
 * stems, e.g. "MYREEF") via CustomLevelName. Files whose name is also a
 * stock level, or that the engine can't take as a stage name, are skipped. */
int  ScanCustomLevels();
const char* CustomLevelName(int i);

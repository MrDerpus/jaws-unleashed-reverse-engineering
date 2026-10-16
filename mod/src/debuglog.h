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
 * Game debug text (2026-10-12). Jaws.exe calls a printf-style debug print
 * (0x4549D0, cdecl, format + args) from 171 places ("Razas damage!\n",
 * "HP:%f\n", "StoryMissionCompleted:%d\n", ...), but the release build
 * emptied it to a lone `ret`. This patches a jump there into our own
 * printer, which writes each line with a timestamp to C:\jaws_debug.log
 * (watch it with `tail -f`). Identical consecutive lines are collapsed.
 */

/* Call once at startup; safe to call again. Returns false if the exe bytes
 * don't match (different exe version) or the patch failed. */
bool InstallDebugPrint();

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
 * Teleport bookmarks: 9 slots of world coordinates, persisted to
 * C:\jaws_bookmarks.txt, one "<slot> <x> <y> <z> [name]" line per saved
 * slot; '#' lines are comments. The file is meant to be hand-edited and is
 * re-read whenever its modification time changes.
 *
 * Storage is process-wide, not per-DeviceProxy: the game recreates its D3D
 * device hundreds of times per session (see README "Screenshots"), and any
 * per-instance state resets each time.
 *
 * Bookmarks are plain world coordinates with no level attached -- the same
 * slot means a different place in a different GDW.
 */
static const int BOOKMARK_SLOTS     = 9;
static const int BOOKMARK_LABEL_MAX = 48;

/* Re-reads the file if it changed on disk (cheap: one stat call). */
void BookmarkReloadIfChanged();

/* slot is 1-based (1..9). `label` (optional) receives the slot's name, or "". */
bool BookmarkGet(int slot, float& x, float& y, float& z, const char** label = nullptr);
/* Saves the file. Clears the slot's name, since it's a new position. */
void BookmarkSet(int slot, float x, float y, float z);

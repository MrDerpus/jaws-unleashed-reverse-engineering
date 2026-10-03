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
 * Object-ID registry dump (debug, read-only; 2026-10-03).
 *
 * Every BRTR node and ACTN action is registered by ID in a hash map at
 * engine+0x50 (engine = [0x920E24]); all ID lookups (0x6C3010 action,
 * 0x6C2F90 brick) go through 0x6B8A00 on it:
 *   map+4  bucket count, map+8 bucket array (entry pointers)
 *   entry  [0] id, [1] ?, [2] object, [3] next entry
 * For each ID in C:\jaws_ids.txt (one per line, decimal or 0x hex; a
 * built-in list if the file is missing) the dump writes the entry and the
 * object's first 64 dwords to C:\jaws_iddump.txt, plus any other entries
 * whose object's own ID field (+4) equals that ID, and the runtime
 * instances that +0x20 / +0x24 point at (live actions). Only memory reads, no
 * game code is called.
 */
#include <stddef.h>

/* Appends one dump to C:\jaws_iddump.txt; a one-line summary goes in `msg`. */
bool DumpIdRegistry(char* msg, size_t msg_sz);

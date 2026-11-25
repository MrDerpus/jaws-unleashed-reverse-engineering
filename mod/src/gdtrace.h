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
 * GDFile read trace (research tool, 2026-11-25).
 *
 * Only active when a file named jaws_gdfile_trace.on exists next to Jaws.exe
 * at game start. It then replaces the Seek (+0x0C), Tell (+0x10) and Read
 * (+0x1C) slots of the three GDFile classes' vtables (0x7F5C0C disk file,
 * 0x7F5CF4 GDMemFile, 0x7F5DDC stream file) with wrappers that append one
 * 24-byte record per call to jaws_gdfile_trace.bin (game folder):
 *
 *   uint32 kind   0 read, 1 seek, 2 tell; class index (0..2) << 8
 *   uint32 file   GDFile object (this)
 *   uint32 ret    caller's return address (identifies the GDFile reader)
 *   uint32 pos    file position before the call (tell: the result)
 *   uint32 a      read: byte count; seek: offset
 *   uint32 b      read: result; seek: origin
 *
 * scripts/gdw_to_text.py uses it to learn the type of every value the
 * loader reads (int, real, string, ...) so a binary level can be rewritten
 * in the GDED text format.
 */

/* Called from Direct3DCreate8. */
void InstallGdTrace();
/* Per frame: flush the trace file. */
void FlushGdTrace();

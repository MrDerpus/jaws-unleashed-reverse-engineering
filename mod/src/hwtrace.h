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
 * Write-watch trace (2026-10-12, debug). Puts CPU hardware data breakpoints
 * (DR0-DR3, write, 4 bytes) on up to four addresses in every game thread and
 * records which code writes them: the writing instruction plus the first few
 * return addresses found on the stack. Used to find the code that pushes the
 * shark out of collision geometry. Results go to the mod log.
 */
#include <windows.h>

/* Start watching addrs[0..n-1] (n <= 4). Fails if a trace is running. */
bool HwTraceStart(const DWORD* addrs, const char* const* labels, int n, char* err, size_t err_sz);
/* Stop, clear the breakpoints and write the summary through log(). */
void HwTraceStop(void (*log)(const char*));
bool HwTraceActive();

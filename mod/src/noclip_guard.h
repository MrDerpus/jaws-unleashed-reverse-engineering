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
 * While F7 no-clip is on (2026-11-25), the shark also ignores:
 *
 *  - Area triggers (ANSphereCheck, level entrances/exits and the "enter this
 *    area?" / "leave this stage?" prompts they start). Tick 0x43BF60 (vtable
 *    0x7D128C slot +0x58) asks 0x43BDE0 whether its target (object ID +0x11C)
 *    is outside the circle, keeps that in +0x100 and fires m_enter_act /
 *    m_leave_act when it flips. The hook keeps +0x100 up to date without
 *    firing, for triggers whose target is the shark, so turning no-clip off
 *    outside a zone doesn't fire it either. Triggers aimed at other objects
 *    keep working.
 *  - Buoy pushes (ANTol): tick 0x43F6A0 (vtable 0x7D18D4 slot 0) is skipped.
 *  - Currents (NAWhirl2000, "Current's too strong."): force function
 *    0x63BD80 (thiscall (pos*, out*), ret 8; slots 0x7F0AD0 and 0x7D952C)
 *    returns "no force" (0, *out = 0) when asked about the shark's position.
 *
 * Hooks are vtable slot swaps in .rdata, each checked against the stock
 * function first.
 */

/* Installs the hooks once; returns false if any slot didn't match. */
bool InstallNoclipGuards();

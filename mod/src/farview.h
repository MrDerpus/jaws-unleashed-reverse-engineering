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
 * Far view (Shift+F4, 2026-10-17): longer draw distance at runtime, in any
 * level, without editing level files. Values from the OPEN_S tests
 * (edited_levels/FAR_X.GDW, user-confirmed): camera far plane 600 -> 3000,
 * above-water fog -> 1000..2900, underwater fog -> 100..400. Underwater fog
 * ends past ~400 made objects flicker or vanish (and 2500 crashed), because
 * underwater the fog end is also the camera's far plane.
 *
 * Engine side (decompiled 2026-10-17):
 *   NAWaterYCamera (action, live vtable 0x7F0120) owns the fog switching.
 *     +0x80 / +0x88   node IDs of the above / below GDFog
 *     +0x90 / +0x98   m_fogbelowstartPC / m_fogbelowendPC
 *     +0xB0 / +0xB8   m_fogstartbottom / m_fogendbottom (deep water)
 *     +0x150          0 = camera above water, 1 = below
 *   Its tick 0x62B430 copies the underwater values every frame into the below
 *   fog (+0x12C start, +0x134 end) AND the current camera's far plane
 *   (+0x11C). Going above water (0x62AC40) sets the far plane once from a
 *   linked object; nothing touches it again until the next crossing.
 *   0x5519A0(3) = current camera (cdecl), 0x6C3010 = live object by ID.
 */

/* Toggles far view. Returns the new state. */
bool ToggleFarView();
bool FarViewEnabled();

/* Call once per frame (game thread). Applies the values while enabled and
 * restores the level's own values when turned off. */
void UpdateFarView();

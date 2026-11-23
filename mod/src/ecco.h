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
 * Ecco mode (2026-10-21, Phase A of the Ecco-in-Jaws port): the movement
 * part of Ecco the Dolphin: Defender of the Future's player controller
 * (DolphCtrl tick 0x19E270 in the PS2 exe SLUS_203.94, decompiled in
 * ~/Projects/ECCO/re/dolphctrl/, write-up docs/ecco_dolphin_controller.md)
 * re-implemented in C++ and driving the Jaws shark's brick.
 *
 * Ported: all 7 movement states (0 idle/brake/back up, 1 swim with speed
 * levels, 2 charge + super charge, 3 jump, 4 tail walk, 5 180-degree turn,
 * 6 circling/barrel roll), the water physics (gravity on the part of the
 * body above the surface, direction-dependent drag), the steering rate
 * smoothing, auto-levelling ("turn up") and the idle look-at-camera
 * routine, with the 3D DolphConfig of 120NORTH (node 2337). Animation
 * frames are simulated (several state changes are timed by clip frames);
 * nothing is drawn with them yet. Left out: sonar, air, songs, HUD,
 * sounds, splashes, bone bending, side-scroll mode, Ecco's own collision.
 *
 * Hook: the player shark controller's per-frame tick (vtable 0x7F28FC slot
 * 0x48 = 0x667FB0, thiscall, no args). While Ecco mode is on the hook runs
 * the shark tick (or skips it, `skip_shark_tick 1`), then overwrites the
 * shark brick's transform with the dolphin simulation. The brick position is
 * re-read every frame, so engine collision pushes and F8 teleports carry over.
 *
 * Optional tuning file C:\jaws_ecco.txt ("key value" lines, # comments),
 * read each time Ecco mode is switched on: scale (Jaws units per Ecco unit,
 * default 4), invert_x, invert_y, skip_shark_tick, body_length (Ecco units,
 * default 3.2).
 */

/* Patches the vtable slot once. Idempotent; false if the exe differs. */
bool InstallEccoHook();

/* Turns Ecco mode on/off; returns the new state. */
bool ToggleEcco();
bool EccoEnabled();

/* Latest main-camera position (from the view matrix), used by the idle routine. */
void EccoSetCamera(float x, float y, float z);

/* Short status line for the overlay ("Ecco: swim 2 lvl 3.1 ..."). */
const char* EccoStatus();

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
 * Mod settings file jaws_config.txt next to Jaws.exe (2026-11-25; falls back
 * to jaws_config.txt when the game folder has none). "key value" lines,
 * `#` comments; re-read when the file changes.
 *
 *   controls_from   PROFILE4.sav   save whose control layout is used ("none" = off).
 *                                  A bare file name is looked up next to Jaws.exe.
 *   controls_apply  new            new = set the layout at startup, so every new
 *                                        game gets it (loaded saves keep theirs)
 *                                  all = also replace the controls of any save
 *                                        that is loaded
 *   farview / fog_off / foliage_hide / noclip / invincible / ecco_mode  on|off
 *                                  start states of Shift+F4 / F4 / F6 / F7 / F11 /
 *                                  Shift+F2 (set at start and when the line changes)
 *   key   <action> <key>           single bindings on top of controls_from (or
 *   mouse <action> <button>        of the game's startup defaults); "none"
 *   pad   <action> <button>        unbinds, 0xNN gives a raw code
 *
 *   Actions: swim turn_up turn_down turn_left turn_right charge_attack bite
 *   shark_vision stealth_attack tail_whip target_lock next_target
 *   previous_target next_body_part previous_body_part map pause dodge
 *   camera_mode (the game's controls-menu names). Key names: config.cpp.
 *   The live layout is written to jaws_controls_current.txt (game folder) in the same
 *   syntax whenever it changes (including changes made in the game's menu).
 *
 * How controls work (Jaws.exe, decompiled 2026-11-25):
 *   Live bindings = three arrays of 31 dwords indexed by action:
 *     0x8A0094 keyboard, 0x8A0208 second slot (mouse), 0x8A0300 gamepad.
 *   Startup (0x483CE0, vtable slot of the input object 0x8D67F8) copies the
 *   built-in defaults 0x8A0110 into the keyboard array, creates the devices
 *   (keyboard device -> [0x8D6818]); method 0x483F30 clears the input
 *   bindings and registers them again from the arrays.
 *   The profile (0x8D0110, = PROFILE<N>.sav) stores the 19 rebindable actions
 *   (action order table 0x7E07E0) as dwords (action << 16 | key):
 *     +0x5C keyboard (key & 0xFF), +0xA8 second slot (& 0x1FF), +0xF4 gamepad.
 *   Loading a save (0x539B30) copies those into the arrays; a NEW game
 *   (0x537090) clears the profile and copies the arrays back into it, without
 *   resetting them. That is why "load your save, quit, start a new game"
 *   keeps your layout, and why setting the arrays at startup is enough.
 */

/* Call once per frame (game thread). */
void UpdateModConfig();

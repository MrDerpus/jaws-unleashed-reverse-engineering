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
 * Lets the mod swallow keyboard input from the game while the teleport text
 * box is open, so typed digits/spaces don't trigger shark actions.
 *
 * The game reads the keyboard through DirectInput 8. All devices of a class
 * share one COM vtable, so we create a throwaway keyboard device of our own,
 * patch GetDeviceState / GetDeviceData in its vtable, and release it -- the
 * patch then applies to the game's devices too, regardless of whether they
 * were created before or after us.
 */

/* Idempotent; call once dinput8.dll is loaded (any time after startup --
 * it's a static import of Jaws.exe). */
void InstallInputBlock();

/* While true, the game sees no keys pressed and no buffered input events. */
extern bool g_block_game_input;

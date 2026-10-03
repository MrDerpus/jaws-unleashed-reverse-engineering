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
 * Player shark position / facing / teleport, via the pointer chain found by
 * decompiling Jaws.exe (2026-10-01):
 *   0x90BC04          global singleton: player shark controller (ctor at
 *                     0x664BD8 stores `this` here, dtor clears it)
 *   ctrl+0x50         the shark's scene object (brick) -- the debug
 *                     "SharkRelPos" routine at 0x671060 reads it this way
 * Brick layout (from the engine's world-matrix updater at 0x696EA0):
 *   +0x0C  flags; 0x20 = cached world matrix is stale
 *   +0x14  parent brick pointer (or null)
 *   +0x50  local transform, 4x3 floats: X/Y/Z basis rows, then translation
 *   +0x84  cached world transform (local x parent world), same layout;
 *          translation at +0xA8
 * The shark model faces its local +Z axis (head/mouth child nodes sit at
 * +Z, tail at -Z in FISH.GDW's BRTR), so the facing direction is the
 * world transform's Z basis row.
 */
#include <stddef.h>

struct SharkState {
    float x, y, z;       /* world position */
    float yaw_deg;       /* heading: 0 = +Z, 90 = +X, range [0, 360) */
    float pitch_deg;     /* + = nose up */
};

/* All reads/writes go through Read/WriteProcessMemory so a dangling pointer
 * during level load fails cleanly instead of crashing the game. */
bool ReadShark(SharkState& out);

/* Invincibility: refills current health (ctrl+0x2B0) to max health
 * (ctrl+0x2A8), and current hunger (ctrl+0x2B4) to its max (ctrl+0x2AC) --
 * the same routines compute/clamp/zero both pairs together. Both fields confirmed by decompilation: the ability-setup
 * routine at 0x53AD50 computes the max from save-file ability levels and
 * clamps current to it, and the is-dead check at 0x664770 tests
 * current <= 0. Call once per frame while enabled. */
bool RefillSharkHealth();

/* Death block: patches the shark controller's state setter (0x65EDA0,
 * thiscall SetState(state, -1, -1), ret 0xC) so requests to enter state 7
 * ("dead") are dropped while `g_block_shark_death` is set. Every death path
 * goes through it: health <= 0 (0x65D871), the scripted "DIEM" kill message
 * (0x65B871), and two timer-based deaths (0x668CC6, 0x66D4E9).
 * Idempotent; verifies the original bytes first and does nothing on a
 * different exe build. */
bool InstallDeathBlock();
extern "C" volatile int g_block_shark_death;
extern "C" volatile int g_blocked_deaths;   /* incremented per dropped death */

/* Moves the shark to a world position. Returns false (with a reason in
 * `err`) if the shark doesn't exist or memory access fails. Writes the brick's
 * local and world translation and the controller's stored last position
 * (ctrl+0x680), which the collision move sweeps from; without that, targets
 * behind terrain snapped back (2026-10-04). */
bool TeleportShark(float x, float y, float z, char* err, size_t err_sz);

/* Debug (2026-10-04): lists every place that holds a position (`want`, or the
 * shark's current one) as three consecutive floats within `tol`: the controller
 * (0x2000 bytes), the brick (0x400) and every heap object a controller
 * dword points at (0x400 each), plus one level deeper under ctrl+0x50/0x54/0x58. Used to find the collision code's stored
 * "previous position", which makes teleports into/through geometry snap
 * back. Writes one line per hit into `out` (newline-separated). Not called
 * by default; it found ctrl+0x680 and [ctrl+0x58]+0xA8. */
void ScanSharkPositionCopies(const float* want /* null = current */, float tol, char* out, size_t out_sz);

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
 * Ecco's sonar in Ecco mode (2026-10-21, step 3 of the Ecco-in-Jaws port,
 * "visual + sound only"). Ecco PS2 decompile: trigger FUN_001ABBE8, spawner
 * FUN_00304920, cone tick NASonarConeAct 0x304E40, wave tick NASonarAct
 * 0x304220 (docs/ecco_dolphin_controller.md "Step 3").
 *
 * Press F (or the middle mouse button) underwater: a cone grows from the
 * dolphin's head, pointing from the camera through the head, and fades out
 * over 32 ticks; a wave disc leaves the head along the dolphin's heading at
 * 2.4 Ecco units per tick and fades. Holding the key re-arms the 30-tick
 * cooldown (as in Ecco); no new pulse until it's released. No air cost (the
 * port has no air yet), no magnet/power sonar, no effect on Jaws objects.
 *
 * Files, all optional, in the game folder next to Jaws.exe:
 *   jaws_sonar.wav        played with PlaySound on each pulse
 *   jaws_sonar_cone.obj   cone mesh (Ecco's sonarkup Cone01, along +Z)
 *   jaws_sonar_wave.obj   wave mesh (Ecco's OilTank01#1 + #2 domes, axis Y)
 * scripts/stage_ecco_sonar.py writes all three from the extracted Ecco files.
 * Missing meshes fall back to a generated cone / ring of the same size.
 * Read when Ecco mode is switched on.
 */
#include "d3d8_iface.h"

void SonarLoad();

/* Game tick (Ecco mode on). Positions in Jaws units; fwd/up unit vectors;
 * scale = Jaws units per Ecco unit; depth = head height below the water
 * surface in Ecco units (negative = underwater), or 0 when unknown. */
void SonarTick(bool pressed, const float head[3], const float fwd[3], const float up[3],
               const float cam[3], float scale, float depth, bool have_water);

/* Remove all pulses (Ecco mode off, stage change). */
void SonarClear();

/* Draws live pulses with the given main-camera view/projection. */
void SonarDraw(IDirect3DDevice8* dev, const D3DMATRIX& view, const D3DMATRIX& proj);

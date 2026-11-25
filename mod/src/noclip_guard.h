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
 *
 * Air swim (2026-11-25, user-confirmed): the water action sets three
 * function pointers, all float cdecl f(const float* pos): 0x8B2E94 = wave
 * surface height (197 call sites), 0x8B2E98 (3 sites, unknown), 0x8B2E9C =
 * flat water level (107 sites); both return -2147483648.0 where there is no
 * water. Every caller uses `call [ptr]`, so while no-clip is on the mod
 * points 0x8B2E94 and 0x8B2E9C at wrappers that tell callers apart by
 * return address:
 *  - shark tick, wave surface: 0x66D6FB/0x66D70E (head/tail vs surface ->
 *    airborne ctrl+0x4A0 and fraction out of water, i.e. air vs water
 *    physics), 0x66D762 (near-surface ctrl+0x828), 0x66D2E4 (clears the
 *    on-ground ctrl+0x5A8), 0x66E4A7 (surface swim anim, m_felszineny),
 *    0x6703A7/0x6703EB (wake) -> surface 1000 units above the shark, also
 *    where there is no water (AQUARIUM away from the pools);
 *  - shark tick, flat level: 0x67031E/0x67033C (blocks the 0x40000 button
 *    out of water) -> same lift;
 *  - above-water camera 0x676AC0, site 0x676C3B (camera Y = water +
 *    cfg[0xDC]) -> the camera's own planned Y when above the water, so it
 *    rises with the shark instead of staying by the waves;
 *  - everything else gets the real value. NOT lifted: 0x66DDC5/0x66DDFB =
 *    m_maxdepth limit (keeps the shark at most m_maxdepth below the surface;
 *    lifting it flung the shark up ~1000 units per frame).
 * Re-installed every frame (the water action rewrites the pointers on level
 * load), put back when no-clip goes off. AIRSWIM_DEBUG=1 logs callers near
 * the shark to jaws_mod.log.
 */

/* Installs the hooks once; returns false if any slot didn't match. */
bool InstallNoclipGuards();

/* Call once per frame: installs / removes the air-swim water-height wrapper
 * to follow the F7 no-clip state. */
void UpdateNoclipAirSwim();

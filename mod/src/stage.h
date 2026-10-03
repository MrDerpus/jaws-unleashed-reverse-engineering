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
 * Stage (level) reload, via the engine's own deferred stage request
 * (decompiled 2026-10-03):
 *   0x920E24          global pointer to the engine object
 *   engine vtable     0x7F6018; slot +0x78 = 0x6C3FD0 (raw loader, loads
 *                     immediately -- never call it mid-frame), slot +0x80 =
 *                     0x6C3C50, RequestStage(flags, name): thiscall, ret 8,
 *                     does only `engine+0x40C |= flags; strcpy(engine+0x410,
 *                     name)`. The leftover dev "Open Stage" menu calls it
 *                     with (1, path).
 *   engine+0xB8       name the current stage was loaded with (the loader
 *                     copies its argument here)
 * The engine tick (0x6C7800) sees flag 1 at a safe point in its loop,
 * unloads the current world (vtbl+0x2C), loads engine+0x410 through the raw
 * loader, and re-initialises (vtbl+0x28). The .GDW is re-read from disk.
 */
#include <stddef.h>

/* Queues a reload of the current stage. Returns false (reason in `msg`)
 * if there's no engine/stage yet or the exe doesn't match; on success
 * `msg` holds the stage name. */
bool RequestStageReload(char* msg, size_t msg_sz);

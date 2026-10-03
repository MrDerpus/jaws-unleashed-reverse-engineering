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
 * Per-stage replacement of the game's on-screen messages (2026-10-04),
 * from the hand-editable C:\jaws_messages.txt:
 *     <STAGE or *> <slot> <text>      e.g.  TEST 598 SWIM IN TO LEAVE!\n\nPRESS ^OK^ ...
 * `#` lines are comments, `\n` in the text is a line break, ^OK^ / ^CANCEL^
 * / ^CONT^ are the game's button tokens. Slot numbers: docs/game_messages.txt
 * (scripts/dump_messages.py). The file is re-read when it changes.
 *
 * How it works (Jaws.exe, decompiled): [0x854D14 + 4*lang] -> 5 language
 * tables of 1000 message pointers (English first, 0x84FEF0, writable .data).
 * Code asks for a message by its English text; FUN_00453d00 hashes the text
 * (case-insensitive, hash built once at startup from the ORIGINAL strings)
 * to a number and returns tables[lang][number - 1]. So repointing a table
 * slot changes what's shown, and the lookup itself keeps working. Every
 * language's slot is repointed; originals are restored when the stage
 * changes to one without overrides.
 */

/* Call once per frame: applies/restores overrides when the loaded stage or
 * the file changes. Cheap when nothing changed. */
void UpdateMessageOverrides();

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
// Usage (headless postScript): SplitReadOnly.java <hex split address>
// Split the memory block containing the address there and mark the part below it read-only,
// so the decompiler folds constant-pool words (field offsets, call targets) into constants.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.*;
public class SplitReadOnly extends GhidraScript {
    @Override
    public void run() throws Exception {
        Address a = toAddr(Long.parseLong(getScriptArgs()[0], 16));
        Memory m = currentProgram.getMemory();
        MemoryBlock b = m.getBlock(a);
        if (!b.getStart().equals(a)) m.split(b, a);
        MemoryBlock low = m.getBlock(a.subtract(1));
        low.setWrite(false);
        for (MemoryBlock x : m.getBlocks())
            println(x.getName() + " " + x.getStart() + "-" + x.getEnd() + " r" + x.isRead() + " w" + x.isWrite() + " x" + x.isExecute());
    }
}

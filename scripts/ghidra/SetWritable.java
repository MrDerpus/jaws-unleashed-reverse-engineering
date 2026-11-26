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
// Usage (headless postScript): SetWritable.java <hex start> <hex end>
// Split memory at start and end and mark [start, end) writable (e.g. a .data area inside a
// range made read-only by SplitReadOnly.java).
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.*;
public class SetWritable extends GhidraScript {
    @Override
    public void run() throws Exception {
        Address s = toAddr(Long.parseLong(getScriptArgs()[0], 16));
        Address e = toAddr(Long.parseLong(getScriptArgs()[1], 16));
        Memory m = currentProgram.getMemory();
        for (Address a : new Address[] {s, e}) {
            MemoryBlock b = m.getBlock(a);
            if (b != null && !b.getStart().equals(a)) m.split(b, a);
        }
        m.getBlock(s).setWrite(true);
        for (MemoryBlock x : m.getBlocks())
            println(x.getName() + " " + x.getStart() + "-" + x.getEnd() + " w" + x.isWrite());
    }
}

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
// Usage (headless postScript): CreateFuncs.java <file with one hex address per line>
// Disassembles at each address and creates a function there if there isn't one already
// (for call targets and vtable slots the auto-analysis missed).
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import java.nio.file.*;
public class CreateFuncs extends GhidraScript {
    @Override
    public void run() throws Exception {
        int made = 0, had = 0, failed = 0;
        for (String line : Files.readAllLines(Paths.get(getScriptArgs()[0]))) {
            if (line.isBlank() || line.startsWith("#")) continue;
            Address a = toAddr(line.trim());
            if (getFunctionAt(a) != null) { had++; continue; }
            if (getInstructionAt(a) == null) {
                clearListing(a);
                new DisassembleCommand(a, null, true).applyTo(currentProgram, monitor);
            }
            CreateFunctionCmd c = new CreateFunctionCmd(a);
            if (c.applyTo(currentProgram, monitor)) made++; else failed++;
        }
        println("CreateFuncs: created " + made + ", already there " + had + ", failed " + failed);
    }
}

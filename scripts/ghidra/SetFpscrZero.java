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
// Usage (headless postScript): SetFpscrZero.java
// SH-4: assume FPSCR.PR = 0 (single precision) and FPSCR.SZ = 0 (32-bit fmov) everywhere,
// so the decompiler doesn't fork every float operation on the unknown FPU mode.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.ProgramContext;
import java.math.BigInteger;
public class SetFpscrZero extends GhidraScript {
    @Override
    public void run() throws Exception {
        ProgramContext pc = currentProgram.getProgramContext();
        var min = currentProgram.getMinAddress(); var max = currentProgram.getMaxAddress();
        for (String n : new String[] {"FPSCR_PR", "FPSCR_SZ"}) {
            Register r = currentProgram.getRegister(n);
            if (r == null) { println("no register " + n); continue; }
            pc.setValue(r, min, max, BigInteger.ZERO);
            println("set " + n + " = 0");
        }
    }
}

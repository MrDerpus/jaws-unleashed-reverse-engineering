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

// Usage (headless postScript): DecompAt.java <outfile> <hexaddr> [hexaddr ...]
// Decompiles the function containing each address, plus lists callers.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import java.io.*;

public class DecompAt extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        PrintWriter out = new PrintWriter(new FileWriter(args[0]));
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        for (int i = 1; i < args.length; i++) {
            Address a = toAddr(args[i]);
            Function f = getFunctionContaining(a);
            if (f == null) { out.println("==== " + args[i] + ": no function (data?)");
                for (Reference r : getReferencesTo(a)) {
                    Function g = getFunctionContaining(r.getFromAddress());
                    out.println("  ref from " + r.getFromAddress() + " " + r.getReferenceType() + " in " + (g == null ? "<none>" : g.getName()));
                }
                continue; }
            out.println("==== " + f.getName() + " @ " + f.getEntryPoint());
            for (Reference r : getReferencesTo(f.getEntryPoint()))
                out.println("  called from " + r.getFromAddress());
            DecompileResults res = dec.decompileFunction(f, 120, monitor);
            if (res.decompileCompleted()) out.println(res.getDecompiledFunction().getC());
        }
        out.close();
    }
}

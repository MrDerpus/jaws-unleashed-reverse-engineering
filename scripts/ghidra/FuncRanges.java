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

// List every function with its body ranges (read-only), for the scripts/ecco_jaws_*.py matchers.
// Usage: -postScript FuncRanges.java <out.tsv>
// Output: entry<TAB>name<TAB>start-end[<TAB>start-end...] (hex)
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import java.io.*;

public class FuncRanges extends GhidraScript {
    @Override
    public void run() throws Exception {
        try (PrintWriter w = new PrintWriter(new FileWriter(getScriptArgs()[0]))) {
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                StringBuilder sb = new StringBuilder(f.getEntryPoint().toString());
                sb.append('\t').append(f.getName(true));
                for (AddressRange r : f.getBody()) sb.append('\t').append(r.getMinAddress()).append('-').append(r.getMaxAddress());
                w.println(sb);
            }
        }
    }
}

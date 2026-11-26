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
// Usage (headless postScript): UnapplyNames.java <tsv>
// Each line: <hexaddr>[\t...]. Resets the function at addr to its default name (global namespace) and
// removes plate-comment lines starting with "1999->2000 match" or "source file (" (undoes ApplyLabels/ApplyComments).
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
public class UnapplyNames extends GhidraScript {
    @Override
    public void run() throws Exception {
        int n = 0;
        for (String line : Files.readAllLines(Paths.get(getScriptArgs()[0]))) {
            if (line.isBlank() || line.startsWith("#")) continue;
            Address a = toAddr(line.split("\t")[0]);
            Function f = getFunctionAt(a);
            if (f != null) {
                f.setParentNamespace(currentProgram.getGlobalNamespace());
                f.setName(null, SourceType.DEFAULT);
            }
            String c = getPlateComment(a);
            if (c != null) {
                String k = Arrays.stream(c.split("\n")).filter(s -> !s.startsWith("1999->2000 match") && !s.startsWith("source file (")).collect(Collectors.joining("\n"));
                setPlateComment(a, k.isEmpty() ? null : k);
            }
            n++;
        }
        println("UnapplyNames: " + n + " reset");
    }
}

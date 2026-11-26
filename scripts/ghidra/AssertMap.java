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

// Usage (headless postScript): AssertMap.java <outfile>
// For every "GDASSERT failed on:" string: find the functions that use it (directly or via an
// SH-4 constant-pool word), decompile them and print every C line that mentions GDASSERT,
// so the source file name and line number passed to the assert handler are visible.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;

public class AssertMap extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        PrintWriter out = new PrintWriter(new FileWriter(args[0]));
        Memory mem = currentProgram.getMemory();
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        byte[] pat = "GDASSERT failed on:".getBytes("ISO-8859-1");
        Map<Function, List<String>> funcs = new TreeMap<>((x, y) -> x.getEntryPoint().compareTo(y.getEntryPoint()));
        Address a = mem.getMinAddress();
        while ((a = mem.findBytes(a, pat, null, true, monitor)) != null) {
            Set<Function> fs = new LinkedHashSet<>();
            for (Reference r : getReferencesTo(a)) {
                Function f = getFunctionContaining(r.getFromAddress());
                if (f != null) { fs.add(f); continue; }
                for (Reference r2 : getReferencesTo(r.getFromAddress())) {
                    Function g = getFunctionContaining(r2.getFromAddress());
                    if (g != null) fs.add(g);
                }
            }
            // fallback: scan memory for the raw pointer value (pool words Ghidra didn't mark)
            if (fs.isEmpty()) {
                long v = a.getOffset();
                byte[] le = new byte[] {(byte) v, (byte) (v >> 8), (byte) (v >> 16), (byte) (v >> 24)};
                Address p = mem.getMinAddress();
                while ((p = mem.findBytes(p, le, null, true, monitor)) != null) {
                    for (Reference r2 : getReferencesTo(p)) {
                        Function g = getFunctionContaining(r2.getFromAddress());
                        if (g != null) fs.add(g);
                    }
                    Function g = getFunctionBefore(p);
                    if (fs.isEmpty() && g != null && p.subtract(g.getBody().getMaxAddress()) < 0x400) fs.add(g);
                    p = p.add(1);
                }
            }
            String s = readString(a);
            if (fs.isEmpty()) out.println("UNREFERENCED " + a + " " + s);
            for (Function f : fs) funcs.computeIfAbsent(f, k -> new ArrayList<>()).add(s);
            a = a.add(pat.length);
        }
        for (Map.Entry<Function, List<String>> e : funcs.entrySet()) {
            Function f = e.getKey();
            out.println("==== " + f.getEntryPoint() + " " + f.getName() + " size " + f.getBody().getNumAddresses());
            DecompileResults res = dec.decompileFunction(f, 120, monitor);
            if (res.decompileCompleted()) {
                String[] L = res.getDecompiledFunction().getC().split("\n");
                for (int i = 0; i < L.length; i++) {
                    if (!L[i].contains("GDASSERT")) continue;
                    int s0 = i; while (s0 > 0 && !L[s0 - 1].trim().endsWith(";") && !L[s0 - 1].trim().endsWith("{") && !L[s0 - 1].trim().endsWith("}") && i - s0 < 4) s0--;
                    StringBuilder sb = new StringBuilder();
                    for (int j = s0; j < L.length && j < i + 6; j++) { sb.append(L[j].trim()).append(' '); if (L[j].trim().endsWith(";")) break; }
                    out.println("   " + sb);
                }
            } else out.println("   (decompile failed) " + e.getValue());
        }
        out.close();
    }

    private String readString(Address a) throws Exception {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 300; i++) {
            byte b = currentProgram.getMemory().getByte(a.add(i));
            if (b == 0) break;
            sb.append((char) (b & 0xff));
        }
        return sb.toString().replace("\n", "\\n");
    }
}

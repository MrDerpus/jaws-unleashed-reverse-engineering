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

// Decompile every function that references the given addresses, and/or the
// function containing an address given as f:ADDR (created if missing).
// Each decompiled function is followed by its callers/references.
// Usage: -postScript RefsDecomp.java <out.txt> <addr|f:addr> [...]
// Note: Ghidra fails to load scripts from paths containing a dash (OSGi
// bundle error); run it from this folder or another dash-free path.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import java.io.*; import java.util.*;
public class RefsDecomp extends GhidraScript {
  public void run() throws Exception {
    String[] a = getScriptArgs();
    PrintWriter out = new PrintWriter(new FileWriter(a[0]));
    DecompInterface dec = new DecompInterface(); dec.openProgram(currentProgram);
    Set<Function> done = new HashSet<>();
    for (int i=1;i<a.length;i++){
      if (a[i].startsWith("f:")) { Address fa=toAddr(a[i].substring(2)); Function f=getFunctionContaining(fa); if(f==null){disassemble(fa); f=createFunction(fa,null);} if(f==null){out.println("no func "+a[i]);continue;}
        DecompileResults res = dec.decompileFunction(f,120,monitor); out.println("==== "+f.getName()+" @ "+f.getEntryPoint()); out.println(res.getDecompiledFunction()==null?"(fail)":res.getDecompiledFunction().getC());
        for (Reference cr : getReferencesTo(f.getEntryPoint())) { Function c=getFunctionContaining(cr.getFromAddress()); out.println("   caller/ref: "+cr.getFromAddress()+" "+(c==null?"":c.getName())); }
        continue; }
      Address t = toAddr(a[i]);
      out.println("#### refs to "+a[i]);
      for (Reference r : getReferencesTo(t)) {
        Function f = getFunctionContaining(r.getFromAddress());
        out.println("  from "+r.getFromAddress()+" in "+(f==null?"none":f.getName()+"@"+f.getEntryPoint()));
        if (f!=null && done.add(f)) {
          DecompileResults res = dec.decompileFunction(f,120,monitor);
          out.println("==== "+f.getName()+" @ "+f.getEntryPoint());
          out.println(res.getDecompiledFunction()==null?"(fail)":res.getDecompiledFunction().getC());
          for (Reference cr : getReferencesTo(f.getEntryPoint())) { Function c=getFunctionContaining(cr.getFromAddress()); out.println("   caller: "+cr.getFromAddress()+" "+(c==null?"":c.getName())); }
        }
      }
    }
    out.close();
  }
}

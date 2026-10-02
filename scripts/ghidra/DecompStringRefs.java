// Usage (headless postScript): DecompStringRefs.java <outfile> <string1> [string2 ...]
// For each exact-match defined string, decompiles every function that references it.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import java.io.*;
import java.util.*;

public class DecompStringRefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        PrintWriter out = new PrintWriter(new FileWriter(args[0]));
        Set<String> wanted = new HashSet<>(Arrays.asList(args).subList(1, args.length));
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        Set<Function> done = new HashSet<>();
        for (Data d : currentProgram.getListing().getDefinedData(true)) {
            if (!d.hasStringValue()) continue;
            Object v = d.getValue();
            if (v == null || !wanted.contains(v.toString())) continue;
            out.println("==== STRING \"" + v + "\" @ " + d.getAddress());
            for (Reference r : getReferencesTo(d.getAddress())) {
                Function f = getFunctionContaining(r.getFromAddress());
                out.println("  ref from " + r.getFromAddress() + " in " + (f == null ? "<none>" : f.getName() + " @ " + f.getEntryPoint()));
                if (f == null || !done.add(f)) continue;
                DecompileResults res = dec.decompileFunction(f, 120, monitor);
                if (res.decompileCompleted())
                    out.println("---- " + f.getName() + " @ " + f.getEntryPoint() + "\n" + res.getDecompiledFunction().getC());
            }
        }
        out.close();
    }
}

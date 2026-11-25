# SPDX-License-Identifier: GPL-3.0-or-later
#
# Jaws Unleashed reverse engineering tools
# Copyright (C) 2026 MrDerpus and contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Spread Defender (ECCO.ELF) names over Jaws.exe through the call graph, starting from known pairs.

For a known pair (Defender function E, Jaws function J), both callee lists are aligned in order (dynamic
programming: already-paired callees must line up, unknown ones may pair with unknown ones). An unknown callee
pair that falls between two aligned known neighbours (or at the ends of lists whose known callees all line
up) Every known pair votes for all pairings of its still-unknown callees (and, separately, of its unknown
callers), each pairing weighted 1/(unknown on one side * unknown on the other). A pairing is accepted when it is
the best for both sides, reaches MIN_SCORE and beats the runner-up on either side by MARGIN. The loop repeats
(each round shrinks the unknown sets) until nothing new is found. Call order is ignored on purpose: the two
compilers order calls differently and Jaws turned some direct calls into virtual ones.

Defender callees: SH-4 `bsr` targets and `mov.l @(disp,PC)` loads of function addresses, in code order.
Jaws callees: x86 `call rel32` / `jmp rel32` to function entries (thunks followed), in address order.

With --map 0.MAP (Defender's linker map) a locality phase runs too: functions of one source file are laid
out in source order in both binaries, so the unnamed functions between two named ones from the same file are
paired in order when both gaps hold the same number of functions.

Usage:
  python3 -I ecco_jaws_callgraph.py [--map 0.MAP] ECCO.ELF Jaws.exe JAWS_FUNCS.tsv OUT.tsv SEED.tsv [SEED.tsv ...]
SEED files: first column Jaws address (hex), a column named `ecco_symbol` with the Defender symbol.
OUT.tsv: jaws_addr, name, ecco_symbol, source (seed file name or 'callgraph'), votes, round.
"""
import os
import struct
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ecco_jaws_vtables import Elf, Pe, demangle  # noqa: E402

MIN_SCORE = 1.0   # summed vote weight a pair needs
MARGIN = 2.0      # and it must beat the runner-up (either side) by this factor
MAX_LIST = 16     # skip callee/caller lists longer than this (too ambiguous)
MAX_GAP = 6       # locality phase: largest gap filled in order


def defender_callgraph(elf):
    st = [s for s in elf.secs if s[1] == 2][0]
    strs = elf.secs[st[6]]
    funcs = {}
    for i in range(st[5] // 16):
        nm, val, size, info, _, _ = struct.unpack_from('<IIIBBH', elf.d, st[4] + i * 16)
        if info & 15 == 2 and size:
            n = elf.d[strs[4] + nm:elf.d.index(b'\0', strs[4] + nm)].decode('latin-1')
            funcs.setdefault(val, (n, size))
    by_name = {n: a for a, (n, _) in funcs.items()}

    def off(va):
        for s in elf.secs:
            if s[1] == 1 and s[3] and s[3] <= va < s[3] + s[5]:
                return va - s[3] + s[4]
    calls = {}
    for a, (n, size) in funcs.items():
        o = off(a)
        out = []
        for k in range(0, size - 1, 2):
            h = struct.unpack_from('<H', elf.d, o + k)[0]
            pc = a + k
            tgt = None
            if h >> 12 == 0xB:                           # bsr disp12
                disp = h & 0xFFF
                if disp & 0x800:
                    disp -= 0x1000
                tgt = pc + 4 + disp * 2
            elif h >> 12 == 0xD:                         # mov.l @(disp,PC),Rn
                la = (pc & ~3) + 4 + (h & 0xFF) * 4
                if la < a + size + 0x400:
                    tgt = elf.u32(la)
            if tgt in funcs and tgt != a:
                out.append(funcs[tgt][0])
        calls[n] = dedupe(out)
    return calls, by_name


def jaws_bodies(pe, path, want_names=False):
    t = [s for s in pe.secs if s[0] == b'.text'][0]
    entries, bodies, names = set(), {}, {}
    for line in open(path):
        p = line.rstrip('\n').split('\t')
        if len(p) < 3:
            continue
        e = int(p[0], 16)
        entries.add(e)
        names[e] = p[1]
        bodies[e] = [tuple(int(x, 16) for x in r.split('-')) for r in p[2:]]

    def code(a, b):
        return pe.d[a - t[1] + t[3]:b + 1 - t[1] + t[3]]

    # Ghidra misses most vtable-only functions: add every vtable slot and every direct call target as an
    # entry; such functions get a body from their entry up to the next known entry.
    txt = code(t[1], t[1] + t[4] - 1)
    extra = set()
    for vt in pe.vt_starts:
        for f in pe.vtable(vt):
            extra.add(f)
    for k in range(len(txt) - 4):
        if txt[k] == 0xE8:
            tgt = t[1] + k + 5 + struct.unpack_from('<i', txt, k + 1)[0]
            if t[1] <= tgt < t[1] + t[4] and (tgt & 0xF) == 0 and txt[tgt - t[1] - 1] in (0x90, 0xCC, 0xC3):
                extra.add(tgt)
    extra -= entries
    allent = sorted(entries | extra)
    import bisect
    for e in extra:
        i = bisect.bisect_right(allent, e)
        end = allent[i] - 1 if i < len(allent) else e + 0x100
        bodies[e] = [(e, min(end, e + 0x4000))]
        names[e] = 'FUN_%08x' % e
    entries |= extra
    return (bodies, names) if want_names else bodies


def jaws_callgraph(pe, path):
    t = [s for s in pe.secs if s[0] == b'.text'][0]
    bodies, names = jaws_bodies(pe, path, True)
    entries = set(bodies)

    def code(a, b):
        return pe.d[a - t[1] + t[3]:b + 1 - t[1] + t[3]]

    def resolve(x):
        # follow a thunk (single jmp) to its target
        for _ in range(3):
            c = code(x, x + 4)
            if names.get(x, '').startswith('thunk_') and c[:1] == b'\xe9':
                x = x + 5 + struct.unpack_from('<i', c, 1)[0]
            else:
                break
        return x
    calls = {}
    for e, rs in bodies.items():
        out = []
        for a, b in rs:
            if not (t[1] <= a < t[1] + t[4]):
                continue
            c = code(a, b)
            k = 0
            while k < len(c) - 4:
                if c[k] in (0xE8, 0xE9):
                    tgt = a + k + 5 + struct.unpack_from('<i', c, k + 1)[0]
                    if tgt in entries and tgt != e:
                        out.append(resolve(tgt))
                        k += 5
                        continue
                k += 1
        calls[e] = dedupe(out)
    return calls, names


def dedupe(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


j2e_global = {}
MAP = None


def map_files(path):
    """Linker map: (class, method) -> object file, from lines like `0x8c0466d0   GDFile::_ReadInt(int&)`."""
    import re
    out, cur = {}, None
    for line in open(path, encoding='latin-1'):
        m = re.match(r'From file: (\S+)(?:\s+subfile: (\S+))?', line)
        if m:
            cur = m.group(2) or m.group(1)
            continue
        m = re.match(r'0x[0-9a-f]{8}\s+\*?\s*(\w+)::_{1,3}(\w+)\(', line)
        if m and cur:
            out.setdefault((m.group(1), m.group(2)), cur)
    return out


def sandwich(e2j, info, rnd, dorder, jentries):
    """Between two consecutive named Jaws functions that come from the same Defender file in the same order,
    pair the unnamed functions in order when both gaps hold the same number (1..MAX_GAP)."""
    import bisect
    anchors = sorted((j, e) for j, e in j2e_global.items() if e in dorder)
    new = 0
    for (j1, e1), (j2, e2) in zip(anchors, anchors[1:]):
        f1, i1, lst = dorder[e1]
        f2, i2, _ = dorder[e2]
        if f1 != f2 or i2 <= i1 + 1:
            continue
        dmid = [n for _, n in lst[i1 + 1:i2]]
        a, b = bisect.bisect_right(jentries, j1), bisect.bisect_left(jentries, j2)
        jmid = jentries[a:b]
        if any(n in e2j for n in dmid) or any(j in j2e_global for j in jmid):
            continue
        if not (1 <= len(dmid) <= MAX_GAP) or len(dmid) != len(jmid):
            continue
        for n, j in zip(dmid, jmid):
            e2j[n] = j
            j2e_global[j] = n
            info[j] = ('locality', 0, rnd)
            new += 1
    return new


def main():
    global MAP
    if '--map' in sys.argv:
        k = sys.argv.index('--map')
        MAP = sys.argv[k + 1]
        del sys.argv[k:k + 2]
    if len(sys.argv) < 6:
        raise SystemExit(__doc__)
    elf, pe = Elf(sys.argv[1]), Pe(sys.argv[2])
    ecalls, ebyname = defender_callgraph(elf)
    jcalls, jnames = jaws_callgraph(pe, sys.argv[3])

    e2j, info = {}, {}
    for seed in sys.argv[5:]:
        rows = open(seed).read().splitlines()
        hdr = rows[0].split('\t')
        col = hdr.index('ecco_symbol')
        for r in rows[1:]:
            p = r.split('\t')
            j, e = int(p[0], 16), p[col]
            if e in e2j or j in j2e_global:
                continue
            e2j[e] = j
            j2e_global[j] = e
            info[j] = (os.path.basename(seed), 0, 0)
    print('seeds: %d pairs; Defender functions %d, Jaws functions %d' % (len(e2j), len(ecalls), len(jcalls)))

    # Defender function order per source file (from the linker map) and Jaws entry order, for the locality
    # phase; the map belongs to a slightly different build, so files are looked up by class + method name
    dorder, jentries = {}, sorted(jcalls)
    if MAP:
        fileof = map_files(MAP)
        per = defaultdict(list)
        for n, a in ebyname.items():
            c, m = demangle(n)
            if c is None:
                continue
            f = fileof.get((c, {'~' + c: 'dt', c: 'ct'}.get(m, m)))
            if f:
                per[f].append((a, n))
        for f, lst in per.items():
            lst.sort()
            for i, (_, n) in enumerate(lst):
                dorder[n] = (f, i, lst)

    # callers (reverse graph) for the second direction
    ecallers, jcallers = defaultdict(list), defaultdict(list)
    for e, lst in ecalls.items():
        for x in lst:
            ecallers[x].append(e)
    for j, lst in jcalls.items():
        for y in lst:
            jcallers[y].append(j)

    rnd = 0
    while True:
        rnd += 1
        score = defaultdict(float)
        for e, j in list(e2j.items()):
            for E, J in ((ecalls.get(e, []), jcalls.get(j, [])), (ecallers.get(e, []), jcallers.get(j, []))):
                Eu = [x for x in E if x not in e2j]
                Ju = [y for y in J if y not in j2e_global]
                if not Eu or not Ju or len(Eu) > MAX_LIST or len(Ju) > MAX_LIST:
                    continue
                w = 1.0 / (len(Eu) * len(Ju))
                for x in Eu:
                    for y in Ju:
                        score[(x, y)] += w
        best_e, best_j = defaultdict(list), defaultdict(list)
        for (x, y), v in score.items():
            best_e[x].append((v, y))
            best_j[y].append((v, x))
        new = 0
        for x, lst in best_e.items():
            lst.sort(reverse=True)
            v, y = lst[0]
            if v < MIN_SCORE or (len(lst) > 1 and lst[1][0] * MARGIN > v):
                continue
            lj = sorted(best_j[y], reverse=True)
            if lj[0][1] != x or (len(lj) > 1 and lj[1][0] * MARGIN > v):
                continue
            e2j[x] = y
            j2e_global[y] = x
            info[y] = ('callgraph', v, rnd)
            new += 1
        new_cg = new
        new_loc = sandwich(e2j, info, rnd, dorder, jentries) if dorder else 0
        print('round %d: %d call-graph + %d locality pairs (total %d)' % (rnd, new_cg, new_loc, len(e2j)))
        if not new_cg and not new_loc:
            break

    with open(sys.argv[4], 'w') as f:
        f.write('jaws_addr\tname\tecco_symbol\tsource\tvotes\tround\n')
        for j in sorted(j2e_global):
            e = j2e_global[j]
            cls, meth = demangle(e)
            name = '%s::%s' % (cls, meth) if cls else e.lstrip('_')
            src, v, r = info[j]
            f.write('%08x\t%s\t%s\t%s\t%.2f\t%d\n' % (j, name, e, src, v, r))


if __name__ == '__main__':
    main()

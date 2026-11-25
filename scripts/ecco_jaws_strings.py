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

"""Match Jaws.exe functions to Ecco: Defender (ECCO.ELF) functions by the strings they use.

Defender (SH-4) loads string addresses from literal pools inside each function's symbol range; Jaws (x86)
uses them as 32-bit immediates. A string used by few functions in both games links them. Each function pair
gets a score = sum over shared strings (and 32-bit constants) of 1/(uses in Defender * uses in Jaws); a pair is kept when each side
is the other's best match and the score is at least MIN_SCORE.

Usage:
  python3 -I ecco_jaws_strings.py ECCO.ELF Jaws.exe JAWS_FUNCS.tsv OUT.tsv
JAWS_FUNCS.tsv: one line per Jaws function: entry<TAB>name<TAB>start-end[<TAB>start-end...] (hex), e.g. from
a Ghidra script listing function bodies.
OUT.tsv: jaws_addr, name, score, shared strings, ecco symbol, example string.
"""
import os
import re
import struct
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ecco_jaws_vtables import Elf, Pe, demangle  # noqa: E402

MIN_LEN = 4
MIN_SCORE = 1.0
CONSTS = True      # also match 32-bit constants (chunk tags, stamps, unusual floats)
COMMON = {0x3F800000, 0xBF800000, 0x3F000000, 0x40000000, 0xFFFFFFFF, 0x0000FFFF, 0x00FF00FF, 0xFF00FF00,
          0x80000000, 0x7FFFFFFF, 0x447A0000, 0x42C80000, 0x3DCCCCCD}


def cstring(get, va):
    raw = get(va, 120)
    if raw is None:
        return None
    end = raw.find(b'\0')
    if end < MIN_LEN:
        return None
    s = raw[:end]
    if not all(32 <= c < 127 or c in (9, 10, 13) for c in s):
        return None
    return s.decode('latin-1')


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    elf, pe = Elf(sys.argv[1]), Pe(sys.argv[2])

    # ---- Defender: strings per function
    def e_get(va, n):
        for s in elf.secs:
            if s[1] == 1 and s[3] and s[3] <= va < s[3] + s[5] and s[2] & 2:
                o = va - s[3] + s[4]
                return elf.d[o:o + n]
        return None
    st = [s for s in elf.secs if s[1] == 2][0]
    strs = elf.secs[st[6]]
    e_funcs = []
    for i in range(st[5] // 16):
        nm, val, size, info, _, _ = struct.unpack_from('<IIIBBH', elf.d, st[4] + i * 16)
        if info & 15 == 2 and size:
            n = elf.d[strs[4] + nm:elf.d.index(b'\0', strs[4] + nm)].decode('latin-1')
            e_funcs.append((val, size, n))
    # The Hitachi compiler addresses strings as <string table base> + <offset>: both are literal-pool words
    # (e.g. GetClassName: r0 = 0x8C2AD454, r2 = 0x135, add -> "NAWhirl2000"). So every pool pointer is
    # combined with every small pool constant; only results that start right after a NUL count as strings.
    e_str = defaultdict(set)          # string -> defender functions
    for val, size, n in e_funcs:
        words = [elf.u32(a) for a in range((val + 3) & ~3, val + size, 4)]
        bases = {w for w in words if 0x8C276450 <= w < 0x8C2E608C}
        offs = {w for w in words if 0 < w < 0x10000} | {0}
        found = set()
        for b in bases:
            for c in offs:
                prev = e_get(b + c - 1, 1)
                if prev != b'\0':
                    continue
                s = cstring(e_get, b + c)
                if s:
                    found.add(s)
        for s in found:
            e_str[s].add(n)
        if CONSTS:
            for w in words:
                if w >= 0x10000 and not (0x8C000000 <= w < 0x8D000000) and w not in COMMON:
                    e_str['#%08x' % w].add(n)

    # ---- Jaws: strings per function (any 32-bit immediate in a function body)
    def j_get(va, n):
        for name, sva, vs, ro, rs in pe.secs:
            if name in (b'.rdata', b'.data') and sva <= va < sva + rs:
                return pe.d[va - sva + ro:va - sva + ro + n]
        return None
    from ecco_jaws_callgraph import jaws_bodies
    t = [s for s in pe.secs if s[0] == b'.text'][0]
    j_str = defaultdict(set)
    for entry, rs in jaws_bodies(pe, sys.argv[3]).items():
        for a, b in rs:
            if not (t[1] <= a < t[1] + t[4]):
                continue
            code = pe.d[a - t[1] + t[3]:b + 1 - t[1] + t[3]]
            for k in range(len(code) - 3):
                w = struct.unpack_from('<I', code, k)[0]
                if 0x7CE000 <= w < 0xE6C000:
                    s = cstring(j_get, w)
                    if s:
                        j_str[s].add(entry)
                elif CONSTS and w >= 0x10000 and w not in COMMON and not (0x400000 <= w < 0xE6C000):
                    j_str['#%08x' % w].add(entry)

    # ---- score pairs
    score = defaultdict(float)
    count = defaultdict(int)
    nstr = defaultdict(int)     # how many of the shared tokens are real strings
    example = {}
    for s in set(e_str) & set(j_str):
        es, js = e_str[s], j_str[s]
        if len(es) > 8 or len(js) > 8:
            continue
        w = 1.0 / (len(es) * len(js))
        for e in es:
            for j in js:
                score[(e, j)] += w
                count[(e, j)] += 1
                if not s.startswith('#'):
                    nstr[(e, j)] += 1
                if (e, j) not in example or len(s) > len(example[(e, j)]):
                    example[(e, j)] = s
    best_e, best_j = {}, {}
    for (e, j), v in score.items():
        if v > best_j.get(j, (0, None))[0]:
            best_j[j] = (v, e)
        if v > best_e.get(e, (0, None))[0]:
            best_e[e] = (v, j)
    rows = []
    for j, (v, e) in best_j.items():
        # constants alone are weak: need a real string, or two or more shared constants
        if v >= MIN_SCORE and best_e[e][1] == j and (nstr[(e, j)] or count[(e, j)] >= 2):
            cls, meth = demangle(e)
            name = '%s::%s' % (cls, meth) if cls else e.lstrip('_')
            rows.append((j, name, v, count[(e, j)], e, example[(e, j)]))
    rows = [r for r in rows if r[0] % 16 == 0]   # game code is 16-byte aligned; skip C runtime internals
    rows.sort()
    with open(sys.argv[4], 'w') as f:
        f.write('jaws_addr\tname\tscore\tshared\tecco_symbol\texample\n')
        for j, name, v, c, e, ex in rows:
            f.write('%08x\t%s\t%.2f\t%d\t%s\t%s\n' % (j, name, v, c, e, re.sub(r'\s+', ' ', ex)[:60]))
    print('strings: %d Defender, %d Jaws, %d shared; %d function pairs'
          % (len(e_str), len(j_str), len(set(e_str) & set(j_str)), len(rows)))


if __name__ == '__main__':
    main()

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

"""Name the functions of a 1999 Ecco: Defender Dreamcast program (raw SH-4 1ST_READ.BIN at 0x8C010000)
from the June 2000 ECCO.ELF (symbols) and its linker map 0.map (source file of every symbol; the map is from a
slightly different link, so files are looked up by symbol name, not address).

The two compilers generate different code for the same source, so code bytes aren't compared. Phases:
  1. vtable: the 1999 vtables (one block of 8-byte slots: function pointer, 0) are split where code points
     into them; factory vtables are recognised by slot 0 (GetClassName returning the class-name string),
     class vtables through the factory's Create (slot 1) -> constructor -> vtable address. Tables with the
     same (1999, 2000) lengths are aligned as a group (columns scored by agreement on empty stubs; 1999 GDAct
     tables lack CreateProps, so Execute is 1999 slot 9 = 2000 slot 10), then each table is aligned with
     the ELF vtable of the same class using the votes (dynamic programming). An empty stub never pairs
     with a getter.
  2. strings: functions that use the same rare strings/constants (weak: 2000 code reaches most strings
     through packed blocks); best match both ways and score >= MIN_STR_SCORE.
  3. callgraph: matched pairs vote for pairings of their unknown callees and callers (order-insensitive).
  4. locality: equal-sized gaps between two matches from the same source file are paired in order.
  Phases 3-4 repeat until nothing changes.
Usage:
  python3 -I scripts/ecco1999_match.py ECCO.ELF 0.map 1ST_READ.BIN FUNCS.tsv OUT.tsv
FUNCS.tsv: entry<TAB>name<TAB>start-end... (hex), Ghidra's function list of the 1999 program
(scripts/ghidra/FuncRanges.java); vtable slots add the entries Ghidra missed.
OUT.tsv: addr, size, ecco_symbol, demangled, source_file, method.
OUT_files.tsv: every function with its source file: 'matched', 'vtable' (unnamed slot of a vtable whose
  matched slots all come from one file) or 'inferred' (between two anchors from the same file).
Read-only."""
import os
import re
import struct
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ecco_jaws_vtables import Elf, demangle  # noqa: E402

BASE99 = 0x8C010000
MIN_SCORE = 1.0
MIN_STR_SCORE = 2.0
SIZE_RATIO = 3.0
MARGIN = 2.0
MAX_LIST = 24
MAX_GAP = 8


def ends(words):
    """Code length (in words) by linear sweep: stop after rts/jmp/bra + delay slot past the last branch target."""
    far = 0
    i = 0
    n = len(words)
    while i < n:
        w = words[i]
        hi = w >> 12
        if w & 0xFF00 in (0x8900, 0x8B00, 0x8D00, 0x8F00):          # bt/bf(/s)
            d = w & 0xFF
            d = d - 256 if d > 127 else d
            far = max(far, i + 2 + d)
        elif hi == 0xA:                                              # bra
            d = w & 0xFFF
            d = d - 4096 if d > 2047 else d
            t = i + 2 + d
            if 0 <= t < n:
                far = max(far, t)
            if i + 1 >= far:
                return i + 2
        elif w == 0x000B or (w & 0xF0FF) == 0x402B:                  # rts / jmp @Rn
            if i + 1 >= far:
                return i + 2
        i += 1
    return n


class Prog:
    def __init__(self, get_bytes, funcs):
        """funcs: {addr: max_size}."""
        self.get = get_bytes
        self.f = {}
        for a, sz in funcs.items():
            raw = get_bytes(a, sz)
            if not raw or len(raw) < 2:
                continue
            self.f[a] = (None, len(raw), sz)

    def u32(self, va):
        b = self.get(va, 4)
        return struct.unpack('<I', b)[0] if b and len(b) == 4 else None

    def u16(self, va):
        b = self.get(va, 2)
        return struct.unpack('<h', b)[0] if b and len(b) == 2 else None

    def cstr(self, va):
        b = self.get(va, 100)
        if not b:
            return None
        e = b.find(b'\0')
        if e < 4 or not all(32 <= c < 127 or c in (9, 10) for c in b[:e]):
            return None
        return b[:e].decode('latin-1')

    def analyse(self, is_func):
        """Per function, from every aligned 32-bit word in its range (code + literal pool): strings,
        constants and function pointers (in pool order), plus bsr targets; and a coarse opcode profile."""
        self.strs, self.consts, self.calls, self.prof = {}, {}, {}, {}
        for a, (words, nbytes, sz) in self.f.items():
            strs, consts, calls = [], [], []
            raw = self.get(a, sz) or b''
            words = struct.unpack_from('<%dH' % (len(raw) // 2), raw)
            pool = []
            for i, w in enumerate(words):
                if w >> 12 == 0xD:                                   # mov.l @(disp,PC),Rn
                    ea = ((a + 2 * i) & ~3) + 4 + (w & 0xFF) * 4
                    if a <= ea < a + len(raw) - 3:
                        pool.append(ea)
            if pool:
                start = min(pool)
                pool = set(pool) | set(range(start, a + len(raw) - 3, 4))
            for ea in sorted(set(pool)):
                v = struct.unpack_from('<I', raw, ea - a)[0]
                if 0x8C010000 <= v < 0x8D000000:
                    if is_func(v):
                        calls.append(v)
                    else:
                        s = self.cstr(v)
                        if s:
                            strs.append(s)
                elif v not in (0, 0x3F800000, 0xBF800000, 0x3F000000, 0xFFFFFFFF) and v > 0xFFFF:
                    consts.append(v)
            for i, w in enumerate(struct.unpack_from('<%dH' % (len(raw) // 2), raw)):
                if w >> 12 == 0xB:
                    dsp = w & 0xFFF
                    dsp = dsp - 4096 if dsp > 2047 else dsp
                    t = a + 2 * i + 4 + 2 * dsp
                    if is_func(t):
                        calls.append(t)
            self.strs[a] = strs
            self.consts[a] = consts
            self.calls[a] = calls


def elf_key(sym):
    cls, meth = demangle(sym)
    if cls:
        if meth == cls:
            meth = '__ct'
        elif meth == '~' + cls:
            meth = '__dt'
        return (cls, meth)
    base = sym[1:] if sym.startswith('_') else sym
    base = re.sub(r'__F.*$', '', base)
    return (None, base)


def map_key(text):
    m = re.match(r'([A-Za-z_]\w*)::_(\w+?)\(', text)
    if m:
        meth = m.group(2)
        meth = {'__ct': '__ct', '__dt': '__dt'}.get(meth, meth)
        return (m.group(1), meth.lstrip('_') if meth not in ('__ct', '__dt') else meth)
    m = re.match(r'_(\w+)', text)
    return (None, m.group(1)) if m else (None, text)


def sh4_pool_and_calls(get, f, code_end, limit=400):
    """mov.l pool values and bsr targets of the function at f, up to its first rts (+ delay slot)."""
    vals, calls = [], []
    for i in range(limit):
        b = get(f + 2 * i, 2)
        if not b or len(b) < 2:
            break
        w = struct.unpack('<H', b)[0]
        if w >> 12 == 0xD:
            ea = ((f + 2 * i) & ~3) + 4 + (w & 0xFF) * 4
            bb = get(ea, 4)
            if bb and len(bb) == 4:
                vals.append(struct.unpack('<I', bb)[0])
        elif w >> 12 == 0xB:
            dd = w & 0xFFF
            dd = dd - 4096 if dd > 2047 else dd
            calls.append(f + 2 * i + 4 + 2 * dd)
        if w == 0x000B:
            break
    return vals, calls


def vtables99(d, code_end):
    """1999 program: the vtable block (8-byte slots: function pointer, 0), split at the addresses code
    references; factories (slot 0 returns the class name) and class vtables (factory Create -> ctor -> vtable)."""
    get = lambda va, n: d[va - BASE99:va - BASE99 + n] if 0 <= va - BASE99 < len(d) else None
    slots = {}
    for o in range(code_end - BASE99, len(d) - 8, 4):
        w0, w1 = struct.unpack_from('<II', d, o)
        if BASE99 <= w0 < code_end and w0 % 2 == 0 and w1 == 0:
            slots[BASE99 + o] = w0
    runs, prev = [], None
    for a in sorted(slots):
        if prev is not None and a == prev + 8:
            runs[-1].append(a)
        else:
            runs.append([a])
        prev = a
    vt = {}
    for run in runs:
        if len(run) < 8:
            continue
        lo, hi = run[0], run[-1] + 8
        starts = set()
        for o in range(0, code_end - BASE99, 4):
            v = struct.unpack_from('<I', d, o)[0]
            if lo <= v < hi and (v - lo) % 8 == 0:
                starts.add(v)
        starts = sorted(starts)
        for s, e in zip(starts, starts[1:] + [hi]):
            vt[s] = [slots.get(a) for a in range(s, e, 8)]

    def cstr(a):
        b = get(a, 80)
        if not b:
            return None
        e = b.find(b'\0')
        return b[:e].decode('latin-1') if e > 0 and all(32 <= c < 127 for c in b[:e]) else None
    fact = {}
    for s, sl in vt.items():
        if len(sl) >= 5 and sl[0]:
            vals, _ = sh4_pool_and_calls(get, sl[0], code_end, 6)
            if vals and cstr(vals[0]) and re.match(r'^[A-Za-z_]\w*$', cstr(vals[0])):
                fact[s] = cstr(vals[0])
    cls = {}
    for s, name, slot, suffix in [(s, n, k, sfx) for s, n in fact.items() for k, sfx in ((1, ''), (2, 'Props'))]:
        if len(vt[s]) <= slot:
            continue
        cr = vt[s][slot]
        name = name + suffix
        if not cr:
            continue
        vals, calls = sh4_pool_and_calls(get, cr, code_end)
        found = [v for v in vals if v in vt]
        if not found:
            for g in [v for v in vals if BASE99 <= v < code_end] + calls:
                vv, _ = sh4_pool_and_calls(get, g, code_end)
                found = [v for v in vv if v in vt]
                if found:
                    break
        if found and found[0] not in cls:
            cls[found[0]] = name
    return vt, fact, cls


def align(xs, ys, score):
    """Global alignment of two slot lists maximizing summed score (gaps free); returns index pairs."""
    n, m = len(xs), len(ys)
    D = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            D[i][j] = max(D[i + 1][j], D[i][j + 1], D[i + 1][j + 1] + score(xs[i], ys[j]))
    out, i, j = [], 0, 0
    while i < n and j < m:
        sc = score(xs[i], ys[j])
        if D[i][j] == D[i + 1][j + 1] + sc and sc > 0:
            out.append((i, j))
            i += 1
            j += 1
        elif D[i][j] == D[i + 1][j]:
            i += 1
        else:
            j += 1
    return out


def vtable_pairs(elf, vt, fact, cls, compat=lambda x, y: 0.01):
    """Vote 1999 function <-> 2000 function from vtables of the same class (and its factory).
    compat(x, y): small bonus for slots whose functions have the same shape, negative if they can't match."""
    def evt(name, suffix=''):
        # 1999 registry names sometimes lack the 2000 class prefix (SharkTank -> TRSharkTank)
        for pre in ('', 'TR', 'DD', 'NA', 'GD', 'ML', 'MB'):
            base = name[:-5] if suffix == '' and name.endswith('Props') else name
            ev = elf.vtable(pre + name + suffix)
            if ev:
                return ev
        return None
    pairs = []
    for s, name in fact.items():
        ev = evt(name, 'Factory')
        if ev:
            pairs.append((vt[s], [f for f, _ in ev]))
    for s, name in cls.items():
        ev = evt(name)
        if ev:
            pairs.append((vt[s], [f for f, _ in ev]))
    # how many vtables use each function, per side: a stub shared by many 1999 tables must map to a 2000
    # function that is shared too
    use99, use00 = Counter(), Counter()
    for xs, ys in pairs:
        for x in set(xs):
            use99[x] += 1
        for y in set(ys):
            use00[y] += 1
    votes = defaultdict(float)
    # round 0: tables of the same (1999 length, 2000 length) share one slot layout. Align the columns once
    # per group (score = how often the two slots agree on being an empty stub), then vote along that layout.
    # This catches shifts a single table can't show (1999 GDAct tables lack CreateProps, so GetFactory and
    # everything after it sit one slot earlier).
    groups = defaultdict(list)
    for xs, ys in pairs:
        groups[(len(xs), len(ys))].append((xs, ys))
    grouped = set()
    for (n, m), mem in groups.items():
        if len(mem) < 5 or n == m:
            continue
        col = {}
        for i in range(n):
            for j in range(m):
                ok = [compat(xs[i], ys[j]) > 0 for xs, ys in mem if xs[i] and ys[j]]
                col[(i, j)] = (sum(ok) / len(ok) - 0.75) if ok else -1
        for i, j in align(list(range(n)), list(range(m)), lambda i, j: col[(i, j)]):
            for xs, ys in mem:
                if xs[i] and ys[j] and compat(xs[i], ys[j]) > 0:
                    votes[(xs[i], ys[j])] += 1
        grouped.update(id(p) for p in mem)
    for xs, ys in pairs:                       # round 1: equal-length tables, by index
        if len(xs) == len(ys):
            for x, y in zip(xs, ys):
                if x and y and compat(x, y) > 0:
                    votes[(x, y)] += 1
    for _ in range(2):                         # rounds 2-3: align all tables using the votes so far
        new = defaultdict(float)
        for xs, ys in pairs:
            for i, j in align(xs, ys, lambda x, y: votes.get((x, y), 0) + (compat(x, y) if x and y else -1)):
                if xs[i] and ys[j]:
                    new[(xs[i], ys[j])] += 1
        votes = new
    best = {}
    for (x, y), v in votes.items():
        if use99[x] >= 3 and use00[y] < 2:
            continue
        if v > best.get(x, (0, None))[0]:
            best[x] = (v, y)
    bya = defaultdict(list)
    for x, (v, y) in best.items():
        bya[y].append((v, x))
    out = {}
    for y, lst in bya.items():
        lst.sort(reverse=True)
        if len(lst) == 1 or lst[0][0] > lst[1][0]:
            out[lst[0][1]] = y
    return out


def main(argv):
    elf_p, map_p, bin_p, funcs_p, out_p = argv[1:6]
    elf = Elf(elf_p)
    # ---- 2000 side: function symbols from the symbol table
    st = [s for s in elf.secs if s[1] == 2][0]
    strs = elf.secs[st[6]]
    E = {}
    for i in range(st[5] // 16):
        nm, val, size, info, _, ndx = struct.unpack_from('<IIIBBH', elf.d, st[4] + i * 16)
        if info & 0xF == 2 and val and size:
            n = elf.d[strs[4] + nm:elf.d.index(b'\0', strs[4] + nm)].decode('latin-1')
            E.setdefault(val, (n, size))

    def eget(va, n):
        for s in elf.secs:
            if s[1] == 1 and s[3] and s[3] <= va < s[3] + s[5]:
                o = va - s[3] + s[4]
                return elf.d[o:o + min(n, s[3] + s[5] - va)]
        return None
    # source file of each 2000 function, by name: 0.map belongs to a slightly different link ("debug.elf")
    # than ecco.elf, so its addresses don't line up; names do.
    mapfile = {}
    cur = None
    for line in open(map_p, encoding='latin-1'):
        m = re.match(r'From file: (\S+?)(?:\.elf\.lib)?(?:\s+subfile:\s+(\S+))?\s+==>', line)
        if m:
            cur = m.group(2) or m.group(1)
            continue
        m = re.match(r'0x[0-9a-f]{8}\s+\*?\s*(\S.*?)\s*$', line)
        if m and cur:
            mapfile.setdefault(map_key(m.group(1)), cur)
    fileof = {a: mapfile.get(elf_key(n), '') for a, (n, _) in E.items()}
    # ---- 1999 side
    d99 = open(bin_p, 'rb').read()

    def get99(va, n):
        o = va - BASE99
        return d99[o:o + n] if 0 <= o < len(d99) else None
    entries = set(int(line.split('\t')[0], 16) for line in open(funcs_p))
    code_end = max(entries) + 0x1000
    vt, fact, cls = vtables99(d99, code_end)
    for sl in vt.values():
        entries.update(f for f in sl if f)
    entries = sorted(entries)
    F99 = {a: min(nxt - a, 0x4000) for a, nxt in zip(entries, entries[1:] + [BASE99 + len(d99)])}
    # allow the linear sweep to run to the next function entry (Ghidra bodies are fine, but keep pools out)
    A = Prog(eget, {a: s for a, (n, s) in E.items()})
    B = Prog(get99, F99)
    A.analyse(lambda v: v in E)
    B.analyse(lambda v: v in F99)
    match, method = {}, {}           # 1999 addr -> 2000 addr
    rev = {}

    def add(b, a, how):
        if b in match or a in rev:
            return False
        # an empty stub and a getter are never the same function (1999 GDAct vtables have GetFactory one
        # slot earlier, followed by an empty per-class stub). Empty in 1999 but code in 2000 is allowed:
        # those are methods written after May 1999 (e.g. TRSharkTank::Execute).
        if {kind(get99, b), kind(eget, a)} == {'empty', 'getter'}:
            return False
        match[b], rev[a], method[b] = a, b, how
        return True
    def kind(get, va):
        """Shape of a tiny function: 'empty' (rts; nop), 'getter' (mov.l @(disp,PC),r0; rts) or 'code'."""
        w = get(va, 4) or b''
        if w == b'\x0b\x00\x09\x00':
            return 'empty'
        if len(w) == 4 and w[1] == 0xD0 and w[2:] == b'\x0b\x00':
            return 'getter'
        return 'code'

    def compat(b, a):
        # same shape: small bonus; empty in 1999 but code in 2000 (written later): allowed, weaker;
        # anything else (getter vs empty, code vs empty in 2000, ...) can't be the same function
        # (only empties matter: getter vs code is neutral, the two compilers load constants differently)
        kb, ka = kind(get99, b), kind(eget, a)
        if (kb == 'empty') == (ka == 'empty'):
            return 0.01
        return 0.001 if (kb, ka) == ('empty', 'code') else -1.0
    # ---- phase 1: vtables (slot alignment of the same class's vtables, factories included)
    for b, a in vtable_pairs(elf, vt, fact, cls, compat).items():
        if b in B.f and a in A.f:
            add(b, a, 'vtable')
    print('vtables 1999: %d, factories %d, class vtables %d' % (len(vt), len(fact), len(cls)))
    pass
    n1 = len(match)
    # ---- phase 2: strings + constants
    ua = defaultdict(set)
    ub = defaultdict(set)
    for a in A.f:
        for s in set(A.strs[a]) | {('c', c) for c in A.consts[a]}:
            ua[s].add(a)
    for b in B.f:
        for s in set(B.strs[b]) | {('c', c) for c in B.consts[b]}:
            ub[s].add(b)
    score = defaultdict(float)
    for s, bs in ub.items():
        as_ = ua.get(s)
        if not as_ or len(as_) * len(bs) > 40:
            continue
        w = 1.0 / (len(as_) * len(bs))
        for b in bs:
            for a in as_:
                score[(b, a)] += w
    bestb, besta = {}, {}
    for (b, a), sc in score.items():
        if sc > bestb.get(b, (0, None))[0]:
            bestb[b] = (sc, a)
        if sc > besta.get(a, (0, None))[0]:
            besta[a] = (sc, b)
    for b, (sc, a) in bestb.items():
        if sc >= MIN_STR_SCORE and besta[a][1] == b:
            add(b, a, 'strings')
    n2 = len(match) - n1
    # ---- phases 3+4
    ea_sorted = sorted(A.f)
    eb_sorted = sorted(B.f)
    ia = {a: i for i, a in enumerate(ea_sorted)}
    ib = {b: i for i, b in enumerate(eb_sorted)}

    def size_ok(b, a):
        x, y = B.f[b][1], A.f[a][1]
        return max(x, y) <= SIZE_RATIO * min(x, y) + 8
    rounds = 0
    n3 = n4 = 0
    while True:
        rounds += 1
        new = 0
        # call-graph voting (order-insensitive): each known pair votes for pairings of its unknown callees,
        # and separately of its unknown callers
        callers_b, callers_a = defaultdict(set), defaultdict(set)
        for x, cl in B.calls.items():
            for y in cl:
                callers_b[y].add(x)
        for x, cl in A.calls.items():
            for y in cl:
                callers_a[y].add(x)
        votes = defaultdict(float)
        for b, a in list(match.items()):
            for lb, la in ((set(B.calls.get(b, [])), set(A.calls.get(a, []))), (callers_b[b], callers_a[a])):
                ub = [x for x in lb if x not in match]
                ua = [y for y in la if y not in rev]
                if not ub or not ua or len(ub) > MAX_LIST or len(ua) > MAX_LIST:
                    continue
                w = 1.0 / (len(ub) * len(ua))
                for x in ub:
                    for y in ua:
                        if size_ok(x, y):
                            votes[(x, y)] += w
        bb, ba = {}, {}
        for (x, y), v in votes.items():
            for best, k, o in ((bb, x, y), (ba, y, x)):
                cur = best.get(k)
                if cur is None:
                    best[k] = [v, o, 0.0]
                elif v > cur[0]:
                    best[k] = [v, o, cur[0]]
                elif v > cur[2]:
                    cur[2] = v
        for x, (v, y, second) in bb.items():
            vy, xb, second_y = ba[y]
            if xb == x and v >= MIN_SCORE and v >= MARGIN * second and v >= MARGIN * second_y:
                if add(x, y, 'callgraph'):
                    new += 1
                    n3 += 1
        # locality
        mb = sorted(match)
        for b1, b2 in zip(mb, mb[1:]):
            a1, a2 = match[b1], match[b2]
            if a2 <= a1:
                continue
            gb = eb_sorted[ib[b1] + 1:ib[b2]]
            ga = ea_sorted[ia[a1] + 1:ia[a2]]
            if not gb or len(gb) != len(ga) or len(gb) > MAX_GAP:
                continue
            if fileof.get(a1) != fileof.get(a2):
                continue
            if all(size_ok(x, y) for x, y in zip(gb, ga)):
                for x, y in zip(gb, ga):
                    if add(x, y, 'locality'):
                        new += 1
                        n4 += 1
        if not new or rounds > 30:
            break
    # source file for each 2000 function: nearest map entry at or below
    def src(a):
        return fileof.get(a, '')
    with open(out_p, 'w') as o:
        o.write('addr\tsize\tecco_symbol\tdemangled\tsource_file\tmethod\n')
        for b in sorted(match):
            a = match[b]
            sym = E[a][0]
            dm = demangle(sym)
            dms = '%s::%s' % dm if dm else sym
            o.write('%08X\t%d\t%s\t%s\t%s\t%s\n' % (b, B.f[b][1], sym, dms, src(a), method[b]))
    # every 1999 function with its source file: matched, or inferred when the nearest matched functions
    # before and after it come from the same 2000 source file (code of one file is contiguous)
    allb = sorted(B.f)
    # unnamed functions in a vtable (e.g. the empty per-file copies of inline base methods) belong to the
    # file of that vtable's matched slots; used as extra anchors when every table holding them agrees
    vfile = defaultdict(set)
    nuse = Counter(f for sl in vt.values() for f in set(sl) if f)
    for sl in vt.values():
        # only slots unique to this table say where it was compiled (inherited ones come from the base file)
        fs = Counter(src(match[f]) for f in sl if f in match and nuse[f] == 1 and src(match[f]))
        if fs:
            top = fs.most_common(1)[0][0]
            for f in sl:
                if f and f not in match and f in B.f:
                    vfile[f].add(top)
    anchor = {b: src(a) for b, a in match.items()}
    for f, fs in vfile.items():
        if len(fs) == 1:
            anchor[f] = next(iter(fs))
    mb = sorted(b for b in anchor if anchor[b])
    import bisect
    inferred = 0
    with open(re.sub(r'\.tsv$', '', out_p) + '_files.tsv', 'w') as o:
        o.write('addr\tsize\tname\tsource_file\thow\n')
        for b in allb:
            if b in match:
                a = match[b]
                dm = demangle(E[a][0])
                o.write('%08X\t%d\t%s\t%s\tmatched\n' % (b, B.f[b][1], '%s::%s' % dm if dm[0] else E[a][0], src(a)))
                continue
            if b in anchor and anchor[b]:
                o.write('%08X\t%d\t\t%s\tvtable\n' % (b, B.f[b][1], anchor[b]))
                inferred += 1
                continue
            i = bisect.bisect_left(mb, b)
            if 0 < i < len(mb):
                f1, f2 = anchor[mb[i - 1]], anchor[mb[i]]
                if f1 and f1 == f2:
                    o.write('%08X\t%d\t\t%s\tinferred\n' % (b, B.f[b][1], f1))
                    inferred += 1
                    continue
            o.write('%08X\t%d\t\t\t\n' % (b, B.f[b][1]))
    print('source file inferred for %d more functions (between two matches from the same file)' % inferred)
    tot = len(B.f)
    stubs = sorted(b for b, a in match.items() if kind(get99, b) == 'empty' and kind(eget, a) == 'code')
    print('empty in 1999 but with code in 2000 (written later): %d' % len(stubs))
    print('1999 functions: %d, 2000 functions: %d' % (tot, len(A.f)))
    # quality: consecutive matches (1999 order) from the same 2000 source file should keep their order
    mb = sorted(match)
    same = [(match[x], match[y]) for x, y in zip(mb, mb[1:]) if src(match[x]) == src(match[y])]
    mono = sum(1 for p, q in same if q > p)
    filechg = sum(1 for x, y in zip(mb, mb[1:]) if src(match[x]) != src(match[y]))
    print('order check: %d of %d same-file neighbours ascending (%.1f%%); %d file changes'
          % (mono, len(same), 100.0 * mono / max(1, len(same)), filechg))
    print('matched: %d (%.1f%%): vtable %d, strings %d, callgraph %d, locality %d, rounds %d'
          % (len(match), 100.0 * len(match) / tot, n1, n2, n3, n4, rounds))


if __name__ == '__main__':
    main(sys.argv)

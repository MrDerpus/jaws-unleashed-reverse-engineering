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

"""Name Jaws.exe virtual functions from Ecco: Defender's unstripped Dreamcast ECCO.ELF.

Both games share the GDED class system. For each class that exists in both (Jaws side found from its
factory, see JAWS_OBJECTS below), a vtable slot is "own" when the class overrides it:
  - Defender: the slot's symbol belongs to that class (`_Execute__11NAWhirl2000Fv`).
  - Jaws: the slot differs from the parent's slot (parent taken from Defender's DWARF hierarchy).
Per family (classes under the same child of GDBase / GDBaseProps / ...) every slot gets the set of classes
that override it; Defender slots are then aligned to Jaws slots in order (Jaws inserted new virtuals), by
dynamic programming over the Jaccard similarity of those sets. A Jaws function is named after the Defender
function in the same class and aligned slot when both games override it there.

Usage:
  python3 -I ecco_jaws_vtables.py ECCO.ELF Jaws.exe JAWS_OBJECTS.tsv OUTDIR
JAWS_OBJECTS.tsv: class, factory_vt, obj_size, obj_ctor, obj_vt, props_size, props_ctor, props_vt (hex),
as written by the JawsFactories Ghidra script.
Writes OUTDIR/slot_map.tsv and OUTDIR/jaws_vnames.tsv (addr, name, class, ecco slot, jaws slot, jaccard,
support, ecco symbol).
"""
import csv
import os
import re
import struct
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dwarf1_classes as D  # noqa: E402


# ---- Defender (SH-4 ELF) ---------------------------------------------------------------------------------
class Elf:
    def __init__(self, path):
        self.d = d = open(path, 'rb').read()
        shoff, = struct.unpack_from('<I', d, 0x20)
        shentsize, shnum, _ = struct.unpack_from('<HHH', d, 0x2E)
        self.secs = [struct.unpack_from('<IIIIIIIIII', d, shoff + i * shentsize) for i in range(shnum)]
        self.byname, self.byaddr = {}, defaultdict(list)
        st = [s for s in self.secs if s[1] == 2][0]
        strs = self.secs[st[6]]
        for i in range(st[5] // 16):
            nm, val, size, info, _, ndx = struct.unpack_from('<IIIBBH', d, st[4] + i * 16)
            n = d[strs[4] + nm:d.index(b'\0', strs[4] + nm)].decode('latin-1')
            if n and val:
                self.byname[n] = (val, size)
                self.byaddr[val].append(n)

    def u32(self, va):
        for s in self.secs:
            if s[1] == 1 and s[3] and s[3] <= va < s[3] + s[5]:
                return struct.unpack_from('<I', self.d, va - s[3] + s[4])[0]
        return 0

    def vtable(self, cls):
        """Function slots (header words dropped) as (addr, symbol)."""
        k = '___vt__%d%s' % (len(cls), cls)
        if k not in self.byname:
            return None
        va, size = self.byname[k]
        out = []
        for i in range(2, size // 4):
            f = self.u32(va + 4 * i)
            names = [n for n in self.byaddr.get(f, []) if n.startswith('_')]
            out.append((f, names[0] if names else None))
        return out


MANGLED = re.compile(r'^_(__[a-z]{2}|\w+?)__(\d+)(\w+)$')


def demangle(sym):
    """cfront/Hitachi: _Method__<len>Class<args> -> (Class, Method). Constructor/destructor/operators too."""
    if not sym:
        return None, None
    m = MANGLED.match(sym)
    if not m:
        return None, sym
    meth, n, rest = m.group(1), int(m.group(2)), m.group(3)
    cls = rest[:n]
    if len(cls) < n:
        return None, sym
    meth = {'__dt': '~' + cls, '__ct': cls}.get(meth, meth)
    return cls, meth


# ---- Jaws (PE) ---------------------------------------------------------------------------------------------
class Pe:
    def __init__(self, path):
        self.d = d = open(path, 'rb').read()
        pe = struct.unpack_from('<I', d, 0x3C)[0]
        nsec = struct.unpack_from('<H', d, pe + 6)[0]
        opt = struct.unpack_from('<H', d, pe + 20)[0]
        base = struct.unpack_from('<I', d, pe + 24 + 28)[0]
        self.secs = []
        for i in range(nsec):
            o = pe + 24 + opt + i * 40
            name = d[o:o + 8].rstrip(b'\0')
            vs, va, rs, ro = struct.unpack_from('<IIII', d, o + 8)
            self.secs.append((name, base + va, vs, ro, rs))
        t = [s for s in self.secs if s[0] == b'.text'][0]
        r = [s for s in self.secs if s[0] == b'.rdata'][0]
        self.text = (t[1], t[1] + t[2])
        # vtable starts: every "mov dword [reg(+disp8)], imm32" (C7 /0) storing an .rdata address of code
        self.vt_starts = set()
        tx = d[t[3]:t[3] + t[4]]
        for i in range(len(tx) - 7):
            if tx[i] != 0xC7:
                continue
            m = tx[i + 1]
            if m >> 6 == 0 and m & 7 not in (4, 5) and (m >> 3) & 7 == 0:
                imm = struct.unpack_from('<I', tx, i + 2)[0]
            elif m >> 6 == 1 and m & 7 != 4 and (m >> 3) & 7 == 0:
                imm = struct.unpack_from('<I', tx, i + 3)[0]
            else:
                continue
            if r[1] <= imm < r[1] + r[2] and self.is_text(self.u32(imm)):
                self.vt_starts.add(imm)

    def u32(self, va):
        for _, sva, vs, ro, rs in self.secs:
            if sva <= va < sva + rs:
                return struct.unpack_from('<I', self.d, va - sva + ro)[0]
        return 0

    def is_text(self, v):
        return self.text[0] <= v < self.text[1]

    def vtable(self, vt, extra=()):
        out, a = [], vt
        while len(out) < 600 and (a == vt or (a not in self.vt_starts and a not in extra)):
            w = self.u32(a)
            if not self.is_text(w):
                break
            out.append(w)
            a += 4
        return out


# ---- alignment -------------------------------------------------------------------------------------------
def align(esig, jsig):
    """Monotonic alignment of Defender slots to Jaws slots maximizing summed Jaccard (DP, gaps allowed)."""
    ne, nj = len(esig), len(jsig)

    def jac(a, b):
        if not a and not b:
            return 0.0
        return len(a & b) / len(a | b)
    best = [[0.0] * (nj + 1) for _ in range(ne + 1)]
    back = [[None] * (nj + 1) for _ in range(ne + 1)]
    for i in range(ne + 1):
        for j in range(nj + 1):
            if i == 0 and j == 0:
                continue
            cands = []
            if i:
                cands.append((best[i - 1][j], 'e'))
            if j:
                cands.append((best[i][j - 1], 'j'))
            if i and j:
                s = jac(esig[i - 1], jsig[j - 1])
                if s > 0:
                    cands.append((best[i - 1][j - 1] + s, 'm'))
            best[i][j], back[i][j] = max(cands)
    pairs, i, j = [], ne, nj
    while i or j:
        b = back[i][j]
        if b == 'm':
            pairs.append((i - 1, j - 1, jac(esig[i - 1], jsig[j - 1]), len(esig[i - 1] | jsig[j - 1])))
            i, j = i - 1, j - 1
        elif b == 'e':
            i -= 1
        else:
            j -= 1
    return pairs[::-1]


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    elf, pe = Elf(sys.argv[1]), Pe(sys.argv[2])
    out = sys.argv[4]
    os.makedirs(out, exist_ok=True)

    # Defender hierarchy (first base class) from the DWARF info
    dies = D.parse(D.elf_section(elf.d, '.debug'))
    T = D.Types(dies)
    parent = {}
    for nm, off in D.classes(dies).items():
        for k in dies[off]['kids']:
            if dies[k]['tag'] == 0x1C:
                parent[nm] = T.name(dies[k]['a'])
                break

    jobj = list(csv.DictReader(open(sys.argv[3]), delimiter='\t'))
    extra = {int(r[k], 16) for r in jobj for k in ('obj_vt', 'props_vt', 'factory_vt') if r[k]}
    pairs = {}   # Defender class -> (defender slots [(addr, sym)], jaws slots [addr])
    for r in jobj:
        c = r['class']
        for ecls, jvt in ((c, r['obj_vt']), (c + 'Props', r['props_vt']), (c + 'Factory', r['factory_vt'])):
            ev = elf.vtable(ecls)
            if ev and jvt:
                pairs[ecls] = (ev, pe.vtable(int(jvt, 16), extra))
    # base classes without a Jaws factory can't be compared; families are rooted below the top classes
    def chain(c):
        out = [c]
        while out[-1] in parent and len(out) < 30:
            out.append(parent[out[-1]])
        return out

    def family(c):
        ch = chain(c)
        return ch[-3] if len(ch) >= 3 else ch[-1]

    def nearest_shared_parent(c):
        for p in chain(c)[1:]:
            if p in pairs:
                return p
        return None

    fams = defaultdict(list)
    for c in pairs:
        fams[family(c)].append(c)

    slot_rows, names = [], []
    for fam, members in sorted(fams.items()):
        esig, jsig = defaultdict(set), defaultdict(set)
        ne = nj = 0
        for c in members:
            ev, jv = pairs[c]
            ne, nj = max(ne, len(ev)), max(nj, len(jv))
            for k, (_, sym) in enumerate(ev):
                if demangle(sym)[0] == c:
                    esig[k].add(c)
            p = nearest_shared_parent(c)
            if p is None:
                continue
            pj = pairs[p][1]
            for k, f in enumerate(jv):
                if k >= len(pj) or f != pj[k]:
                    jsig[k].add(c)
        # only classes whose Jaws parent is known take part, else every Jaws slot would count as "own"
        known = {c for c in members if nearest_shared_parent(c)}
        es = [esig[k] & known for k in range(ne)]
        js = [jsig[k] for k in range(nj)]
        for k_e, k_j, jac, sup in align(es, js):
            slot_rows.append((fam, k_e, k_j, jac, sup))
            if jac < 0.5 or sup < 2:
                continue
            for c in members:
                ev, jv = pairs[c]
                if k_e >= len(ev) or k_j >= len(jv):
                    continue
                cls, meth = demangle(ev[k_e][1])
                if cls != c:
                    continue
                p = nearest_shared_parent(c)
                if p and k_j < len(pairs[p][1]) and pairs[p][1][k_j] == jv[k_j]:
                    continue     # Defender overrides here but Jaws inherits: skip
                names.append((jv[k_j], '%s::%s' % (cls, meth), c, k_e, k_j, jac, sup, ev[k_e][1]))

    with open(os.path.join(out, 'slot_map.tsv'), 'w') as f:
        f.write('family\tecco_slot\tjaws_slot\tjaccard\tsupport\n')
        for r in slot_rows:
            f.write('%s\t%d\t%d\t%.2f\t%d\n' % r)
    # one name per Jaws address; conflicting names are reported, the best-scoring one kept
    by = defaultdict(list)
    for n in names:
        by[n[0]].append(n)
    with open(os.path.join(out, 'jaws_vnames.tsv'), 'w') as f:
        f.write('addr\tname\tclass\tecco_slot\tjaws_slot\tjaccard\tsupport\tecco_symbol\n')
        conflicts = 0
        for a in sorted(by):
            lst = sorted(by[a], key=lambda n: -n[5])
            if len({n[1] for n in lst}) > 1:
                conflicts += 1
            n = lst[0]
            f.write('%08x\t%s\t%s\t%d\t%d\t%.2f\t%d\t%s\n' % n)
    print('%d classes in both games, %d families, %d named Jaws functions (%d with conflicting candidates)'
          % (len(pairs), len(fams), len(by), conflicts))


if __name__ == '__main__':
    main()

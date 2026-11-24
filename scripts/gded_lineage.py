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

"""Compare GDED files across Game World Builder versions (Ecco: Defender 2.1.12.1,
Ecco: Sentinels of the Universe 2.3.2.1, Jaws 2.6.3.16).

Usage:
  python3 -I scripts/gded_lineage.py info FILE...            version, top-level chunks, class-table sizes
  python3 -I scripts/gded_lineage.py compare A=GLOB[,GLOB][@VER] B=... [C=...]
                                                            union of CLAS class names per group, overlaps;
                                                            @VER keeps only files whose version starts VER
  python3 -I scripts/gded_lineage.py placed FILE [CLASS...]  count BRTR nodes/actions per class
  python3 -I scripts/gded_lineage.py prop FILE ID...         name PROP IDs (0x0800xxxx) from the file's own table
  python3 -I scripts/gded_lineage.py fields A=GLOB[,GLOB][@VER] B=... [C=...]
                                                            per-class field differences (union over files)

CLAS layout: BRCM/ACCM/CPCM/PRCM = class-name lists; PRIM = field table, uint32 count +
count x (field name, class name) strings. A PROP ID is 0x08000000 | index into that table, so
each file names its own properties (19 of 20 Jaws levels share one table; TITLE0 differs).

Version differences handled:
  - Dreamcast Ecco builds put a PVR loading image before the preamble (found by search).
  - 2.1 chunks are packed; 2.3 and 2.6 chunks are 4-byte padded (detected per chunk).
  - CLAS name lists (BRCM/ACCM/CPCM/PRCM) are packed up to 2.3, padded in 2.6.
  - Zero runs between top-level chunks (Sentinels) are skipped.
Read-only; pass untrusted files by path and run with python3 -I.
"""
import collections, glob, re, struct, sys

TAG = re.compile(rb'[A-Z0-9_]{4}')
LISTS = ('BRCM', 'ACCM', 'CPCM', 'PRCM')


def version(data):
    m = re.search(rb'GDED BINARY FORMAT, VERSION ([0-9.]+)', data[:0x50000])
    return m.group(1).decode().rstrip('.') if m else None


def _ok(data, p, end):
    return p + 8 <= end and TAG.fullmatch(data[p:p+4]) is not None


def walk(data, start, end):
    """Sibling chunks in [start, end) as (tag, offset, size)."""
    out, p = [], start
    while p + 8 <= end:
        if not _ok(data, p, end) and _ok(data, (p + 3) & ~3, end):
            p = (p + 3) & ~3
            continue
        if not _ok(data, p, end):
            q = p
            while q < min(end, p + 0x40000) and data[q] == 0:
                q += 1
            if q != p and _ok(data, q, end):
                p = q
                continue
            break
        sz = struct.unpack_from('<I', data, p + 4)[0]
        if p + 8 + sz > end:
            break
        out.append((data[p:p+4].decode(), p, sz))
        p += 8 + sz
    return out


def top_chunks(data):
    i = data.find(b'GDED BINARY FORMAT')
    return walk(data, data.find(b'\r\n\r\n', i) + 4, len(data))


def class_lists(data):
    v = version(data)
    aligned = tuple(int(x) for x in v.split('.')[:2]) >= (2, 6)
    clas = [c for c in top_chunks(data) if c[0] == 'CLAS'][0]
    res = {}
    for tag, o, _ in walk(data, clas[1] + 8, clas[1] + 8 + clas[2]):
        if tag not in LISTS:
            continue
        n = struct.unpack_from('<I', data, o + 8)[0]
        p, names = o + 12, []
        for _ in range(n):
            ln = struct.unpack_from('<I', data, p)[0]
            names.append(data[p+4:p+4+ln].split(b'\0')[0].decode('latin-1'))
            p += 4 + ln
            if aligned:
                p = (p + 3) & ~3
        res[tag] = names
    return res


def field_table(data):
    """CLAS PRIM: list of (field, class); PROP ID 0x08000000|i -> entry i."""
    v = version(data)
    aligned = tuple(int(x) for x in v.split('.')[:2]) >= (2, 6)
    clas = [c for c in top_chunks(data) if c[0] == 'CLAS'][0]
    prim = [c for c in walk(data, clas[1] + 8, clas[1] + 8 + clas[2]) if c[0] == 'PRIM'][0]
    n = struct.unpack_from('<I', data, prim[1] + 8)[0]
    p, out = prim[1] + 12, []
    for _ in range(n):
        pair = []
        for _ in range(2):
            ln = struct.unpack_from('<I', data, p)[0]
            pair.append(data[p+4:p+4+ln].split(b'\0')[0].decode('latin-1'))
            p += 4 + ln
            if aligned:
                p = (p + 3) & ~3
        out.append(tuple(pair))
    return out


def class_fields(data):
    res = collections.OrderedDict()
    for f, c in field_table(data):
        res.setdefault(c, []).append(f)
    return res


def placed(data):
    """Heuristic: CHBR/ACTN tags after RSRC whose class ID (0x01../0x02..) indexes BRCM/ACCM."""
    L = class_lists(data)
    rsrc = [c for c in top_chunks(data) if c[0] == 'RSRC'][0]
    start = rsrc[1] + 8 + rsrc[2]
    c = collections.Counter()
    for tag, hi, lst in ((b'CHBR', 1, L['BRCM']), (b'ACTN', 2, L['ACCM'])):
        p = start
        while (p := data.find(tag, p + 1)) >= 0:
            if p + 12 > len(data):
                break
            cid = struct.unpack_from('<I', data, p + 8)[0]
            if cid >> 24 == hi and (cid & 0xFFF) < len(lst):
                c[lst[cid & 0xFFF]] += 1
    return c


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return
    cmd, args = argv[1], argv[2:]
    if cmd == 'info':
        for f in args:
            d = open(f, 'rb').read()
            tops = top_chunks(d)
            L = class_lists(d)
            print(f'{f}: GDED {version(d)}, preamble @0x{d.find(b"GDED"):X}')
            print('   top:', ' '.join(t for t, _, _ in tops))
            print('   classes:', {k: len(v) for k, v in L.items()})
    elif cmd == 'compare':
        U = {}
        for a in args:
            name, pat = a.split('=', 1)
            pat, _, want_v = pat.partition('@')
            u = {t: set() for t in LISTS}
            files = sorted({f for g in pat.split(',') for f in glob.glob(g, recursive=True)})
            n = 0
            for f in files:
                d = open(f, 'rb').read()
                if not version(d) or not version(d).startswith(want_v):
                    continue
                for t, v in class_lists(d).items():
                    u[t] |= set(v)
                n += 1
            U[name] = u
            print(f'{name}: {n} files', {t: len(v) for t, v in u.items()})
        names = list(U)
        for t in LISTS:
            print(f'\n== {t}')
            for i, a in enumerate(names):
                for b in names[i+1:]:
                    rest = [U[c][t] for c in names if c not in (a, b)]
                    only = (U[a][t] & U[b][t]) - set().union(*rest) if rest else U[a][t] & U[b][t]
                    print(f'  {a} & {b} only ({len(only)}):', ' '.join(sorted(only)))
    elif cmd == 'placed':
        d = open(args[0], 'rb').read()
        c = placed(d)
        want = set(args[1:])
        for k, v in c.most_common():
            if not want or k in want:
                print(f'{v:6d}  {k}')
    elif cmd == 'prop':
        t = field_table(open(args[0], 'rb').read())
        for a in args[1:]:
            i = int(a, 16) & 0xFFFFFF
            print(f'0x{0x08000000 | i:08X}', '.'.join(reversed(t[i])) if i < len(t) else 'out of range')
    elif cmd == 'fields':
        G = []
        for a in args:
            name, pat = a.split('=', 1)
            pat, _, want_v = pat.partition('@')
            u, n = collections.defaultdict(set), 0
            for f in sorted({f for g in pat.split(',') for f in glob.glob(g, recursive=True)}):
                d = open(f, 'rb').read()
                if not version(d) or not version(d).startswith(want_v):
                    continue
                for c, v in class_fields(d).items():
                    u[c] |= set(v)
                n += 1
            G.append((name, u))
            print(f'{name}: {n} files, {len(u)} classes, {sum(len(v) for v in u.values())} fields')
        common = set(G[0][1]).intersection(*[set(c) for _, c in G[1:]])
        same = sum(1 for c in common if all(g[c] == G[0][1][c] for _, g in G))
        print(f'classes in all: {len(common)}, identical fields in all: {same}')
        for cls in sorted(common):
            if all(g[cls] == G[0][1][cls] for _, g in G):
                continue
            print(f'\n{cls}: ' + ' / '.join(f'{n} {len(c[cls])}' for n, c in G))
            for (n1, c1), (n2, c2) in zip(G, G[1:]):
                add, rem = sorted(c2[cls] - c1[cls]), sorted(c1[cls] - c2[cls])
                if add or rem:
                    print(f'   {n1}->{n2}: +{" ".join(add)}  -{" ".join(rem)}')
        if len(G) >= 2:
            a_, b_ = G[-2], G[-1]
            rest = set().union(*[set(g) for _, g in G[:-2]]) if len(G) > 2 else set()
            only = sorted((set(a_[1]) & set(b_[1])) - rest)
            print(f'\n=== classes in {a_[0]} and {b_[0]} only ({len(only)})')
            for cls in only:
                x, y = a_[1][cls], b_[1][cls]
                print(f'{cls}: {a_[0]} {len(x)} / {b_[0]} {len(y)}' + ('' if x == y else f'  +{" ".join(sorted(y - x))}  -{" ".join(sorted(x - y))}'))
    else:
        print(__doc__)


if __name__ == '__main__':
    main(sys.argv)

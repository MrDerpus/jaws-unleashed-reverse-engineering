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

"""List the GDASSERT call sites of a Dreamcast SH-4 program built with Appaloosa's engine
(1999 Ecco: Defender prototypes): source file, line number, address and asserted expression.

Each assert loads its format string ("GDASSERT failed on: (<expr>) file: %s, line: %d") with a
PC-relative mov.l; the source-file string pointer and the line number (mov.w pool constant,
or mov #imm) are loaded within ~14 instructions. A line number that the heuristic can't pin
down prints as None (check those in Ghidra: the call's last argument is a DAT_ int16).
Hits whose file is "?" are constant-pool words misread as code and are skipped.
Usage: python3 -I scripts/sh4_asserts.py 1ST_READ.BIN   (load address 0x8C010000)
Read-only."""
import re, struct, sys
BASE = 0x8C010000
d = open(sys.argv[1], 'rb').read()
def s_at(a):
    o = a - BASE
    if not (0 <= o < len(d)): return None
    e = d.find(b'\0', o, o + 300)
    return d[o:e].decode('latin-1') if e > 0 else None
asserts = {BASE + m.start(): m.group(1).decode('latin-1') for m in re.finditer(rb'GDASSERT failed on: \((.*?)\) file', d)}
files = {BASE + m.start() + 1: m.group(1).decode() for m in re.finditer(rb'[\x00\xff]([A-Za-z0-9_]+\.(?:cpp|h))\x00', d)}
def decode(pc):
    w = struct.unpack_from('<H', d, pc - BASE)[0]
    if w >> 12 == 0xD:   # mov.l @(disp,PC),Rn
        ea = ((pc & ~3) + 4 + (w & 0xFF) * 4)
        return ('L', (w >> 8) & 15, struct.unpack_from('<I', d, ea - BASE)[0] if 0 <= ea - BASE < len(d) - 4 else None)
    if w >> 12 == 0x9:   # mov.w @(disp,PC),Rn
        ea = pc + 4 + (w & 0xFF) * 2
        return ('W', (w >> 8) & 15, struct.unpack_from('<h', d, ea - BASE)[0] if 0 <= ea - BASE < len(d) - 2 else None)
    if w >> 12 == 0xE:   # mov #imm,Rn
        v = w & 0xFF; v = v - 256 if v > 127 else v
        return ('I', (w >> 8) & 15, v)
    return None
res = []
for o in range(0, len(d) - 2, 2):
    x = decode(BASE + o)
    if not x or x[0] != 'L' or x[2] not in asserts: continue
    pc = BASE + o
    fname = line = None
    win = [decode(pc + k * 2) for k in range(-14, 15)]
    win = [w for w in win]
    for k, y in zip(range(-14, 15), win):
        if not y: continue
        if y[0] == 'L' and y[2] in files and fname is None: fname = files[y[2]]
    # line: the closest small-constant load (W or I) into a register, prefer r6 / r2..r7, value 1..20000
    best = None
    for k, y in zip(range(-14, 15), win):
        if y and y[0] in 'WI' and y[2] is not None and 3 <= y[2] <= 20000 and y[1] != x[1] \
           and str(y[2]) not in re.findall(r'\d+', asserts[x[2]]):
            score = (y[0] != 'W', y[1] != 6, abs(k))
            if best is None or score < best[0]: best = (score, y[2], y[1])
    res.append((fname or '?', best[1] if best else None, pc, asserts[x[2]]))
seen = set()
for f, l, pc, a in sorted(res, key=lambda r: (r[0], r[1] or 0)):
    if (pc) in seen: continue
    seen.add(pc)
    if f == "?": continue
    print(f'{f:14} line {str(l):>5}  @{pc:08X}  {a}')
found = {a for *_, a in res}
for a in asserts.values():
    if a not in found: print('NOT FOUND:', a)

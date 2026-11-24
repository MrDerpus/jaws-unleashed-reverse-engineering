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

"""List a GD-ROM dump (disc.gdi + 2048-byte .iso tracks): ISO9660 tree of the
high-density area, with file dates, and the GDED version of every .GDE file.
Usage: python3 -I scripts/gdrom_ls.py DISC_DIR [--extract OUTDIR PATTERN]"""
import os, re, struct, sys

d = sys.argv[1]
tracks = []
for line in open(os.path.join(d, 'disc.gdi')).read().split('\n')[1:]:
    f = line.split()
    if len(f) >= 5 and f[3] == '2048':
        tracks.append((int(f[1]), os.path.join(d, f[4])))
tracks.sort()
handles = [(lba, open(p, 'rb'), os.path.getsize(p) // 2048) for lba, p in tracks]


def read(lba, n):
    out = b''
    while n > 0:
        for base, fh, cnt in reversed(handles):
            if base <= lba < base + cnt:
                take = min(n, (base + cnt - lba) * 2048)
                fh.seek((lba - base) * 2048)
                out += fh.read(take)
                lba += (take + 2047) // 2048
                n -= take
                break
        else:
            out += b'\0' * n
            break
    return out


pvd = read(45000 + 16, 2048)
assert pvd[1:6] == b'CD001', 'no PVD'
root = pvd[156:156 + 34]
files = []


def walk(lba, size, path, depth=0):
    data = read(lba, size)
    i = 0
    while i < len(data):
        ln = data[i]
        if ln == 0:
            i = (i // 2048 + 1) * 2048
            continue
        rec = data[i:i + ln]
        ext, sz = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]
        y, mo, dy, h, mi, s = rec[18:24]
        flags, nl = rec[25], rec[32]
        name = rec[33:33 + nl]
        i += ln
        if name in (b'\0', b'\1'):
            continue
        name = name.decode('ascii', 'replace').split(';')[0]
        date = '%04d-%02d-%02d' % (1900 + y, mo, dy)
        if flags & 2:
            if depth < 8:
                walk(ext, sz, path + name + '/', depth + 1)
        else:
            files.append((path + name, ext, sz, date))


walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], '/')
ver = {}
for p, ext, sz, date in files:
    if p.upper().endswith('.GDE') and sz:
        head = read(ext, min(sz, 0x50000))
        k = head.find(b'GDED BINARY FORMAT')
        m = re.search(rb'VERSION ([0-9.]+)', head[k:k + 60]) if k >= 0 else None
        ver[p] = m.group(1).decode().rstrip('.') if m else '?'
if '--extract' in sys.argv:
    out, pat = sys.argv[sys.argv.index('--extract') + 1], sys.argv[sys.argv.index('--extract') + 2]
    os.makedirs(out, exist_ok=True)
    for p, ext, sz, date in files:
        if re.search(pat, p, re.I):
            with open(os.path.join(out, os.path.basename(p)), 'wb') as fo:
                fo.write(read(ext, sz))
for p, ext, sz, date in files:
    print(f'{date}  {sz:>10}  {p}  {ver.get(p, "")}')

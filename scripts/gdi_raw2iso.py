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

"""Convert a GDI disc dump whose data tracks are raw 2352-byte sectors (track0N.bin) into a
GDI with 2048-byte .iso data tracks, as scripts/gdrom_ls.py expects. Audio tracks are listed unchanged
(not copied). Usage: python3 -I scripts/gdi_raw2iso.py SRC_DIR DST_DIR   Writes only into DST_DIR."""
import sys, os
src, dst = sys.argv[1:]
os.makedirs(dst, exist_ok=True)
lines = open(os.path.join(src, 'disc.gdi')).read().split('\n')
out = []
for line in lines[1:]:
    f = line.split()
    if len(f) < 5: continue
    if f[2] == '4':
        name = os.path.splitext(f[4])[0] + '.iso'
        if f[3] == '2048':
            os.link(os.path.join(src, f[4]), os.path.join(dst, name))
        else:
            with open(os.path.join(src, f[4]), 'rb') as i, open(os.path.join(dst, name), 'wb') as o:
                while (s := i.read(2352 * 512)):
                    for k in range(0, len(s), 2352): o.write(s[k+16:k+16+2048])
        out.append(f"{f[0]} {f[1]} 4 2048 {name} 0")
    else:
        out.append(f"{f[0]} {f[1]} {f[2]} {f[3]} {f[4]} 0")
open(os.path.join(dst, 'disc.gdi'), 'w').write(f"{len(out)}\n" + "\n".join(out) + "\n")

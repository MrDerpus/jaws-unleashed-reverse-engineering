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

"""Make a level's entrance load a different .GDW (2026-10-04).

    python3 scripts/redirect_stage.py IN.GDW OUT.GDW FROM TO
    e.g. python3 scripts/redirect_stage.py GAME_GDWs/OPEN_S.GDW OPEN_S.GDW FISH TEST

Level entrances are area triggers whose actions end in a GDLoad action
(ACTN class 0x02038036) holding the stage name to load in PROP 0x08001839
([uint32 length incl. NUL][name]). This rewrites every such name equal to
FROM, anywhere in the file (OPEN_S's Fisherman's Isle loader sits in one of
its embedded loading-screen sub-archives, not the main BRTR). The new name must have the same length (the bytes are replaced in
place, so no chunk sizes change), e.g. OPEN_S's Fisherman's Isle entrance
FISH -> TEST makes the game load TEST.GDW there (used for custom levels; see
docs/custom_level_tutorial.md). Names are matched case-insensitively.
"""
import struct
import sys


P_STAGE = 0x08001839


def main(src, dst, old, new):
    if len(old) != len(new):
        raise SystemExit(f'{new!r} must be as long as {old!r} ({len(old)} letters)')
    d = bytearray(open(src, 'rb').read())
    want = struct.pack('<II', P_STAGE, len(old) + 1)
    hits, p = 0, 0
    while True:
        p = d.find(want, p)
        if p < 0:
            break
        val = p + 8
        if d[p - 8:p - 4] == b'PROP' and bytes(d[val:val + len(old)]).upper() == old.upper().encode() \
                and d[val + len(old)] == 0:
            d[val:val + len(new)] = new.encode()
            hits += 1
        p += 4
    if not hits:
        raise SystemExit(f'no stage name {old!r} found in {src}')
    open(dst, 'wb').write(d)
    print(f'{hits} entrance(s) now load {new}.GDW instead of {old}.GDW -> {dst}')


if __name__ == '__main__':
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])

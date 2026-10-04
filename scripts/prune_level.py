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

"""Drop the resources a level no longer uses (2026-10-04).

    python3 scripts/prune_level.py IN.GDW OUT.GDW

A stripped level (strip_level.py) still carries every texture, mesh, sound
and skeleton of the original. This keeps only the RSRC blocks the level can
reach and removes the rest:
  - roots: every typed reference in the primary BRTR and SCRT, i.e. a
    resource tag followed by an ID that exists in RSRC (['GMDL'][id] mesh
    links, ['SKEL'][id], ['MREG'][id] in PRIMs, ['GTEX'][id] on sprites,
    ['GSFX'][id] lists in sound banks, ['GMAT'][id], ['GMOA'][id]...)
  - then whatever kept resources reference the same way (mesh -> materials
    (MATS) -> textures (TEXP), MREG -> mesh, GSFX -> GSMP sample, ...).
Scanning is done at 4-byte steps; a coincidental tag + valid ID inside other
data only keeps a block that could have gone, never drops one.
RSRC's 12-byte header is a constant stamp (no count), and gdw_grow fixes
RSRC's size, FSIZ, SKIP and the FDIR offset of the embedded loading-screen
archive, which is left untouched (it has its own RSRC).
Run it on the finished level (build.sh does), not on the base: the palette
materials (mat_<id>) of a level kit point at base resources no node uses yet.
"""
import collections
import sys

from gdw_grow import replace_chunk_payload, top_chunks, u32

RSRC_HEADER = 12


def blocks(d, rsrc):
    """[(tag, id, start, end_with_padding)] of the primary RSRC."""
    out, p, end = [], rsrc + 8 + RSRC_HEADER, rsrc + 8 + u32(d, rsrc + 4)
    while p + 8 <= end:
        nxt = (p + 8 + u32(d, p + 4) + 3) & ~3
        out.append((bytes(d[p:p + 4]), u32(d, p + 8), p, min(nxt, end)))
        p = nxt
    return out


def typed_refs(d, a, z, known):
    """(tag, id) pairs in d[a:z] at 4-byte steps that name a known resource."""
    out, tags = set(), {t for t, _ in known}
    for q in range(a, z - 7, 4):
        t = bytes(d[q:q + 4])
        if t in tags and (t, u32(d, q + 4)) in known:
            out.add((t, u32(d, q + 4)))
    return out


def prune(d):
    """Returns (new file bytes, Counter of kept, Counter of removed)."""
    tc = top_chunks(d)
    rsrc = tc['RSRC']
    blk = blocks(d, rsrc)
    byid = collections.defaultdict(list)
    for b in blk:
        byid[(b[0], b[1])].append(b)
    roots = set()
    for tag in ('BRTR', 'SCRT'):
        p = tc[tag]
        roots |= typed_refs(d, p, p + 8 + u32(d, p + 4), byid)
    keep, todo = set(roots), list(roots)
    while todo:
        for _, _, a, z in byid[todo.pop()]:
            for k in typed_refs(d, a + 12, z, byid):   # +12: skip own tag, size, id
                if k not in keep:
                    keep.add(k)
                    todo.append(k)
    payload = bytearray(d[rsrc + 8:rsrc + 8 + RSRC_HEADER])
    kept, removed = collections.Counter(), collections.Counter()
    for t, i, a, z in blk:
        if (t, i) in keep:
            payload += d[a:z]
            kept[t.decode()] += z - a
        else:
            removed[t.decode()] += z - a
    out = bytearray(d)
    replace_chunk_payload(out, rsrc, bytes(payload))
    return bytes(out), kept, removed


def main(src, dst):
    d = open(src, 'rb').read()
    out, kept, removed = prune(d)
    # Check: every typed reference the level makes still resolves.
    tc = top_chunks(out)
    left = {(t, i) for t, i, _, _ in blocks(out, tc['RSRC'])}
    for tag in ('BRTR', 'SCRT'):
        p = tc[tag]
        refs = typed_refs(out, p, p + 8 + u32(out, p + 4), {(t, i) for t, i, _, _ in blocks(d, top_chunks(d)['RSRC'])})
        assert refs <= left, f'{tag} lost {sorted(refs - left)[:5]}'
    for t in sorted(set(kept) | set(removed)):
        print(f'{t}: kept {kept[t] / 1e6:7.2f} MB, removed {removed[t] / 1e6:7.2f} MB')
    open(dst, 'wb').write(out)
    print(f'{src}: {len(d) / 1e6:.1f} MB -> {dst}: {len(out) / 1e6:.1f} MB')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])

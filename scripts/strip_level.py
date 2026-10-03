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

"""Strip a level's scenery to get a blank base for custom scenes (2026-10-03).

    python3 scripts/strip_level.py IN.GDW OUT.GDW [--minimal]
                                   [--keep-class 0x0107402F ...]
                                   [--keep-name NAME ...] [--keep-id ID ...]

Removes top-level BRTR nodes (with their whole subtree) that are scenery:
  - classes SCENERY_CLASSES: plain model bricks (rocks, sand, piers, houses,
    props: 648 in FISH), flora (seaweed/plants: 143), and 0x01072071 (2)
  - groups named in SCENERY_GROUPS (FISH: 'Tiles', the tiled seafloor/flora)
  - reference templates named in SCENERY_TEMPLATES, plus every top-level
    reference node (PROP 0x080017F0) that copies them (FISH: pier `molo` x12,
    breakable posts `Torheto_pozna 1` x7, fishing boat `Kis_Halaszhajo` x3)
Kept no matter what:
  - KEEP_NAMES (the sky dome)
  - nodes a kept node points at through ID_PROPS (reference / mission link /
    template / child list / the water's sun): kept unchanged
  - nodes whose ID appears as a uint32 inside a top-level ACTN block
    (stage/quest logic; FISH: 8 small objects incl. the tutorial's
    rope-breaking rock): kept but moved HIDE_DY units down, out of sight
Everything else (cameras, lights, fog, water, sounds, HUD, weapons, AI,
missions, effects, creature/NPC templates, stage exits) is untouched, and so
is RSRC (unused meshes/textures simply stay unreferenced).

--minimal (2026-10-04) also removes the visible gameplay content, leaving
only engine plumbing (water, sun, sky, cameras, fog, lights, HUD, effects,
sound definitions, creature templates, the stage exit): classes
MINIMAL_CLASSES (NPCs, waypoints, bird flock, fish schools, the SC17 mission
root and sharks, the collectible, the beach sound area), any top-level node with a creature-generator action
(MINIMAL_ACTN_CLASSES: ambient marlins, rays, otters...) and top-level nodes
named in MINIMAL_NAMES (FISH: whale carcass, crowd, collectible groups).
"""
import struct
import sys

from gdw_grow import find_brtr, replace_chunk_payload, u32

SCENERY_CLASSES = {0x0107402F, 0x0106F06E, 0x01072071}
SCENERY_TEMPLATES = {'molo', 'Kis_Halaszhajo', 'Torheto_pozna 1'}
# Kept-class top-level groups that only hold scenery (FISH: 'Tiles', 173
# seafloor/flora meshes: ope seafloor clusters, plants, trees, corals).
SCENERY_GROUPS = {'Tiles'}
KEEP_NAMES = {'NEW_SKY_OPEN'}
MINIMAL_CLASSES = {
    0x01085081,  # NPCs (FemOld, Leanyka, Izmiguy, ConstrWorker 1)
    0x010C80C7,  # NAWayPoint (NPC walk points)
    0x01096095,  # bird flock (Madarraj)
    0x01078077,  # fish school sprites
    0x01104103,  # MineAllMine Mission Root
    0x01094092,  # MineAllMine Mission Shark 1-5
    0x0112B12A,  # collectible ('07 - Treasure Chest')
    0x0101B019,  # PartiHangArea (beach sound area)
}
# Creature generators: ACTN class 0x02129128 ('MarlinGenAct', 'MantarayGen'...)
# on group nodes 'Parent<X>Gen'; PROP 0x08000A78 = creature template node,
# 0x08000A79 = count, 0x08000A82 = area. They spawn ambient wildlife at runtime
# (marlins and rays still appeared in the first minimal build, 2026-10-04).
MINIMAL_ACTN_CLASSES = {0x02129128}
MINIMAL_NAMES = {'WhaleCarcass MorePrim', 'CrowdAllo', 'CollectableObjects', 'CollectibleAddOn'}
P_NAME, P_REF, P_FLAGS, P_TRANSFORM, P_AABB = 0x080017D8, 0x080017F0, 0x080017D9, 0x080017DA, 0x080017DF
HIDE_DY = -50000.0  # moves stage-logic-referenced scenery far below the world
# Kept nodes' properties known to hold node IDs (see CLAUDE.md).
# 0x08001376: NAWater2004's sun node (FISH: 'Sun', 3569, a plain-model brick).
# Removing it made the water surface stop rendering (user-tested 2026-10-03).
ID_PROPS = (0x080017F0, 0x08000AE5, 0x08000AE6, 0x080004A1, 0x080003C7, 0x08001376)


def props(d, q, qend):
    out = {}
    while q + 12 <= qend and d[q:q + 4] == b'PROP':
        s = u32(d, q + 4)
        out[u32(d, q + 8)] = d[q + 12:q + 8 + s]
        q += 8 + ((s + 3) & ~3)
    return out


def main(src, dst, keep_classes=(), keep_names=(), keep_ids=(), minimal=False):
    d = bytearray(open(src, 'rb').read())
    brtr = find_brtr(d)
    end = brtr + 8 + u32(d, brtr + 4)
    nodes = {}                 # id -> (class, props, children ids)
    actns = {}                 # id -> classes of the node's own ACTN blocks
    offsets = {}               # id -> CHBR file offset

    def walk(p):
        s, q, pr, kids, acts = u32(d, p + 4), p + 16, {}, [], set()
        while q < p + 8 + s:
            if d[q:q + 4] == b'PRPS':
                pr = props(d, q + 8, q + 8 + u32(d, q + 4))
            elif d[q:q + 4] == b'CHBR':
                kids.append(walk(q))
            elif d[q:q + 4] == b'ACTN':
                acts.add(u32(d, q + 8))
            q = (q + 8 + u32(d, q + 4) + 3) & ~3
        nodes[u32(d, p + 12)] = (u32(d, p + 8), pr, kids)
        actns[u32(d, p + 12)] = acts
        offsets[u32(d, p + 12)] = p
        return u32(d, p + 12)

    chunks, p = [], brtr + 16  # top-level sequence: (tag, start, end, node id)
    while p < end:
        t, nxt = d[p:p + 4], (p + 8 + u32(d, p + 4) + 3) & ~3
        chunks.append((t, p, nxt, walk(p) if t == b'CHBR' else None))
        p = nxt

    def name(n):
        return nodes[n][1].get(P_NAME, b'')[4:].split(b'\0')[0].decode('latin1')

    def subtree(n):
        out = [n]
        for k in nodes[n][2]:
            out += subtree(k)
        return out

    def prop_at(n, pid):
        p = offsets[n]
        q = p + 16
        while d[q:q + 4] != b'PRPS':
            q = (q + 8 + u32(d, q + 4) + 3) & ~3
        r, rend = q + 8, q + 8 + u32(d, q + 4)
        while r < rend:
            if u32(d, r + 8) == pid:
                return r + 12
            r += 8 + ((u32(d, r + 4) + 3) & ~3)
        return None

    def hide(top_id):
        """Move a subtree straight down by HIDE_DY: the top node and any
        absolute-transform (flag 0x20000000) descendant get their translation
        moved; every node's world-space AABB moves."""
        for n in subtree(top_id):
            flags = u32(nodes[n][1].get(P_FLAGS, bytes(4)), 0)
            t = prop_at(n, P_TRANSFORM)
            if t is not None and (n == top_id or flags & 0x20000000):
                struct.pack_into('<f', d, t + 40, struct.unpack_from('<f', d, t + 40)[0] + HIDE_DY)
            bb = prop_at(n, P_AABB)
            if bb is not None:
                for k in (4, 16):
                    struct.pack_into('<f', d, bb + k, struct.unpack_from('<f', d, bb + k)[0] + HIDE_DY)

    top = [c[3] for c in chunks if c[3] is not None]
    templates = {n for n in top if name(n) in SCENERY_TEMPLATES}
    keep = set(KEEP_NAMES) | set(keep_names)
    classes = SCENERY_CLASSES | (MINIMAL_CLASSES if minimal else set())
    groups = SCENERY_GROUPS | (MINIMAL_NAMES if minimal else set())
    spawners = MINIMAL_ACTN_CLASSES if minimal else set()
    remove = {n for n in top if name(n) not in keep and n not in keep_ids and nodes[n][0] not in keep_classes and (
        nodes[n][0] in classes or n in templates or name(n) in groups
        or any(actns[x] & spawners for x in subtree(n))
        or u32(nodes[n][1].get(P_REF, bytes(4)), 0) in templates)}
    doomed = {x for n in remove for x in subtree(n)}

    # Protect anything kept data might point at.
    # ACTN (quest/stage logic) references only need the ID to exist, so those
    # nodes are kept but hidden; nodes kept nodes point at through ID_PROPS
    # (e.g. the water's sun) are kept as they are.
    by_actn, by_prop = set(), set()
    for t, a, z, _ in chunks:
        if t == b'ACTN':
            by_actn |= {u32(d, o) for o in range(a, z - 3, 4)} & doomed
    for n, (_, pr, _) in nodes.items():
        if n not in doomed:
            for k in ID_PROPS:
                v = pr.get(k, b'')
                by_prop |= set(struct.unpack(f'<{len(v) // 4}I', v[:len(v) // 4 * 4])) & doomed
    for n in list(remove):
        sub = set(subtree(n))
        if by_prop & sub:
            remove.discard(n)
            print(f'  keeping {n} {name(n)!r} (referenced by a kept node)')
        elif by_actn & sub:
            remove.discard(n)
            hide(n)
            print(f'  keeping {n} {name(n)!r} hidden {-HIDE_DY:g} units down (referenced by stage logic)')

    payload = bytes(d[brtr + 8:chunks[0][1]])  # magic, root count
    for t, a, z, n in chunks:
        if n not in remove:
            payload += bytes(d[a:z])
    removed_nodes = sum(len(subtree(n)) for n in remove)
    replace_chunk_payload(d, brtr, payload)
    open(dst, 'wb').write(d)
    print(f'removed {len(remove)} top-level nodes ({removed_nodes} incl. children) of {len(top)}; '
          f'BRTR {end - brtr - 8} -> {len(payload)} bytes')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--minimal', action='store_true',
                    help='also remove NPCs, animals, missions and collectibles')
    ap.add_argument('--keep-class', nargs='*', default=[], type=lambda s: int(s, 0))
    ap.add_argument('--keep-name', nargs='*', default=[])
    ap.add_argument('--keep-id', nargs='*', default=[], type=int)
    a = ap.parse_args()
    main(a.src, a.dst, set(a.keep_class), set(a.keep_name), set(a.keep_id), a.minimal)

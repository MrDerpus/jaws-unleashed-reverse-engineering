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

    python3 scripts/strip_level.py IN.GDW OUT.GDW [--minimal | --blank]
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
  - nodes whose ID appears as a value in a PROP of a top-level ACTN block
    (stage/quest logic): kept but moved HIDE_DY units down, out of sight.
    Until 2026-10-04 this scanned every uint32 of the block, chunk sizes
    included, and FISH's small scenery IDs (72, 84, 128, 272, 288, 500, 516)
    collided with them: 8 unreferenced objects were hidden instead of removed.
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

--blank (2026-10-04, implies --minimal) also removes what's left of the
original level: BLANK_NAMES (FISH's leftover rocks/planes, floaters, fishing
chair, the buoy template) and every node whose name contains 'ship' plus
BLANK_SHIP_NAMES (boat/ship explosion, sinking and debris effects), and drops
the stage exit's CHBR children (the buoy ring; the exit itself stays). Of
those, a node is kept if anything kept points at it: a PROP value (of any
kept node or action, any depth) equal to an ID in its subtree. IDs below
1000 are ignored for this check, because small values (sizes, counts) in
PROPs collide with them. Sound banks, HUD, weapons, effects the shark uses
and creature templates stay.
It also recentres the level on the world origin: the shark's spawn
(RECENTRE_SPAWN) moves to x = z = 0, and the nodes tied to the original
location (RECENTRE_NAMES: spawn marker, sky dome, the water's sun, the
light's sun, the minimap anchor) move by the same amount, so they keep their
place relative to the spawn. And it disables the stock exit (which fires
when the shark leaves an 800-unit circle around the old spawn): its action
list moves from leave to enter, and the zone is parked at x = z =
EXIT_PARKED with radius 0. build_scene.py still finds it and reuses its
actions for exit zones made in Blender; without any, the level has no exit. Use prune_level.py afterwards (or on the built
level) to drop the resources nothing uses any more.
"""
import struct
import sys

from gdw_grow import find_brtr, replace_chunk_payload, u32
from insert_brtr_node import replace_prop

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
BLANK_NAMES = {'Box185 2', 'Box216 2', 'Kotelszakito_szikla_vf16', 'Plane01 1', 'fishbone 1',
               'szikla elem41 1', 'szikla elem52', 'szikla elem64 1', 'tores', 'horgaszszek',
               'Floater1_Brown', 'Floater2_Brown', 'BolyaDefOpen'}
BLANK_SHIP_NAMES = {'hajo_csavar_bubu', 'ANXploGen 1_dc', 'boat_crash', 'cuttergun_shot'}
AREA_TRIGGER = 0x01134132
RECENTRE_SPAWN = 'SHARRRK'
RECENTRE_NAMES = {'SHARRRK', 'SharkPosReal', 'NEW_SKY_OPEN', 'Sun', 'Sun(Y)', 'OceanMap1'}
EXIT_PARKED = 100000.0
P_AT_ENTER, P_AT_LEAVE, P_AT_RADIUS = 0x08000290, 0x08000291, 0x0800028F
MIN_TRUSTED_ID = 1000
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


def prop_values(d, a, z):
    """Every uint32 inside the PROP payloads of the chunk tree d[a:z]
    (PRPS/OBPR property lists of nodes, actions and PRIMs at any depth)."""
    out, q = set(), a
    while q + 8 <= z:
        t, s = d[q:q + 4], u32(d, q + 4)
        if t in (b'PRPS', b'OBPR'):
            r, rend = q + 8, q + 8 + s
            while r + 12 <= rend and d[r:r + 4] == b'PROP':
                ps = u32(d, r + 4)
                v = d[r + 12:r + 8 + ps]
                out |= set(struct.unpack_from(f'<{len(v) // 4}I', v))
                r += 8 + ((ps + 3) & ~3)
        elif t in (b'CHBR', b'ACTN', b'PRIM'):
            out |= prop_values(d, q + 16, q + 8 + s)
        q = (q + 8 + s + 3) & ~3
    return out


def main(src, dst, keep_classes=(), keep_names=(), keep_ids=(), minimal=False, blank=False):
    minimal = minimal or blank
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

    def shift(top_id, delta):
        """Move a subtree by delta (x, y, z): the top node and any
        absolute-transform (flag 0x20000000) descendant get their translation
        moved; every node's world-space AABB moves."""
        def add(o, k, v):
            struct.pack_into('<f', d, o + k, struct.unpack_from('<f', d, o + k)[0] + v)
        for n in subtree(top_id):
            flags = u32(nodes[n][1].get(P_FLAGS, bytes(4)), 0)
            t = prop_at(n, P_TRANSFORM)
            if t is not None and (n == top_id or flags & 0x20000000):
                for i in range(3):
                    add(t, 36 + 4 * i, delta[i])
            bb = prop_at(n, P_AABB)
            if bb is not None:
                for i in range(3):
                    add(bb, 4 * i, delta[i])
                    add(bb, 12 + 4 * i, delta[i])

    def hide(top_id):
        """Move a subtree straight down by HIDE_DY."""
        shift(top_id, (0.0, HIDE_DY, 0.0))

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
    def without_children(a, z):
        """A top-level CHBR without its CHBR children (keeps PRPS, ACTN, PRIM)."""
        q, node = a + 16, bytearray(d[a:a + 16])
        while q < z:
            nq = (q + 8 + u32(d, q + 4) + 3) & ~3
            if d[q:q + 4] != b'CHBR':
                node += d[q:nq]
            q = nq
        struct.pack_into('<I', node, 4, len(node) - 8)
        return bytes(node)

    def drops_ring(n):
        return blank and n is not None and nodes[n][0] == AREA_TRIGGER and nodes[n][2]

    if blank:
        extra = {n for n in top if name(n) not in keep and n not in keep_ids and (
            name(n) in BLANK_NAMES or name(n) in BLANK_SHIP_NAMES or 'ship' in name(n).lower())}
        # Drop leftovers nothing kept points at, until nothing changes (a
        # removed node can be the only thing pointing at another one).
        while True:
            used = set()
            for t, a, z, n in chunks:
                if n in remove | extra or t not in (b'CHBR', b'ACTN'):
                    continue
                if drops_ring(n):
                    node = without_children(a, z)
                    used |= prop_values(node, 16, len(node))
                else:
                    used |= prop_values(d, a + 16, z)
            protected = {n for n in extra
                         if {x for x in subtree(n) if x >= MIN_TRUSTED_ID} & used}
            if not protected:
                break
            for n in protected:
                print(f'  keeping {n} {name(n)!r} (a kept node points at it)')
            extra -= protected
        remove |= extra
    doomed = {x for n in remove for x in subtree(n)}

    # Protect anything kept data might point at.
    # ACTN (quest/stage logic) references only need the ID to exist, so those
    # nodes are kept but hidden; nodes kept nodes point at through ID_PROPS
    # (e.g. the water's sun) are kept as they are.
    by_actn, by_prop = set(), set()
    for t, a, z, _ in chunks:
        if t == b'ACTN':
            by_actn |= prop_values(d, a + 16, z) & doomed
    ring = {x for n in top if drops_ring(n) for k in nodes[n][2] for x in subtree(k)}
    for n, (_, pr, _) in nodes.items():
        if n not in doomed and n not in ring:
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

    disabled = {}   # exit node id -> its action list (moved from leave to enter)
    if blank:
        spawn = [n for n in top if name(n) == RECENTRE_SPAWN and n not in remove]
        if len(spawn) != 1:
            raise SystemExit(f'expected one {RECENTRE_SPAWN!r} node, found {len(spawn)}')
        sx, _, sz = struct.unpack_from('<3f', d, prop_at(spawn[0], P_TRANSFORM) + 36)
        delta = (-sx, 0.0, -sz)
        for n in top:
            if name(n) in RECENTRE_NAMES and n not in remove:
                shift(n, delta)
        print(f'  recentred {len([n for n in top if name(n) in RECENTRE_NAMES and n not in remove])} '
              f'location nodes by ({delta[0]:.1f}, 0, {delta[2]:.1f}): spawn now at x = z = 0')
        for n in top:
            if nodes[n][0] != AREA_TRIGGER or n in remove:
                continue
            leave = nodes[n][1].get(P_AT_LEAVE, bytes(4))
            if u32(leave, 0) == 0:
                continue
            disabled[n] = bytes(leave)   # swapped when the node is written (sizes differ)
            struct.pack_into('<f', d, prop_at(n, P_AT_RADIUS), 0.0)
            t = prop_at(n, P_TRANSFORM)
            x, y, z = struct.unpack_from('<3f', d, t + 36)
            shift(n, (EXIT_PARKED - x, 0.0, EXIT_PARKED - z))
            print(f'  {n} {name(n)!r}: stock exit disabled (enter-type, radius 0, parked at x = z = {EXIT_PARKED:g})')

    payload = bytes(d[brtr + 8:chunks[0][1]])  # magic, root count
    for t, a, z, n in chunks:
        if n in remove:
            continue
        if drops_ring(n) or n in disabled:
            node = bytes(d[a:z])
            if drops_ring(n):
                # The exit's buoy ring: keep the node's own chunks, drop CHBR children.
                node = without_children(a, z)
                print(f'  {n} {name(n)!r}: dropped {len(nodes[n][2])} child nodes (buoy ring)')
            if n in disabled:
                node = replace_prop(replace_prop(node, P_AT_ENTER, disabled[n]), P_AT_LEAVE, bytes(4))
            payload += node
            continue
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
    ap.add_argument('--blank', action='store_true',
                    help='--minimal plus the original level\'s leftovers and ship effects')
    ap.add_argument('--keep-class', nargs='*', default=[], type=lambda s: int(s, 0))
    ap.add_argument('--keep-name', nargs='*', default=[])
    ap.add_argument('--keep-id', nargs='*', default=[], type=int)
    a = ap.parse_args()
    main(a.src, a.dst, set(a.keep_class), set(a.keep_name), set(a.keep_id), a.minimal, a.blank)

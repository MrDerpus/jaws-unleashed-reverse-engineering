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

"""Proof of concept: run the cut "Hot Pursuit" quest (StagePursuitQuest2) in
MINEMSHA's canal, on the cut mission's leftover jet ski.

    python3 scripts/build_pursuit_test.py [OUT.GDW] [--deploy NAME] [--stock-jetski]

Base: stock GAME_GDWs/MINEMSHA.GDW. Output defaults to edited_levels/PURSUIT.GDW;
--deploy copies it to the live game's custom_levels/NAME.GDW (F9 in-game).

What it adds (see docs/exe_analysis.md "Cut story mission Hot Pursuit"):
  - QUEST: a root-level ACTN of class StagePursuitQuest2 (0x0208D08C), laid out
    like the shipped root quests (DOCKS StageDocksQuest, MINEMSHA Stage0Quest).
    Jet skis = a top-level COPY of 'jetski 1' (node 2670, the ANPosition reference
    inside SC15's SM16UpACreek tree) and of its rider, driving a reversed copy of the
    sail boats' canal route from the cove north up the canal, through two gates (v8,
    default; see CANAL). With --stock-jetski it tracks 'jetski 1' itself on its small
    cove loop, with gate closing switched off (v5: chase, lose, boss phase and win
    confirmed in-game).
    The marker resolves to its spawned copy at runtime (ANPosition vtable +0x24
    -> object ID at +0xF4), the same way shipped quests list boats. The quest is
    a root ACTN, active from load (v2 tried a start zone: the quest never ran).
  - GATES: pink boxes on the jet ski's route. Gate opener = GDControl that hides
    it, gate closer = GDControl that shows it again.
    Marker A (open) and B (close) are empty group nodes on the tracked jet ski's
    route (see CANAL / STOCK), with m_nFlags 0x12 (0x10 = in world): without it a node gets no
    live brick, the quest's position lookup returns null and the gate never opens.
  - END ZONE: an area trigger (copied from FISH's exit, PRPS only) at the
    route's end; entering it starts a StagePursuitQuest2Event (message 5 ->
    boss fight, accepted once the gate has closed behind the jet ski) and hides
    a yellow probe cube there (shows that the zone fires at all).
  - WIN MARKER: a blue pillar near the spawn; m_OnAccomplished = GDControl that
    hides it.
All new controls/events sit on one new group-type node (actions on group nodes
get live instances at load; see add_trigger.py). That node also needs m_nFlags
0x10 (in world): with NorthBrick's 0x2 its actions got no live instance, so the
quest could not start the gate opener and the zones started nothing (v3 test).
"""
import argparse
import os
import shutil
import struct
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import add_trigger
import brtr_scene_graph as g
from add_trigger import Ids, make_control
from gdw_grow import find_brtr, replace_chunk_payload, append_to_chunk, top_chunks, u32
from gdw_materials import build_gmat_index
from insert_brtr_node import top_level_nodes, build_node, prop_offsets, replace_prop
from obj_to_gmdl import load_parts, build_gmdl, next_free_id
from build_scene import LIVE_DATA

BASE = ROOT / 'GAME_GDWs' / 'MINEMSHA.GDW'
FISH = ROOT / 'GAME_GDWs' / 'FISH.GDW'
# ---- MINEMSHA nodes ----
SHARK = 13828            # SHARRRK, spawn (-1258, 0, -1020)
JETSKI = 2670            # 'jetski 1', ANPosition -> JetSki template, route PROP 0x080001F0
MODEL_TEMPLATE = 956     # 'nadas03 14': plain rendered GDModel, opaque (0x820), absolute
GROUP_TEMPLATE = 151     # 'NorthBrick': empty GDStdBrick (group type 0x010B10AA)
WHITE_GMAT = 1534        # opaque material on a plain white 8x8 texture
FISH_EXIT = 1551         # FISH area trigger (class 0x01134132), used for its PRPS

# ---- layout (world, y = water surface) ----
GATE_SIZE = (160.0, 40.0, 6.0)          # x, y (centred on the surface), z
PILLAR_POS = (-1170.0, 0.0, -1010.0)
PILLAR_SIZE = (12.0, 120.0, 12.0)

# Two layouts:
#   canal (default, v8): the quest tracks a copy of 'jetski 1' and its rider (top-level,
#     outside SC15's tree) driving a copy of the sail boats' canal route, reversed so it
#     runs from the cove north up the main canal (vitorlas_a1_a2 path, node 2658, 24
#     points, ~1230 units). Set up like the sail boats that drive it: both path fields
#     on the route, no chase mode / chase area. Two gates on the route; each wall's own
#     position is both its open marker (opens when the jet ski is within 150) and its
#     close marker (shuts once the jet ski passed within 100 and is 150 beyond).
#   stock (--stock-jetski, v5): the quest tracks 'jetski 1' itself, which drives its
#     small figure-eight jetskipath in the cove: no closers, close marker unreachable.
# Found on the way (v6/v7, F12 boat probe): 'jetski 1' and copies DO follow their path
# (state 2, sub-state 3); both stock jet-ski routes are just small loops in the cove.
# m_runaway 2 + m_alarmer 1 made a copy flee up the canal instead (sub-states 6/2).
ROUTE_SRC = 2658         # vitorlas_a1_a2 path (open, used by sail boats vitorlas_a 4 / 6)
CANAL = {
    'gates': [(-1275.0, 0.0, -370.0), (-1234.0, 0.0, -60.0)],   # on the route
    'end_zone': ((-1353.0, 0.0, 215.0), 60.0),                  # route end: message 5
    'closers': True,
}
STOCK = {
    'gate': (-1257.0, 0.0, -945.0),            # between spawn and the cove
    'open_marker': (-1257.0, 0.0, -800.0),     # every jetskipath point is within 150: opens at once
    'close_marker': (-1257.0, -3000.0, -800.0),  # unreachable (the list must stay non-empty)
    'end_zone': ((-1257.0, 0.0, -800.0), 45.0),
    'closers': False,
}
RIDER = 2682             # 'ccjetski', BGPolicemanRef (Civilian template), jetski 1's crew
# ANPosition (class descriptor 0x8CBB10, 98 fields) PROP = 0x080001EE + field index.
P_PATH1, P_ROUTE = 0x080001EF, 0x080001F0    # fields 1/2: both = route on the sail boats
P_CHASE_PROC, P_CHASE_AREA = 0x080001FB, 0x080001FC
P_CREW = 0x08000214                          # m_customcrew
# Driving tune (v10): with jetski 1's m_speed 250 and m_turnd/m_stopd 0 (inherit) the copy
# drove north but rammed the canal's bends (the route is the slow sail boats'), got stuck
# or wrecked itself. Ocean boats use m_turnd 40, m_stopd 20.
P_SPEED, P_TURND, P_STOPD = 0x08000212, 0x08000218, 0x08000219
DRIVE = {P_SPEED: 120.0, P_TURND: 40.0, P_STOPD: 20.0}
P_TRACK, P_TRACK_CLOSED = 0x080018BC, 0x080018BD   # GDPath points [n][xyz...], closed flag
LOST_DIST = 700.0

PINK, BLUE, YELLOW = (1.0, 0.2, 0.7, 1.0), (0.2, 0.4, 1.0, 1.0), (1.0, 0.9, 0.1, 1.0)
PROBE_SIZE = (10.0, 10.0, 10.0)        # yellow cube at the end zone, hidden when the zone fires
IN_WORLD = 0x12                        # m_nFlags like SHARRRK: 0x10 = in world, so the node gets a
                                       # live brick (position); NorthBrick's 0x2 gets none

# ---- classes / PROP IDs ----
QUEST2_CLASS, QUEST2_EVENT_CLASS = 0x0208D08C, 0x02086085
P_JETSKIS, P_OPENPOS, P_CLOSEPOS, P_OPENERS, P_CLOSERS, P_BOSSES = range(0x080011D9, 0x080011DF)
P_ON_ACCOMPLISHED, P_ON_BOSSFIGHT, P_LOST_DIST = 0x080011DF, 0x080011E0, 0x080011E1
P_XF, P_AABB, P_NAME, P_FLAGS, P_VIEWPORT, P_COLOR = (
    0x080017DA, 0x080017DF, 0x080017D8, 0x080017D9, 0x080017DD, 0x08001879)
P_AT_TARGET, P_AT_RADIUS, P_AT_ENTER, P_AT_LEAVE = 0x0800028E, 0x0800028F, 0x08000290, 0x08000291

HIDE, SHOW = 0x8F000100, 0x8F000080


def prop(pid, value):
    e = b'PROP' + struct.pack('<II', 4 + len(value), pid) + value
    return e + b'\0' * (-len(e) % 4)


def ids_value(ids):
    return struct.pack('<I', len(ids)) + b''.join(struct.pack('<I', i) for i in ids)


def name_value(s):
    b = s.encode() + b'\0'
    return struct.pack('<I', len(b)) + b + b'\0' * (-len(b) % 4)


def actn(cls, aid, props, name, active):
    """ACTN with the base action fields every shipped quest/event carries."""
    base = [(0x080017C3, name_value(name)), (0x080017C4, struct.pack('<I', 2 if active else 0)),
            (0x080017C5, bytes(4)), (0x080017C6, bytes(4)), (0x080017C7, struct.pack('<I', 3)),
            (0x080017C8, bytes(4))]
    body = b''.join(prop(p, v) for p, v in sorted(props + base))
    out = b'ACTN' + struct.pack('<III', 0, cls, aid) + b'PRPS' + struct.pack('<I', len(body)) + body
    return out[:4] + struct.pack('<I', len(out) - 8) + out[8:]


def box_obj(size, path):
    """Axis-aligned box centred on the origin, as an OBJ with outward faces."""
    sx, sy, sz = (s / 2 for s in size)
    v = [(x, y, z) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
    faces = [(1, 2, 4, 3), (5, 7, 8, 6), (1, 5, 6, 2), (3, 4, 8, 7), (1, 3, 7, 5), (2, 6, 8, 4)]
    with open(path, 'w') as f:
        f.write(''.join(f'v {x} {y} {z}\n' for x, y, z in v))
        f.write('vt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\n')
        for q in faces:
            f.write('f ' + ' '.join(f'{i}/{k + 1}' for k, i in enumerate(q)) + '\n')


def add_box(d, size, gmats, tmp):
    obj = os.path.join(tmp, f'box_{size[0]:g}x{size[1]:g}x{size[2]:g}.obj')
    box_obj(size, obj)
    mesh_id = next_free_id(d)
    blob, nv, nt, _ = build_gmdl(mesh_id, load_parts(obj, 1.0, WHITE_GMAT, gmats))
    append_to_chunk(d, top_chunks(d)['RSRC'], blob)
    print(f'GMDL {mesh_id}: box {size}, {nv} verts, {nt} tris')
    return mesh_id


def model_node(d, tops, nid, mesh, pos, colour, name):
    xf = (1, 0, 0, 0, 1, 0, 0, 0, 1) + pos
    node = bytearray(build_node(d, tops[MODEL_TEMPLATE], nid, xf, mesh, {P_VIEWPORT: 0x20003}))
    struct.pack_into('<4f', node, prop_offsets(node)[P_COLOR], *colour)
    return replace_prop(bytes(node), P_NAME, name_value(name))


def group_node(d, tops, nid, pos, name, children=b'', flags=None):
    p, s = tops[GROUP_TEMPLATE]
    node = bytes(d[p:p + 8 + s]) + b'\0' * (-(8 + s) % 4)
    node = bytearray(node)
    struct.pack_into('<I', node, 12, nid)
    node = replace_prop(bytes(node), P_XF, struct.pack('<12f', 1, 0, 0, 0, 1, 0, 0, 0, 1, *pos))
    node = replace_prop(node, P_AABB, struct.pack('<6f', *pos, *pos))
    node = replace_prop(node, P_NAME, name_value(name))
    if flags is not None:
        node = replace_prop(node, P_FLAGS, struct.pack('<I', flags))
    node += children
    return node[:4] + struct.pack('<I', len(node) - 8) + node[8:]


def zone_node(nid, pos, radius, action_ids, name):
    f = FISH.read_bytes()
    tops, _ = top_level_nodes(f, find_brtr(f))
    p, s = tops[FISH_EXIT]
    src, q = f[p:p + 8 + s], 16
    while src[q:q + 4] != b'PRPS':
        q = (q + 8 + u32(src, q + 4) + 3) & ~3
    prps = src[q:q + 8 + u32(src, q + 4)]
    node = bytearray(src[:16] + prps)
    struct.pack_into('<I', node, 4, len(node) - 8)
    struct.pack_into('<I', node, 12, nid)
    x, y, z = pos
    node = replace_prop(bytes(node), P_AT_TARGET, struct.pack('<I', SHARK))
    node = replace_prop(node, P_AT_RADIUS, struct.pack('<f', radius))
    node = replace_prop(node, P_AT_ENTER, ids_value(action_ids))
    node = replace_prop(node, P_AT_LEAVE, ids_value([]))
    node = replace_prop(node, P_NAME, name_value(name))
    node = replace_prop(node, P_XF, struct.pack('<12f', 1, 0, 0, 0, 1, 0, 0, 0, 1, x, y, z))
    return replace_prop(node, P_AABB, struct.pack('<6f', x - radius, y - 50, z - radius,
                                                   x + radius, y + 50, z + radius))


def nested_node(d, brtr, node_id):
    """Raw bytes of the CHBR with node_id anywhere in BRTR (must have no children)."""
    p, end = brtr + 16, brtr + 8 + u32(d, brtr + 4)
    while (p := d.find(b'CHBR', p, end)) != -1:
        if d[p + 16:p + 20] == b'PRPS' and u32(d, p + 12) == node_id:
            node = bytes(d[p:p + 8 + u32(d, p + 4)])
            prps_end = 24 + u32(node, 20)
            assert len(node) - prps_end < 4, f'node {node_id} has children'
            return node + b'\0' * (-len(node) % 4)
        p += 4
    raise SystemExit(f'node {node_id} not found')


def set_props(node, values):
    for pid, v in values.items():
        node = replace_prop(node, pid, v)
    return node


def free_jetski(d, brtr, ski_id, rider_id, start, route, name, bounds=None):
    """Top-level copies of 'jetski 1' (moved to start, both path fields = route, chase
    mode and area off like the sail boats, crew = the rider copy) and of its rider."""
    ski = bytearray(nested_node(d, brtr, JETSKI))
    struct.pack_into('<I', ski, 12, ski_id)
    po = prop_offsets(ski)
    xf = list(struct.unpack_from('<12f', ski, po[P_XF]))
    dx, dy, dz = (start[k] - xf[9 + k] for k in range(3))
    xf[9:12] = start
    bb = list(struct.unpack_from('<6f', ski, po[P_AABB]))
    bb = [bb[0] + dx, bb[1] + dy, bb[2] + dz, bb[3] + dx, bb[4] + dy, bb[5] + dz]
    if bounds is not None:
        bb = list(bounds)           # v9: cover the whole route (rules out AABB culling)
    ski = set_props(bytes(ski), {
        P_XF: struct.pack('<12f', *xf), P_AABB: struct.pack('<6f', *bb),
        P_PATH1: struct.pack('<I', route), P_ROUTE: struct.pack('<I', route),
        P_CHASE_PROC: bytes(4), P_CHASE_AREA: bytes(4),
        P_CREW: ids_value([rider_id]), P_NAME: name_value(name),
        **{pid: struct.pack('<f', v) for pid, v in DRIVE.items()}})
    rider = bytearray(nested_node(d, brtr, RIDER))
    struct.pack_into('<I', rider, 12, rider_id)
    # authored local (1257.83, 0, 967.32) under SM16UpACreek at (-1257.83, 0, -967.32):
    # world = origin; as a top-level node it keeps that world spot
    rider = set_props(bytes(rider), {P_XF: struct.pack('<12f', 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0),
                                     P_NAME: name_value(name + 'Rider')})
    return ski + rider


def remove_nodes(d, brtr, node_ids):
    """Cut childless CHBRs out of a standalone copy of the BRTR chunk (d = that copy,
    brtr = its offset in it), fixing every ancestor's size and BRTR's; hand the result
    to replace_chunk_payload so FSIZ/SKIP/FDIR follow. An ancestor whose size excludes the removed node's trailing padding
    (last child) loses only the bytes it actually covered."""
    for nid in node_ids:
        end = brtr + 8 + u32(d, brtr + 4)
        anc, hit = [], None

        def walk(lo, hi):
            nonlocal hit
            p = lo
            while p < hi - 8 and hit is None:
                tag, sz = d[p:p + 4], u32(d, p + 4)
                if tag == b'CHBR':
                    if u32(d, p + 12) == nid:
                        hit = (p, sz)
                        return
                    anc.append(p)
                    walk(p + 16, p + 8 + sz)
                    if hit is None:
                        anc.pop()
                p = (p + 8 + sz + 3) & ~3

        walk(brtr + 16, end)
        if hit is None:
            raise SystemExit(f'node {nid} not found')
        p, sz = hit
        cut_end = (p + 8 + sz + 3) & ~3
        for a in anc:
            a_end = a + 8 + u32(d, a + 4)
            struct.pack_into('<I', d, a + 4, u32(d, a + 4) - (min(cut_end, a_end) - p))
        struct.pack_into('<I', d, brtr + 4, u32(d, brtr + 4) - (cut_end - p))
        del d[p:cut_end]


def route_node(d, brtr, path_id, world_xf):
    """Top-level copy of the canal route, points reversed (cove first), placed at the
    source path's world transform (its points are local to it)."""
    node = bytearray(nested_node(d, brtr, ROUTE_SRC))
    struct.pack_into('<I', node, 12, path_id)
    track = prop_offsets(node)[P_TRACK]
    n = u32(node, track)
    pts = [struct.unpack_from('<3f', node, track + 4 + 12 * k) for k in range(n)][::-1]
    for k, p in enumerate(pts):
        struct.pack_into('<3f', node, track + 4 + 12 * k, *p)
    node = set_props(bytes(node), {P_XF: struct.pack('<12f', *world_xf),
                                   P_NAME: name_value('PursuitRoute')})
    xf = world_xf
    world = [(xf[0]*x + xf[3]*y + xf[6]*z + xf[9], xf[1]*x + xf[4]*y + xf[7]*z + xf[10],
              xf[2]*x + xf[5]*y + xf[8]*z + xf[11]) for x, y, z in pts]
    return node, world


def control(cid, word, targets, name):
    add_trigger.STEPS, add_trigger.DELAY = [(word, name)], 0
    return make_control(cid, targets)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?', default=str(ROOT / 'edited_levels' / 'PURSUIT.GDW'))
    ap.add_argument('--deploy', metavar='NAME')
    ap.add_argument('--stock-jetski', action='store_true',
                    help="v5 layout: track 'jetski 1' itself in the cove, no gate closing")
    a = ap.parse_args()
    lay = STOCK if a.stock_jetski else CANAL

    d = bytearray(BASE.read_bytes())
    gmats = build_gmat_index(d)
    with tempfile.TemporaryDirectory() as tmp:
        gate_mesh = add_box(d, GATE_SIZE, gmats, tmp)
        pillar_mesh = add_box(d, PILLAR_SIZE, gmats, tmp)
        probe_mesh = add_box(d, PROBE_SIZE, gmats, tmp)

    brtr = find_brtr(d)
    tops, end = top_level_nodes(d, brtr)
    ids = Ids(d)
    pillar, holder, zone, probe, quest, win, event, probe_ctl = (ids.new() for _ in range(8))
    nodes, actions = b'', b''

    if a.stock_jetski:
        tracked, route_desc = JETSKI, "'jetski 1' on jetskipath"
        gate_spots = [lay['gate']]
        open_spots, close_spots = [lay['open_marker']], [lay['close_marker']]
    else:
        gnodes, _, rx = g.load_nodes(bytes(d))
        route_id, tracked, rider = ids.new(), ids.new(), ids.new()
        rnode, pts = route_node(d, brtr, route_id, g.authored_world(gnodes, rx)[ROUTE_SRC])
        margin = 100.0
        bounds = (min(p[0] for p in pts) - margin, -300.0, min(p[2] for p in pts) - margin,
                  max(p[0] for p in pts) + margin, 300.0, max(p[2] for p in pts) + margin)
        nodes += rnode + free_jetski(d, brtr, tracked, rider, pts[0], route_id, 'PursuitJetski', bounds)
        route_desc = f'copy of jetski 1 on route {route_id} ({len(pts)} points, start {tuple(round(v) for v in pts[0])})'
        gate_spots = open_spots = close_spots = lay['gates']

    walls, openers, closers, open_ids, close_ids = [], [], [], [], []
    for k, spot in enumerate(gate_spots):
        wall, op, cl = ids.new(), ids.new(), ids.new()
        nodes += model_node(d, tops, wall, gate_mesh, spot, PINK, f'PursuitGate{k + 1}')
        actions += control(op, HIDE, [wall], 'hide') + control(cl, SHOW, [wall], 'show')
        walls.append(wall); openers.append(op); closers.append(cl)
    for spots, out in ((open_spots, open_ids), (close_spots, close_ids)):
        for k, spot in enumerate(spots):
            if out is close_ids and close_spots is open_spots:
                out.append(open_ids[k])           # canal: one marker per gate, used for both
                continue
            mid = ids.new()
            nodes += group_node(d, tops, mid, spot, f'PursuitGateMarker{k + 1}', flags=IN_WORLD)
            out.append(mid)

    actions += (control(win, HIDE, [pillar], 'hide') + control(probe_ctl, HIDE, [probe], 'hide')
                + actn(QUEST2_EVENT_CLASS, event, [(0x08001165, bytes(4)), (0x08001166, struct.pack('<I', 5)),
                                                   (0x08001167, struct.pack('<I', 5))],
                       'PursuitEvent_ReachedEnd', active=False))
    quest_actn = actn(QUEST2_CLASS, quest, [
        (0x08001161, ids_value([])), (0x08001162, ids_value([])),     # base: checkpoints, checkpoint actions
        (0x08001163, ids_value([])), (0x08001164, ids_value([])),     # base: events, mission bricks
        (P_JETSKIS, ids_value([tracked])),
        (P_OPENPOS, ids_value(open_ids)), (P_CLOSEPOS, ids_value(close_ids)),
        # Without closers (stock layout) 'all gates closed' (count < next-to-close index)
        # is true from the start, so the end zone's message 5 starts the boss phase at
        # once. m_GateClosePosIDList must stay non-empty: the tick reads entry [c-1].
        (P_OPENERS, ids_value(openers)), (P_CLOSERS, ids_value(closers if lay['closers'] else [])),
        (P_BOSSES, ids_value([])),
        (P_ON_ACCOMPLISHED, struct.pack('<I', win)), (P_ON_BOSSFIGHT, bytes(4)),
        (P_LOST_DIST, struct.pack('<f', LOST_DIST)),
    ], 'StagePursuitQuest2', active=True)
    # Active from load at the root, like the shipped root quests (v1 ticked this way: the
    # lose condition fired). v2 put it, inactive, on the group node with a start zone,
    # and it never ran.
    end_pos, end_r = lay['end_zone']
    nodes += (model_node(d, tops, pillar, pillar_mesh, PILLAR_POS, BLUE, 'PursuitWinMarker')
              + model_node(d, tops, probe, probe_mesh, end_pos, YELLOW, 'PursuitZoneProbe')
              + group_node(d, tops, holder, PILLAR_POS, 'PursuitControls', actions, flags=IN_WORLD)
              + zone_node(zone, end_pos, end_r, [event, probe_ctl], 'PursuitEndZone'))

    if not a.stock_jetski:
        # The loiterer: SC15's 'jetski 1' and its rider; nothing else references them.
        # Cut out after copying them; BRTR shrinks, so re-read its end and node offsets.
        size_before = u32(d, brtr + 4)
        chunk = bytearray(d[brtr:brtr + 8 + size_before])
        remove_nodes(chunk, 0, [JETSKI, RIDER])
        replace_chunk_payload(d, brtr, bytes(chunk[8:8 + u32(chunk, 4)]))  # fixes FSIZ/SKIP/FDIR
        print(f"removed 'jetski 1' ({JETSKI}) and its rider ({RIDER}): BRTR -{size_before - u32(d, brtr + 4)} bytes")
        tops, end = top_level_nodes(d, brtr)

    # Root-level ACTNs come right after the root PRPS, before the first CHBR.
    payload = bytes(d[brtr + 8:end])
    first_chbr = min(p for p, _ in tops.values()) - (brtr + 8)
    payload = payload[:first_chbr] + quest_actn + payload[first_chbr:] + nodes
    replace_chunk_payload(d, brtr, payload)

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes(d)
    print(f'quest {quest} (root, active): jet ski {tracked} = {route_desc}, lost distance {LOST_DIST:g}')
    print(f'gates (pink) {walls} openers {openers} closers {closers if lay["closers"] else "none"}; '
          f'open markers {open_ids} close markers {close_ids}')
    print(f'end zone {zone} -> event {event} + probe {probe} (yellow); win marker {pillar} (blue) hidden by {win}; holder {holder}')
    print(f'wrote {a.out} ({len(d):,} bytes)')
    if a.deploy:
        name = a.deploy.upper()
        if os.path.exists(os.path.join(LIVE_DATA, name + '.GDW')):
            raise SystemExit(f'{name} is a stock level name')
        live_dir = os.path.join(os.path.dirname(LIVE_DATA.rstrip('/')), 'custom_levels')
        os.makedirs(live_dir, exist_ok=True)
        shutil.copyfile(a.out, os.path.join(live_dir, name + '.GDW'))
        print(f'deployed to {live_dir}/{name}.GDW -- F9 in-game to load it')


if __name__ == '__main__':
    main()

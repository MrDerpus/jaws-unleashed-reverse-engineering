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

"""Bring back Ecco's fish school (MLHalRaj): compiled into Jaws.exe, never placed.

    python3 scripts/build_fishball_test.py [OUT.GDW] [--deploy NAME]

Base: levels/custom_fish/FISH_blank_base.GDW (spawn at the origin). Output defaults to
edited_levels/FISHBALL.GDW; --deploy copies it to the game's custom_levels/NAME.GDW (F9).

Layout copied from Ecco: Defender of the Future (120NORTH, node 6354):
    GDStdBrick  'FishBall N'        carries the MLHalRaj ACTN
      GDStdBrick 'FishBall N Body'  empty, identity
        GDModel  'FishBall N Fish'  the fish model (local transform = scale/orientation)
MLHalRaj's init (Jaws 0x4E9A80) takes the brick's first child, then that child's first
child as the model, hides it (m_nFlags 0x100) and draws it mnum times itself (draw
0x4E9FF0, render matrix = fish matrix x model local). Tick 0x4EA3E0: fish 0 leads, turning
to a new random heading every ccount..ccount+ccountrnd ticks and back towards the brick
when it leaves the sphere mrange (or the box boxx/y/z when mrange = 0); the others hold a
random offset (frange x frange x rangez; rangez -1 = frange) from the leader, catching up
at 'fast' when farther than maxleader. felid = objects to flee from (within ecconear).
mrange, maxleader and ecconear are compared with SQUARED distances. Fish swim along +Z.
mincolor/maxcolor (added in Jaws) shade each fish by its angle to the camera.

The fish: WRACK's clownfish (GMDL 1361 -> GMAT 739 -> GTEX 219), copied in under the
next free resource IDs, at WRACK's scale 7.5 (about 1.1 units long).

For comparison, two shipped Jaws schools stand beside them: MLHalRaj3 is a GD3dSprite
subclass (flat sprite fish), placed as a top-level template plus MLHalRaj3Reference nodes
(m_Ref = template, with their own count/size/speed). The FISH templates 'Piros-Feher Hal
Sprite' (23022) and 'Zebra Hal Sprite' (22980) are copied as they are (their sprite
materials 966/969 are still in the blank base), and each gets a copy of FISH's reference
'piros-feher' (34098). Their m_enemy is 'HalRiaszto' (26265), a child of the shark.
"""
import argparse
import os
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from add_trigger import Ids, chunk_headers
from build_pursuit_test import prop, ids_value, name_value
from build_scene import LIVE_DATA
from gdw_grow import find_brtr, replace_chunk_payload, append_to_chunk, top_chunks, u32
from gdw_textures import find_block
from insert_brtr_node import top_level_nodes, build_node, prop_offsets, replace_prop
from obj_to_gmdl import next_free_id

BASE = ROOT / 'levels' / 'custom_fish' / 'FISH_blank_base.GDW'
FISH = ROOT / 'GAME_GDWs' / 'FISH.GDW'
WRACK = ROOT / 'GAME_GDWs' / 'WRACK.GDW'
FISH_MESH, FISH_SCALE = 1361, 7.5      # WRACK clownfish (ClownFish Path Include:Clown_Fish 1)
SHARK = 26116                          # SHARRRK
GROUP_TEMPLATE = 1015                  # 'ZeroPosition': empty GDStdBrick, m_nFlags 0x12
MODEL_TEMPLATE = 79                    # stock FISH non-solid model (build_scene's ghost template)
IN_WORLD = 0x12
# m_RenderSetting / m_ChannelSetting of WRACK's moving clownfish (node 27961); the
# template's own 0x40000800 / 0 are rock-wall values.
FISH_RENDER = {0x08001876: 0x860, 0x08001878: 0x3F}

HALRAJ_CLASS = 0x02144143              # ACCM index 0x143 (+1 in the middle bits, like MLMadarRaj 0x0214C14B)
P_XF, P_AABB, P_NAME, P_FLAGS, P_VIEWPORT = 0x080017DA, 0x080017DF, 0x080017D8, 0x080017D9, 0x080017DD
# MLHalRaj fields, PROP 0x08000984 + field index (FISH CLAS/PRIM)
FIELDS = ['mnum', 'mrange', 'boxx', 'boxy', 'boxz', 'frange', 'rangez', 'maxspeed', 'maxspeedmulrnd',
          'fast', 'rotaccel', 'escaccel', 'animspeed', 'animspeedrnd', 'ccount', 'ccountrnd', 'fp',
          'ecconear', 'maxleader', 'eatscale', 'damage', 'felid', 'zaj', 'mincolor', 'maxcolor']
P_FIELD = {f: 0x08000984 + i for i, f in enumerate(FIELDS)}
INTS = {'mnum', 'ccount', 'ccountrnd', 'zaj'}

# Ecco 120NORTH's values with distances roughly doubled (the clownfish is ~1.7x Ecco's
# fish03). eatscale/damage/fp/animspeed are not read by the Jaws code.
ECCO = dict(mnum=19, mrange=100.0, boxx=0.0, boxy=0.0, boxz=0.0, frange=8.0, rangez=-4.0,
            maxspeed=0.3, maxspeedmulrnd=0.3, fast=0.5, rotaccel=0.005, escaccel=0.009,
            animspeed=1.0, animspeedrnd=0.2, ccount=30, ccountrnd=30, fp=0.3, ecconear=400.0,
            maxleader=100.0, eatscale=1.4, damage=1.6, zaj=0, mincolor=0.6, maxcolor=1.0)
SCHOOLS = [   # (position, overrides); spawn is (0, -6.5, 0) facing +Z
    # v2 (user: "make them larger"): ~3x the fish, ~2x the spread (mrange is squared: 4x)
    # v3 (user: "make them 50X" the fish count): stress test, 10,000 fish drawn one by one
    ((0.0, -12.0, 50.0), dict(mnum=3000, mrange=400.0, frange=16.0, rangez=-8.0)),
    ((-45.0, -14.0, 60.0), dict(mnum=5000, mrange=900.0, frange=24.0, rangez=-12.0)),
    ((45.0, -10.0, 60.0), dict(mnum=2000, mrange=100.0, frange=8.0, rangez=-4.0, maxspeed=0.2)),
]
JAWS_TEMPLATES = (23022, 22980)     # FISH MLHalRaj3 templates, copied with their IDs
JAWS_REFERENCE = 34098              # FISH MLHalRaj3Reference 'piros-feher' (40 fish)
JAWS_SCHOOLS = [((-100.0, -10.0, 55.0), 23022, 'Jaws school red-white'),
                ((100.0, -10.0, 55.0), 22980, 'Jaws school zebra')]
P_REF = 0x080017F0
SPAN = 70.0   # half-size of every school node's AABB (leader range + follower offsets)


def copy_fish(d, src):
    """Copy GMDL FISH_MESH with its GMATs and their textures from src into d's RSRC
    under the next free IDs. Returns the new mesh ID."""
    nxt = next_free_id(d)
    p = find_block(src, b'GMDL', FISH_MESH)
    gmdl = bytearray(src[p:p + 8 + u32(src, p + 4)]); gmdl += bytes(-len(gmdl) % 4)
    m = gmdl.find(b'MATS')
    gmat_ids = [u32(gmdl, m + 16 + 8 * i) for i in range(u32(gmdl, m + 8))]
    blob, tex_map, gmat_map = b'', {}, {}
    for g in gmat_ids:
        q = find_block(src, b'GMAT', g)
        gmat = bytearray(src[q:q + 8 + u32(src, q + 4)]); gmat += bytes(-len(gmat) % 4)
        t = gmat.find(b'TEXP')
        for i in range(u32(gmat, t + 8)):
            old = u32(gmat, t + 16 + 8 * i)
            if old not in tex_map:
                r = find_block(src, b'GTEX', old)
                gtex = bytearray(src[r:r + 8 + u32(src, r + 4)]); gtex += bytes(-len(gtex) % 4)
                tex_map[old] = nxt; nxt += 1
                struct.pack_into('<I', gtex, 8, tex_map[old])
                blob += gtex
            struct.pack_into('<I', gmat, t + 16 + 8 * i, tex_map[old])
        gmat_map[g] = nxt; nxt += 1
        struct.pack_into('<I', gmat, 8, gmat_map[g])
        blob += gmat
    for i, g in enumerate(gmat_ids):
        struct.pack_into('<I', gmdl, m + 16 + 8 * i, gmat_map[g])
    mesh_id = nxt
    struct.pack_into('<I', gmdl, 8, mesh_id)
    append_to_chunk(d, top_chunks(d)['RSRC'], blob + gmdl)
    print(f'copied WRACK GMDL {FISH_MESH} -> {mesh_id}, GMAT {gmat_map}, GTEX {tex_map}')
    return mesh_id


def group_node(d, tops, nid, pos, name, children=b''):
    """Copy of the base's empty GDStdBrick GROUP_TEMPLATE, plus children (ACTN/CHBR)."""
    p, s = tops[GROUP_TEMPLATE]
    node = bytes(d[p:p + 8 + s]) + b'\0' * (-(8 + s) % 4)
    node = node[:12] + struct.pack('<I', nid) + node[16:]
    node = replace_prop(node, P_XF, struct.pack('<12f', 1, 0, 0, 0, 1, 0, 0, 0, 1, *pos))
    node = replace_prop(node, P_NAME, name_value(name))
    node = replace_prop(node, P_FLAGS, struct.pack('<I', IN_WORLD))
    node += children
    return node[:4] + struct.pack('<I', len(node) - 8) + node[8:]


def halraj_actn(aid, values, felid, name):
    props = []
    for f in FIELDS:
        if f == 'felid':
            props.append((P_FIELD[f], ids_value(felid)))
        else:
            props.append((P_FIELD[f], struct.pack('<I' if f in INTS else '<f', values[f])))
    base = [(0x080017C3, name_value(name)), (0x080017C4, struct.pack('<I', 2)),   # active
            (0x080017C5, bytes(4)), (0x080017C6, bytes(4)), (0x080017C7, struct.pack('<I', 3)),
            (0x080017C8, bytes(4))]
    body = b''.join(prop(p, v) for p, v in sorted(props + base))
    out = b'ACTN' + struct.pack('<III', 0, HALRAJ_CLASS, aid) + b'PRPS' + struct.pack('<I', len(body)) + body
    return out[:4] + struct.pack('<I', len(out) - 8) + out[8:]


def school(d, tops, fish_tpl, fish_data, ids, mesh, pos, values, k):
    root, body, fish, act = ids.new(), ids.new(), ids.new(), ids.new()
    s = FISH_SCALE
    model = build_node(d, fish_tpl, fish, (s, 0, 0, 0, s, 0, 0, 0, s, 0, 0, 0), mesh,
                       {P_VIEWPORT: 0x20003, **FISH_RENDER}, fish_data)
    bb = struct.pack('<6f', *(c - SPAN for c in pos), *(c + SPAN for c in pos))
    model = replace_prop(model, P_NAME, name_value(f'FishBall {k} Fish'))
    model = replace_prop(model, P_FLAGS, struct.pack('<I', IN_WORLD))
    model = replace_prop(model, P_AABB, bb)
    mid = group_node(d, tops, body, (0.0, 0.0, 0.0), f'FishBall {k} Body', model)
    mid = replace_prop(mid, P_AABB, bb)
    top = group_node(d, tops, root, pos, f'FishBall {k}',
                     halraj_actn(act, values, [SHARK], f'MLHalRaj {k}') + mid)
    top = replace_prop(top, P_AABB, bb)
    print(f'school {k}: node {root} at {pos}, action {act}, body {body}, fish {fish}; '
          + ', '.join(f'{f}={values[f]:g}' for f in ('mnum', 'mrange', 'frange', 'rangez', 'maxspeed')))
    return top


def fish_node(f, nid):
    """Raw bytes of FISH's CHBR nid (anywhere in BRTR), padded."""
    b = find_brtr(f)
    end, p = b + 8 + u32(f, b + 4), b + 16
    while (p := f.find(b'CHBR', p, end)) != -1:
        if f[p + 16:p + 20] == b'PRPS' and u32(f, p + 12) == nid:
            n = f[p:p + 8 + u32(f, p + 4)]
            return n + b'\0' * (-len(n) % 4)
        p += 4
    raise SystemExit(f'FISH node {nid} not found')


def jaws_schools(f, ids):
    """Shipped MLHalRaj3 templates (verbatim) plus one reference per school."""
    out = b''.join(fish_node(f, t) for t in JAWS_TEMPLATES)
    for pos, tpl, name in JAWS_SCHOOLS:
        nid = ids.new()
        node = bytearray(fish_node(f, JAWS_REFERENCE))
        struct.pack_into('<I', node, 12, nid)
        node = replace_prop(bytes(node), P_REF, struct.pack('<I', tpl))
        node = replace_prop(node, P_XF, struct.pack('<12f', 1, 0, 0, 0, 1, 0, 0, 0, 1, *pos))
        node = replace_prop(node, P_AABB, struct.pack('<6f', *pos, *pos))
        node = replace_prop(node, P_NAME, name_value(name))
        out += node
        print(f'{name}: MLHalRaj3Reference {nid} at {pos} -> template {tpl}')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?', default=str(ROOT / 'edited_levels' / 'FISHBALL.GDW'))
    ap.add_argument('--deploy', metavar='NAME')
    a = ap.parse_args()

    d = bytearray(BASE.read_bytes())
    mesh = copy_fish(d, WRACK.read_bytes())
    f = FISH.read_bytes()
    ftops, _ = top_level_nodes(f, find_brtr(f))

    brtr = find_brtr(d)
    tops, end = top_level_nodes(d, brtr)
    assert SHARK in tops, 'SHARRRK not found in the base'
    ids = Ids(d)
    for t in JAWS_TEMPLATES:   # copied with their own IDs (children and actions included)
        sub = fish_node(f, t)
        for p, _ in chunk_headers(sub, 0, len(sub)):
            assert u32(sub, p + 12) not in ids.used, f'ID {u32(sub, p + 12)} of template {t} is used in the base'
            ids.used.add(u32(sub, p + 12))
    nodes = b''.join(school(d, tops, ftops[MODEL_TEMPLATE], f, ids, mesh, pos, {**ECCO, **ov}, k + 1)
                     for k, (pos, ov) in enumerate(SCHOOLS))
    nodes += jaws_schools(f, ids)
    replace_chunk_payload(d, brtr, bytes(d[brtr + 8:end]) + nodes)

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes(d)
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

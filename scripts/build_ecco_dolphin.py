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

"""Ecco the dolphin as the player model (Ecco port, Phase B1).

    python3 scripts/build_ecco_dolphin.py [OUT.GDW] [--deploy NAME] [--size S]

Converts Ecco: Defender of the Future's player rig (110L_BAY `Ecco.gdm`, already
extracted by ~/Projects/ECCO: skeletons/110L_BAY/Ecco_gdm.json + the OBJ/textures
it names) into a Jaws skinned model and puts it on the player shark in the blank
FISH base (levels/custom_fish/FISH_blank_base.GDW). Output defaults to
edited_levels/DOLPHIN.GDW; --deploy copies it to custom_levels/NAME.GDW (F9).

Ecco rigs are rigid segments (each vertex belongs to one bone, stored bone-local);
Jaws rigs are skinned (rest mesh + WGHT + MTOB inverse rest matrices). Conversion:
    rest world_i = pose at frame 0 (the frame baked into Ecco's GMDL)
    VERT/GMDL    = Ecco's GMDL vertices, same order (rest mesh)
    WGHT         = one bone per vertex, weight 1
    MTOB_i       = inverse(rest world_i)
    TRAN, ROTS   = Ecco's, unchanged math (both engines: local = [R(q)^T | TRAN])
Both games are left-handed with Y up. Ecco's nose points along local -Z, the
shark's along +Z, so everything is turned 180 degrees about Y, C = diag(-1, 1, -1):
positions/normals/TRAN -> C v, quaternion (x, y, z, w) -> (-x, y, -z, w). Positions
are scaled so the dolphin is `--size` times the Phase A physics scale (Jaws units
per Ecco unit, 4), divided by GWside's own transform scale (2.1).

Animation: Ecco has no clip dictionary; DolphCtrl plays fixed ranges of the
319-frame pool (docs/ecco_dolphin_controller.md "Animation clips"). The shark
controller looks its clips up by name (e.g. SHARK_GW_PITBULL04, case-insensitive)
from the model's ANIM dictionary, so the dolphin's ANIM lists all 73 great white
clip names, each mapped to a dolphin range (CLIP_MAP), plus Ecco_* names for the
dolphin ranges themselves. Root motion is zero. The rig is padded to the shark's
40 bones with dummy bones in case code reads bones by index.

The model goes on GWside (26124, child of SHARRRK): its PROP 0x08001873 (GMDL) and
0x080018FF (SKEL) are repointed, the baked vertex colours (0x0800187A, one float4
per vertex) resized, the AABB recomputed. Materials are clones of the shark's
skin GMAT with Ecco's textures; the forehead star glyphs (StarText A-E) keep their
vertices but get no triangles.
"""
import argparse
import json
import os
import shutil
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from build_scene import LIVE_DATA
from gdw_grow import find_brtr, replace_chunk_payload, append_to_chunk, top_chunks, u32
from gdw_textures import build_gtex, clone_gmat, find_block
from insert_brtr_node import prop_offsets, replace_prop
from obj_to_gmdl import build_gmdl, chunk, pad, next_free_id
import rip_skeletons

BASE = ROOT / 'levels' / 'custom_fish' / 'FISH_blank_base.GDW'
ECCO = Path.home() / 'Projects' / 'ECCO'
RIG = ECCO / 'skeletons' / '110L_BAY' / 'Ecco_gdm.json'
OBJ = ECCO / 'models' / '110L_BAY' / 'Ecco__ECCOfin05.obj'
TEX = ECCO / 'textures' / '110L_BAY'
GWSIDE = 26124                 # player shark model node (child of SHARRRK 26116)
SHARK_GMDL = 1890
PHYS_SCALE = 4.0               # Jaws units per Ecco unit (mod ecco.cpp default)
GWSIDE_SCALE = 2.1             # GWside's transform scale
JAWS_BONES = 40                # great white bone count
SKEL_VERSION = 20020410

P_MESH, P_SKEL, P_VCOL, P_AABB, P_XF = 0x08001873, 0x080018FF, 0x0800187A, 0x080017DF, 0x080017DA

# Material groups in the OBJ -> (texture file, part); StarText* = no triangles.
MATERIALS = {'ECCOsum__ecco_113': 'EccoTex_R.png',
             'ECCOSzem__ecco_114': 'szem1__0157.png',
             'AIH__ecco_115': 'AIH_close__0158.png'}

# Dolphin frame ranges of Ecco.gdm's pool (DolphCtrl's clip table).
ECCO_CLIPS = {
    'Ecco_Rest': (0, 5), 'Ecco_SwimSlow': (6, 37), 'Ecco_Swim': (38, 69), 'Ecco_SwimFast': (70, 101),
    'Ecco_TailWalk': (102, 133), 'Ecco_Idle': (134, 165), 'Ecco_Charge': (166, 196),
    'Ecco_Brake': (197, 213), 'Ecco_Turn180A': (214, 249), 'Ecco_Turn180B': (250, 285),
    'Ecco_Charge2': (286, 318),
}
# Great white clip names (FISH SKEL 1766) -> dolphin range. Bites keep >= 34 frames
# where the controller times damage to clip frames (Pitbull04: start +12/+23/+33).
SWIM2 = (6, 69)                # two swim cycles, 64 frames
CLIP_MAP = {
    'Shark_GW_UszasA': 'Ecco_Swim', 'Shark_GW_UszasB': 'Ecco_SwimFast', 'Shark_GW_UszasKajla': 'Ecco_SwimFast',
    'Shark_GW_StunnedSwim01': 'Ecco_SwimSlow',
    'Shark_GW_Landwalk': 'Ecco_TailWalk', 'Shark_GW_Landwalk_Idle': 'Ecco_TailWalk',
    'Shark_GW_Landwalk_Jump': 'Ecco_TailWalk', 'Shark_GW_Landwalk_Left': 'Ecco_TailWalk',
    'Shark_GW_Landwalk_Right': 'Ecco_TailWalk',
    'Shark_GW_Launch01': 'Ecco_Charge2', 'Shark_GW_chargeNagy_i12L32o__an': 'Ecco_Charge',
    'Shark_GW_OpenMouthCharge': 'Ecco_Charge', 'Shark_GW_OpenMouthCharge_NC': 'Ecco_Charge',
    'Shark_GW_BodyBomb2': 'Ecco_Turn180B', 'Shark_GW_BodySlam_Left': 'Ecco_Turn180A',
    'Shark_GW_BodySlam_Right': 'Ecco_Turn180B', 'Shark_GW_DeathSpinCW_Begin': 'Ecco_Turn180A',
    'Shark_GW_DeathSpinCW_Spin': 'Ecco_Turn180B', 'Shark_GW_Fordulasok_BJFL_': 'Ecco_Turn180A',
    'Shark_GW_FordulasokTepes': 'Ecco_Turn180B', 'Shark_GW_NarrowLeft': 'Ecco_Turn180A',
    'Shark_GW_NarrowRight': 'Ecco_Turn180B', 'Shark_GW_FarokCsap': 'Ecco_Turn180A',
    'Shark_GW_die_i17L31o_': 'Ecco_Brake', 'Shark_GW_Die02': 'Ecco_Brake',
}
DEFAULT_CLIP = SWIM2           # bites, swallows, throws, tail whips, ...


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2*(y*y + z*z), 2*(x*y - z*w), 2*(x*z + y*w)],
                     [2*(x*y + z*w), 1 - 2*(x*x + z*z), 2*(y*z - x*w)],
                     [2*(x*z - y*w), 2*(y*z + x*w), 1 - 2*(x*x + y*y)]])


def pose(parents, trans, rots, frame):
    W = []
    for i, p in enumerate(parents):
        L = np.eye(4)
        L[:3, :3] = quat_mat(rots[i][frame]).T
        L[:3, 3] = trans[i]
        W.append(W[p] @ L if p >= 0 else L)
    return W


def parse_obj(path):
    """-> positions, normals, uvs (OBJ order = Ecco GMDL order), [(material, tris)]."""
    P, N, T, groups = [], [], [], []
    for line in open(path):
        f = line.split()
        if not f:
            continue
        if f[0] == 'v':
            P.append(list(map(float, f[1:4])))
        elif f[0] == 'vn':
            N.append(list(map(float, f[1:4])))
        elif f[0] == 'vt':
            T.append((float(f[1]), float(f[2])))
        elif f[0] == 'usemtl':
            groups.append((f[1], []))
        elif f[0] == 'f':
            groups[-1][1].append([int(c.split('/')[0]) - 1 for c in f[1:4]])
    return np.array(P), np.array(N), T, groups


def convert(size):
    rig = json.loads(RIG.read_text())
    bones = rig['bones']
    P, N, T, groups = parse_obj(OBJ)
    n = len(P)
    assert n == rig['mesh_vertices'] == len(T) == len(N)
    frames = rig['frames']
    parents = [b['parent'] for b in bones]
    trans = [np.array(b['tran']) for b in bones]
    rots = [np.array(b['rots']) for b in bones]

    # Frame 0 rebuilds the OBJ mesh (the Ecco ripper checked it to 5e-5).
    W0 = pose(parents, trans, rots, 0)
    owner = np.full(n, -1)
    for i, b in enumerate(bones):
        for k, v in zip(b['vert_index'], b['verts']):
            owner[k] = i
            err = np.abs(W0[i][:3, :3] @ v + W0[i][:3, 3] - P[k]).max()
            assert err < 1e-3, (i, k, err)
    assert (owner >= 0).all()

    # Turn 180 degrees about Y and scale; pad to JAWS_BONES with dummy children of the root.
    s = size * PHYS_SCALE / GWSIDE_SCALE
    C = np.diag([-1.0, 1.0, -1.0])
    nd = JAWS_BONES - len(bones)
    parents += [0] * nd
    trans = [s * (C @ t) for t in trans] + [np.zeros(3)] * nd
    ident = np.tile([0.0, 0.0, 0.0, 1.0], (frames, 1))
    rots = [r * [-1, 1, -1, 1] for r in rots] + [ident] * nd
    pos = s * (P @ C)
    nrm = N @ C
    nb = len(parents)

    # File tree: first child + next sibling links in index order.
    kids = [[j for j in range(nb) if parents[j] == i] for i in range(nb)]
    first = {i: k[0] for i, k in enumerate(kids) if k}
    nxt = {}
    for k in kids:
        for a, b in zip(k, k[1:]):
            nxt[a] = b
    # Engine bone order (rip_skeletons.parse_bones / FUN_006F46D0): root, then each
    # bone's whole sibling chain before its child.
    order = [0]

    def visit(i):
        while i is not None:
            order.append(i)
            if i in nxt:
                visit(nxt[i])
            i = first.get(i)
    if 0 in nxt:
        visit(nxt[0])
    visit(first.get(0))
    engine = {b: k for k, b in enumerate(order)}
    assert sorted(order) == list(range(nb))

    Wr = pose(parents, trans, rots, 0)

    def node(tag, i):
        M = np.linalg.inv(Wr[i])
        mtob = struct.pack('<12f', *M[:3, 0], *M[:3, 1], *M[:3, 2], *M[:3, 3])
        parts = [chunk(b'MTOB', mtob), chunk(b'TRAN', struct.pack('<3f', *trans[i])),
                 chunk(b'ROTS', rots[i].astype('<f4').tobytes())]
        if i in first:
            parts.append(node(b'CHLD', first[i]))
        if i in nxt:
            parts.append(node(b'BROT', nxt[i]))
        return chunk(tag, *parts)

    names = list(ECCO_CLIPS)
    ranges = list(ECCO_CLIPS.values())
    shark = json.loads((ROOT / 'skeletons' / 'FISH' / 'skel_01766.json').read_text())
    for a in shark['animations']:
        names.append(a['name'])
        m = CLIP_MAP.get(a['name'])
        ranges.append(ECCO_CLIPS[m] if m else DEFAULT_CLIP)
    anim = struct.pack('<II', len(names), sum(len(x) + 1 for x in names))
    anim += b''.join(pad(struct.pack('<I', len(x) + 1) + x.encode() + b'\0') for x in names)
    anim += struct.pack(f'<{len(names)}I', *(r[0] for r in ranges))
    anim += struct.pack(f'<{len(names)}I', *(r[1] for r in ranges))

    wght = b''.join(struct.pack('<4i4f', engine[owner[k]], -1, -1, -1, 1.0, 0.0, 0.0, 0.0) for k in range(n))
    zeros = bytes(12 * frames)
    head = struct.pack('<5I', 0, 1, SKEL_VERSION, frames, 0) + zeros + zeros   # id patched later
    skel = (head, chunk(b'VERT', struct.pack('<I', n) + pos.astype('<f4').tobytes()),
            chunk(b'NORM', nrm.astype('<f4').tobytes()), chunk(b'WGHT', wght),
            chunk(b'ANIM', anim), node(b'BONE', 0))

    # Self-check in Jaws terms: skin = world_f . MTOB, against the converted Ecco pose.
    for f in (0, 50, 150, 230, 300):
        Wf = pose(parents, trans, rots, f)
        Wsrc = pose([b['parent'] for b in bones], [np.array(b['tran']) for b in bones],
                    [np.array(b['rots']) for b in bones], f)
        err = 0.0
        for k in range(0, n, 7):
            i = owner[k]
            jaws = (Wf[i] @ np.linalg.inv(Wr[i]) @ np.append(pos[k], 1))[:3]
            v = bones[i]['verts'][bones[i]['vert_index'].index(k)]
            ecco = s * (C @ (Wsrc[i][:3, :3] @ v + Wsrc[i][:3, 3]))
            err = max(err, np.abs(jaws - ecco).max())
        assert err < 1e-3, (f, err)
    print(f'  rig: {nb} bones ({nd} dummies), {n} verts, {frames} frames, {len(names)} clips, '
          f'scale {s:.3f}, length {np.ptp(pos[:, 2]):.2f} local units')

    tris = {m: [] for m in MATERIALS}
    for mname, ts in groups:
        if mname in tris:
            for a, b, c in ts:
                # Jaws winding: in raw (left-handed) coordinates -(B-A)x(C-A) points along the normal.
                fn = -np.cross(pos[b] - pos[a], pos[c] - pos[a])
                tris[mname].append((a, b, c) if fn @ (nrm[a] + nrm[b] + nrm[c]) >= 0 else (a, c, b))
    return skel, pos, nrm, T, tris


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?', default=str(ROOT / 'edited_levels' / 'DOLPHIN.GDW'))
    ap.add_argument('--deploy', metavar='NAME')
    ap.add_argument('--size', type=float, default=1.0, help='model size relative to the physics scale')
    a = ap.parse_args()

    skel_parts, pos, nrm, T, tris = convert(a.size)
    d = bytearray(BASE.read_bytes())
    nid = next_free_id(d)

    # Textures + materials (clones of the shark's skin GMAT).
    p = find_block(d, b'GMDL', SHARK_GMDL)
    m = d.find(b'MATS', p)
    skin_gmat = u32(d, m + 16)
    blob, gmat_of = b'', {}
    for mname, tex in MATERIALS.items():
        gtex, (w, h, bpp) = build_gtex(nid, Image.open(TEX / tex).convert('RGB'), keep_alpha=False)
        blob += gtex + pad(clone_gmat(d, skin_gmat, nid + 1, nid))
        gmat_of[mname] = nid + 1
        print(f'  {mname}: GTEX {nid} {w}x{h}x{bpp}, GMAT {nid + 1} (clone of {skin_gmat})')
        nid += 2

    # GMDL: parts in Ecco's vertex order; the unused StarText vertices ride in the last part.
    def verts(lo, hi):
        return [(tuple(pos[k]), tuple(nrm[k]), (T[k][0], 1.0 - T[k][1])) for k in range(lo, hi)]
    spans, lo = [], 0
    for mname in MATERIALS:
        ts = tris[mname]
        hi = max(max(t) for t in ts) + 1
        spans.append([mname, lo, hi])
        assert min(min(t) for t in ts) >= lo
        lo = hi
    spans[-1][2] = len(pos)
    parts = [(gmat_of[mn], verts(lo, hi), [[i - lo for i in t] for t in tris[mn]]) for mn, lo, hi in spans]
    mesh_id, skel_id = nid, nid + 1
    gmdl, nv, nt, _ = build_gmdl(mesh_id, parts)
    assert nv == len(pos)
    head = bytearray(skel_parts[0])
    struct.pack_into('<I', head, 0, skel_id)
    skel = pad(chunk(b'SKEL', bytes(head), *skel_parts[1:]))
    append_to_chunk(d, top_chunks(d)['RSRC'], blob + gmdl + skel)
    print(f'  GMDL {mesh_id}: {nv} verts, {nt} tris; SKEL {skel_id}: {len(skel):,} bytes')

    # Round trip through the Jaws skeleton parser.
    sp = find_block(d, b'SKEL', skel_id)
    sb = bytes(d[sp:sp + 8 + u32(d, sp + 4)])
    parsed = rip_skeletons.parse_bones(sb[sb.find(b'BONE') + 8:])
    assert len(parsed) == JAWS_BONES

    # Repoint GWside, resizing nested chunk sizes (SHARRRK -> GWside).
    brtr = find_brtr(d)
    end = brtr + 8 + u32(d, brtr + 4)
    chain, q = [], (brtr + 16 + 8 + u32(d, brtr + 20) + 3) & ~3
    while q < end:
        size = u32(d, q + 4)
        if d[q:q + 4] == b'CHBR' and u32(d, q + 12) == GWSIDE:
            chain.append(q)
            break
        if d[q:q + 4] == b'CHBR' and size > 8 and d.find(struct.pack('<I', GWSIDE), q, q + 8 + size) != -1 \
                and _contains_node(d, q, GWSIDE):
            chain.append(q)
            q = (q + 16 + 8 + u32(d, q + 20) + 3) & ~3      # descend past its PRPS
            continue
        q = (q + 8 + size + 3) & ~3
    gw = chain[-1]
    node = bytes(d[gw:gw + 8 + u32(d, gw + 4)])
    node = bytearray(node + b'\0' * (-len(node) % 4))
    po = prop_offsets(node)
    struct.pack_into('<I', node, po[P_MESH] + 4, mesh_id)
    struct.pack_into('<I', node, po[P_SKEL] + 4, skel_id)
    xf = struct.unpack_from('<12f', node, po[P_XF])
    world = [(xf[0]*x + xf[3]*y + xf[6]*z + xf[9], xf[1]*x + xf[4]*y + xf[7]*z + xf[10],
              xf[2]*x + xf[5]*y + xf[8]*z + xf[11]) for x, y, z in pos]
    struct.pack_into('<6f', node, po[P_AABB], *[min(w[k] for w in world) for k in range(3)],
                     *[max(w[k] for w in world) for k in range(3)])
    avg = struct.unpack_from('<4f', node, po[P_VCOL] + 4)
    node = replace_prop(bytes(node), P_VCOL, struct.pack('<I', len(pos)) + struct.pack('<4f', *avg) * len(pos))
    old = 8 + u32(d, gw + 4)
    old_padded = old + (-old % 4)
    delta = len(node) - old_padded
    payload = bytearray(d[brtr + 8:gw]) + node + d[gw + old_padded:end]
    for c in chain[:-1]:                     # ancestors' CHBR sizes
        o = c - (brtr + 8)
        struct.pack_into('<I', payload, o + 4, u32(payload, o + 4) + delta)
    replace_chunk_payload(d, brtr, bytes(payload))
    print(f'  GWside: GMDL {mesh_id}, SKEL {skel_id}, {len(pos)} vertex colours (node {delta:+d} bytes)')

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


def _contains_node(d, q, node_id):
    """True if CHBR q has a descendant CHBR with node_id."""
    end = q + 8 + u32(d, q + 4)
    r = (q + 16 + 8 + u32(d, q + 20) + 3) & ~3
    while r < end:
        if d[r:r + 4] == b'CHBR' and (u32(d, r + 12) == node_id or _contains_node(d, r, node_id)):
            return True
        r = (r + 8 + u32(d, r + 4) + 3) & ~3
    return False


if __name__ == '__main__':
    main()

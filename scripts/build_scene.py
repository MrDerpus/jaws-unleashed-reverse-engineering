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

"""Build a level from a Blender scene export in one step.

    python3 scripts/build_scene.py BASE.GDW OUT.GDW EXPORT_DIR [--deploy NAME]

EXPORT_DIR is written by scripts/blender_export_scene.py (manifest.json plus
one OBJ per unique mesh, plus images). Each image becomes a new GTEX
(gdw_textures.build_gtex, power-of-two resize) and each textured Blender
material a new GMAT cloned from 1073 with its TEXP pointed at that GTEX. For each unique mesh: OBJ -> GMDL (obj_to_gmdl.py),
plus a generated MREG collision region if any object using it is solid. All
resources go into RSRC with consecutive next-free IDs. Then one new BRTR node
per object, cloned from a known-visible template:
    solid objects     node 77 (szikla elem43: has a PRIM, m_Viewport 0x20003),
                      PRIM repointed at the mesh's MREG
    non-solid         node 79 (szikla elem34, no PRIM), m_Viewport -> 0x20003
with the object's full game-space transform. The result is checked (chunk
chain, FSIZ/SKIP/FDIR, BRTR walk) before writing.

Large meshes are cut into tiles (2026-10-04): the engine fades a very large
object out whenever it judges it out of view (a one-piece 1500-unit floor
faded when the shark looked away; 8x8 tiles of ~190 units fixed it,
user-confirmed). Any mesh wider than SPLIT_OVER game units on an axis is cut
into a grid of cells of at most TILE units (by triangle centroid, in
mesh-local space); each cell becomes its own GMDL (+ MREG) and node, with its
vertices re-centred and the node translation moved to match. Also keeps each
piece under the 65,535-vertex GMDL limit. --tile 0 turns it off.

Exit zones (2026-10-04): manifest 'exits' (Blender objects with jaws_exit)
replace the base level's own exit. That exit is an area trigger (class
AREA_TRIGGER, fields m_type/m_target/m_radius/m_enter_act/m_leave_act/...):
FISH's fires when the shark LEAVES a 795-unit circle marked by 72 buoy
children. The first zone reuses that node (buoys dropped, moved, radius set,
its leave action list moved to the enter list, like OPEN_S's level entrances);
further zones are copies of its PRPS pointing at the same action.

--show-exits (testing) adds a see-through, non-solid column at each exit zone
(radius = the zone's), so zones can be seen in-game: in the exit object's
material colour, or bright pink without one. Opaque colours are made
see-through; a material Alpha below 1 is kept.

Spawn: the manifest's 'spawn' (a Blender object with jaws_spawn = 1) moves
the shark's start nodes SPAWN_NODES (FISH: 'SHARRRK', the shark, and its
marker 'SharkPosReal') there, facing the object's -Y. Their subtrees' AABBs
and absolute-transform descendants move with them. Without one, the base's
spawn stays (blank base: game (0, -6.5, 0), right above Blender's origin).

The base's exit trigger (an area trigger with a non-empty leave or enter
list) is reused for exit zones; strip_level.py --blank leaves it disabled.

--music keep|none|DIR replaces the level music (gdw_music.py): keep FISH's,
'none' = silence (~41 MB smaller), or a folder with calm_above / calm_under /
suspense / action audio files (any format ffmpeg reads; missing ones fall
back to calm_above).

--prune (build.sh uses it) drops the resources the finished level doesn't
use (prune_level.py), after everything else.

--deploy NAME copies OUT.GDW to the live game's custom_levels/NAME.GDW, next
to Jaws.exe (the mod loads it from there; F9 in-game opens the level picker,
F10 reloads the current level). NAME must not be a stock level's name and may
only use letters, digits and _ (max 31). A first-time backup
NAME.GDW.pre_build is kept.
Run from scripts/ (imports the sibling tools).
"""
import argparse
import json
import math
import os
import re
import shutil
import struct
import tempfile

from gdw_grow import append_to_chunk, find_brtr, replace_chunk_payload, top_chunks, u32
from gdw_materials import build_gmat_index
from gdw_music import replace_music
from prune_level import prune
from insert_brtr_node import build_node, max_node_id, prop_offsets, replace_prop, top_level_nodes
from gdw_textures import build_gtex, clone_gmat
from obj_to_gmdl import build_gmdl, build_mreg, load_parts, next_free_id

from PIL import Image

LIVE_DATA = os.path.expanduser('~/.steam/debian-installation/steamapps/compatdata/2342933845/'
                               'pfx/drive_c/Program Files (x86)/Jaws Unleashed/data')
TEMPLATE_SOLID, TEMPLATE_GHOST = 77, 79   # read from --templates, so a stripped base works
TEMPLATES_GDW = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'GAME_GDWs', 'FISH.GDW')
TEMPLATE_GMAT = 1073            # FISH rock wall: one-sided (TWOS 0)
TEMPLATE_GMAT_TWO_SIDED = 668   # FISH seaweed: same, but TWOS 1
# Node render settings for cut-out transparency (FISH seaweed nodes):
# m_RenderSetting 0x80000920, m_StaticLights 0x81000021. Tested 2026-10-03:
# a 32-bit texture is see-through on any node; normal settings blend partial
# alpha smoothly, these cut it on/off. Back faces are controlled only by the
# material: TWOS 1 (668) shows them, TWOS 0 (1073) culls them (4-plane test;
# an earlier reading that the node setting also toggled culling came from
# counting the panels left-to-right while looking at them from behind).
CUTOUT_NODE = {0x08001876: 0x80000920, 0x08001875: 0x81000021}
P_VIEWPORT, VIEWPORT_ALL = 0x080017DD, 0x20003
AREA_TRIGGER = 0x01134132
P_AT_RADIUS, P_AT_ENTER, P_AT_LEAVE = 0x0800028F, 0x08000290, 0x08000291
P_TRANSFORM, P_AABB = 0x080017DA, 0x080017DF
P_NAME, P_FLAGS, FLAG_ABSOLUTE = 0x080017D8, 0x080017D9, 0x20000000
SPAWN_NODES = ('SHARRRK', 'SharkPosReal')
EXIT_PINK = (255, 20, 200, 150)   # --show-exits default marker colour (RGBA)
TILE = 200.0         # max tile size, game units
SPLIT_OVER = 300.0   # only meshes wider than this on some axis get cut


def split_parts(parts, tile):
    """[(gmat, verts, tris)] -> [(offset, parts)]: one entry per grid cell,
    vertices re-centred on the cell's bounds centre (offset, mesh-local)."""
    pts = [v[0] for _, verts, _ in parts for v in verts]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    ext = [hi[i] - lo[i] for i in range(3)]
    if not tile or max(ext) <= SPLIT_OVER:
        return [((0.0, 0.0, 0.0), parts)]
    n = [max(1, math.ceil(e / tile)) if e > SPLIT_OVER else 1 for e in ext]
    size = [ext[i] / n[i] or 1.0 for i in range(3)]
    cells = {}   # cell -> {part index: [tri]}
    for pi, (_, verts, tris) in enumerate(parts):
        for t in tris:
            c = [sum(verts[j][0][i] for j in t) / 3 for i in range(3)]
            key = tuple(min(n[i] - 1, int((c[i] - lo[i]) / size[i])) for i in range(3))
            cells.setdefault(key, {}).setdefault(pi, []).append(t)
    out = []
    for key in sorted(cells):
        sub = []
        for pi, tris in sorted(cells[key].items()):
            g, verts, _ = parts[pi]
            remap = {}
            for t in tris:
                for j in t:
                    remap.setdefault(j, len(remap))
            sub.append((g, [verts[j] for j in remap], [[remap[j] for j in t] for t in tris]))
        cp = [v[0] for _, verts, _ in sub for v in verts]
        off = tuple((min(p[i] for p in cp) + max(p[i] for p in cp)) / 2 for i in range(3))
        sub = [(g, [(tuple(v[0][i] - off[i] for i in range(3)),) + tuple(v[1:]) for v in verts], tris)
               for g, verts, tris in sub]
        out.append((off, sub))
    return out


def exit_nodes(d, brtr, exits, first_new_id):
    """Rebuild the level's exit trigger as the given zones; returns the new
    BRTR payload."""
    nodes, end = top_level_nodes(d, brtr)
    old = [n for n, (p, s) in nodes.items() if u32(d, p + 8) == AREA_TRIGGER
           and (_prop(d[p:p + 8 + s], P_AT_LEAVE)[:4] != bytes(4)
                or _prop(d[p:p + 8 + s], P_AT_ENTER)[:4] != bytes(4))]
    if len(old) != 1:
        raise SystemExit(f'expected one exit trigger in the base, found {old}')
    p, s = nodes[old[0]]
    src = bytes(d[p:p + 8 + s])
    acts = _prop(src, P_AT_LEAVE)
    if acts[:4] == bytes(4):
        acts = _prop(src, P_AT_ENTER)     # blank base: disabled, actions already on enter
    # header + PRPS + the node's own ACTNs; no CHBR children (the buoy ring)
    head, q, own = src[:16], 16, b''
    prps = b''
    while q < len(src):
        t, n = src[q:q + 4], (q + 8 + u32(src, q + 4) + 3) & ~3
        if t == b'PRPS':
            prps = src[q:n]
        elif t != b'CHBR':
            own += src[q:n]
        q = n
    out = []
    for k, z in enumerate(exits):
        node = bytearray(head + prps + (own if k == 0 else b''))
        struct.pack_into('<I', node, 4, len(node) - 8)
        if k:
            struct.pack_into('<I', node, 12, first_new_id + k - 1)
        node = replace_prop(bytes(node), P_AT_ENTER, acts)
        node = replace_prop(node, P_AT_LEAVE, bytes(4))
        node = replace_prop(node, P_AT_RADIUS, struct.pack('<f', z['radius']))
        x, y, zz = z['pos']
        r = z['radius']
        node = replace_prop(node, P_TRANSFORM, struct.pack('<12f', 1, 0, 0, 0, 1, 0, 0, 0, 1, x, y, zz))
        node = replace_prop(node, P_AABB, struct.pack('<6f', x - r, y - 50, zz - r, x + r, y + 50, zz + r))
        out.append(node)
        print(f"exit zone {u32(node, 12)}: {z['name']} at ({x:.0f}, {y:.0f}, {zz:.0f}), radius {r:.0f}"
              + (' (base exit, buoys removed)' if k == 0 else ''))
    payload = d[brtr + 8:p] + b''.join(out) + d[(p + 8 + s + 3) & ~3:end]
    return bytes(payload)


def node_props(d, c):
    """{prop id: payload offset} of the CHBR at c, in place."""
    q = c + 16
    while d[q:q + 4] != b'PRPS':
        q = (q + 8 + u32(d, q + 4) + 3) & ~3
    out, r, rend = {}, q + 8, q + 8 + u32(d, q + 4)
    while r < rend:
        out[u32(d, r + 8)] = r + 12
        r += 8 + ((u32(d, r + 4) + 3) & ~3)
    return out


def set_spawn(d, brtr, spawn):
    """Move the shark's start nodes (SPAWN_NODES) to spawn['pos'], facing
    spawn['forward'] (game x, z), in place: no sizes change."""
    fx, fz = spawn['forward']
    n = math.hypot(fx, fz) or 1.0
    fx, fz = fx / n, fz / n
    # the shark faces its local +Z; X = Y x Z keeps FISH's handedness
    basis = (fz, 0.0, -fx, 0.0, 1.0, 0.0, fx, 0.0, fz)
    nodes, _ = top_level_nodes(d, brtr)
    done = []
    for nid, (c, sz) in nodes.items():
        pr = node_props(d, c)
        name = d[pr[P_NAME] + 4:pr[P_NAME] + 4 + u32(d, pr[P_NAME])].split(b'\0')[0].decode('latin1') \
            if P_NAME in pr else ''
        if name not in SPAWN_NODES:
            continue
        t = pr[P_TRANSFORM]
        delta = [spawn['pos'][i] - struct.unpack_from('<f', d, t + 36 + 4 * i)[0] for i in range(3)]
        struct.pack_into('<12f', d, t, *basis, *spawn['pos'])

        def walk(c, top):
            pr = node_props(d, c)
            flags = struct.unpack_from('<I', d, pr[P_FLAGS])[0] if P_FLAGS in pr else 0
            if not top and flags & FLAG_ABSOLUTE and P_TRANSFORM in pr:
                for i in range(3):
                    o = pr[P_TRANSFORM] + 36 + 4 * i
                    struct.pack_into('<f', d, o, struct.unpack_from('<f', d, o)[0] + delta[i])
            if P_AABB in pr:
                for i in range(6):
                    o = pr[P_AABB] + 4 * i
                    struct.pack_into('<f', d, o, struct.unpack_from('<f', d, o)[0] + delta[i % 3])
            q, end = c + 16, c + 8 + u32(d, c + 4)
            while q < end:
                if d[q:q + 4] == b'CHBR':
                    walk(q, False)
                q = (q + 8 + u32(d, q + 4) + 3) & ~3
        walk(c, True)
        done.append(name)
    if not done:
        raise SystemExit(f'spawn: none of {SPAWN_NODES} found in the base')
    x, y, z = spawn['pos']
    print(f"spawn: {', '.join(done)} at ({x:.1f}, {y:.1f}, {z:.1f}), facing ({fx:.2f}, {fz:.2f})")


def _prop(node, prop_id):
    po = prop_offsets(node)
    return node[po[prop_id]:po[prop_id] + u32(node, po[prop_id] - 8) - 4]


def add_exit_markers(man, tmp):
    """Add a see-through column per exit zone to the manifest (in place), in
    the zone's material colour (exporter 'colour'), default bright pink."""
    mats = man.setdefault('materials', {})
    for k, z in enumerate(man['exits']):
        r, seg, y0, y1 = z['radius'], 32, -60.0, 40.0   # local, around the zone's y
        rgba = tuple(z.get('colour') or EXIT_PINK)
        if rgba[3] >= 255:
            rgba = rgba[:3] + (EXIT_PINK[3],)    # opaque material: keep it see-through
        tok = 'bmat_exitviz_%02x%02x%02x%02x' % rgba
        if tok not in mats:
            png = os.path.join(tmp, tok + '.png')
            Image.new('RGBA', (8, 8), rgba).save(png)
            mats[tok] = {'blender_material': f'exit marker #%02x%02x%02x' % rgba[:3], 'image': png,
                         'alpha': 'BLEND', 'backface_culling': False}
        lines = [f'usemtl {tok}']
        for i in range(seg):
            a = 2 * math.pi * i / seg
            lines += [f'v {r * math.cos(a):.4f} {y0} {r * math.sin(a):.4f}',
                      f'v {r * math.cos(a):.4f} {y1} {r * math.sin(a):.4f}']
        for i in range(seg + 1):
            lines.append(f'vt {i / seg:.4f} 0\nvt {i / seg:.4f} 1')
        lines.append('vn 0 1 0')
        for i in range(seg):
            a0, a1, b0, b1 = 2 * i + 1, 2 * i + 2, 2 * ((i + 1) % seg) + 1, 2 * ((i + 1) % seg) + 2
            t0, t1, u0, u1 = 2 * i + 1, 2 * i + 2, 2 * i + 3, 2 * i + 4
            lines += [f'f {a0}/{t0}/1 {b0}/{u0}/1 {b1}/{u1}/1', f'f {a0}/{t0}/1 {b1}/{u1}/1 {a1}/{t1}/1']
        obj = os.path.join(tmp, f'exit_marker_{k}.obj')
        open(obj, 'w').write('\n'.join(lines) + '\n')
        key = f'exit_marker_{k}'
        man['meshes'][key] = {'obj': obj, 'gmat': TEMPLATE_GMAT, 'source': f"exit zone {z['name']}",
                              'tokens': [tok]}
        x, y, zz = z['pos']
        man['objects'].append({'name': f"exit marker {z['name']}", 'mesh': key,
                               'xf': [1, 0, 0, 0, 1, 0, 0, 0, 1, x, y, zz], 'collision': False})


def check(d):
    ch = top_chunks(d)
    assert u32(d, 0x2C + 8) == ch['SKIP'], 'FSIZ != SKIP offset'
    assert ch['FDIR'] % 512 == 0, 'FDIR not 512-aligned'
    for k in range(u32(d, ch['FDIR'] + 12)):
        off = u32(d, ch['FDIR'] + 16 + 32 * k)
        assert d[off:off + 4] == b'GDED', 'FDIR entry does not point at GDED'
    r = ch['RSRC']
    end, p = r + 8 + u32(d, r + 4), r + 20
    while p < end:
        p = (p + 8 + u32(d, p + 4) + 3) & ~3
    assert p == end, 'RSRC chain broken'
    b = find_brtr(d)
    end, p = b + 8 + u32(d, b + 4), b + 16
    while p < end:
        p = (p + 8 + u32(d, p + 4) + 3) & ~3
    assert p == end, 'BRTR chain broken'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base')
    ap.add_argument('out')
    ap.add_argument('export_dir')
    ap.add_argument('--deploy', metavar='NAME')
    ap.add_argument('--tile', type=float, default=TILE,
                    help=f'cut meshes wider than {SPLIT_OVER:g} units into tiles of this size (0 = off)')
    ap.add_argument('--show-exits', action='store_true',
                    help='testing: pink see-through column at each exit zone')
    ap.add_argument('--music', default='keep', metavar='keep|none|DIR',
                    help="level music: keep the base's, none (silence), or a folder of audio files")
    ap.add_argument('--prune', action='store_true',
                    help='drop resources the finished level does not use (prune_level.py)')
    ap.add_argument('--templates', default=TEMPLATES_GDW,
                    help='GDW to copy template nodes 77/79 from (default: stock FISH)')
    a = ap.parse_args()

    man = json.load(open(os.path.join(a.export_dir, 'manifest.json')))
    tmp = None
    if a.show_exits and man.get('exits'):
        tmp = tempfile.mkdtemp(prefix='jaws_exitviz_')
        add_exit_markers(man, tmp)
    d = bytearray(open(a.base, 'rb').read())
    gmats = build_gmat_index(d)
    solid = {o['mesh'] for o in man['objects'] if o['collision']}

    # Textured Blender materials -> new GTEX + GMAT (clone of TEMPLATE_GMAT)
    next_id = next_free_id(d)
    blob, named, made, cutout = b'', {}, {}, set()
    for tok, m in man.get('materials', {}).items():
        alpha = m.get('alpha', 'OPAQUE')
        img = (m['image'], alpha != 'OPAQUE')
        if img not in made:
            g, (w, h, bpp) = build_gtex(next_id, Image.open(os.path.join(a.export_dir, img[0])), keep_alpha=img[1])
            blob += g
            made[img] = next_id
            print(f"texture {img[0]}: GTEX {next_id:#x} {w}x{h} {bpp}bpp")
            next_id += 1
        # Opaque materials stay one-sided (1073): Blender's default has culling
        # off, and closed meshes never show their back faces anyway.
        show_back = alpha != 'OPAQUE' and not m.get('backface_culling', False)
        blob += clone_gmat(d, TEMPLATE_GMAT_TWO_SIDED if show_back else TEMPLATE_GMAT, next_id, made[img])
        named[tok] = next_id
        if alpha == 'CLIP':
            cutout.add(tok)
        print(f"material {m['blender_material']!r}: GMAT {next_id:#x} -> GTEX {made[img]:#x}, "
              f"{alpha.lower()}, back faces {'shown' if show_back else 'culled'}")
        next_id += 1

    # Meshes (+ collision regions) -> RSRC; large meshes become several tiles
    ids = {}     # mesh key -> [(mesh_id, region, local offset)]
    for key, m in man['meshes'].items():
        print(f"mesh {m['obj']} (from {m['source']}):")
        parts = load_parts(os.path.join(a.export_dir, m['obj']), 1.0, m['gmat'], gmats, named)
        pieces = split_parts(parts, a.tile)
        if len(pieces) > 1:
            print(f'  large mesh: cut into {len(pieces)} tiles')
        ids[key] = []
        for off, sub in pieces:
            mesh_id = next_id
            g, nv, nt, corners = build_gmdl(mesh_id, sub, collision=key in solid)
            blob += g
            region = None
            if key in solid:
                region = mesh_id + 1
                blob += build_mreg(region, mesh_id, corners)
            next_id = (region or mesh_id) + 1
            ids[key].append((mesh_id, region, off))
            print(f'  -> GMDL {mesh_id:#x}: {nv} verts, {nt} tris' + (f', MREG {region:#x}' if region else ', no collision'))
    append_to_chunk(d, top_chunks(d)['RSRC'], blob)

    # Objects -> BRTR
    brtr = find_brtr(d)
    tdata = open(a.templates, 'rb').read()
    tnodes, _ = top_level_nodes(tdata, find_brtr(tdata))
    node_id = max_node_id(d, brtr) + 1
    blob = b''
    nodes = 0
    for o in man['objects']:
        extra = CUTOUT_NODE if cutout & set(man['meshes'][o['mesh']].get('tokens', [])) else {}
        pieces = ids[o['mesh']]
        for mesh_id, region, off in pieces:
            # move the node by the tile's offset, through the object's basis
            xf = list(o['xf'])
            for i in range(3):
                xf[9 + i] += xf[i] * off[0] + xf[3 + i] * off[1] + xf[6 + i] * off[2]
            if o['collision']:
                blob += build_node(d, tnodes[TEMPLATE_SOLID], node_id, xf, mesh_id, {'prim_region': region, **extra}, tdata)
            else:
                blob += build_node(d, tnodes[TEMPLATE_GHOST], node_id, xf, mesh_id, {P_VIEWPORT: VIEWPORT_ALL, **extra}, tdata)
            node_id += 1
            nodes += 1
        t = o['xf'][9:]
        print(f"node {node_id - len(pieces)}{f'-{node_id - 1}' if len(pieces) > 1 else ''}: {o['name']} "
              f"at ({t[0]:.1f}, {t[1]:.1f}, {t[2]:.1f})"
              + (f' [{len(pieces)} tiles]' if len(pieces) > 1 else '')
              + ('' if o['collision'] else ' [no collision]') + (' [cut-out]' if extra else ''))
    append_to_chunk(d, brtr, blob)
    if man.get('exits'):
        brtr = find_brtr(d)
        replace_chunk_payload(d, brtr, exit_nodes(d, brtr, man['exits'], node_id))
    if man.get('spawn'):
        set_spawn(d, find_brtr(d), man['spawn'])

    check(d)
    if a.music != 'keep':
        if a.music != 'none' and not os.path.isdir(a.music):
            raise SystemExit(f'--music: {a.music!r} is not keep, none or a folder')
        d = replace_music(bytes(d), a.music)
        check(d)
    if a.prune:
        size = len(d)
        d, kept, removed = prune(bytes(d))
        check(d)
        print(f'pruned unused resources: {size / 1e6:.1f} MB -> {len(d) / 1e6:.1f} MB')
    if tmp:
        shutil.rmtree(tmp)
    open(a.out, 'wb').write(d)
    print(f'wrote {a.out} ({len(man["objects"])} objects, {len(man["meshes"])} meshes, {nodes} nodes), checks passed')

    if a.deploy:
        if not re.fullmatch(r'[A-Za-z0-9_]{1,31}', a.deploy):
            raise SystemExit(f'--deploy {a.deploy!r}: use letters, digits and _ only (max 31)')
        if os.path.exists(os.path.join(LIVE_DATA, a.deploy.upper() + '.GDW')):
            raise SystemExit(f'--deploy {a.deploy!r}: a stock level has that name')
        live_dir = os.path.join(os.path.dirname(LIVE_DATA.rstrip('/')), 'custom_levels')
        os.makedirs(live_dir, exist_ok=True)
        live = os.path.join(live_dir, a.deploy.upper() + '.GDW')
        backup = live + '.pre_build'
        if os.path.exists(live) and not os.path.exists(backup):
            shutil.copy2(live, backup)
        shutil.copyfile(a.out, live)
        assert open(live, 'rb').read() == bytes(d)
        print(f'deployed to {live} -- F9 in-game to load it, F10 if already in it')


if __name__ == '__main__':
    main()

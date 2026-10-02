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

--deploy NAME copies OUT.GDW to the live game's data/NAME.GDW (a first-time
backup NAME.GDW.pre_build is kept). Then press F10 in-game to reload.
Run from scripts/ (imports the sibling tools).
"""
import argparse
import json
import os
import shutil
import struct

from gdw_grow import append_to_chunk, find_brtr, top_chunks, u32
from gdw_materials import build_gmat_index
from insert_brtr_node import build_node, max_node_id, top_level_nodes
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
    ap.add_argument('--templates', default=TEMPLATES_GDW,
                    help='GDW to copy template nodes 77/79 from (default: stock FISH)')
    a = ap.parse_args()

    man = json.load(open(os.path.join(a.export_dir, 'manifest.json')))
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

    # Meshes (+ collision regions) -> RSRC
    ids = {}
    for key, m in man['meshes'].items():
        print(f"mesh {m['obj']} (from {m['source']}):")
        parts = load_parts(os.path.join(a.export_dir, m['obj']), 1.0, m['gmat'], gmats, named)
        mesh_id = next_id
        g, nv, nt, corners = build_gmdl(mesh_id, parts, collision=key in solid)
        blob += g
        region = None
        if key in solid:
            region = mesh_id + 1
            blob += build_mreg(region, mesh_id, corners)
        next_id = (region or mesh_id) + 1
        ids[key] = (mesh_id, region)
        print(f'  -> GMDL {mesh_id:#x}: {nv} verts, {nt} tris' + (f', MREG {region:#x}' if region else ', no collision'))
    append_to_chunk(d, top_chunks(d)['RSRC'], blob)

    # Objects -> BRTR
    brtr = find_brtr(d)
    tdata = open(a.templates, 'rb').read()
    tnodes, _ = top_level_nodes(tdata, find_brtr(tdata))
    node_id = max_node_id(d, brtr) + 1
    blob = b''
    for o in man['objects']:
        mesh_id, region = ids[o['mesh']]
        extra = CUTOUT_NODE if cutout & set(man['meshes'][o['mesh']].get('tokens', [])) else {}
        if o['collision']:
            blob += build_node(d, tnodes[TEMPLATE_SOLID], node_id, o['xf'], mesh_id, {'prim_region': region, **extra}, tdata)
        else:
            blob += build_node(d, tnodes[TEMPLATE_GHOST], node_id, o['xf'], mesh_id, {P_VIEWPORT: VIEWPORT_ALL, **extra}, tdata)
        t = o['xf'][9:]
        print(f"node {node_id}: {o['name']} at ({t[0]:.1f}, {t[1]:.1f}, {t[2]:.1f})"
              + ('' if o['collision'] else ' [no collision]') + (' [cut-out]' if extra else ''))
        node_id += 1
    append_to_chunk(d, brtr, blob)

    check(d)
    open(a.out, 'wb').write(d)
    print(f'wrote {a.out} ({len(man["objects"])} objects, {len(man["meshes"])} meshes), checks passed')

    if a.deploy:
        live = os.path.join(LIVE_DATA, a.deploy + '.GDW')
        backup = live + '.pre_build'
        if os.path.exists(live) and not os.path.exists(backup):
            shutil.copy2(live, backup)
        shutil.copyfile(a.out, live)
        assert open(live, 'rb').read() == bytes(d)
        print(f'deployed to {live} -- press F10 in-game')


if __name__ == '__main__':
    main()

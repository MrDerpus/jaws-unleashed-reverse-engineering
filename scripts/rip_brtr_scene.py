"""
Extract the pre-built scene from the BRTR chunk, with textures.

BRTR is the Binary Resource Tree — it stores every scene object already placed
in world space. Each CHBR sub-block is one placed instance: name, 4x3 world
transform, mesh resource ID, vertex colors (baked lighting), and AABB.

Textures (rewritten 2026-10-01): each mesh's submeshes (TSET triangle sets)
get the base texture of their GMAT material (MATS -> GMAT -> TEXP), looked up
only among this GDW's own extracted PNGs -- see gdw_materials.py. The old
heuristic read TSET's vertex counts as texture IDs and borrowed images from
other GDWs, so its assignments were coincidental ID collisions.

This produces:
  scenes/<NAME>_brtr.obj  — merged world-space geometry, one group per object
  scenes/<NAME>_brtr.mtl  — one material per resolved texture, map_Kd per PNG
  scenes/<NAME>_brtr.json — manifest: name, mesh_id, position, tri count, tex_id

Run from project root:
  python3 scripts/rip_brtr_scene.py
"""

import os
import struct
import sys
if 'scripts' not in sys.path:   # run via exec() from the project root (see CLAUDE.md all-GDW loop)
    sys.path.insert(0, 'scripts')
from brtr_scene_graph import resolve_instances
from gdw_materials import MaterialResolver
import json
from pathlib import Path
from functools import lru_cache

# ============================
# CONFIG
# ============================

NAME       = 'FISH'
INPUT_FILE = f'GAME_GDWs/{NAME}.GDW'
OUTPUT_DIR = Path('scenes')


# ============================
# HELPERS
# ============================

def u32(data, off):
    try: return struct.unpack_from('<I', data, off)[0]
    except: return None

def f32(data, off):
    try: return struct.unpack_from('<f', data, off)[0]
    except: return None

def find_tag(data, tag, lo, hi):
    p = data.find(tag, lo, hi)
    if p == -1: return None, None
    return p, u32(data, p+4)


# ============================
# TEXTURE RESOLUTION
# ============================

def build_gmdl_index(data):
    """Returns (res_id->gmdl_offset, res_id->mesh_idx) for all valid meshes."""
    offset_map = {}
    idx_map    = {}
    mesh_idx   = 0
    off = 0
    while True:
        pos = data.find(b'GMDL', off)
        if pos == -1: break
        sz = u32(data, pos+4)
        if not sz or sz > 5_000_000:
            # Implausible size = coincidental "GMDL" bytes, not a block. Must NOT
            # advance mesh_idx: rip_meshes.py doesn't count these either, and
            # mesh_idx is how manifests point at models/<NAME>/<NAME>_mesh_XXXX.obj.
            # (Counting them shifted every later index on GDWs that have such
            # matches, e.g. 769/974 of OPEN_S's mesh_idx values were wrong.
            # Fixed 2026-10-01.)
            off = pos+4; continue
        end = pos+8+sz
        res_id = u32(data, pos+8)

        posi_pos, posi_sz = find_tag(data, b'POSI', pos, end)
        vind_pos, vind_sz = find_tag(data, b'VIND', pos, end)
        if None in (posi_pos, vind_pos) or not posi_sz or not vind_sz:
            off = pos+4; mesh_idx += 1; continue
        n_v = posi_sz // 12
        n_i = vind_sz // 2
        if n_v < 3 or n_i < 3:
            off = pos+4; mesh_idx += 1; continue
        idxs = struct.unpack_from(f'<{n_i}H', data, vind_pos+8)
        if max(idxs) >= n_v:
            off = pos+4; mesh_idx += 1; continue

        if res_id and res_id not in offset_map:
            offset_map[res_id] = pos
            idx_map[res_id]    = mesh_idx
        off = pos+4
        mesh_idx += 1
    return offset_map, idx_map


# ============================
# MESH EXTRACTION
# ============================

def extract_mesh(data, gmdl_pos):
    sz = u32(data, gmdl_pos+4)
    if not sz: return None
    end = gmdl_pos+8+sz

    posi_pos, posi_sz = find_tag(data, b'POSI', gmdl_pos, end)
    norm_pos, norm_sz = find_tag(data, b'NORM', gmdl_pos, end)
    uvuv_pos, uvuv_sz = find_tag(data, b'UVUV', gmdl_pos, end)
    vind_pos, vind_sz = find_tag(data, b'VIND', gmdl_pos, end)
    if None in (posi_pos, vind_pos) or not posi_sz or not vind_sz:
        return None

    n_v = posi_sz // 12
    n_i = vind_sz // 2
    if n_v < 3 or n_i < 3: return None
    idxs = list(struct.unpack_from(f'<{n_i}H', data, vind_pos+8))
    if max(idxs) >= n_v: return None

    verts = [(f32(data, posi_pos+8+i*12),
              f32(data, posi_pos+8+i*12+4),
              f32(data, posi_pos+8+i*12+8)) for i in range(n_v)]

    norms = []
    if norm_pos and norm_sz == posi_sz:
        norms = [(f32(data, norm_pos+8+i*12),
                  f32(data, norm_pos+8+i*12+4),
                  f32(data, norm_pos+8+i*12+8)) for i in range(n_v)]

    uvs = []
    if uvuv_pos and uvuv_sz == n_v*8:
        uvs = [(f32(data, uvuv_pos+8+i*8),
                1.0 - f32(data, uvuv_pos+8+i*8+4)) for i in range(n_v)]

    return verts, norms, uvs, idxs


# ============================
# BRTR SCENE PARSE
# ============================

def parse_prps_props(brtr, offset):
    """Parse a PRPS block at brtr[offset], return dict of prop_id -> bytes."""
    if brtr[offset:offset+4] != b'PRPS': return {}
    prps_sz = u32(brtr, offset+4)
    end = offset + 8 + prps_sz
    p   = offset + 8
    props = {}
    while p < end - 8:
        if brtr[p:p+4] != b'PROP':
            p += 1; continue
        psz = u32(brtr, p+4)
        pid = u32(brtr, p+8)
        props[pid] = brtr[p+12 : p+8+psz]
        p += 8 + psz
    return props


def parse_brtr(data):
    """Return the list of placed scene objects with true world transforms.

    Uses brtr_scene_graph.resolve_instances, which composes nested CHBR
    transforms through their parents, expands reference instancing
    (PROP 0x080017F0, one copy per reference node) and applies the
    MSMineAllMineMission whale relocation. Before 2026-10-01 this function read
    every node's raw LOCAL transform as if it were world space and ignored
    references entirely, so nested meshes were misplaced and every
    reference-placed copy was missing.
    """
    nodes, instances = resolve_instances(data)
    print(f'  {len(nodes)} CHBR nodes -> {len(instances)} placed instances '
          f'({sum(1 for i in instances if i["via_ref"] is not None)} reference copies, '
          f'{sum(1 for i in instances if i["is_template"])} template placements)')

    objects = []
    for inst in instances:
        props = nodes[inst['node_id']]['props']

        # Mesh reference: [uint32 "GMDL"][uint32 mesh_resource_id]
        mesh_id = None
        d = props.get(0x08001873)
        if d is not None and len(d) >= 8:
            mesh_id = u32(d, 4)

        # Vertex colors: uint32 count + count*16 RGBA float32
        vcols = []
        d = props.get(0x0800187A)
        if d is not None and len(d) >= 4:
            n_vc = u32(d, 0)
            if n_vc and len(d) >= 4 + n_vc*16:
                vcols = [struct.unpack_from('<4f', d, 4 + i*16) for i in range(n_vc)]

        objects.append({
            'node_id':      inst['node_id'],
            'name':         inst['name'],
            'xf':           inst['world_xf'],
            'mesh_id':      mesh_id,
            'vcols':        vcols,
            'depth':        inst['depth'],
            'via_ref':      inst['via_ref'],
            'is_template':  inst['is_template'],
            'relocated_by': inst['relocated_by'],
        })
    return objects


# ============================
# TRANSFORM
# ============================

def xform_verts(verts, xf):
    out = []
    for x, y, z in verts:
        out.append((xf[0]*x + xf[3]*y + xf[6]*z + xf[9],
                    xf[1]*x + xf[4]*y + xf[7]*z + xf[10],
                    xf[2]*x + xf[5]*y + xf[8]*z + xf[11]))
    return out

def xform_norms(norms, xf):
    out = []
    for x, y, z in norms:
        out.append((xf[0]*x + xf[3]*y + xf[6]*z,
                    xf[1]*x + xf[4]*y + xf[7]*z,
                    xf[2]*x + xf[5]*y + xf[8]*z))
    return out


# ============================
# WRITE SCENE
# ============================

def write_scene(objects, data, gmdl_index, mesh_idx_map, resolver):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_obj  = OUTPUT_DIR / f'{NAME}_brtr.obj'
    out_mtl  = OUTPUT_DIR / f'{NAME}_brtr.mtl'
    out_json = OUTPUT_DIR / f'{NAME}_brtr.json'

    placed = skipped_no_mesh = skipped_bad_geo = with_tex = 0
    v_off = n_off = uv_off = 1
    manifest = []
    used_materials = {}  # tex_id -> png_path, for the .mtl file
    geo_cache = {}       # mesh_id -> decoded geometry
    mat_cache = {}       # mesh_id -> (per-triangle material names, dominant tex_id)

    with open(out_obj, 'w') as fobj:
        fobj.write(f'# Jaws Unleashed — {NAME} BRTR scene. Y-up, right-handed (game Z negated). Blender: default OBJ import (forward -Z, up Y).\n')
        fobj.write(f'# {sum(1 for o in objects if o["mesh_id"] and o["mesh_id"] in gmdl_index)} placed mesh instances\n')
        fobj.write(f'mtllib {out_mtl.name}\n\n')

        for obj in objects:
            if not obj['mesh_id'] or obj['mesh_id'] not in gmdl_index:
                skipped_no_mesh += 1
                continue
            if not obj['xf']:
                skipped_no_mesh += 1
                continue

            if obj['mesh_id'] not in geo_cache:      # each mesh is reused by many instances
                geo_cache[obj['mesh_id']] = extract_mesh(data, gmdl_index[obj['mesh_id']])
            geo = geo_cache[obj['mesh_id']]
            if geo is None:
                skipped_bad_geo += 1
                continue

            verts, norms, uvs, idxs = geo
            xf  = obj['xf']
            wv  = xform_verts(verts, xf)
            wn  = xform_norms(norms, xf) if norms else []

            safe = (obj['name'] or f'node_{obj["node_id"]}').replace(' ','_').replace('/','_')
            if obj['via_ref'] is not None:
                safe += f'@ref{obj["via_ref"]}'      # one OBJ object per reference copy
            if obj['is_template']:
                safe = 'TEMPLATE__' + safe            # authored template spot; usually not rendered in-game
            fobj.write(f'o {safe}\n')

            # Per-triangle material from the mesh's submeshes (gdw_materials.py).
            mid = obj['mesh_id']
            if mid not in mat_cache:
                gpos = gmdl_index[mid]
                subs = resolver.submesh_textures(gpos, gpos + 8 + u32(data, gpos + 4)) if uvs else []
                tri_mat = ['none'] * (len(idxs) // 3)
                best = (0, None)
                for first, count, tid, png in subs:
                    if png is None:
                        continue
                    used_materials[tid] = png
                    for t in range(first, min(first + count, len(tri_mat))):
                        tri_mat[t] = f'mat_{tid}'
                    if count > best[0]:
                        best = (count, tid)
                mat_cache[mid] = (tri_mat, best[1])
            tri_mat, main_tid = mat_cache[mid]
            if main_tid is not None:
                with_tex += 1

            # Game is DirectX left-handed, OBJ right-handed: negate Z (see
            # rip_meshes.py). Manifest xf/pos below stay in raw game coordinates.
            for x, y, z in wv:
                fobj.write(f'v {x:.4f} {y:.4f} {-z:.4f}\n')
            for nx, ny, nz in wn:
                fobj.write(f'vn {nx:.5f} {ny:.5f} {-nz:.5f}\n')
            for u, v in uvs:
                fobj.write(f'vt {u:.5f} {v:.5f}\n')

            has_uv = bool(uvs)
            has_n  = bool(wn)
            cur_mat = None
            for i in range(0, len(idxs)-2, 3):
                if tri_mat[i // 3] != cur_mat:
                    cur_mat = tri_mat[i // 3]
                    fobj.write(f'usemtl {cur_mat}\n')
                # Original VIND order is correct once Z is mirrored (see rip_meshes.py).
                a, b, c = idxs[i]+v_off, idxs[i+1]+v_off, idxs[i+2]+v_off
                if has_uv and has_n:
                    au,bu,cu = idxs[i]+uv_off, idxs[i+1]+uv_off, idxs[i+2]+uv_off
                    an,bn,cn = idxs[i]+n_off,  idxs[i+1]+n_off,  idxs[i+2]+n_off
                    fobj.write(f'f {a}/{au}/{an} {b}/{bu}/{bn} {c}/{cu}/{cn}\n')
                elif has_n:
                    an,bn,cn = idxs[i]+n_off, idxs[i+1]+n_off, idxs[i+2]+n_off
                    fobj.write(f'f {a}//{an} {b}//{bn} {c}//{cn}\n')
                else:
                    fobj.write(f'f {a} {b} {c}\n')

            v_off  += len(wv)
            n_off  += len(wn)
            uv_off += len(uvs)
            placed += 1

            manifest.append({
                'node_id':  obj['node_id'],
                'name':     obj['name'],
                'mesh_id':  obj['mesh_id'],
                'mesh_idx': mesh_idx_map.get(obj['mesh_id'], -1),
                'xf':       list(xf),   # WORLD transform (composed + instanced)
                'pos':      [xf[9], xf[10], xf[11]],
                'tris':     len(idxs)//3,
                'vcols':    len(obj['vcols']),
                'tex_id':   main_tid,   # texture of the largest submesh (OBJ has per-face materials)
                'depth':        obj['depth'],
                'via_ref':      obj['via_ref'],
                'is_template':  obj['is_template'],
                'relocated_by': obj['relocated_by'],
            })

            if placed % 100 == 0:
                print(f'  {placed} objects placed…')

    with open(out_json, 'w') as fj:
        json.dump(manifest, fj, indent=2)

    with open(out_mtl, 'w') as fmtl:
        fmtl.write(f'# Jaws Unleashed — {NAME} BRTR scene materials\n')
        fmtl.write('newmtl none\nKd 0.6 0.6 0.6\n\n')
        for tid, png_path in sorted(used_materials.items()):
            rel_path = Path(os.path.relpath(png_path, OUTPUT_DIR))
            fmtl.write(f'newmtl mat_{tid}\n')
            fmtl.write('Ka 1.0 1.0 1.0\nKd 1.0 1.0 1.0\n')
            fmtl.write(f'map_Kd {rel_path.as_posix()}\n\n')

    print(f'\nPlaced          : {placed}')
    print(f'  with texture  : {with_tex}')
    print(f'Skipped no mesh : {skipped_no_mesh}')
    print(f'Skipped bad geo : {skipped_bad_geo}')
    print(f'Unique textures : {len(used_materials)}')
    print(f'OBJ             : {out_obj}  ({out_obj.stat().st_size//1024} KB)')
    print(f'MTL             : {out_mtl}')
    print(f'JSON            : {out_json}')


# ============================
# MAIN
# ============================

def main():
    print(f'Loading {INPUT_FILE}…')
    data = open(INPUT_FILE, 'rb').read()
    print(f'  {len(data):,} bytes\n')

    print('Building GMDL index…')
    gmdl_index, mesh_idx_map = build_gmdl_index(data)
    print(f'  {len(gmdl_index)} valid meshes\n')


    print('Indexing materials (MATS -> GMAT -> TEXP)…')
    resolver = MaterialResolver(data, NAME, 'textures')
    print(f'  {len(resolver.gmat)} GMAT materials, {len(resolver.files)} texture PNGs in textures/{NAME}/\n')

    print('Parsing BRTR scene…')
    objects = parse_brtr(data)
    print(f'  {len(objects)} CHBR nodes total')
    with_mesh = sum(1 for o in objects if o['mesh_id'] and o['mesh_id'] in gmdl_index)
    with_vcol = sum(1 for o in objects if o['vcols'])
    print(f'  {with_mesh} with resolvable mesh')
    print(f'  {with_vcol} with vertex colors (baked lighting)\n')

    print('Writing scene OBJ…')
    write_scene(objects, data, gmdl_index, mesh_idx_map, resolver)


if __name__ == '__main__':
    main()

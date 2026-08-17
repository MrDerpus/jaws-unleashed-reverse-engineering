"""
Extract the pre-built scene from the BRTR chunk, with textures.

BRTR is the Binary Resource Tree — it stores every scene object already placed
in world space. Each CHBR sub-block is one placed instance: name, 4x3 world
transform, mesh resource ID, vertex colors (baked lighting), and AABB.

Each mesh's TSET block references 1+ texture IDs per layer (see CLAUDE.md's
TSET Format section). TSET layer semantics are NOT fully decoded — a mesh can
reference several unrelated textures (e.g. a rock referencing a black runtime
render-target, an underwater caustic texture, AND a grass alpha decal, all at
once). There is no single correct "the diffuse" texture in general. This
script uses a heuristic: gather every texture ID referenced anywhere in a
mesh's TSET, resolve each through textures/texture_db.json (preferring an
entry from the same GDW being exported), skip ones whose PNG is degenerate
(flat/blank — usually an unfilled runtime render target), and pick the
largest remaining one as that mesh's material. Treat the resulting texture
assignment as approximate, not authoritative.

This produces:
  scenes/<NAME>_brtr.obj  — merged world-space geometry, one group per object
  scenes/<NAME>_brtr.mtl  — one material per resolved texture, map_Kd per PNG
  scenes/<NAME>_brtr.json — manifest: name, mesh_id, position, tri count, tex_id

Run from project root:
  python3 scripts/rip_brtr_scene.py
"""

import struct
import json
from pathlib import Path
from functools import lru_cache

# ============================
# CONFIG
# ============================

NAME       = 'FISH'
INPUT_FILE = f'GAME_GDWs/{NAME}.GDW'
OUTPUT_DIR = Path('scenes')
TEXTURE_DB_FILE = Path('textures/texture_db.json')


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

def parse_tset_texture_ids(data, gmdl_pos, gmdl_end):
    """Return all texture IDs referenced by a GMDL's TSET block, layer 0 first."""
    tset = data.find(b'TSET', gmdl_pos, gmdl_end)
    if tset == -1:
        return []
    tsz = u32(data, tset + 4)
    n_layers = u32(data, tset + 8)
    if not tsz or not n_layers or n_layers >= 50 or tsz != (1 + n_layers * 5) * 4:
        return []
    ids = []
    for i in range(n_layers):
        base = tset + 8 + 4 + i * 20
        for j in range(1, 5):  # val_A, val_B, val_C, val_D
            tid = u32(data, base + j * 4)
            if tid and tid not in ids:
                ids.append(tid)
    return ids


@lru_cache(maxsize=None)
def _is_blank_image(png_path):
    """True if the PNG is flat/single-color (likely an unfilled runtime render target)."""
    try:
        from PIL import Image
        extrema = Image.open(png_path).convert('RGB').getextrema()
        # blank/flat if every channel's (min, max) pair collapses to a single value
        return all(lo == hi for lo, hi in extrema)
    except Exception:
        return False


def load_texture_db():
    if not TEXTURE_DB_FILE.exists():
        print(f'  WARNING: {TEXTURE_DB_FILE} not found — run scripts/build_texture_db.py first. No textures will be assigned.')
        return {}
    with open(TEXTURE_DB_FILE) as f:
        return json.load(f)


def resolve_primary_texture(tex_ids, gdw_name, texture_db):
    """Pick the largest non-blank texture among tex_ids, preferring same-GDW entries."""
    best = None  # (area, tex_id, file_path)
    for tid in tex_ids:
        entries = texture_db.get(str(tid))
        if not entries:
            continue
        entry = next((e for e in entries if e['gdw'] == gdw_name), entries[0])
        png_path = Path(entry['file'])
        if not png_path.exists():
            continue
        if _is_blank_image(str(png_path)):
            continue
        area = entry['w'] * entry['h']
        if best is None or area > best[0]:
            best = (area, tid, str(png_path))
    if best is None:
        return None
    return best[1], best[2]


def build_texture_index(data, gmdl_index, gdw_name, texture_db):
    """Returns res_id -> (tex_id, png_path) for meshes with a resolvable texture."""
    tex_index = {}
    for res_id, gmdl_pos in gmdl_index.items():
        sz = u32(data, gmdl_pos + 4)
        if not sz:
            continue
        end = gmdl_pos + 8 + sz
        tex_ids = parse_tset_texture_ids(data, gmdl_pos, end)
        if not tex_ids:
            continue
        resolved = resolve_primary_texture(tex_ids, gdw_name, texture_db)
        if resolved:
            tex_index[res_id] = resolved
    return tex_index


# ============================
# GMDL INDEX
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
            off = pos+4; mesh_idx += 1; continue
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
    """Return list of scene objects from the BRTR chunk."""
    candidates = []
    pos = 0
    while True:
        idx = data.find(b'BRTR', pos)
        if idx == -1: break
        if idx + 20 <= len(data) and u32(data, idx+8) == 0x01025024 and u32(data, idx+12) == 1 and data[idx+16:idx+20] == b'PRPS':
            candidates.append((u32(data, idx+4), idx))
        pos = idx + 4
    if not candidates:
        raise RuntimeError('BRTR chunk not found')
    brtr_sz, brtr_pos = max(candidates)
    brtr      = data[brtr_pos+8 : brtr_pos+8+brtr_sz]
    print(f'BRTR @ 0x{brtr_pos:X}  size={brtr_sz:,}')

    objects = []
    pos = 0
    while True:
        p = brtr.find(b'CHBR', pos)
        if p == -1: break

        chbr_sz = u32(brtr, p+4)
        # CHBR payload: [4-byte magic][4-byte node_id][PRPS ...]
        node_id  = u32(brtr, p+12)
        prps_off = p + 16

        props = parse_prps_props(brtr, prps_off)
        if not props:
            pos = p+4; continue

        # Name
        name = ''
        if 0x080017D8 in props:
            d = props[0x080017D8]
            if len(d) >= 4:
                slen = u32(d, 0)
                if slen and slen <= len(d)-4:
                    name = d[4:4+slen].decode('utf-8','replace').strip('\x00').strip()

        # Transform (12 float column-major 4x3)
        xf = None
        if 0x080017DA in props and len(props[0x080017DA]) >= 48:
            xf = struct.unpack_from('<12f', props[0x080017DA])

        # Mesh reference: [uint32 "GMDL"][uint32 mesh_resource_id]
        mesh_id = None
        if 0x08001873 in props:
            d = props[0x08001873]
            if len(d) >= 8:
                mesh_id = u32(d, 4)

        # AABB
        aabb = None
        if 0x080017DF in props and len(props[0x080017DF]) >= 24:
            aabb = list(struct.unpack_from('<6f', props[0x080017DF]))

        # Vertex colors: uint32 count + count*16 RGBA float32
        vcols = []
        if 0x0800187A in props:
            d = props[0x0800187A]
            if len(d) >= 4:
                n_vc = u32(d, 0)
                if n_vc and len(d) >= 4 + n_vc*16:
                    for i in range(n_vc):
                        base = 4 + i*16
                        vcols.append(struct.unpack_from('<4f', d, base))

        objects.append({
            'node_id': node_id,
            'name':    name,
            'xf':      xf,
            'mesh_id': mesh_id,
            'aabb':    aabb,
            'vcols':   vcols,
        })
        pos = p + 4

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

def write_scene(objects, data, gmdl_index, mesh_idx_map, tex_index):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_obj  = OUTPUT_DIR / f'{NAME}_brtr.obj'
    out_mtl  = OUTPUT_DIR / f'{NAME}_brtr.mtl'
    out_json = OUTPUT_DIR / f'{NAME}_brtr.json'

    placed = skipped_no_mesh = skipped_bad_geo = with_tex = 0
    v_off = n_off = uv_off = 1
    manifest = []
    used_materials = {}  # tex_id -> png_path, for the .mtl file

    with open(out_obj, 'w') as fobj:
        fobj.write(f'# Jaws Unleashed — {NAME} BRTR scene (DirectX Y-up)\n')
        fobj.write(f'# {sum(1 for o in objects if o["mesh_id"] and o["mesh_id"] in gmdl_index)} placed mesh instances\n')
        fobj.write(f'mtllib {out_mtl.name}\n\n')

        for obj in objects:
            if not obj['mesh_id'] or obj['mesh_id'] not in gmdl_index:
                skipped_no_mesh += 1
                continue
            if not obj['xf']:
                skipped_no_mesh += 1
                continue

            geo = extract_mesh(data, gmdl_index[obj['mesh_id']])
            if geo is None:
                skipped_bad_geo += 1
                continue

            verts, norms, uvs, idxs = geo
            xf  = obj['xf']
            wv  = xform_verts(verts, xf)
            wn  = xform_norms(norms, xf) if norms else []

            safe = (obj['name'] or f'node_{obj["node_id"]}').replace(' ','_').replace('/','_')
            fobj.write(f'o {safe}\n')

            tex_res = tex_index.get(obj['mesh_id']) if uvs else None
            if tex_res:
                tid, png_path = tex_res
                used_materials[tid] = png_path
                fobj.write(f'usemtl mat_{tid}\n')
                with_tex += 1
            else:
                fobj.write('usemtl none\n')

            for x, y, z in wv:
                fobj.write(f'v {x:.4f} {y:.4f} {z:.4f}\n')
            for nx, ny, nz in wn:
                fobj.write(f'vn {nx:.5f} {ny:.5f} {nz:.5f}\n')
            for u, v in uvs:
                fobj.write(f'vt {u:.5f} {v:.5f}\n')

            has_uv = bool(uvs)
            has_n  = bool(wn)
            for i in range(0, len(idxs)-2, 3):
                # Winding swap (b<->c) — see the note in rip_meshes.py: GDW VIND
                # order is DirectX clockwise-front, OBJ/OpenGL expect CCW-front.
                a, b, c = idxs[i]+v_off, idxs[i+2]+v_off, idxs[i+1]+v_off
                if has_uv and has_n:
                    au,bu,cu = idxs[i]+uv_off, idxs[i+2]+uv_off, idxs[i+1]+uv_off
                    an,bn,cn = idxs[i]+n_off,  idxs[i+2]+n_off,  idxs[i+1]+n_off
                    fobj.write(f'f {a}/{au}/{an} {b}/{bu}/{bn} {c}/{cu}/{cn}\n')
                elif has_n:
                    an,bn,cn = idxs[i]+n_off, idxs[i+2]+n_off, idxs[i+1]+n_off
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
                'xf':       list(xf),
                'pos':      [xf[9], xf[10], xf[11]],
                'tris':     len(idxs)//3,
                'vcols':    len(obj['vcols']),
                'tex_id':   tex_res[0] if tex_res else None,
            })

            if placed % 100 == 0:
                print(f'  {placed} objects placed…')

    with open(out_json, 'w') as fj:
        json.dump(manifest, fj, indent=2)

    with open(out_mtl, 'w') as fmtl:
        fmtl.write(f'# Jaws Unleashed — {NAME} BRTR scene materials\n')
        fmtl.write('newmtl none\nKd 0.6 0.6 0.6\n\n')
        for tid, png_path in sorted(used_materials.items()):
            # scenes/ is a sibling of textures/ at project root — relative path from OUTPUT_DIR
            rel_path = Path('..') / png_path
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

    print('Loading texture database…')
    texture_db = load_texture_db()
    print(f'  {len(texture_db)} texture IDs known\n')

    print('Resolving mesh textures via TSET…')
    tex_index = build_texture_index(data, gmdl_index, NAME, texture_db)
    print(f'  {len(tex_index)}/{len(gmdl_index)} meshes resolved a texture\n')

    print('Parsing BRTR scene…')
    objects = parse_brtr(data)
    print(f'  {len(objects)} CHBR nodes total')
    with_mesh = sum(1 for o in objects if o['mesh_id'] and o['mesh_id'] in gmdl_index)
    with_vcol = sum(1 for o in objects if o['vcols'])
    print(f'  {with_mesh} with resolvable mesh')
    print(f'  {with_vcol} with vertex colors (baked lighting)\n')

    print('Writing scene OBJ…')
    write_scene(objects, data, gmdl_index, mesh_idx_map, tex_index)


if __name__ == '__main__':
    main()

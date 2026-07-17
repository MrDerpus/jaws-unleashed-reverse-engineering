"""
Reconstruct a FISH.GDW level scene as a single Wavefront OBJ.

For each named scene object that has a mesh reference (PROP 0x08001873),
look up its GMDL geometry, apply its 3x4 world-space transform, and
write all geometry into one merged OBJ file with per-object groups.
"""

import struct
import json
from pathlib import Path

# =====================================
# CONFIG
# =====================================

NAME = 'FISH'
INPUT_FILE = f'../GAME_GDWs/{NAME}.GDW'
OUTPUT_DIR  = Path(f'../scenes')
OUTPUT_OBJ  = OUTPUT_DIR / f'{NAME}_scene.obj'
OUTPUT_JSON = OUTPUT_DIR / f'{NAME}_manifest.json'


# =====================================
# HELPERS
# =====================================

def read_u32(data, offset):
    try: return struct.unpack('<I', data[offset:offset+4])[0]
    except: return None

def read_f32(data, offset):
    try: return struct.unpack('<f', data[offset:offset+4])[0]
    except: return None

def find_tag_in(data, tag, start, end):
    p = data.find(tag, start, end)
    if p == -1: return None, None
    return p, read_u32(data, p+4)


def apply_transform(verts, xf):
    """Apply column-major 4x3 matrix (12 floats) to list of (x,y,z).
    Layout: xf[0..2]=X-basis, xf[3..5]=Y-basis, xf[6..8]=Z-basis, xf[9..11]=translation."""
    out = []
    for x, y, z in verts:
        nx = xf[0]*x + xf[3]*y + xf[6]*z + xf[9]
        ny = xf[1]*x + xf[4]*y + xf[7]*z + xf[10]
        nz = xf[2]*x + xf[5]*y + xf[8]*z + xf[11]
        out.append((nx, ny, nz))
    return out


def apply_rot(norms, xf):
    """Apply only the 3x3 rotation/scale portion of the column-major matrix."""
    out = []
    for nx, ny, nz in norms:
        ox = xf[0]*nx + xf[3]*ny + xf[6]*nz
        oy = xf[1]*nx + xf[4]*ny + xf[7]*nz
        oz = xf[2]*nx + xf[5]*ny + xf[8]*nz
        out.append((ox, oy, oz))
    return out


# =====================================
# PARSE GDW
# =====================================

def load_gdw(path):
    with open(path, 'rb') as f:
        return f.read()


def build_gmdl_index(data):
    """Build dict: mesh_resource_id → file offset of GMDL tag."""
    index = {}
    off = 0
    while True:
        pos = data.find(b'GMDL', off)
        if pos == -1: break
        sz = read_u32(data, pos+4)
        if sz and sz < 5_000_000:
            mesh_id = read_u32(data, pos+8)
            if mesh_id and mesh_id not in index:
                index[mesh_id] = pos
        off = pos + 4
    return index


def extract_mesh(data, gmdl_pos):
    """Extract geometry from GMDL. Returns (verts, norms, uvs, indices) or None."""
    sz = read_u32(data, gmdl_pos+4)
    if not sz: return None
    end = gmdl_pos + 8 + sz

    posi_pos, posi_sz = find_tag_in(data, b'POSI', gmdl_pos, end)
    norm_pos, norm_sz = find_tag_in(data, b'NORM', gmdl_pos, end)
    uvuv_pos, uvuv_sz = find_tag_in(data, b'UVUV', gmdl_pos, end)
    vind_pos, vind_sz = find_tag_in(data, b'VIND', gmdl_pos, end)

    if None in (posi_pos, vind_pos) or not posi_sz or not vind_sz:
        return None

    n_verts   = posi_sz // 12
    n_indices = vind_sz // 2
    if n_verts < 3 or n_indices < 3:
        return None

    indices = list(struct.unpack_from(f'<{n_indices}H', data, vind_pos+8))
    if max(indices) >= n_verts:
        return None

    verts = [(read_f32(data, posi_pos+8+i*12),
              read_f32(data, posi_pos+8+i*12+4),
              read_f32(data, posi_pos+8+i*12+8)) for i in range(n_verts)]

    norms = []
    if norm_pos and norm_sz == posi_sz:
        norms = [(read_f32(data, norm_pos+8+i*12),
                  read_f32(data, norm_pos+8+i*12+4),
                  read_f32(data, norm_pos+8+i*12+8)) for i in range(n_verts)]

    uvs = []
    if uvuv_pos and uvuv_sz == n_verts * 8:
        uvs = [(read_f32(data, uvuv_pos+8+i*8),
                1.0 - read_f32(data, uvuv_pos+8+i*8+4)) for i in range(n_verts)]

    return verts, norms, uvs, indices


def parse_scene_objects(data, gmdl_index):
    """Walk PRPS blocks and extract objects with name + transform + mesh ref."""
    objects = []
    off = 0
    while True:
        p = data.find(b'PRPS', off)
        if p == -1: break
        size = read_u32(data, p+4)
        if not size or size > 500_000:
            off = p+4; continue
        end = p + 8 + size

        name = None
        transform = None
        aabb = None
        mesh_ref = None

        q = p + 8
        while q < end - 8:
            tag = data[q:q+4]
            sz  = read_u32(data, q+4)
            if sz is None or sz > size: break
            if tag == b'PROP':
                pid = read_u32(data, q+8)
                if pid == 0x080017D8:
                    slen = read_u32(data, q+12)
                    if slen and slen < 256:
                        name = data[q+16:q+16+slen].decode('ascii','?').strip('\x00')
                elif pid == 0x080017DA:
                    n = min(sz//4, 12)
                    transform = [read_f32(data, q+12+i*4) for i in range(n)]
                elif pid == 0x080017DF:
                    aabb = [read_f32(data, q+12+i*4) for i in range(6)]
                elif pid == 0x08001873:
                    mesh_ref = read_u32(data, q+12+4)  # second uint32
            q += 8 + (sz or 0)

        if name and transform and mesh_ref and mesh_ref in gmdl_index:
            objects.append({
                'name':      name,
                'mesh_id':   mesh_ref,
                'gmdl_pos':  gmdl_index[mesh_ref],
                'transform': transform,
                'aabb':      aabb,
            })
        off = p + 4
    return objects


# =====================================
# WRITE SCENE
# =====================================

def write_scene(objects, data, output_obj, output_json):
    vertex_offset = 1   # OBJ indices are 1-based
    normal_offset = 1
    uv_offset     = 1

    manifest = []
    placed   = 0
    skipped  = 0

    with open(output_obj, 'w') as fobj:
        fobj.write(f'# Jaws Unleashed — {NAME} scene (DirectX Y-up coordinates)\n')
        fobj.write(f'# {len(objects)} placed objects\n\n')

        for obj in objects:
            mesh = extract_mesh(data, obj['gmdl_pos'])
            if mesh is None:
                skipped += 1
                continue

            verts, norms, uvs, indices = mesh
            xf = obj['transform']

            w_verts = apply_transform(verts, xf)
            w_norms = apply_rot(norms, xf) if norms else []

            safe_name = obj['name'].replace(' ', '_').replace('\x00', '')
            fobj.write(f'o {safe_name}\n')

            for x, y, z in w_verts:
                fobj.write(f'v {x:.4f} {y:.4f} {z:.4f}\n')
            for nx, ny, nz in w_norms:
                fobj.write(f'vn {nx:.5f} {ny:.5f} {nz:.5f}\n')
            for u, v in uvs:
                fobj.write(f'vt {u:.5f} {v:.5f}\n')

            has_uv = bool(uvs)
            has_n  = bool(w_norms)
            for i in range(0, len(indices)-2, 3):
                a = indices[i]   + vertex_offset
                b = indices[i+1] + vertex_offset
                c = indices[i+2] + vertex_offset
                if has_uv and has_n:
                    an = indices[i]   + normal_offset
                    bn = indices[i+1] + normal_offset
                    cn = indices[i+2] + normal_offset
                    au = indices[i]   + uv_offset
                    bu = indices[i+1] + uv_offset
                    cu = indices[i+2] + uv_offset
                    fobj.write(f'f {a}/{au}/{an} {b}/{bu}/{bn} {c}/{cu}/{cn}\n')
                elif has_n:
                    an = indices[i]   + normal_offset
                    bn = indices[i+1] + normal_offset
                    cn = indices[i+2] + normal_offset
                    fobj.write(f'f {a}//{an} {b}//{bn} {c}//{cn}\n')
                else:
                    fobj.write(f'f {a} {b} {c}\n')

            vertex_offset += len(verts)
            normal_offset += len(w_norms) if w_norms else 0
            uv_offset     += len(uvs)     if uvs else 0

            manifest.append({
                'name':     obj['name'],
                'mesh_id':  obj['mesh_id'],
                'pos':      [xf[9], xf[10], xf[11]],
                'verts':    len(verts),
                'tris':     len(indices) // 3,
            })
            placed += 1
            if placed % 50 == 0:
                print(f'  placed {placed}…')

    with open(output_json, 'w') as fj:
        json.dump(manifest, fj, indent=2)

    print(f'\nPlaced  : {placed}')
    print(f'Skipped : {skipped}')
    print(f'OBJ     : {output_obj}')
    print(f'JSON    : {output_json}')


# =====================================
# MAIN
# =====================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f'Loading {INPUT_FILE}…')
    data = load_gdw(INPUT_FILE)
    print(f'  {len(data):,} bytes')

    print('Building GMDL index…')
    gmdl_index = build_gmdl_index(data)
    print(f'  {len(gmdl_index)} unique mesh IDs')

    print('Parsing scene objects…')
    objects = parse_scene_objects(data, gmdl_index)
    print(f'  {len(objects)} placeable objects')

    print('Writing scene OBJ…')
    write_scene(objects, data, OUTPUT_OBJ, OUTPUT_JSON)


if __name__ == '__main__':
    main()

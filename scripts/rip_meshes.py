import struct
from pathlib import Path

# =====================================
# CONFIG
# =====================================

NAME = 'FISH'
INPUT_FILE = f'../GAME_GDWs/{NAME}.GDW'
OUTPUT_DIR = Path(f'../models/{NAME}')


# =====================================
# HELPERS
# =====================================

def read_u32(data, offset):
    try:
        return struct.unpack('<I', data[offset:offset + 4])[0]
    except:
        return None

def read_f32(data, offset):
    try:
        return struct.unpack('<f', data[offset:offset + 4])[0]
    except:
        return None

def find_tag(data, tag, start, end):
    p = data.find(tag, start, end)
    if p == -1:
        return None, None
    return p, read_u32(data, p + 4)


# =====================================
# MAIN
# =====================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(INPUT_FILE, 'rb') as f:
        data = f.read()

    print(f'Loaded {len(data):,} bytes from {INPUT_FILE}')

    offset    = 0
    mesh_idx  = 0
    extracted = 0
    skipped   = 0

    while True:
        pos = data.find(b'GMDL', offset)
        if pos == -1:
            break

        gmdl_size = read_u32(data, pos + 4)
        if not gmdl_size or gmdl_size > 5_000_000:
            offset = pos + 4
            continue

        gmdl_end = pos + 8 + gmdl_size

        posi_pos, posi_sz = find_tag(data, b'POSI', pos, gmdl_end)
        norm_pos, norm_sz = find_tag(data, b'NORM', pos, gmdl_end)
        uvuv_pos, uvuv_sz = find_tag(data, b'UVUV', pos, gmdl_end)
        vind_pos, vind_sz = find_tag(data, b'VIND', pos, gmdl_end)

        if None in (posi_pos, vind_pos) or not posi_sz or not vind_sz:
            mesh_idx += 1
            offset = pos + 4
            skipped += 1
            continue

        n_verts   = posi_sz // 12
        n_indices = vind_sz // 2

        if n_verts < 3 or n_indices < 3:
            mesh_idx += 1
            offset = pos + 4
            skipped += 1
            continue

        indices = struct.unpack_from(f'<{n_indices}H', data, vind_pos + 8)
        if max(indices) >= n_verts:
            mesh_idx += 1
            offset = pos + 4
            skipped += 1
            continue

        # Positions
        verts = []
        for i in range(n_verts):
            base = posi_pos + 8 + i * 12
            verts.append((read_f32(data, base),
                          read_f32(data, base + 4),
                          read_f32(data, base + 8)))

        # Normals
        norms = []
        if norm_pos and norm_sz == posi_sz:
            for i in range(n_verts):
                base = norm_pos + 8 + i * 12
                norms.append((read_f32(data, base),
                               read_f32(data, base + 4),
                               read_f32(data, base + 8)))

        # UVs
        uvs = []
        if uvuv_pos and uvuv_sz == n_verts * 8:
            for i in range(n_verts):
                base = uvuv_pos + 8 + i * 8
                uvs.append((read_f32(data, base),
                             1.0 - read_f32(data, base + 4)))

        # Write OBJ
        fname = OUTPUT_DIR / f'{NAME}_mesh_{mesh_idx:04d}.obj'
        with open(fname, 'w') as f:
            f.write(f'# GMDL @ 0x{pos:X}  verts={n_verts}  tris={n_indices // 3}\n')
            for x, y, z in verts:
                f.write(f'v {x:.6f} {y:.6f} {z:.6f}\n')
            for nx, ny, nz in norms:
                f.write(f'vn {nx:.6f} {ny:.6f} {nz:.6f}\n')
            for u, v in uvs:
                f.write(f'vt {u:.6f} {v:.6f}\n')
            has_uv = bool(uvs)
            has_n  = bool(norms)
            for i in range(0, n_indices - 2, 3):
                a = indices[i] + 1
                b = indices[i + 1] + 1
                c = indices[i + 2] + 1
                if has_uv and has_n:
                    f.write(f'f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n')
                elif has_n:
                    f.write(f'f {a}//{a} {b}//{b} {c}//{c}\n')
                else:
                    f.write(f'f {a} {b} {c}\n')

        print(f'  [{mesh_idx:04d}] {fname.name}  verts={n_verts}  tris={n_indices // 3}')
        extracted += 1
        mesh_idx  += 1
        offset = pos + 4

    print(f'\nExtracted : {extracted}')
    print(f'Skipped   : {skipped}')
    print(f'Output    : {OUTPUT_DIR}')


if __name__ == '__main__':
    main()

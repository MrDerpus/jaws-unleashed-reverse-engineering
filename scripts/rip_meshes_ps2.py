import struct
from pathlib import Path

# =====================================
# CONFIG
# =====================================

NAME = '_FISH'
INPUT_FILE = f'../GAME_GDWs/{NAME}.GDE'
OUTPUT_DIR = Path(f'../models/{NAME}_PS2')

# Triangles whose cross-product magnitude falls below this are strip
# connector/degenerate triangles (repeated or collinear verts) and are
# dropped rather than written to the OBJ.
DEGENERATE_AREA_THRESHOLD = 1.0


# =====================================
# HELPERS
# =====================================

def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def f32(d, o):
    return struct.unpack_from('<f', d, o)[0]


def find_tag(data, tag, start, end):
    p = data.find(tag, start, end)
    return p


def cross(a, b):
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])


def sub(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


# =====================================
# GMDL PARSING
# =====================================

def parse_gmdl(data, pos):
    size = u32(data, pos + 4)
    if not size or size > 5_000_000:
        return None
    end = pos + 8 + size

    vert_pos = find_tag(data, b'VERT', pos, end)
    strp_pos = find_tag(data, b'STRP', pos, end)
    if vert_pos == -1 or strp_pos == -1:
        return None

    vcount = u32(data, vert_pos + 8)
    poss_pos = vert_pos + 12
    if data[poss_pos:poss_pos+4] != b'POSS':
        return None
    poss_size = u32(data, poss_pos + 4)
    poss_payload = data[poss_pos+8:poss_pos+8+poss_size]
    if len(poss_payload) < 4:
        return None
    scale = f32(poss_payload, 0)
    body = poss_payload[4:]
    n = len(body) // 8
    if n != vcount or n < 3:
        return None
    raw = struct.unpack(f'<{n*4}h', body[:n*8])
    positions = [(raw[i*4]*scale, raw[i*4+1]*scale, raw[i*4+2]*scale) for i in range(n)]

    norm_pos = poss_pos + 8 + poss_size
    normals = []
    if data[norm_pos:norm_pos+4] == b'NORM':
        norm_size = u32(data, norm_pos + 4)
        if norm_size == n * 12:
            norm_payload = data[norm_pos+8:norm_pos+8+norm_size]
            normals = [struct.unpack_from('<3f', norm_payload, i*12) for i in range(n)]

    uvs = []
    if normals:
        uvuv_pos = norm_pos + 8 + u32(data, norm_pos + 4)
        if data[uvuv_pos:uvuv_pos+4] == b'UVUV':
            uvuv_size = u32(data, uvuv_pos + 4)
            if uvuv_size == n * 8:
                uv_payload = data[uvuv_pos+8:uvuv_pos+8+uvuv_size]
                uvs = [struct.unpack_from('<2f', uv_payload, i*8) for i in range(n)]

    strp_size = u32(data, strp_pos + 4)
    strp_payload = data[strp_pos+8:strp_pos+8+strp_size]
    if len(strp_payload) < 4:
        return None
    count = u32(strp_payload, 0)
    if count * 2 + 4 > len(strp_payload):
        return None
    entries_raw = struct.unpack_from(f'<{count}H', strp_payload, 4)

    strips = []
    cur = []
    for e in entries_raw:
        idx = e & 0x7FFF
        flag = (e & 0x8000) != 0
        if idx == 0x7FFF:
            if cur:
                strips.append(cur)
            cur = []
        else:
            if idx >= n:
                return None
            cur.append((idx, flag))
    if cur:
        strips.append(cur)

    triangles = []
    for strip in strips:
        for i in range(len(strip) - 2):
            i0, _f0 = strip[i]
            i1, _f1 = strip[i+1]
            i2, f2 = strip[i+2]
            flip = (i % 2 == 0) ^ f2
            a, b = (i2, i1) if flip else (i1, i2)
            p0, p1, p2 = positions[i0], positions[a], positions[b]
            cr = cross(sub(p1, p0), sub(p2, p0))
            area = (cr[0]**2 + cr[1]**2 + cr[2]**2) ** 0.5
            if area < DEGENERATE_AREA_THRESHOLD:
                continue
            triangles.append((i0, a, b))

    if len(triangles) < 1:
        return None

    return {
        'positions': positions,
        'normals': normals,
        'uvs': uvs,
        'triangles': triangles,
    }


# =====================================
# MAIN
# =====================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(INPUT_FILE, 'rb') as f:
        data = f.read()

    print(f'Loaded {len(data):,} bytes from {INPUT_FILE}')

    offset = 0
    mesh_idx = 0
    extracted = 0
    skipped = 0

    while True:
        pos = data.find(b'GMDL', offset)
        if pos == -1:
            break

        mesh = parse_gmdl(data, pos)
        if mesh is None:
            mesh_idx += 1
            offset = pos + 4
            skipped += 1
            continue

        verts = mesh['positions']
        norms = mesh['normals']
        uvs = mesh['uvs']
        tris = mesh['triangles']
        has_n = bool(norms)
        has_uv = bool(uvs)

        fname = OUTPUT_DIR / f'{NAME}_mesh_{mesh_idx:04d}.obj'
        with open(fname, 'w') as f:
            f.write(f'# GMDL @ 0x{pos:X}  verts={len(verts)}  tris={len(tris)}\n')
            for x, y, z in verts:
                f.write(f'v {x:.6f} {y:.6f} {z:.6f}\n')
            for nx, ny, nz in norms:
                f.write(f'vn {nx:.6f} {ny:.6f} {nz:.6f}\n')
            for u, v in uvs:
                f.write(f'vt {u:.6f} {1.0 - v:.6f}\n')
            for i0, i1, i2 in tris:
                a, b, c = i0 + 1, i1 + 1, i2 + 1
                if has_uv and has_n:
                    f.write(f'f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n')
                elif has_n:
                    f.write(f'f {a}//{a} {b}//{b} {c}//{c}\n')
                else:
                    f.write(f'f {a} {b} {c}\n')

        print(f'  [{mesh_idx:04d}] {fname.name}  verts={len(verts)}  tris={len(tris)}')
        extracted += 1
        mesh_idx += 1
        offset = pos + 4

    print(f'\nExtracted : {extracted}')
    print(f'Skipped   : {skipped}')
    print(f'Output    : {OUTPUT_DIR}')


if __name__ == '__main__':
    main()

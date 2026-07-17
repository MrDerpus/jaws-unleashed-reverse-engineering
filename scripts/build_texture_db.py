"""
Build a cross-GDW texture database.

Scans all GDW files for GTEXT and GTEX texture blocks, records their IDs,
dimensions, and corresponding extracted PNG filenames. Outputs:

  textures/texture_db.json  — texture_id -> list of {gdw, file, w, h, bpp}

Use this to resolve mesh TSET texture references to actual PNG files,
even when the texture is stored in a different GDW than the mesh.

Run from project root:
  python3 scripts/build_texture_db.py
"""

import struct
import json
from pathlib import Path

GDW_DIR  = Path('GAME_GDWs')
TEX_DIR  = Path('textures')
OUT_FILE = TEX_DIR / 'texture_db.json'

LEVELS = [
    'AQUARIUM', 'ARMADA', 'BEACH', 'BEACHPST', 'CHASE',
    'DEEPSEA', 'DEEPSEA2', 'DOCKS', 'FISH', 'GAUNTLET',
    'KATATAMA', 'MINEMSHA', 'OPEN_NE', 'OPEN_NW', 'OPEN_S',
    'START', 'TITLE', 'TITLE0', 'TOWN', 'WRACK',
]


def u32(data, off):
    try:
        return struct.unpack_from('<I', data, off)[0]
    except:
        return None


GTEXT_HEADER = 0x54  # matches rip_textures.py HEADER_SIZE

def scan_gtext(gdw_name, data):
    """Yield (tex_id, seq_idx, width, height, bpp) for each extractable GTEXT block.

    seq_idx mirrors rip_textures.py's texture_index: increments for every block
    where payload_size > 0, regardless of BPP — matching the extractor exactly.
    """
    seq_idx = 0
    pos = 0
    while True:
        p = data.find(b'GTEXT', pos)
        if p == -1:
            break

        block_size = u32(data, p + 4)
        if not block_size or block_size > 10_000_000:
            pos = p + 4
            continue

        payload_size = block_size - GTEXT_HEADER
        if payload_size <= 0:
            # rip_textures.py skips without incrementing for these
            pos = p + 4
            continue

        tex_id = u32(data, p + 0x08)
        width  = u32(data, p + 0x18)
        height = u32(data, p + 0x1C)
        bpp    = u32(data, p + 0x20)

        if None not in (tex_id, width, height, bpp) and bpp in (24, 32):
            if 0 < width <= 4096 and 0 < height <= 4096:
                yield tex_id, seq_idx, width, height, bpp

        # Always increment — matches rip_textures.py behavior for all valid blocks
        seq_idx += 1
        pos = p + block_size


def scan_gtex(gdw_name, data):
    """Yield (tex_id, seq_idx, width, height, bpp) for each valid GTEX+TGAN block."""
    seq_idx = 0
    pos = 0
    while True:
        p = data.find(b'GTEX', pos)
        if p == -1:
            break
        if data[p + 4:p + 5] == b'T':  # skip GTEXT
            pos = p + 1
            continue

        block_size = u32(data, p + 4)
        if not block_size or block_size < 32 or block_size > 5_000_000:
            pos = p + 4
            continue

        payload_start = p + 8
        block_end = payload_start + block_size
        tex_id = u32(data, payload_start)

        tgan_pos = data.find(b'TGAN', payload_start, block_end)
        if tgan_pos == -1:
            pos = p + 4
            continue

        if tgan_pos - payload_start < 12:
            pos = p + 4
            continue

        width     = u32(data, tgan_pos - 12)
        height    = u32(data, tgan_pos - 8)
        bpp       = u32(data, tgan_pos - 4)
        tgan_size = u32(data, tgan_pos + 4)

        if None in (width, height, bpp, tgan_size):
            pos = p + 4
            continue
        if not (0 < width <= 4096 and 0 < height <= 4096):
            pos = p + 4
            continue
        if bpp not in (24, 32):
            pos = p + 4
            continue

        pixel_size = width * height * (bpp // 8)
        if tgan_size < pixel_size:
            pos = p + 4
            continue

        yield tex_id, seq_idx, width, height, bpp
        seq_idx += 1
        pos = p + 4


def gtext_filename(gdw_name, seq_idx, tex_id, width, height, bpp):
    fmt = 'rgba32' if bpp == 32 else 'rgb24'
    return f'textures/{gdw_name}/gtext/texture_{seq_idx:04}_id{tex_id:08x}_{width}x{height}_{fmt}.png'


def gtex_filename(gdw_name, seq_idx, tex_id, width, height, bpp):
    fmt = 'rgba32' if bpp == 32 else 'rgb24'
    return f'textures/{gdw_name}/gtex/gtex_{seq_idx:04}_id{tex_id:08x}_{width}x{height}_{fmt}.png'


def main():
    TEX_DIR.mkdir(exist_ok=True)

    # db[tex_id] = list of {gdw, file, w, h, bpp, source}
    db = {}

    for name in LEVELS:
        gdw_path = GDW_DIR / f'{name}.GDW'
        if not gdw_path.exists():
            print(f'  SKIP {name}.GDW (not found)')
            continue

        data = gdw_path.read_bytes()
        print(f'Scanning {name}.GDW ({len(data):,} bytes)…')

        gtext_count = 0
        for tex_id, seq_idx, w, h, bpp in scan_gtext(name, data):
            fname = gtext_filename(name, seq_idx, tex_id, w, h, bpp)
            entry = {'gdw': name, 'file': fname, 'w': w, 'h': h, 'bpp': bpp, 'src': 'GTEXT'}
            db.setdefault(tex_id, []).append(entry)
            gtext_count += 1

        gtex_count = 0
        for tex_id, seq_idx, w, h, bpp in scan_gtex(name, data):
            fname = gtex_filename(name, seq_idx, tex_id, w, h, bpp)
            entry = {'gdw': name, 'file': fname, 'w': w, 'h': h, 'bpp': bpp, 'src': 'GTEX'}
            db.setdefault(tex_id, []).append(entry)
            gtex_count += 1

        print(f'  GTEXT: {gtext_count}  GTEX: {gtex_count}  (total IDs so far: {len(db)})')

    # Convert int keys to strings for JSON
    db_out = {str(k): v for k, v in sorted(db.items())}

    with open(OUT_FILE, 'w') as f:
        json.dump(db_out, f, indent=2)

    print(f'\nDone. {len(db)} unique texture IDs across all GDWs.')
    print(f'Database: {OUT_FILE}')

    # Stats
    single_gdw = sum(1 for v in db.values() if len(set(e['gdw'] for e in v)) == 1)
    multi_gdw  = len(db) - single_gdw
    print(f'  Unique to one GDW : {single_gdw}')
    print(f'  Shared across GDWs: {multi_gdw}')

    # Report on AQUARIUM TSET references
    aquarium_path = GDW_DIR / 'AQUARIUM.GDW'
    if aquarium_path.exists():
        aq_data = aquarium_path.read_bytes()
        tset_ids = set()
        pos = 0
        while True:
            p = aq_data.find(b'GMDL', pos)
            if p == -1:
                break
            sz = u32(aq_data, p + 4)
            if not sz or sz > 5_000_000:
                pos = p + 4
                continue
            end = p + 8 + sz
            tset = aq_data.find(b'TSET', p, end)
            if tset != -1:
                tsz = u32(aq_data, tset + 4)
                n_layers = u32(aq_data, tset + 8)
                if tsz and n_layers and n_layers < 50 and tsz == (1 + n_layers * 5) * 4:
                    for i in range(n_layers):
                        base = tset + 8 + 4 + i * 20
                        for j in range(1, 5):
                            tid = u32(aq_data, base + j * 4)
                            if tid:
                                tset_ids.add(tid)
                else:
                    for i in range(1, (tsz or 0) // 4):
                        tid = u32(aq_data, tset + 8 + i * 4)
                        if tid and tid < 0x10000000:
                            tset_ids.add(tid)
            pos = p + 4

        found_in_db   = sum(1 for tid in tset_ids if str(tid) in db_out)
        not_in_db     = tset_ids - {int(k) for k in db_out}
        in_aquarium   = sum(1 for tid in tset_ids if any(e['gdw'] == 'AQUARIUM' for e in db.get(tid, [])))
        in_other_only = sum(1 for tid in tset_ids if str(tid) in db_out and not any(e['gdw'] == 'AQUARIUM' for e in db[int(str(tid))]))

        print(f'\nAQUARIUM mesh texture refs: {len(tset_ids)}')
        print(f'  Resolved in DB        : {found_in_db}')
        print(f'  In AQUARIUM.GDW itself: {in_aquarium}')
        print(f'  In other GDWs only    : {in_other_only}')
        print(f'  Not found anywhere    : {len(not_in_db)}')


if __name__ == '__main__':
    main()

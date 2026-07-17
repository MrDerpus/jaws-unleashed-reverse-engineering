import struct
from pathlib import Path
from PIL import Image



# =====================================
# CONFIG
# =====================================

NAME = 'FISH'
INPUT_FILE = f'../GAME_GDWs/{NAME}.GDW'
OUTPUT_DIR = Path(f'../textures/{NAME}/gtex')

FLIP_VERTICAL = True



# =====================================
# HELPERS
# =====================================

def ensure_dir(path):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)



def read_u32(data, offset):
    try:
        return struct.unpack('<I', data[offset:offset + 4])[0]
    except:
        return None



# =====================================
# SAVE TEXTURE
# =====================================

def save_texture(raw, width, height, bpp, index, tex_id):

    if bpp == 32:

        expected = width * height * 4

        if len(raw) < expected:
            return False

        # Format is ARGB: byte[0]=A, byte[1]=R, byte[2]=G, byte[3]=B
        # Confirmed via binary analysis: D3DFMT_A8R8G8B8, engine stores TGA in ARGB byte order.
        # Chroma key = CYAN (#00FFFF, D3D DWORD 0xFF00FFFF): pixels where R≈0,G≈255,B≈255 → transparent.
        buf = bytearray(expected)
        for i in range(expected // 4):
            a, r, g, b = raw[i*4], raw[i*4+1], raw[i*4+2], raw[i*4+3]
            is_chroma = (r < 20 and g > 235 and b > 235)
            buf[i*4]   = r
            buf[i*4+1] = g
            buf[i*4+2] = b
            buf[i*4+3] = 0 if is_chroma else a

        img = Image.frombytes('RGBA', (width, height), bytes(buf))

        if FLIP_VERTICAL:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)

        fname = f'gtex_{index:04}_id{tex_id:08x}_{width}x{height}_rgba32.png'
        img.save(OUTPUT_DIR / fname)
        return True

    elif bpp == 24:

        expected = width * height * 3

        if len(raw) < expected:
            return False

        img = Image.frombytes('RGB', (width, height), raw[:expected])

        # GTEX 24bpp stores R, B, G (not R, G, B) — swap G and B to correct
        r_ch, g_ch, b_ch = img.split()
        img = Image.merge('RGB', (r_ch, b_ch, g_ch))

        if FLIP_VERTICAL:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)

        fname = f'gtex_{index:04}_id{tex_id:08x}_{width}x{height}_rgb24.png'
        img.save(OUTPUT_DIR / fname)
        return True

    return False



# =====================================
# MAIN
# =====================================

def main():

    ensure_dir(OUTPUT_DIR)

    with open(INPUT_FILE, 'rb') as f:
        data = f.read()

    print(f'Loaded {len(data)} bytes')

    offset = 0
    index = 0
    successful = 0
    skipped = 0

    while True:

        pos = data.find(b'GTEX', offset)

        if pos == -1:
            break

        # GTEX followed by T = GTEXT — skip
        if data[pos + 4:pos + 5] == b'T':
            offset = pos + 1
            continue

        block_size = read_u32(data, pos + 4)

        if block_size is None or block_size < 32 or block_size > 5_000_000:
            offset = pos + 4
            continue

        payload_start = pos + 8
        block_end = payload_start + block_size

        # First uint32 of payload is always the texture ID
        tex_id = read_u32(data, payload_start)
        if tex_id is None:
            tex_id = 0

        # Find TGAN sub-chunk within this GTEX block
        tgan_pos = data.find(b'TGAN', payload_start, block_end)

        if tgan_pos == -1:
            skipped += 1
            offset = pos + 4
            continue

        # Width, height, BPP are always the three uint32s immediately before TGAN
        if tgan_pos - payload_start < 12:
            offset = pos + 4
            continue

        width     = read_u32(data, tgan_pos - 12)
        height    = read_u32(data, tgan_pos - 8)
        bpp       = read_u32(data, tgan_pos - 4)
        tgan_size = read_u32(data, tgan_pos + 4)

        if None in (width, height, bpp, tgan_size):
            offset = pos + 4
            continue

        if not (0 < width <= 4096 and 0 < height <= 4096):
            offset = pos + 4
            continue

        if bpp not in (24, 32):
            print(f'  SKIP unsupported BPP={bpp} @ 0x{pos:X} ({width}x{height})')
            skipped += 1
            offset = pos + 4
            continue

        channels   = bpp // 8
        pixel_size = width * height * channels

        if tgan_size < pixel_size:
            offset = pos + 4
            continue

        # TGAN content = [header bytes][pixel data]
        # header_bytes = tgan_size - pixel_size
        header_bytes = tgan_size - pixel_size
        pixel_start  = tgan_pos + 8 + header_bytes

        raw = data[pixel_start: pixel_start + pixel_size]

        if len(raw) < pixel_size:
            offset = pos + 4
            continue

        print(f'GTEX @ 0x{pos:X}: id={tex_id:#010x} {width}x{height} {bpp}bpp (TGAN header={header_bytes}b)')

        try:

            ok = save_texture(raw, width, height, bpp, index, tex_id)

            if ok:
                fmt = 'rgba32' if bpp == 32 else 'rgb24'
                print(f'  -> gtex_{index:04}_id{tex_id:08x}_{width}x{height}_{fmt}.png')
                successful += 1
            else:
                print(f'  [!] Save failed')

        except Exception as e:
            print(f'  ERROR: {e}')

        index += 1
        offset = pos + 4

    print('\n' + '=' * 60)
    print(f'Extracted : {successful}')
    print(f'Attempted : {index}')
    print(f'Skipped   : {skipped}')
    print(f'Output    : {OUTPUT_DIR}')



if __name__ == '__main__':
    main()

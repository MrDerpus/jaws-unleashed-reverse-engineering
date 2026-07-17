import struct
from pathlib import Path

from PIL import Image


# =====================================
# CONFIG
# =====================================

name = '_FISH'
INPUT_FILE = f'../GAME_GDWs/{name}.GDE'
OUTPUT_DIR = Path(f'../textures/{name}_PS2/gtext')

FLIP_VERTICAL = False


# =====================================
# HELPERS
# =====================================

def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def ensure_dir(path):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)


# PS2 GS 8-bit (PSMT8) texture memory is block-swizzled, not raster order.
# Standard public unswizzle algorithm (verified against known PS2 tools).
def unswizzle8(data, width, height):
    out = bytearray(width * height)
    for y in range(height):
        row_base = y * width
        for x in range(width):
            block_loc = (y & (~0xf)) * width + (x & (~0xf)) * 2
            swap_sel = (((y + 2) >> 2) & 0x1) * 4
            pos_y = (((y & (~3)) >> 1) + (y & 1)) & 0x7
            col_loc = pos_y * width * 2 + ((x + swap_sel) & 0x7) * 4
            byte_num = ((y >> 1) & 1) + ((x >> 2) & 2)
            swizzled_index = block_loc + col_loc + byte_num
            out[row_base + x] = data[swizzled_index]
    return bytes(out)


def decode_psmct32(raw, w, h):
    img = Image.new('RGBA', (w, h))
    img.putdata([(raw[i*4], raw[i*4+1], raw[i*4+2], raw[i*4+3]) for i in range(w*h)])
    return img


def decode_psmct16(raw, w, h):
    pixels = struct.unpack_from(f'<{w*h}H', raw, 0)
    out = []
    for v in pixels:
        a = (v >> 15) & 1
        r = (v >> 10) & 0x1f
        g = (v >> 5) & 0x1f
        b = v & 0x1f
        out.append((r * 255 // 31, g * 255 // 31, b * 255 // 31, 255 if a else 0))
    img = Image.new('RGBA', (w, h))
    img.putdata(out)
    return img


def decode_psmt8(raw, w, h, has_alpha):
    pal_bytes = 4 if has_alpha else 3
    pal_size = 256 * pal_bytes
    palette = raw[:pal_size]
    indices = raw[pal_size:pal_size + w * h]
    unswiz = unswizzle8(indices, w, h)

    pal = []
    for i in range(256):
        off = i * pal_bytes
        if has_alpha:
            pal.append((palette[off], palette[off+1], palette[off+2], palette[off+3]))
        else:
            pal.append((palette[off], palette[off+1], palette[off+2], 255))

    img = Image.new('RGBA', (w, h))
    img.putdata([pal[b] for b in unswiz])
    return img


# =====================================
# MAIN
# =====================================

def main():
    ensure_dir(OUTPUT_DIR)

    with open(INPUT_FILE, 'rb') as f:
        data = f.read()

    print(f'Loaded {len(data):,} bytes from {INPUT_FILE}')

    positions = []
    pos = 0
    while True:
        pos = data.find(b'GTEXT', pos)
        if pos == -1:
            break
        positions.append(pos)
        pos += 5

    print(f'Found {len(positions)} GTEXT tag matches')

    extracted = 0
    skipped_false_positive = 0
    skipped_unsupported = 0

    for seq, pos in enumerate(positions):
        base = pos + 8  # 5-byte tag + 3-byte alignment pad
        if data[base+8:base+12] != b'OBPR':
            skipped_false_positive += 1
            continue

        obpr_size = u32(data, base + 12)
        after_obpr = base + 16 + obpr_size
        tex_id = u32(data, base)
        width = u32(data, after_obpr + 8)
        height = u32(data, after_obpr + 12)

        if data[after_obpr + 20:after_obpr + 24] != b'ZIPN':
            skipped_false_positive += 1
            continue

        zipn_size = u32(data, after_obpr + 24)
        payload_off = after_obpr + 28
        w2, h2, fmt = struct.unpack_from('<3I', data, payload_off + 4)
        pixel_off = payload_off + 20

        if zipn_size <= 20:
            # empty/reference block, no pixel payload (declares dims but no data)
            skipped_false_positive += 1
            continue

        pixel_data = data[pixel_off:pixel_off + (zipn_size - 20)]

        base_fmt = fmt & 0xFFFF
        try:
            if base_fmt == 0:
                img = decode_psmct32(pixel_data, w2, h2)
                fmt_name = 'psmct32'
            elif base_fmt == 2:
                img = decode_psmct16(pixel_data, w2, h2)
                fmt_name = 'psmct16'
            elif base_fmt == 0x13:
                has_alpha = (fmt & 0x10000) == 0
                img = decode_psmt8(pixel_data, w2, h2, has_alpha)
                fmt_name = 'psmt8a' if has_alpha else 'psmt8'
            else:
                print(f'  [!] Unsupported fmt=0x{fmt:X} at 0x{pos:X} ({w2}x{h2})')
                skipped_unsupported += 1
                continue
        except Exception as e:
            print(f'  [!] Decode failed at 0x{pos:X}: {e}')
            skipped_unsupported += 1
            continue

        if FLIP_VERTICAL:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)

        fname = OUTPUT_DIR / f'gtext_ps2_{seq:04d}_id{tex_id:08x}_{w2}x{h2}_{fmt_name}.png'
        img.save(fname)
        extracted += 1

    print()
    print(f'Extracted           : {extracted}')
    print(f'False positives      : {skipped_false_positive}')
    print(f'Unsupported/failed   : {skipped_unsupported}')
    print(f'Output               : {OUTPUT_DIR}')


if __name__ == '__main__':
    main()

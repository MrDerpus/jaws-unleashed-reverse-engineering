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

import struct
from pathlib import Path

from PIL import Image


# =====================================
# CONFIG
# =====================================

name = 'FISH'
INPUT_FILE = f'../GAME_GDWs/ps2/DATA/{name}.GDE'
OUTPUT_DIR = Path(f'../textures/{name}_PS2/gtex')

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
#
# PS2 GTEX block layout (4-byte tag, distinct from the 5-byte GTEXT
# marker handled by rip_gtext_ps2.py):
#   GTEX [uint32 block_size]
#     [uint32 tex_id][uint32 flags]
#     [optional OBPR{ PROP{ prop_id=0x04000030, type="TEXC"/"TEXB" } }...]
#     [uint32 const/hash][uint32 zero][uint32 width][uint32 height][uint32 bpp]
#     ZIPN [uint32 size]
#       [uint32 remaining][uint32 width][uint32 height][uint32 format][uint32 unknown=1]
#       [pixel data]
#
# Roughly two-thirds of GTEX blocks in a given GDE are metadata-only
# (no ZIPN payload at all -- runtime-filled render targets / references,
# same as PC's GTEX system) and are skipped.
# =====================================

def main():
    ensure_dir(OUTPUT_DIR)

    with open(INPUT_FILE, 'rb') as f:
        data = f.read()

    print(f'Loaded {len(data):,} bytes from {INPUT_FILE}')

    positions = []
    pos = 0
    while True:
        pos = data.find(b'GTEX', pos)
        if pos == -1:
            break
        if data[pos:pos+5] != b'GTEXT':
            positions.append(pos)
        pos += 4

    print(f'Found {len(positions)} GTEX tag matches')

    extracted = 0
    skipped_no_pixels = 0
    skipped_unsupported = 0

    for seq, pos in enumerate(positions):
        block_size = u32(data, pos + 4)
        block_end = pos + 8 + block_size
        payload = pos + 8

        tex_id = u32(data, payload)
        p = payload + 8  # skip tex_id, flags

        if data[p:p+4] == b'OBPR':
            obpr_size = u32(data, p + 4)
            p += 8 + obpr_size

        # const(4) zero(4) width(4) height(4) bpp(4) precede the ZIPN tag
        if p + 24 > block_end or data[p+20:p+24] != b'ZIPN':
            skipped_no_pixels += 1
            continue

        width = u32(data, p + 8)
        height = u32(data, p + 12)

        zipn_pos = p + 20
        zipn_size = u32(data, zipn_pos + 4)
        sub_off = zipn_pos + 8
        w2, h2, fmt = struct.unpack_from('<3I', data, sub_off + 4)
        pixel_off = sub_off + 20

        if zipn_size <= 20:
            skipped_no_pixels += 1
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

        fname = OUTPUT_DIR / f'gtex_ps2_{seq:04d}_id{tex_id:08x}_{w2}x{h2}_{fmt_name}.png'
        img.save(fname)
        extracted += 1

    print()
    print(f'Extracted           : {extracted}')
    print(f'No pixel payload     : {skipped_no_pixels}')
    print(f'Unsupported/failed   : {skipped_unsupported}')
    print(f'Output               : {OUTPUT_DIR}')


if __name__ == '__main__':
    main()

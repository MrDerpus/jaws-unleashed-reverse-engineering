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

"""New textures and materials for a GDW (2026-10-03).

Texture block (the plain variant, 258/321 FISH textures; "GTEXT" was never a
tag: it's the GTEX tag followed by a size whose low byte is 0x54 = 'T'):
    GTEX [size]
      [tex_id][flags 1][stamp 0x0131F253][0][width][height][bpp 24|32]
      TGAN [tgan_size]
        [tgan_size - 4]
        18-byte TGA header (type 2, w, h, bpp, descriptor 0 for 24 / 8 for 32)
        pixels, bottom-up rows, BGR / BGRA
        26-byte TGA 2.0 footer: 8 zero bytes + "TRUEVISION-XFILE.\\0"
Material: a byte copy of a working GMAT with its ID and its TEXP base-texture
ID replaced. 1073 (FISH rock wall, TWOS 0) or 668 (FISH seaweed, TWOS 1 =
two-sided; otherwise identical sub-chunk set):
    GMAT [size] [gmat_id][flags 0x21] OBPR [0] [stamp] TEXP [n]['GTEX'][tex_id]... REFL BUMP COLS ...
"""
import struct

from PIL import Image

from gdw_grow import u32

TEX_STAMP = 0x0131F253
TGA_FOOTER = bytes(8) + b'TRUEVISION-XFILE.\0'


def pow2_size(img, max_side=1024):
    """Nearest power-of-two size per side (capped), like shipped textures."""
    def p2(n):
        n = max(1, min(n, max_side))
        lo = 1 << (n.bit_length() - 1)
        return lo if n - lo <= 2 * lo - n else 2 * lo
    return p2(img.width), p2(img.height)


def build_gtex(tex_id, img, resize=True, keep_alpha=True):
    """PIL image -> GTEX block bytes. Alpha (if kept) -> 32bpp, otherwise 24bpp."""
    has_alpha = keep_alpha and (img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info))
    img = img.convert('RGBA' if has_alpha else 'RGB')
    if resize and img.size != pow2_size(img):
        img = img.resize(pow2_size(img), Image.LANCZOS)
    w, h = img.size
    bpp = 32 if has_alpha else 24
    pixels = img.transpose(Image.FLIP_TOP_BOTTOM).tobytes('raw', 'BGRA' if has_alpha else 'BGR')
    tga = struct.pack('<BBB5sHHHHBB', 0, 0, 2, bytes(5), 0, 0, w, h, bpp, 8 if has_alpha else 0)
    tgan_payload_len = 4 + len(tga) + len(pixels) + len(TGA_FOOTER)
    payload = (struct.pack('<7I', tex_id, 1, TEX_STAMP, 0, w, h, bpp)
               + b'TGAN' + struct.pack('<II', tgan_payload_len, tgan_payload_len - 4)
               + tga + pixels + TGA_FOOTER)
    block = b'GTEX' + struct.pack('<I', len(payload)) + payload
    return block + bytes(-len(block) % 4), (w, h, bpp)


def find_block(d, tag, res_id):
    """Offset of the RSRC block `tag` with ID res_id in the primary archive."""
    r = d.find(b'RSRC')
    while u32(d, r + 8) != 0x0131F508:
        r = d.find(b'RSRC', r + 4)
    end, p = r + 8 + u32(d, r + 4), r + 20
    while p < end:
        if d[p:p + 4] == tag and u32(d, p + 8) == res_id:
            return p
        p = (p + 8 + u32(d, p + 4) + 3) & ~3
    raise KeyError(f'{tag.decode()} {res_id} not found')


def clone_gmat(d, src_id, new_id, tex_id):
    """Copy GMAT src_id with a new ID and TEXP base texture tex_id."""
    p = find_block(d, b'GMAT', src_id)
    block = bytearray(d[p:p + 8 + u32(d, p + 4)])
    block += bytes(-len(block) % 4)
    struct.pack_into('<I', block, 8, new_id)
    t = block.find(b'TEXP')
    assert t > 0 and u32(block, t + 8) >= 1 and block[t + 12:t + 16] == b'GTEX'
    struct.pack_into('<I', block, t + 16, tex_id)
    return bytes(block)

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

"""Dreamcast PVR texture decoder for Ecco: Defender (DC) and Sentinels .GDE files.

Library:  decode(buf) -> PIL RGBA image, buf starting at a 'PVRT' header.
          gde_textures(data) -> yields (name, image) for every GTEX in a GDE.
CLI:      python3 -I scripts/pvr_decode.py LEVEL.GDE OUTDIR [NAME_REGEX]

In these files a texture is GTEX [size][name_len][name] ... OBPR ... KAMU, and the
real PVRT image header follows KAMU (an earlier 'PVRT' inside OBPR is only a type
marker). Supported data types: 1/2 twiddled (+mips), 3/4 VQ (+mips), 9 rectangle,
13 twiddled rectangle, 16/17 small VQ (+mips). Pixel formats: 0 ARGB1555,
1 RGB565, 2 ARGB4444. Mipmapped VQ: the full-size index block starts after the
codebook and the smaller levels (1 + sum (s/2)^2 bytes) and is followed by
padding, so it is not at the end of the data. See docs/ecco_leftovers.md
"Smurfs video (2002)".
"""
import os
import re
import struct
import sys

from PIL import Image


def _px(fmt, v):
    if fmt == 0:   # ARGB1555
        return ((v >> 10 & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v & 31) * 255 // 31, 255 if v >> 15 else 0)
    if fmt == 1:   # RGB565
        return ((v >> 11 & 31) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v & 31) * 255 // 31, 255)
    if fmt == 2:   # ARGB4444
        return ((v >> 8 & 15) * 17, (v >> 4 & 15) * 17, (v & 15) * 17, (v >> 12 & 15) * 17)
    raise ValueError('pixel format %d' % fmt)


def _tw(x, y):
    """Dreamcast twiddle: interleave bits, y in the even positions."""
    r, b = 0, 0
    while x or y:
        r |= (y & 1) << b | (x & 1) << (b + 1)
        x >>= 1
        y >>= 1
        b += 2
    return r


def decode(buf):
    assert buf[:4] == b'PVRT', 'not a PVRT header'
    size = struct.unpack_from('<I', buf, 4)[0]
    fmt, typ = buf[8], buf[9]
    w, h = struct.unpack_from('<HH', buf, 12)
    data = buf[16:8 + size]
    out = [None] * (w * h)
    if typ in (1, 2, 0xD):                        # twiddled (+mips): full level is last
        need = w * h * 2
        d = data[len(data) - need:] if typ == 2 else data[:need]
        m = min(w, h)
        for y in range(h):
            for x in range(w):
                t = (x // m) + (y // m) * (w // m)
                i = t * m * m + _tw(x % m, y % m)
                out[y * w + x] = _px(fmt, struct.unpack_from('<H', d, i * 2)[0])
    elif typ in (3, 4, 0x10, 0x11):               # VQ: 2x2 blocks of 4 pixels, 8 bytes per entry
        nidx = (w // 2) * (h // 2)
        mip = 0 if typ in (3, 0x10) else 1 + sum((s // 2) ** 2 for s in (2 ** i for i in range(1, w.bit_length() - 1)))
        if typ in (3, 4):
            cbsize = 2048
        else:                                     # small VQ: shorter codebook, padded data
            cbsize = (len(data) - mip - nidx) // 64 * 64
        cb = data[:cbsize]
        idx = data[cbsize + mip: cbsize + mip + nidx]
        for by in range(h // 2):
            for bx in range(w // 2):
                e = idx[_tw(bx, by)]
                for k, (dx, dy) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
                    v = struct.unpack_from('<H', cb, (e * 4 + k) * 2)[0]
                    out[(by * 2 + dy) * w + bx * 2 + dx] = _px(fmt, v)
    elif typ == 9:                                # plain rectangle
        for i in range(w * h):
            out[i] = _px(fmt, struct.unpack_from('<H', data, i * 2)[0])
    else:
        raise ValueError('data type %d' % typ)
    im = Image.new('RGBA', (w, h))
    im.putdata(out)
    return im


def gde_textures(data):
    """Yield (name, image or exception) for every GTEX with a PVRT image."""
    p = 0
    while (p := data.find(b'GTEX', p + 1)) >= 0:
        sz, nl = struct.unpack_from('<II', data, p + 4)
        if not (0 < nl < 160 and 0 < sz < 4_000_000):
            continue
        end = p + 8 + sz
        name = data[p + 12:p + 12 + nl].rstrip(b'\0').decode('latin-1')
        k = data.find(b'KAMU', p, end)
        q = data.find(b'PVRT', k, end) if k > 0 else -1
        if q < 0:
            continue
        try:
            yield name, decode(data[q:end])
        except Exception as e:   # unsupported type: report, keep going
            yield name, e


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    src, out = argv[1], argv[2]
    pat = re.compile(argv[3], re.I) if len(argv) > 3 else None
    os.makedirs(out, exist_ok=True)
    data = open(src, 'rb').read()
    ok = bad = 0
    seen = set()
    for name, im in gde_textures(data):
        base = name.replace('\\', '/').split('/')[-1]
        if pat and not pat.search(name):
            continue
        if isinstance(im, Exception):
            bad += 1
            print(f'  [!] {name}: {im}')
            continue
        safe = re.sub(r'[^\w\-.]', '_', os.path.splitext(base)[0])
        fn, n = safe, 1
        while fn.lower() in seen:
            n += 1
            fn = f'{safe}_{n}'
        seen.add(fn.lower())
        im.save(os.path.join(out, fn + '.png'))
        ok += 1
    print(f'{ok} textures written to {out}, {bad} unsupported')


if __name__ == '__main__':
    main(sys.argv)

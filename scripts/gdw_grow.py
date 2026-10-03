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

"""Grow a top-level chunk of a GDW's primary archive and fix everything after it.

Resizing RSRC or BRTR shifts the rest of the primary archive, so:
  - the chunk's own size field,
  - FSIZ (its value is the SKIP chunk's file offset),
  - SKIP (0xFF padding, resized so FDIR stays on a 512-byte boundary),
  - every FDIR entry offset (embedded sub-archives after ENDF)
must all be patched. Confirmed in-game for RSRC (2026-07-17) and BRTR
(2026-10-03).
"""
import struct

PREAMBLE = 0x2C  # FSIZ is the first chunk


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def top_chunks(d):
    """{tag: offset} for the primary archive's top-level chunks (stops at ENDF)."""
    out, p = {}, PREAMBLE
    while p + 8 <= len(d):
        tag = d[p:p + 4].decode('latin1')
        out.setdefault(tag, p)
        if tag == 'ENDF':
            break
        p = (p + 8 + u32(d, p + 4) + 3) & ~3
    return out


def find_brtr(d):
    """Offset of the primary BRTR: the largest candidate with the right magic.
    A naive find() lands on coincidental matches inside RSRC in 8 GDWs."""
    cands, pos = [], 0
    while True:
        i = d.find(b'BRTR', pos)
        if i == -1:
            break
        if (i + 20 <= len(d) and u32(d, i + 8) == 0x01025024 and u32(d, i + 12) == 1
                and d[i + 16:i + 20] == b'PRPS'):
            cands.append((u32(d, i + 4), i))
        pos = i + 4
    return max(cands)[1]


def append_to_chunk(d, chunk_pos, blob):
    """Append blob (4-byte multiple) at the end of the chunk at chunk_pos.
    d is a bytearray, edited in place. Returns the blob's file offset."""
    assert len(blob) % 4 == 0
    at = chunk_pos + 8 + u32(d, chunk_pos + 4)
    assert at % 4 == 0
    payload = bytes(d[chunk_pos + 8:at]) + blob
    replace_chunk_payload(d, chunk_pos, payload)
    return at


def replace_chunk_payload(d, chunk_pos, payload):
    """Replace the payload of the top-level chunk at chunk_pos (it may grow or
    shrink by any multiple of 4) and fix FSIZ, SKIP and FDIR. d is a bytearray."""
    assert len(payload) % 4 == 0
    old_size = u32(d, chunk_pos + 4)
    assert (chunk_pos + 8 + old_size) % 4 == 0
    delta = len(payload) - old_size
    d[chunk_pos + 8:chunk_pos + 8 + old_size] = payload
    struct.pack_into('<I', d, chunk_pos + 4, len(payload))

    ch = top_chunks(d)
    skip, fdir_old = ch['SKIP'], ch['FDIR']
    old_skip_size = u32(d, skip + 4)
    struct.pack_into('<I', d, PREAMBLE + 8, skip)  # FSIZ == SKIP offset
    new_skip_size = (-(skip + 8)) % 512
    d[skip + 8:skip + 8 + old_skip_size] = b'\xFF' * new_skip_size
    struct.pack_into('<I', d, skip + 4, new_skip_size)
    fdir = skip + 8 + new_skip_size
    assert d[fdir:fdir + 4] == b'FDIR' and fdir % 512 == 0
    shift = fdir - (fdir_old - delta)  # how far everything after FDIR moved
    for k in range(u32(d, fdir + 12)):
        e = fdir + 16 + 32 * k
        struct.pack_into('<I', d, e, u32(d, e) + shift)
        assert d[u32(d, e):u32(d, e) + 4] == b'GDED', f'FDIR entry {k} does not point at GDED'

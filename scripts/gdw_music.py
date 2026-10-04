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

"""Replace a level's music (2026-10-04).

    python3 scripts/gdw_music.py IN.GDW OUT.GDW none|DIR

Level music is a sound bank node with group name 'Music' (PROP 0x08001939;
FISH: 'SndMusic') naming four tracks (PROP 0x0800193A): Calm_aw (calm, above
water), Calm_uw (calm, underwater), Susp (suspense), Act (action). Its GSFX
list (PROP 0x0800193B, ['GSFX'][id] per name, same order) points at GSFX
blocks, each pointing at one GSMP sample (['GSMP'][id] near its end). FISH's
four samples are 16-bit stereo, 22050 Hz, 117.1 s each.

GSMP sample block (plain variant, category 3 = music):
    [id][flags 1][stamp 0x013131B1][category][rate][n bytes] PCM[n]
    [loop start frame][loop end frame]      (music: 0 and frames - 1)
(SFX use 0, 0 = no loop; 2 extra zero bytes when n % 4 == 2.)

'none' replaces each track with one second of silence (saves ~41 MB in
FISH); a DIR replaces them with audio files named after TRACK_FILES (any
format ffmpeg reads: calm_above.mp3, suspense.ogg, ...). A missing file falls
back to calm_above; without that either, the track is left as it was. The
audio is converted to 16-bit stereo at RATE Hz and loops over its whole
length. Sample IDs and the bank stay the same, so nothing else changes.
"""
import glob
import os
import struct
import subprocess
import sys

from gdw_grow import find_brtr, replace_chunk_payload, top_chunks, u32

P_GROUP, P_NAMES, P_GSFX = 0x08001939, 0x0800193A, 0x0800193B
TRACK_FILES = {'Calm_aw': 'calm_above', 'Calm_uw': 'calm_under', 'Susp': 'suspense', 'Act': 'action'}
FALLBACK = 'calm_above'
RATE, CHANNELS = 22050, 2
STAMP, CATEGORY_MUSIC = 0x013131B1, 3


def music_bank(d):
    """[(track name, GSFX id)] of the level's 'Music' sound bank."""
    b = find_brtr(d)
    end = b + 8 + u32(d, b + 4)
    want = b'PROP' + struct.pack('<III', 14, P_GROUP, 6) + b'Music\0'
    i = d.find(want, b, end)
    if i < 0:
        raise SystemExit("no sound bank with group 'Music' in this level")
    c = d.rfind(b'CHBR', b, i)                  # the bank's node
    q = c + 16
    while d[q:q + 4] != b'PRPS':
        q = (q + 8 + u32(d, q + 4) + 3) & ~3
    props, r, prps_end = {}, q + 8, q + 8 + u32(d, q + 4)
    while r < prps_end and d[r:r + 4] == b'PROP':
        s = u32(d, r + 4)
        props[u32(d, r + 8)] = d[r + 12:r + 8 + s]
        r += 8 + ((s + 3) & ~3)
    raw, names, o = props[P_NAMES], [], 4
    for _ in range(u32(raw, 0)):
        n = u32(raw, o)
        names.append(raw[o + 4:o + 4 + n].split(b'\0')[0].decode('latin1'))
        o += 4 + ((n + 3) & ~3)
    lst = props[P_GSFX]
    gsfx = [u32(lst, 8 + 8 * k) for k in range(u32(lst, 0))]
    return list(zip(names, gsfx))


def rsrc_blocks(d):
    r = top_chunks(d)['RSRC']
    p, end, out = r + 20, r + 8 + u32(d, r + 4), []
    while p + 8 <= end:
        nxt = (p + 8 + u32(d, p + 4) + 3) & ~3
        out.append((bytes(d[p:p + 4]), u32(d, p + 8), p, min(nxt, end)))
        p = nxt
    return r, out


def gsmp_block(sample_id, pcm, rate=RATE, channels=CHANNELS):
    frames = len(pcm) // (2 * channels)
    body = struct.pack('<6I', sample_id, 1, STAMP, CATEGORY_MUSIC, rate, len(pcm)) + pcm
    body += struct.pack('<II', 0, max(frames - 1, 0))
    blk = b'GSMP' + struct.pack('<I', len(body)) + body
    return blk + b'\0' * (-len(blk) % 4)


def decode(path):
    """Any audio file -> 16-bit little-endian PCM, RATE Hz, CHANNELS channels."""
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ar', str(RATE), '-ac', str(CHANNELS),
                        '-f', 's16le', '-'], capture_output=True)
    if r.returncode or not r.stdout:
        raise SystemExit(f'ffmpeg could not read {path}: {r.stderr.decode(errors="replace")[-300:]}')
    return r.stdout


def find_file(folder, stem):
    hits = sorted(f for f in glob.glob(os.path.join(folder, stem + '.*')) if not f.endswith('~'))
    return hits[0] if hits else None


def replace_music(d, mode):
    """mode: 'keep', 'none' or a folder of audio files. Returns new bytes."""
    if mode == 'keep':
        return d
    bank = music_bank(d)
    r, blocks = rsrc_blocks(d)
    gsfx = {i: (a, z) for t, i, a, z in blocks if t == b'GSFX'}
    new = {}   # GSMP id -> new block
    for name, g in bank:
        a, z = gsfx[g]
        k = d.find(b'GSMP', a + 8, z)
        sid = u32(d, k + 4)
        if mode == 'none':
            pcm = bytes(RATE * CHANNELS * 2)
            src = 'silence'
        else:
            stem = TRACK_FILES.get(name, name.lower())
            path = find_file(mode, stem) or find_file(mode, FALLBACK)
            if path is None:
                print(f'music {name}: no {stem}.* or {FALLBACK}.* in {mode}, left as it was')
                continue
            pcm = decode(path)
            src = os.path.basename(path)
        new[sid] = gsmp_block(sid, pcm)
        print(f'music {name} (GSMP {sid}): {src}, {len(pcm) / (RATE * CHANNELS * 2):.1f} s')
    payload = bytearray(d[r + 8:r + 20])
    for t, i, a, z in blocks:
        payload += new[i] if t == b'GSMP' and i in new else d[a:z]
    out = bytearray(d)
    replace_chunk_payload(out, r, bytes(payload))
    return bytes(out)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    src, dst, mode = sys.argv[1:]
    out = replace_music(open(src, 'rb').read(), mode)
    open(dst, 'wb').write(out)
    print(f'wrote {dst} ({len(out) / 1e6:.1f} MB)')

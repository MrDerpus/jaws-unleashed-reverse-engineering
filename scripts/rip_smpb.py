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
import wave
from pathlib import Path

# =====================================
# CONFIG
# =====================================

# Set to None to run across all GDWs, or a specific stem like 'FISH'
NAME = None

INPUT_DIR  = Path('../GAME_GDWs')
OUTPUT_DIR = Path('../audio')


# =====================================
# HELPERS
# =====================================

def read_u32(data, offset):
    try:
        return struct.unpack('<I', data[offset:offset + 4])[0]
    except:
        return None


def extract_smpb_blocks(data, stem):
    results = []
    offset = 0
    while True:
        pos = data.find(b'GSMP', offset)
        if pos == -1:
            break

        block_size = read_u32(data, pos + 4)
        if not block_size or block_size < 32 or block_size > 20_000_000:
            offset = pos + 4
            continue

        sample_id = read_u32(data, pos + 8)
        flags     = read_u32(data, pos + 12)

        # SMPB-type blocks have OBPR embedded where hash/category normally live
        if data[pos + 16:pos + 20] != b'OBPR':
            offset = pos + 4
            continue

        obpr_size = read_u32(data, pos + 20)
        if not obpr_size or obpr_size > block_size:
            offset = pos + 4
            continue

        # Secondary header follows OBPR: [magic 4b][field 4b][sample_rate 4b][byte_count 4b][pad 4b]
        sec_hdr = pos + 16 + 8 + obpr_size
        sample_rate = read_u32(data, sec_hdr + 8)
        byte_count  = read_u32(data, sec_hdr + 12)

        if not sample_rate or sample_rate > 100_000:
            offset = pos + 4
            continue
        if not byte_count or byte_count > block_size:
            offset = pos + 4
            continue

        audio_start = sec_hdr + 20
        raw = data[audio_start : audio_start + byte_count]

        if len(raw) < 64:
            offset = pos + 4
            continue

        dur = byte_count / (sample_rate * 2)
        results.append((sample_id, flags, sample_rate, byte_count, dur, raw))
        offset = pos + 4

    return results


# =====================================
# MAIN
# =====================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if NAME:
        gdw_paths = [INPUT_DIR / f'{NAME}.GDW']
    else:
        gdw_paths = sorted(INPUT_DIR.glob('*.GDW'))

    total = 0

    for gdw_path in gdw_paths:
        if not gdw_path.exists():
            print(f'[!] Not found: {gdw_path}')
            continue

        stem = gdw_path.stem
        with open(gdw_path, 'rb') as f:
            data = f.read()

        blocks = extract_smpb_blocks(data, stem)
        print(f'{stem}: {len(blocks)} SMPB blocks')

        for sample_id, flags, sample_rate, byte_count, dur, raw in blocks:
            fname = f'{stem}_smpb_id{sample_id:04d}_{sample_rate}hz_{dur:.2f}s.wav'
            out_path = OUTPUT_DIR / fname
            with wave.open(str(out_path), 'w') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sample_rate)
                w.writeframes(raw)
            total += 1

    print(f'\nDone. Extracted {total} SMPB audio files to {OUTPUT_DIR}')


if __name__ == '__main__':
    main()

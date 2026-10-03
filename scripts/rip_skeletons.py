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

"""
Extract skeletal animation data from SKEL chunks in RSRC.

Each SKEL block is one character/creature skeleton: a bind-pose reference
mesh (VERT/NORM), per-vertex bone skinning weights (WGHT), an optional named
animation-clip dictionary (ANIM), and a recursive bone hierarchy (BONE, with
CHLD/BROT children) where every bone carries its own bind-pose local
transform (MTOB + TRAN) and a shared-length stream of per-frame rotation
quaternions (ROTS). All bones in a skeleton share one contiguous quaternion
"pool" of length N frames; ANIM slices that pool into named clips via
[start_frame, end_frame] pairs (frame 0 is the shared bind/rest frame,
outside any named clip).

SKEL payload layout:
    [uint32 skel_id][uint32 count=1][uint32 magic]
    [unknown blob, undecoded — precedes VERT, length varies]
    VERT   [uint32 vert_count][vert_count * float32 xyz]   -- bind-pose positions
    NORM   [vert_count * float32 xyz]                       -- bind-pose normals (no count header)
    WGHT   [vert_count * (4x int32 bone_idx (-1=unused), 4x float32 weight)]
    ANIM   optional: [uint32 clip_count][uint32 unknown]
                      clip_count * [uint32 namelen (incl. NUL)][name, NUL-padded to 4]
                      clip_count * uint32 start_frame
                      clip_count * uint32 end_frame
    BONE   recursive bone tree (see parse_bone_node)

Bone node (BONE/CHLD/BROT payload, all three share this grammar):
    MTOB [48]  -- 4x3 float32 bind-pose local transform (3x3 basis + translation),
                  same column-major layout as BRTR PROP 0x080017DA
    TRAN [12]  -- 3x float32, small local offset, role unconfirmed (usually near-zero)
    ROTS [N*16]-- N unit quaternions (x,y,z,w), one per frame in the shared pool
    then zero or more child nodes, tagged CHLD or BROT (no observed semantic
    difference — a bone with two children uses one of each; deeper siblings
    reuse whichever tag is available at that nesting level).

Run from project root:
    python3 scripts/rip_skeletons.py
"""

import struct
import json
from pathlib import Path

# ============================
# CONFIG
# ============================

NAME       = 'FISH'
INPUT_FILE = f'GAME_GDWs/{NAME}.GDW'
OUTPUT_DIR = Path('skeletons') / NAME

CONTAINER_TAGS = (b'BONE', b'CHLD', b'BROT')


# ============================
# HELPERS
# ============================

def u32(data, off):
    return struct.unpack_from('<I', data, off)[0]

def read_chunk(buf, p):
    """Read [tag][uint32 size][payload] at p, return (tag, payload, next_p_aligned_to_4)."""
    tag = buf[p:p + 4]
    sz = u32(buf, p + 4)
    payload = buf[p + 8:p + 8 + sz]
    end = p + 8 + sz
    if end % 4:
        end += 4 - (end % 4)
    return tag, payload, end


# ============================
# BONE HIERARCHY
# ============================

def parse_bone_node(buf, bone_index_counter):
    """Parse one bone node's payload (MTOB+TRAN+ROTS+children). Returns dict."""
    p = 0
    tag, mtob_payload, p = read_chunk(buf, p)
    assert tag == b'MTOB', f'expected MTOB, got {tag}'
    mtob = struct.unpack('<12f', mtob_payload)

    tag, tran_payload, p = read_chunk(buf, p)
    assert tag == b'TRAN', f'expected TRAN, got {tag}'
    tran = struct.unpack('<3f', tran_payload)

    tag, rots_payload, p = read_chunk(buf, p)
    assert tag == b'ROTS', f'expected ROTS, got {tag}'
    frame_count = len(rots_payload) // 16
    rotations = [struct.unpack_from('<4f', rots_payload, i * 16) for i in range(frame_count)]

    bone_index = bone_index_counter[0]
    bone_index_counter[0] += 1

    children = []
    n = len(buf)
    while p + 8 <= n:
        tag = buf[p:p + 4]
        if tag not in (b'CHLD', b'BROT'):
            break
        sz = u32(buf, p + 4)
        child_payload = buf[p + 8:p + 8 + sz]
        children.append(parse_bone_node(child_payload, bone_index_counter))
        p += 8 + sz
        if p % 4:
            p += 4 - (p % 4)

    return {
        'bone_index': bone_index,
        'mtob': mtob,        # 12 floats: 3x3 basis (col-major) + translation
        'tran': tran,        # 3 floats: small local offset, role unconfirmed
        'frame_count': frame_count,
        'rotations': rotations,  # list of (x,y,z,w) unit quaternions, one per shared frame
        'children': children,
    }


# ============================
# ANIM CLIP DICTIONARY
# ============================

def parse_anim(payload):
    count, _unknown = struct.unpack_from('<II', payload, 0)
    p = 8
    names = []
    for _ in range(count):
        namelen = u32(payload, p)
        p += 4
        name = payload[p:p + namelen].rstrip(b'\x00').decode('ascii', 'replace')
        p += namelen
        if p % 4:
            p += 4 - (p % 4)
        names.append(name)
    starts = struct.unpack_from(f'<{count}I', payload, p)
    p += count * 4
    ends = struct.unpack_from(f'<{count}I', payload, p)
    return [
        {'name': n, 'start_frame': s, 'end_frame': e}
        for n, s, e in zip(names, starts, ends)
    ]


# ============================
# WGHT / VERT / NORM
# ============================

def parse_vert(payload):
    count = u32(payload, 0)
    return [struct.unpack_from('<3f', payload, 4 + i * 12) for i in range(count)]

def parse_norm(payload, count):
    return [struct.unpack_from('<3f', payload, i * 12) for i in range(count)]

def parse_wght(payload, count):
    out = []
    for i in range(count):
        off = i * 32
        idx = struct.unpack_from('<4i', payload, off)
        wts = struct.unpack_from('<4f', payload, off + 16)
        # weight slots are only meaningful where the paired index != -1
        influences = [(bi, w) for bi, w in zip(idx, wts) if bi != -1]
        out.append(influences)
    return out


# ============================
# SKEL PARSE
# ============================

def find_skel_blocks(data, rsrc_lo, rsrc_hi):
    positions = []
    pos = rsrc_lo
    while True:
        pos = data.find(b'SKEL', pos, rsrc_hi)
        if pos == -1:
            break
        positions.append(pos)
        pos += 1
    return positions

def parse_skel(data, pos):
    size = u32(data, pos + 4)
    payload = data[pos + 8:pos + 8 + size]

    skel_id, count, magic = struct.unpack_from('<III', payload, 0)

    vert_pos = payload.find(b'VERT')
    norm_pos = payload.find(b'NORM')
    wght_pos = payload.find(b'WGHT')
    anim_pos = payload.find(b'ANIM')
    bone_pos = payload.find(b'BONE')
    if -1 in (vert_pos, norm_pos, wght_pos, bone_pos):
        return None  # not a real SKEL block (false-positive tag match)

    _, vert_payload, _ = read_chunk(payload, vert_pos)
    positions = parse_vert(vert_payload)

    _, norm_payload, _ = read_chunk(payload, norm_pos)
    normals = parse_norm(norm_payload, len(positions))

    _, wght_payload, _ = read_chunk(payload, wght_pos)
    weights = parse_wght(wght_payload, len(positions))

    animations = []
    if anim_pos != -1:
        _, anim_payload, _ = read_chunk(payload, anim_pos)
        animations = parse_anim(anim_payload)

    _, bone_payload, _ = read_chunk(payload, bone_pos)
    bone_index_counter = [0]
    skeleton = parse_bone_node(bone_payload, bone_index_counter)

    return {
        'skel_id': skel_id,
        'file_offset': pos,
        'vertex_count': len(positions),
        'positions': positions,
        'normals': normals,
        'weights': weights,
        'bone_count': bone_index_counter[0],
        'animations': animations,
        'skeleton': skeleton,
    }


# ============================
# MAIN
# ============================

def main():
    data = Path(INPUT_FILE).read_bytes()

    rsrc_pos = data.find(b'RSRC')
    rsrc_size = u32(data, rsrc_pos + 4)
    rsrc_lo = rsrc_pos + 8
    rsrc_hi = rsrc_lo + rsrc_size
    print(f'RSRC @ 0x{rsrc_pos:X}  size={rsrc_size:,}')

    skel_positions = find_skel_blocks(data, rsrc_lo, rsrc_hi)
    print(f'Found {len(skel_positions)} SKEL tag matches')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary = []
    for pos in skel_positions:
        skel = parse_skel(data, pos)
        if skel is None:
            print(f'  0x{pos:X}: false-positive tag match, skipped')
            continue

        clip_names = [a['name'] for a in skel['animations']]
        print(f"  0x{pos:X}: skel_id={skel['skel_id']} bones={skel['bone_count']} "
              f"verts={skel['vertex_count']} clips={len(clip_names)}")

        out_path = OUTPUT_DIR / f"skel_{skel['skel_id']:05d}.json"
        with open(out_path, 'w') as f:
            json.dump(skel, f)

        summary.append({
            'skel_id': skel['skel_id'],
            'file_offset': skel['file_offset'],
            'bone_count': skel['bone_count'],
            'vertex_count': skel['vertex_count'],
            'clip_names': clip_names,
            'file': str(out_path),
        })

    with open(OUTPUT_DIR / '_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f'\nExtracted {len(summary)} skeletons to {OUTPUT_DIR}/')


if __name__ == '__main__':
    main()

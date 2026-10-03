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

Each SKEL block is one skinned character/creature: a rest-pose mesh
(VERT/NORM), per-vertex bone weights (WGHT), an optional named clip table
(ANIM), per-frame root motion, and a bone tree (BONE) whose bones each carry
an inverse rest matrix (MTOB), a local translation (TRAN) and one rotation
quaternion per frame (ROTS). All bones share one pool of N frames; ANIM
slices it into named clips.

Skinning, confirmed against Jaws.exe (2026-10-03) and numerically: skinning
the FISH shark's VERT mesh with frame 0 reproduces its shipped GMDL mesh
(GWside, mesh 1890) with zero error.
    local_i   = [ R(q_i[frame])^T | TRAN_i ]      (R = standard x,y,z,w matrix)
    world_i   = world_parent(i) @ local_i          (root: world = local)
    skin_i    = world_i @ MTOB_i                   (MTOB = inverse rest matrix)
    v'        = sum_i w_i * skin_i @ v             (v = VERT rest position)
Bone rest pose (where VERT lives) = inverse(MTOB). Frame 0 is the pose baked
into the GMDL render mesh. Engine code: bone loader FUN_006F4F00, SKEL
loader FUN_006F47D0, bone order FUN_006F46D0/FUN_006F5140, pose
FUN_006F5600, skinning FUN_006F63F0, frame stepping FUN_006F5EB0.

SKEL payload layout:
    [uint32 skel_id][uint32 flags][uint32 version]
    [uint32 frame_count]
    [uint32 morph_frame_count]              (only when version > 0x13130F1)
    frame_count * float32 xyz               root motion: per-frame displacement,
                                            accumulated onto the object (model space)
    frame_count * float32 xyz               second per-frame track (version >= 0x1317CBA);
                                            role unknown, looks like running position
    VERT   [uint32 vert_count][vert_count * float32 xyz]   rest-pose positions
    NORM   [vert_count * float32 xyz]                       rest-pose normals
    MORF   optional: morph_frame_count * vert_count * xyz   (vertex animation; not
                                            seen in FISH, not extracted)
    WGHT   [vert_count * (4x int32 bone (-1 unused), 4x float32 weight)]
    ANIM   optional: [uint32 clip_count][uint32 unknown]
                      clip_count * [uint32 namelen (incl. NUL)][name, NUL-padded to 4]
                      clip_count * uint32 start_frame, clip_count * uint32 end_frame
    BONE   bone tree (root bone node)

Bone node (BONE/CHLD/BROT payload):
    MTOB [48]  inverse rest matrix, 4x3 column-major (3x3 basis + translation)
    TRAN [12]  local translation relative to the parent bone
    ROTS [N*16] N quaternions (x, y, z, w), local rotation per frame
    CHLD       first child (this bone is its parent)
    BROT       next sibling (shares this bone's parent). Earlier versions of this
               script treated BROT as a child, which put bones on wrong parents.

Bone indices (WGHT, and the 'bones' list written here) follow the engine's
order: root, then for each bone its whole sibling chain before its child.

Output: skeletons/<NAME>/skel_<id>.json with 'bones' (flat, engine order:
parent, inv_bind, tran, rotations), 'positions'/'normals'/'weights',
'animations', 'root_motion', 'meshes' (BRTR nodes that use this skeleton via
PROP 0x080018FF, with their GMDL mesh id), plus _summary.json.

Run from project root:
    python3 scripts/rip_skeletons.py [NAME]      (default FISH)
"""

import json
import struct
import sys
from pathlib import Path

# __file__ is missing when run through the exec() loop in CLAUDE.md
sys.path.insert(0, str(Path(globals().get('__file__', 'scripts/rip_skeletons.py')).resolve().parent))
import brtr_scene_graph

# ============================
# CONFIG
# ============================

NAME       = sys.argv[1] if len(sys.argv) > 1 and __name__ == '__main__' and sys.argv[1].isupper() else 'FISH'
INPUT_FILE = f'GAME_GDWs/{NAME}.GDW'
OUTPUT_DIR = Path('skeletons') / NAME

PROP_SKEL  = 0x080018FF   # skeleton-model node -> ['SKEL'][skel id]


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

def parse_bones(buf):
    """Parse the BONE tree into a flat list in the engine's bone order.
    Each bone: parent, first_child, next_sibling (indices or -1), inv_bind
    (MTOB, 12 floats), tran, rotations."""
    raw = []                                  # file order

    def node(payload, parent):
        me = len(raw)
        rec = {'parent': parent, 'child': None, 'sibling': None}
        raw.append(rec)
        last_child = None
        p = 0
        while p + 8 <= len(payload):
            tag, body, nxt = read_chunk(payload, p)
            if tag == b'MTOB':
                rec['inv_bind'] = list(struct.unpack('<12f', body))
            elif tag == b'TRAN':
                rec['tran'] = list(struct.unpack('<3f', body))
            elif tag == b'ROTS':
                rec['rotations'] = [list(struct.unpack_from('<4f', body, i * 16))
                                    for i in range(len(body) // 16)]
            elif tag == b'CHLD':
                rec['child'] = node(body, me)
            elif tag == b'BROT':
                rec['sibling'] = node(body, parent)
            p = nxt
        return me

    node(buf, -1)

    order = []                                # Jaws.exe FUN_006F46D0 / FUN_006F5140

    def visit(i):
        while i is not None:
            order.append(i)
            if raw[i]['sibling'] is not None:
                visit(raw[i]['sibling'])
            i = raw[i]['child']

    order.append(0)
    if raw[0]['sibling'] is not None:
        visit(raw[0]['sibling'])
    if raw[0]['child'] is not None:
        visit(raw[0]['child'])
    new = {old: k for k, old in enumerate(order)}

    def remap(i):
        return -1 if i is None or i < 0 else new[i]

    return [{
        'index': k,
        'parent': remap(raw[old]['parent']),
        'first_child': remap(raw[old]['child']),
        'next_sibling': remap(raw[old]['sibling']),
        'inv_bind': raw[old]['inv_bind'],
        'tran': raw[old]['tran'],
        'rotations': raw[old]['rotations'],
    } for k, old in enumerate(order)]


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

    skel_id, flags, version = struct.unpack_from('<III', payload, 0)

    vert_pos = payload.find(b'VERT')
    norm_pos = payload.find(b'NORM')
    wght_pos = payload.find(b'WGHT')
    anim_pos = payload.find(b'ANIM')
    bone_pos = payload.find(b'BONE')
    if -1 in (vert_pos, norm_pos, wght_pos, bone_pos):
        return None  # not a real SKEL block (false-positive tag match)

    # header + per-frame tracks (FUN_006F47D0)
    p = 12
    frame_count = u32(payload, p); p += 4
    morph_frames = 0
    if version > 0x13130F1:
        morph_frames = u32(payload, p); p += 4
    tracks = 2 if version >= 0x1317CBA else 1
    # A real SKEL's per-frame tracks end exactly where VERT starts; this also
    # rejects coincidental 'SKEL' byte matches elsewhere in RSRC.
    if p + 12 * frame_count * tracks != vert_pos:
        return None
    root_motion = [list(struct.unpack_from('<3f', payload, p + 12 * i)) for i in range(frame_count)]
    p += 12 * frame_count
    track_b = []
    if tracks == 2:
        track_b = [list(struct.unpack_from('<3f', payload, p + 12 * i)) for i in range(frame_count)]

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
    bones = parse_bones(bone_payload)

    return {
        'skel_id': skel_id,
        'file_offset': pos,
        'version': version,
        'frame_count': frame_count,
        'morph_frame_count': morph_frames,
        'vertex_count': len(positions),
        'positions': positions,
        'normals': normals,
        'weights': weights,
        'bone_count': len(bones),
        'bones': bones,
        'animations': animations,
        'root_motion': root_motion,
        'track_b': track_b,
    }


def skel_users(data):
    """{skel_id: [{node_id, node_name, mesh_id}]} from BRTR nodes carrying
    PROP 0x080018FF = ['SKEL'][id] (e.g. FISH GWside -> SKEL 1766, GMDL 1890)."""
    nodes, _, _ = brtr_scene_graph.load_nodes(data)
    users = {}
    for nid, n in nodes.items():
        v = n['props'].get(PROP_SKEL)
        if v is None or v[:4] != b'SKEL':
            continue
        m = n['props'].get(brtr_scene_graph.PROP_MESH)
        mesh_id = u32(m, 4) if m is not None and m[:4] == b'GMDL' else None
        users.setdefault(u32(v, 4), []).append(
            {'node_id': nid, 'node_name': n['name'], 'mesh_id': mesh_id})
    return users


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
    users = skel_users(data)

    summary = []
    for pos in skel_positions:
        skel = parse_skel(data, pos)
        if skel is None:
            print(f'  0x{pos:X}: false-positive tag match, skipped')
            continue

        skel['meshes'] = users.get(skel['skel_id'], [])
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
            'meshes': skel['meshes'],
            'file': str(out_path),
        })

    with open(OUTPUT_DIR / '_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f'\nExtracted {len(summary)} skeletons to {OUTPUT_DIR}/')


if __name__ == '__main__':
    main()

"""
Resolve BRTR CHBR parent-child hierarchy to true world-space positions.

CHBR nodes nest physically inside a parent CHBR's payload (after its PRPS
block, before the parent's declared end) rather than only being referenced
via the root's PROP 0x080003C7 child-ID list. A nested node's own
PROP 0x080017DA transform is LOCAL to its parent, not world space — reading
it directly (as rip_brtr_scene.py does) gives misleading positions for any
non-top-level node (frequently near-(0,0,0) regardless of true location).

This script walks the tree while composing each node's transform with its
full ancestor chain (world = parent_world âˆ˜ local), producing a correct
world-space position for every node, including deeply nested ones.

Validated 2026-07-16 on FISH.GDW:
  - Resolved node count (2782) exactly matches the known flat CHBR tag count.
  - Known top-level landmark (torzs, a ship hull) and a nested node
    (cadillacbody) resolve to positions ~520 units apart, consistent with
    them being in the same visible cluster in-game.
  - A nested WhaleCarcass Body group resolves near (60,-20,105); a separate
    top-level "Kis_Halaszhajo" (small fishing boat) cluster resolves to the
    exact same position — confirms the composed coordinates line up with
    real in-game landmarks.

Run from project root:
  python3 scripts/resolve_brtr_hierarchy.py
"""

import struct
import json
from pathlib import Path

NAME       = 'FISH'
INPUT_FILE = f'GAME_GDWs/{NAME}.GDW'
OUTPUT_DIR = Path('scenes')


def u32(data, off): return struct.unpack_from('<I', data, off)[0]
def align4(n): return (n + 3) & ~3

def parse_name(data, off, sz):
    if sz < 4: return ''
    slen = u32(data, off)
    if not slen or slen > sz - 4: return ''
    return data[off+4:off+4+slen].decode('utf-8', 'replace').strip('\x00').strip()


IDENTITY_R = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
IDENTITY_T = (0.0, 0.0, 0.0)


def mat_from_xf(xf):
    R = ((xf[0], xf[1], xf[2]), (xf[3], xf[4], xf[5]), (xf[6], xf[7], xf[8]))
    T = (xf[9], xf[10], xf[11])
    return R, T

def apply_R(R, v):
    x, y, z = v
    c0, c1, c2 = R
    return (c0[0]*x + c1[0]*y + c2[0]*z,
            c0[1]*x + c1[1]*y + c2[1]*z,
            c0[2]*x + c1[2]*y + c2[2]*z)

def apply_full(R, T, p):
    wx, wy, wz = apply_R(R, p)
    return (wx + T[0], wy + T[1], wz + T[2])

def compose(parentR, parentT, childR, childT):
    """world = parent(child(p)) -- standard affine composition."""
    newR = (apply_R(parentR, childR[0]), apply_R(parentR, childR[1]), apply_R(parentR, childR[2]))
    newT = apply_full(parentR, parentT, childT)
    return newR, newT


def parse_prps_props(data, prps_payload_start, prps_payload_end):
    props = {}
    p = prps_payload_start
    while p < prps_payload_end - 8:
        if data[p:p+4] != b'PROP':
            p += 1
            continue
        psz = u32(data, p+4)
        pid = u32(data, p+8)
        props[pid] = (p+12, psz-4)
        p += 8 + psz
    return props


def walk(data, start, end, parentR, parentT, parent_id, depth, results):
    pos = start
    while pos < end:
        if pos + 8 > end:
            break
        tag = data[pos:pos+4]
        sz  = u32(data, pos+4)
        payload_start = pos + 8
        payload_end   = payload_start + sz
        if tag == b'CHBR':
            node_id = u32(data, payload_start+4)
            inner   = payload_start + 8
            if data[inner:inner+4] == b'PRPS':
                prps_sz = u32(data, inner+4)
                prps_payload_start = inner + 8
                prps_payload_end   = prps_payload_start + prps_sz
                children_start = align4(prps_payload_end)

                props = parse_prps_props(data, prps_payload_start, prps_payload_end)

                name = ''
                if 0x080017D8 in props:
                    off, psz = props[0x080017D8]
                    name = parse_name(data, off, psz)

                local_R, local_T = IDENTITY_R, IDENTITY_T
                if 0x080017DA in props:
                    off, psz = props[0x080017DA]
                    if psz >= 48:
                        xf = struct.unpack_from('<12f', data, off)
                        local_R, local_T = mat_from_xf(xf)

                mesh_id = None
                if 0x08001873 in props:
                    off, psz = props[0x08001873]
                    if psz >= 8:
                        mesh_id = u32(data, off+4)

                world_R, world_T = compose(parentR, parentT, local_R, local_T)

                results[node_id] = {
                    'name':      name,
                    'local_pos': local_T,
                    'world_pos': world_T,
                    'mesh_id':   mesh_id,
                    'parent_id': parent_id,
                    'depth':     depth,
                }

                walk(data, children_start, payload_end, world_R, world_T, node_id, depth+1, results)
        pos = align4(payload_end)


def main():
    print(f'Loading {INPUT_FILE}...')
    data = open(INPUT_FILE, 'rb').read()

    brtr_pos = data.find(b'BRTR')
    brtr_sz  = u32(data, brtr_pos+4)
    brtr_payload_start = brtr_pos + 8
    brtr_payload_end   = min(brtr_payload_start + brtr_sz, len(data))
    print(f'BRTR @ 0x{brtr_pos:X} size={brtr_sz:,}')

    p = brtr_payload_start + 8  # skip magic(4) + root_count(4)
    assert data[p:p+4] == b'PRPS', 'expected root PRPS at start of BRTR'
    root_sz = u32(data, p+4)
    root_payload_start = p + 8
    root_payload_end   = root_payload_start + root_sz
    root_props = parse_prps_props(data, root_payload_start, root_payload_end)

    root_R, root_T = IDENTITY_R, IDENTITY_T
    if 0x080017DA in root_props:
        off, psz = root_props[0x080017DA]
        if psz >= 48:
            xf = struct.unpack_from('<12f', data, off)
            root_R, root_T = mat_from_xf(xf)

    top_children_start = align4(root_payload_end)

    results = {}
    walk(data, top_children_start, brtr_payload_end, root_R, root_T, None, 0, results)
    print(f'Resolved {len(results)} nodes')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f'{NAME}_resolved_hierarchy.json'
    with open(out_path, 'w') as f:
        json.dump({str(k): v for k, v in results.items()}, f, indent=1)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()

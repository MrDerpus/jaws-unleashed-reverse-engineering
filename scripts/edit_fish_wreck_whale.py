"""
One-off BRTR edit for FISH.GDW: rotate the ship wreck ("torzs", node 424) -90
degrees around the world Y (up) axis, and scale the whale carcass
("WhaleCarcass Body", node 1811) to 5x smaller (0.2x).

Follows the validated live-edit recipe from the BRTR edit experiment (see
CLAUDE.md "Live BRTR Editing" section): PROP 0x080017DA (transform) and
PROP 0x080017DF (AABB) must be patched together and kept in sync, or the
object goes stale for rendering/collision culling.

- torzs is a top-level (depth=0) node, so its own PROP 0x080017DA IS the full
  world transform. Rotation is applied in world space about the node's own
  pivot (translation unchanged): R_new = Ry(-90) @ R_old. The new AABB is
  recomputed exactly by re-transforming the mesh's actual local vertices
  (extracted from its GMDL block) through the new world transform.
- WhaleCarcass Body is nested (parent 1807, local translation ~0). Its own
  PROP 0x080017DA is a LOCAL transform (rip_brtr_scene.py's flat read is
  accurate here since it doesn't compose with the parent). Scaling the local
  basis by 0.2 scales the object by 0.2x in world space regardless of the
  parent's own transform. The stored world-space AABB is scaled exactly via
  the pivot-relative formula: new = pivot + 0.2*(old - pivot), where pivot is
  the node's resolved world position (proven algebraically exact for a pure
  uniform-scale-about-pivot edit with no rotation change or translation
  change -- see scratch derivation in conversation).

Writes an edited copy to GAME_GDWs_edited/FISH.GDW -- does NOT touch the
GAME_GDWs/ research copy.
"""

import struct
import shutil
from pathlib import Path

SRC  = Path('GAME_GDWs/FISH.GDW')
DST  = Path('GAME_GDWs_edited/FISH.GDW')

TORZS_NODE_ID = 424
WHALE_NODE_ID = 1811


def u32(data, off): return struct.unpack_from('<I', data, off)[0]
def f32(data, off): return struct.unpack_from('<f', data, off)[0]
def align4(n): return (n + 3) & ~3


def find_tag(data, tag, lo, hi):
    p = data.find(tag, lo, hi)
    if p == -1: return None, None
    return p, u32(data, p + 4)


# ---------------------------------------------------------------------------
# GMDL index (for torzs mesh vertex extraction -> new AABB)
# ---------------------------------------------------------------------------

def build_gmdl_index(data):
    offset_map = {}
    off = 0
    while True:
        pos = data.find(b'GMDL', off)
        if pos == -1: break
        sz = u32(data, pos + 4)
        if not sz or sz > 5_000_000:
            off = pos + 4; continue
        end = pos + 8 + sz
        res_id = u32(data, pos + 8)
        posi_pos, posi_sz = find_tag(data, b'POSI', pos, end)
        vind_pos, vind_sz = find_tag(data, b'VIND', pos, end)
        if None in (posi_pos, vind_pos) or not posi_sz or not vind_sz:
            off = pos + 4; continue
        n_v = posi_sz // 12
        n_i = vind_sz // 2
        if n_v < 3 or n_i < 3:
            off = pos + 4; continue
        idxs = struct.unpack_from(f'<{n_i}H', data, vind_pos + 8)
        if max(idxs) >= n_v:
            off = pos + 4; continue
        if res_id and res_id not in offset_map:
            offset_map[res_id] = pos
        off = pos + 4
    return offset_map


def extract_local_verts(data, gmdl_pos):
    sz = u32(data, gmdl_pos + 4)
    end = gmdl_pos + 8 + sz
    posi_pos, posi_sz = find_tag(data, b'POSI', gmdl_pos, end)
    n_v = posi_sz // 12
    return [(f32(data, posi_pos + 8 + i * 12),
             f32(data, posi_pos + 8 + i * 12 + 4),
             f32(data, posi_pos + 8 + i * 12 + 8)) for i in range(n_v)]


def xform_verts(verts, xf):
    out = []
    for x, y, z in verts:
        out.append((xf[0]*x + xf[3]*y + xf[6]*z + xf[9],
                    xf[1]*x + xf[4]*y + xf[7]*z + xf[10],
                    xf[2]*x + xf[5]*y + xf[8]*z + xf[11]))
    return out


# ---------------------------------------------------------------------------
# BRTR walk: locate absolute file offsets of target nodes' PROP payloads,
# and compose world transforms (needed for the whale's pivot).
# ---------------------------------------------------------------------------

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
    newR = (apply_R(parentR, childR[0]), apply_R(parentR, childR[1]), apply_R(parentR, childR[2]))
    newT = apply_full(parentR, parentT, childT)
    return newR, newT


def parse_prps_props(data, start, end):
    """Return {prop_id: (value_offset_abs, value_size)}."""
    props = {}
    p = start
    while p < end - 8:
        if data[p:p+4] != b'PROP':
            p += 1; continue
        psz = u32(data, p + 4)
        pid = u32(data, p + 8)
        props[pid] = (p + 12, psz - 4)
        p += 8 + psz
    return props


def walk(data, start, end, parentR, parentT, depth, targets, found):
    pos = start
    while pos < end:
        if pos + 8 > end: break
        tag = data[pos:pos+4]
        sz  = u32(data, pos + 4)
        payload_start = pos + 8
        payload_end   = payload_start + sz
        if tag == b'CHBR':
            node_id = u32(data, payload_start + 4)
            inner   = payload_start + 8
            if data[inner:inner+4] == b'PRPS':
                prps_sz = u32(data, inner + 4)
                prps_payload_start = inner + 8
                prps_payload_end   = prps_payload_start + prps_sz
                children_start = align4(prps_payload_end)

                props = parse_prps_props(data, prps_payload_start, prps_payload_end)

                local_R, local_T = IDENTITY_R, IDENTITY_T
                if 0x080017DA in props:
                    off, psz = props[0x080017DA]
                    if psz >= 48:
                        xf = struct.unpack_from('<12f', data, off)
                        local_R, local_T = mat_from_xf(xf)

                world_R, world_T = compose(parentR, parentT, local_R, local_T)

                if node_id in targets:
                    found[node_id] = {
                        'xf_off':   props.get(0x080017DA, (None, None))[0],
                        'aabb_off': props.get(0x080017DF, (None, None))[0],
                        'world_T':  world_T,
                    }

                walk(data, children_start, payload_end, world_R, world_T, depth + 1, targets, found)
        pos = align4(payload_end)


def find_brtr(data):
    candidates = []
    pos = 0
    while True:
        idx = data.find(b'BRTR', pos)
        if idx == -1: break
        if idx + 20 <= len(data) and u32(data, idx+8) == 0x01025024 and u32(data, idx+12) == 1 and data[idx+16:idx+20] == b'PRPS':
            candidates.append((u32(data, idx+4), idx))
        pos = idx + 4
    brtr_sz, brtr_pos = max(candidates)
    return brtr_pos, brtr_sz


def main():
    print(f'Loading {SRC}...')
    data = bytearray(open(SRC, 'rb').read())
    print(f'  {len(data):,} bytes')

    brtr_pos, brtr_sz = find_brtr(data)
    print(f'BRTR @ 0x{brtr_pos:X} size={brtr_sz:,}')
    brtr_payload_start = brtr_pos + 8
    brtr_payload_end   = brtr_payload_start + brtr_sz

    p = brtr_payload_start + 8  # skip magic + root_count
    assert data[p:p+4] == b'PRPS'
    root_sz = u32(data, p + 4)
    root_payload_start = p + 8
    root_payload_end   = root_payload_start + root_sz
    top_children_start = align4(root_payload_end)

    found = {}
    walk(data, top_children_start, brtr_payload_end, IDENTITY_R, IDENTITY_T, 0,
         {TORZS_NODE_ID, WHALE_NODE_ID}, found)

    assert TORZS_NODE_ID in found, 'torzs node not found'
    assert WHALE_NODE_ID in found, 'whale carcass node not found'

    # -----------------------------------------------------------------
    # torzs: rotate -90 deg about world Y axis (yaw), pivot = its own T
    # -----------------------------------------------------------------
    t = found[TORZS_NODE_ID]
    xf_off = t['xf_off']
    old_xf = list(struct.unpack_from('<12f', data, xf_off))
    old_R = ((old_xf[0], old_xf[3], old_xf[6]),
             (old_xf[1], old_xf[4], old_xf[7]),
             (old_xf[2], old_xf[5], old_xf[8]))
    Ry = ((0.0, 0.0, -1.0),
          (0.0, 1.0,  0.0),
          (1.0, 0.0,  0.0))  # Ry(-90 deg)
    new_R = [[sum(Ry[i][k]*old_R[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    new_xf = [new_R[0][0], new_R[1][0], new_R[2][0],
              new_R[0][1], new_R[1][1], new_R[2][1],
              new_R[0][2], new_R[1][2], new_R[2][2],
              old_xf[9], old_xf[10], old_xf[11]]
    struct.pack_into('<12f', data, xf_off, *new_xf)
    print(f'torzs: patched xf @ 0x{xf_off:X}')
    print(f'  old R rows: {old_R}')
    print(f'  new R rows: {tuple(map(tuple,new_R))}')

    gmdl_index = build_gmdl_index(bytes(data))
    TORZS_MESH_ID = 2369
    assert TORZS_MESH_ID in gmdl_index, 'torzs mesh (2369) not found'
    local_verts = extract_local_verts(bytes(data), gmdl_index[TORZS_MESH_ID])
    world_verts = xform_verts(local_verts, new_xf)
    xs = [v[0] for v in world_verts]; ys = [v[1] for v in world_verts]; zs = [v[2] for v in world_verts]
    new_aabb = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))

    aabb_off = t['aabb_off']
    old_aabb = struct.unpack_from('<6f', data, aabb_off)
    struct.pack_into('<6f', data, aabb_off, *new_aabb)
    print(f'torzs: patched AABB @ 0x{aabb_off:X}')
    print(f'  old AABB: {old_aabb}')
    print(f'  new AABB: {new_aabb}')

    # -----------------------------------------------------------------
    # whale carcass: scale local basis by 0.2 (5x smaller), pivot = world T
    # -----------------------------------------------------------------
    w = found[WHALE_NODE_ID]
    xf_off = w['xf_off']
    old_xf = list(struct.unpack_from('<12f', data, xf_off))
    new_xf = [c * 0.2 for c in old_xf[0:9]] + old_xf[9:12]
    struct.pack_into('<12f', data, xf_off, *new_xf)
    print(f'\nWhaleCarcass Body: patched local xf @ 0x{xf_off:X}')
    print(f'  old basis: {old_xf[0:9]}')
    print(f'  new basis: {new_xf[0:9]}')

    pivot = w['world_T']
    aabb_off = w['aabb_off']
    old_aabb = struct.unpack_from('<6f', data, aabb_off)
    new_aabb = (
        pivot[0] + 0.2 * (old_aabb[0] - pivot[0]),
        pivot[1] + 0.2 * (old_aabb[1] - pivot[1]),
        pivot[2] + 0.2 * (old_aabb[2] - pivot[2]),
        pivot[0] + 0.2 * (old_aabb[3] - pivot[0]),
        pivot[1] + 0.2 * (old_aabb[4] - pivot[1]),
        pivot[2] + 0.2 * (old_aabb[5] - pivot[2]),
    )
    struct.pack_into('<6f', data, aabb_off, *new_aabb)
    print(f'WhaleCarcass Body: patched AABB @ 0x{aabb_off:X} (pivot={pivot})')
    print(f'  old AABB: {old_aabb}')
    print(f'  new AABB: {new_aabb}')

    DST.parent.mkdir(parents=True, exist_ok=True)
    with open(DST, 'wb') as f:
        f.write(data)
    print(f'\nWrote {DST} ({DST.stat().st_size:,} bytes, orig {SRC.stat().st_size:,})')
    assert DST.stat().st_size == SRC.stat().st_size, 'file size changed -- in-place float edits should not resize'


if __name__ == '__main__':
    main()

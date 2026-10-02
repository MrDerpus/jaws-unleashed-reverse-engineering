"""Convert an OBJ into a GMDL mesh and append it to a GDW's RSRC.

    python3 scripts/obj_to_gmdl.py IN.GDW OUT.GDW model.obj [MESH_ID] [--gmat ID] [--scale S]

--scale multiplies positions (Blender's default units are tiny in-game;
the test ring was 100 units across).

MESH_ID defaults to the next free resource ID (highest ID in RSRC + 1).
Resource IDs are one shared space (textures, sounds, materials, meshes, MREGs;
FISH: 1718 blocks, IDs 1..2832). An out-of-range ID (0x7000) was silently
ignored in-game, while the next free ID (2833) rendered (2026-10-03).

Writes the minimal GMDL layout used by 42 shipped FISH meshes:
    GMDL [mesh_id][1][0x0131F505]
      MATR  [1] + identity 4x3
      MATS  [n] + n x ['GMAT'][gmat_id]          one per submesh
      TSET  [n] + n x [i, first_vert, vert_count, first_tri, tri_count]
      TANG  [tri_count]  VIND (uint16 triangle list, absolute indices)
      VERT  [vert_count] POSI, NORM, UVUV
(TNOR/TFLG/VCOL are optional in shipped meshes and left out.)

--collision also builds an MREG collision region for the mesh (next free
resource ID after the mesh) and adds what 122/123 shipped collision meshes
have: TANG gains TNOR (per-triangle normal = -normalize((B-A) x (C-A)) in
game space, 46,153/46,153 shipped triangles) and TFLG ([1][uint16 0x47]
[uint16 0] = all three edge bits set). The triangle count is padded to a
multiple of 4 by repeating the last triangles (drawn on top of themselves),
so every BVH leaf holds exactly 4 triangles. MREG layout (all 123 FISH MREGs
follow it): see build_mreg(). Attach it to a node with a PRIM pointing at
the region ID (insert_brtr_node.py, template node 77).

OBJ conventions match rip_meshes.py and Blender's default OBJ export
(forward -Z, up Y): the game is left-handed, so z and normal z are negated,
v is flipped, and face order is kept. Each `usemtl` group becomes a submesh.
Its GMAT is chosen by material name:
    gmat_<id>   that GMAT resource ID (decimal or 0x hex)
    mat_<tid>   the first GMAT whose base texture is GTEX/GTEXT <tid> (our
                extracted scenes/models use these names)
    anything else, or no usemtl: --gmat (required then)
"""
import argparse
import math
import re
import struct
import sys

from gdw_grow import append_to_chunk, top_chunks
from gdw_materials import build_gmat_index

STAMP = 0x0131F505  # 20051205, on every shipped GMDL


def chunk(tag, *children):
    """Tagged chunk. Children are 4-byte padded between each other, but the
    size field excludes padding after the last one (verified byte-exact on
    shipped meshes with an odd triangle count)."""
    payload = b''.join(pad(c) for c in children[:-1]) + children[-1]
    return tag + struct.pack('<I', len(payload)) + payload


def pad(b):
    return b + b'\0' * (-len(b) % 4)


def parse_obj(path):
    """-> (positions, uvs, normals, [(material, [face, ...])]); a face is a list
    of (v, vt, vn) zero-based indices, vt/vn may be None."""
    P, T, N, groups = [], [], [], []
    cur = None

    def ix(s, n):
        if not s:
            return None
        i = int(s)
        return i - 1 if i > 0 else n + i

    for line in open(path, encoding='utf-8', errors='replace'):
        f = line.split()
        if not f:
            continue
        if f[0] == 'v':
            P.append(tuple(map(float, f[1:4])))
        elif f[0] == 'vt':
            T.append((float(f[1]), float(f[2]) if len(f) > 2 else 0.0))
        elif f[0] == 'vn':
            N.append(tuple(map(float, f[1:4])))
        elif f[0] == 'usemtl':
            cur = None
            name = f[1] if len(f) > 1 else ''
            for g in groups:
                if g[0] == name:
                    cur = g
            if cur is None:
                cur = (name, [])
                groups.append(cur)
        elif f[0] == 'f':
            if cur is None:
                cur = ('', [])
                groups.append(cur)
            face = []
            for c in f[1:]:
                parts = (c.split('/') + ['', ''])[:3]
                face.append((ix(parts[0], len(P)), ix(parts[1], len(T)), ix(parts[2], len(N))))
            cur[1].append(face)
    return P, T, N, [g for g in groups if g[1]]


def submesh(P, T, N, faces):
    """Fan-triangulate and convert to game space. -> (verts, tris), where a
    vert is (pos, normal, uv) and tris index into verts."""
    verts, index, tris = [], {}, []
    for face in faces:
        for k in range(1, len(face) - 1):
            corners = (face[0], face[k], face[k + 1])
            a, b, c = (P[v] for v, _, _ in corners)
            e1 = [b[i] - a[i] for i in range(3)]
            e2 = [c[i] - a[i] for i in range(3)]
            fn = [e1[1]*e2[2] - e1[2]*e2[1], e1[2]*e2[0] - e1[0]*e2[2], e1[0]*e2[1] - e1[1]*e2[0]]
            ln = math.sqrt(sum(x * x for x in fn)) or 1.0
            fn = [x / ln for x in fn]
            tri = []
            for v, t, n in corners:
                x, y, z = P[v]
                nx, ny, nz = N[n] if n is not None else fn
                uu, vv = T[t] if t is not None else (0.0, 0.0)
                vert = ((x, y, -z), (nx, ny, -nz), (uu, 1.0 - vv))
                key = (v, t, n if n is not None else tuple(fn))
                if key not in index:
                    index[key] = len(verts)
                    verts.append(vert)
                tri.append(index[key])
            tris.append(tri)
    return verts, tris


def gmat_for(name, default, gmats, named=None):
    if named and name in named:
        return named[name]
    m = re.fullmatch(r'gmat_(0x[0-9a-fA-F]+|\d+)', name)
    if m:
        return int(m.group(1), 0)
    m = re.fullmatch(r'mat_(\d+)', name)
    if m:
        tid = int(m.group(1))
        for gid in sorted(gmats):
            if gmats[gid][:1] == [tid]:
                return gid
        print(f'  no GMAT with base texture {tid}, using --gmat', file=sys.stderr)
    if default is None:
        raise SystemExit(f'material {name!r} has no GMAT; pass --gmat')
    return default


def build_gmdl(mesh_id, parts, collision=False):
    """parts: [(gmat_id, verts, tris)] -> (GMDL bytes, vert count, tri count,
    game-space triangle corner positions)."""
    if collision:
        # Pad to a multiple of 4 triangles inside the last submesh.
        total = sum(len(t) for _, _, t in parts)
        g, v, t = parts[-1]
        parts = parts[:-1] + [(g, v, t + [t[-1 - k % len(t)] for k in range(-total % 4)])]
    allv, allt, tset = [], [], []
    for i, (_, verts, tris) in enumerate(parts):
        base = len(allv)
        tset.append((i, base, len(verts), len(allt), len(tris)))
        allv += verts
        allt += [[base + j for j in t] for t in tris]
    if len(allv) > 0xFFFF:
        raise SystemExit(f'{len(allv)} vertices; VIND is uint16, split the mesh')

    matr = struct.pack('<I12f', 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0)
    mats = struct.pack('<I', len(parts)) + b''.join(b'GMAT' + struct.pack('<I', g) for g, _, _ in parts)
    tsetb = struct.pack('<I', len(tset)) + b''.join(struct.pack('<5I', *r) for r in tset)
    vind = struct.pack(f'<{3 * len(allt)}H', *[i for t in allt for i in t])
    tang = (struct.pack('<I', len(allt)), chunk(b'VIND', vind))
    corners = [[allv[i][0] for i in t] for t in allt]
    if collision:
        tnor = b''
        for a, b, c in corners:
            e1 = [b[k] - a[k] for k in range(3)]
            e2 = [c[k] - a[k] for k in range(3)]
            n = [e1[1]*e2[2] - e1[2]*e2[1], e1[2]*e2[0] - e1[0]*e2[2], e1[0]*e2[1] - e1[1]*e2[0]]
            ln = math.sqrt(sum(x * x for x in n)) or 1.0
            tnor += struct.pack('<3f', *(-x / ln for x in n))
        tflg = struct.pack('<IHH', 1, 0x47, 0) * len(allt)
        tang += (chunk(b'TNOR', tnor), chunk(b'TFLG', tflg))
    vert = (struct.pack('<I', len(allv)),
            chunk(b'POSI', b''.join(struct.pack('<3f', *v[0]) for v in allv)),
            chunk(b'NORM', b''.join(struct.pack('<3f', *v[1]) for v in allv)),
            chunk(b'UVUV', b''.join(struct.pack('<2f', *v[2]) for v in allv)))
    gmdl = chunk(b'GMDL', struct.pack('<3I', mesh_id, 1, STAMP), chunk(b'MATR', matr),
                 chunk(b'MATS', mats), chunk(b'TSET', tsetb), chunk(b'TANG', *tang),
                 chunk(b'VERT', *vert))
    return pad(gmdl), len(allv), len(allt), corners


def build_mreg(region_id, mesh_id, corners):
    """MREG collision region for a mesh whose triangle count is a multiple of 4.

    MREG [region_id][1]['GMDL'][mesh_id][0xFFFFFFFF]   (flags < 0 = has data)
      PERF [float 0.25]                                  (every FISH MREG)
      BREG [n] + n x AABB(min xyz, max xyz)               n = 2L - 1, L = tris / 4
      STRI [m] + m x uint32 triangle index                 permutation of the mesh's triangles
    BREG is a binary tree in heap order (children of k: 2k+1, 2k+2); leaves
    taken in in-order traversal own consecutive runs of 4 STRI entries; each
    internal box is the union of its children. Verified on all 123 FISH MREGs.
    """
    nt = len(corners)
    assert nt and nt % 4 == 0
    L = nt // 4
    n = 2 * L - 1
    leaves = {}

    def nleaves(k):
        if k >= L - 1:
            return 1
        if k not in leaves:
            leaves[k] = nleaves(2 * k + 1) + nleaves(2 * k + 2)
        return leaves[k]

    boxes = [None] * n
    order = []

    def box_of(tris):
        pts = [p for t in tris for p in corners[t]]
        return [min(p[i] for p in pts) for i in range(3)] + [max(p[i] for p in pts) for i in range(3)]

    def build(k, tris):
        if k >= L - 1:
            order.extend(tris)
            boxes[k] = box_of(tris)
            return
        # Median split on the longest axis of the triangle centroids, sized
        # to the number of leaves the heap shape gives the left subtree.
        cen = {t: [sum(p[i] for p in corners[t]) / 3 for i in range(3)] for t in tris}
        span = [max(cen[t][i] for t in tris) - min(cen[t][i] for t in tris) for i in range(3)]
        axis = span.index(max(span))
        tris = sorted(tris, key=lambda t: cen[t][axis])
        cut = 4 * nleaves(2 * k + 1)
        build(2 * k + 1, tris[:cut])
        build(2 * k + 2, tris[cut:])
        a, b = boxes[2 * k + 1], boxes[2 * k + 2]
        boxes[k] = [min(a[i], b[i]) for i in range(3)] + [max(a[i], b[i]) for i in range(3, 6)]

    build(0, list(range(nt)))
    breg = struct.pack('<I', n) + b''.join(struct.pack('<6f', *b) for b in boxes)
    stri = struct.pack(f'<I{nt}I', nt, *order)
    mreg = chunk(b'MREG', struct.pack('<5I', region_id, 1, 0x4C444D47, mesh_id, 0xFFFFFFFF),
                 chunk(b'PERF', struct.pack('<f', 0.25)), chunk(b'BREG', breg), chunk(b'STRI', stri))
    return pad(mreg)


def load_parts(obj_path, scale, default_gmat, gmats, named=None):
    """OBJ -> [(gmat_id, verts, tris)] in game space, one part per usemtl group."""
    P, T, N, groups = parse_obj(obj_path)
    P = [(x * scale, y * scale, z * scale) for x, y, z in P]
    parts = []
    for name, faces in groups:
        gid = gmat_for(name, default_gmat, gmats, named)
        verts, tris = submesh(P, T, N, faces)
        parts.append((gid, verts, tris))
        print(f'  submesh {name or "(none)"!r}: GMAT {gid}, {len(verts)} verts, {len(tris)} tris')
    return parts


def next_free_id(d):
    """Highest resource ID in any archive's RSRC chain, plus 1."""
    best, start = 0, 0
    while True:
        r = d.find(b'RSRC', start)
        if r == -1:
            return best + 1
        if struct.unpack_from('<I', d, r + 8)[0] == 0x0131F508:  # RSRC sub-header stamp
            end = r + 8 + struct.unpack_from('<I', d, r + 4)[0]
            p = r + 20
            while p + 12 <= end and d[p:p + 4].isalnum():
                size, rid = struct.unpack_from('<II', d, p + 4)
                if size > end - p:
                    break
                best = max(best, rid)
                p = (p + 8 + size + 3) & ~3
        start = r + 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('obj')
    ap.add_argument('mesh_id', nargs='?', type=lambda s: int(s, 0))
    ap.add_argument('--gmat', type=lambda s: int(s, 0))
    ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--collision', action='store_true')
    a = ap.parse_args()

    d = bytearray(open(a.src, 'rb').read())
    parts = load_parts(a.obj, a.scale, a.gmat, build_gmat_index(d))
    free = next_free_id(d)
    if a.mesh_id is None:
        a.mesh_id = free
    elif a.mesh_id > free:
        print(f'warning: {a.mesh_id:#x} is above the next free ID {free:#x}; '
              'out-of-range IDs were ignored in-game', file=sys.stderr)
    blob, nv, nt, corners = build_gmdl(a.mesh_id, parts, a.collision)
    if a.collision:
        region_id = max(free, a.mesh_id) + 1
        blob += build_mreg(region_id, a.mesh_id, corners)
    rsrc = top_chunks(d)['RSRC']
    at = append_to_chunk(d, rsrc, blob)
    print(f'GMDL {a.mesh_id:#x}: {nv} verts, {nt} tris at {at:#x}')
    if a.collision:
        print(f'MREG {region_id:#x}: {nt // 4} leaves -> set as the PRIM region in insert_brtr_node.py')
    open(a.out, 'wb').write(d)


if __name__ == '__main__':
    main()

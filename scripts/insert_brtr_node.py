"""Append brand-new CHBR nodes to a GDW's primary BRTR (scene graph).

Each new node is a byte copy of an existing top-level node, with a new node ID,
a new world translation and optionally a new mesh ID; the AABB is recomputed
from the mesh's vertices. Growing BRTR and fixing FSIZ/SKIP/FDIR is done by
gdw_grow.append_to_chunk.

Usage (edit SPECS below):
    python3 scripts/insert_brtr_node.py IN.GDW OUT.GDW
"""
import struct
import sys

from gdw_grow import append_to_chunk, find_brtr, u32

# (source node id, new world translation (x, y, z), new mesh id or None,
#  {prop id: uint32 value} overrides for existing PROPs; the position may
#  instead be a full 12-float transform (3 basis columns + translation); the key 'prim_region'
#  repoints the node's PRIM (collision link) at that MREG region ID)
SPECS = [
    (77,  (2160.0, -25.0, -3650.0), 0xB11, {'prim_region': 0xB12}),  # A: something.obj, generated collision (obj_to_gmdl.py --collision)
    (77,  (2300.0, -5.0, -3520.0), None, {}),  # C: same wall mesh, has a PRIM (collision -> MREG 0x943)
]

P_TRANSFORM, P_AABB, P_MESH, P_VCOL = 0x080017DA, 0x080017DF, 0x08001873, 0x0800187A
P_PRIM_REGION = 0x080018D8  # inside PRIM's PRPS: ['MREG'][region id]


def top_level_nodes(d, brtr):
    end = brtr + 8 + u32(d, brtr + 4)
    p = brtr + 16
    out = {}
    while p < end:
        t, s = d[p:p + 4], u32(d, p + 4)
        if t == b'CHBR':
            out[u32(d, p + 12)] = (p, s)
        p = (p + 8 + s + 3) & ~3
    return out, end


def max_node_id(d, brtr):
    end = brtr + 8 + u32(d, brtr + 4)
    best = 0

    def walk(p):
        nonlocal best
        best = max(best, u32(d, p + 12))
        q, qend = p + 16, p + 8 + u32(d, p + 4)
        while q < qend:
            if d[q:q + 4] == b'CHBR':
                walk(q)
            q = (q + 8 + u32(d, q + 4) + 3) & ~3

    p = brtr + 16
    while p < end:
        if d[p:p + 4] == b'CHBR':
            walk(p)
        p = (p + 8 + u32(d, p + 4) + 3) & ~3
    return best


def prop_offsets(node):
    """PROP value offsets (relative to node start) in the node's own PRPS."""
    q = 16
    while q < len(node):
        if node[q:q + 4] == b'PRPS':
            out, r, rend = {}, q + 8, q + 8 + u32(node, q + 4)
            while r < rend and node[r:r + 4] == b'PROP':
                s = u32(node, r + 4)
                out[u32(node, r + 8)] = r + 12
                r += 8 + ((s + 3) & ~3)
            return out
        q = (q + 8 + u32(node, q + 4) + 3) & ~3
    raise ValueError('node has no PRPS')


def replace_prop(node, prop_id, value):
    """Return node bytes with PROP prop_id's value replaced (size may change);
    the PRPS and CHBR size fields are fixed up."""
    q = 16
    while node[q:q + 4] != b'PRPS':
        q = (q + 8 + u32(node, q + 4) + 3) & ~3
    r, rend = q + 8, q + 8 + u32(node, q + 4)
    while u32(node, r + 8) != prop_id:
        r += 8 + ((u32(node, r + 4) + 3) & ~3)
    old_len = 8 + ((u32(node, r + 4) + 3) & ~3)
    entry = b'PROP' + struct.pack('<II', 4 + len(value), prop_id) + value
    entry += b'\0' * (-len(entry) % 4)
    node = node[:r] + entry + node[r + old_len:]
    delta = len(entry) - old_len
    node = bytearray(node)
    struct.pack_into('<I', node, q + 4, u32(node, q + 4) + delta)
    struct.pack_into('<I', node, 4, u32(node, 4) + delta)
    return bytes(node)


def set_prim_region(node, region_id):
    """Point the node's PRIM (collision link) at MREG region_id, in place."""
    q = 16
    while q < len(node) and node[q:q + 4] != b'PRIM':
        q = (q + 8 + u32(node, q + 4) + 3) & ~3
    if q >= len(node):
        raise ValueError('template node has no PRIM; use one that does (e.g. node 77)')
    i = node.find(struct.pack('<I', P_PRIM_REGION), q, q + 8 + u32(node, q + 4))
    assert node[i + 4:i + 8] == b'MREG'
    struct.pack_into('<I', node, i + 8, region_id)


def mesh_positions(d, mesh_id):
    """Vertex positions (local space) of the GMDL whose sub-header ID is mesh_id."""
    i = 0
    while True:
        i = d.find(b'GMDL', i)
        if i == -1:
            raise KeyError(f'GMDL {mesh_id:#x} not found')
        size = u32(d, i + 4)
        if u32(d, i + 8) == mesh_id and i + 8 + size <= len(d):
            p = d.find(b'POSI', i, i + 8 + size)
            n = u32(d, p + 4) // 12
            return [struct.unpack_from('<3f', d, p + 8 + 12 * k) for k in range(n)]
        i += 4


def build_node(d, src, new_id, pos, mesh, overrides, src_data=None):
    """src = (offset, size) of the template CHBR in src_data (default: d).
    Mesh lookups (AABB, vertex colours) always use d, the file being built."""
    p, s = src
    node = bytearray((d if src_data is None else src_data)[p:p + 8 + s])
    node += b'\0' * (-len(node) % 4)
    struct.pack_into('<I', node, 12, new_id)
    po = prop_offsets(node)
    xf = list(struct.unpack_from('<12f', node, po[P_TRANSFORM]))
    if len(pos) == 12:
        xf = list(pos)            # full transform: basis columns + translation
    else:
        xf[9:12] = pos            # translation only, keep the template's basis
    struct.pack_into('<12f', node, po[P_TRANSFORM], *xf)
    if mesh is not None:
        struct.pack_into('<I', node, po[P_MESH] + 4, mesh)
    for prop, value in overrides.items():
        if prop == 'prim_region':
            set_prim_region(node, value)
        else:
            struct.pack_into('<I', node, po[prop], value)
    if P_AABB in po:
        # World-space AABB from the mesh's real vertices, so a swapped-in mesh
        # never inherits the source node's (wrong-sized) bounds.
        mesh_id = u32(node, po[P_MESH] + 4)
        world = [(xf[0]*x + xf[3]*y + xf[6]*z + xf[9],
                  xf[1]*x + xf[4]*y + xf[7]*z + xf[10],
                  xf[2]*x + xf[5]*y + xf[8]*z + xf[11]) for x, y, z in mesh_positions(d, mesh_id)]
        bb = [min(w[k] for w in world) for k in range(3)] + [max(w[k] for w in world) for k in range(3)]
        struct.pack_into('<6f', node, po[P_AABB], *bb)
    if mesh is not None and P_VCOL in po:
        # Baked vertex colours hold exactly one RGBA float4 per mesh vertex.
        # Refill with the source's average colour, sized for the new mesh.
        n_old = u32(node, po[P_VCOL])
        cols = [struct.unpack_from('<4f', node, po[P_VCOL] + 4 + 16 * k) for k in range(n_old)]
        avg = [sum(c[i] for c in cols) / n_old for i in range(4)] if n_old else [1.0] * 4
        n = len(mesh_positions(d, mesh))
        node = replace_prop(bytes(node), P_VCOL, struct.pack('<I', n) + struct.pack('<4f', *avg) * n)
    return bytes(node)


def main(src_path, out_path):
    d = bytearray(open(src_path, 'rb').read())
    size_before = len(d)
    brtr = find_brtr(d)
    nodes, brtr_end = top_level_nodes(d, brtr)
    assert brtr_end % 4 == 0
    next_id = max_node_id(d, brtr) + 1

    blob = b''
    for src_id, pos, mesh, overrides in SPECS:
        blob += build_node(d, nodes[src_id], next_id, pos, mesh, overrides)
        print(f'node {next_id}: copy of {src_id} at {pos}' + (f' mesh {mesh:#x}' if mesh else ''))
        next_id += 1

    append_to_chunk(d, brtr, blob)
    print(f'grew by {len(d) - size_before} bytes')
    open(out_path, 'wb').write(d)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

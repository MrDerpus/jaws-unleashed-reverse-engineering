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
Shared BRTR scene-graph resolver: turns a GDW's BRTR chunk into the list of
object *instances* the game actually places, with true world transforms.

Used by rip_brtr_scene.py and resolve_brtr_hierarchy.py. Handles three
placement mechanisms (all verified 2026-10-01):

1. Parent -> child nesting. A CHBR nested inside another CHBR's payload
   stores its PROP 0x080017DA transform LOCAL to the parent:
   world = parent_world o local. EXCEPT when the node's flags (PROP
   0x080017D9, m_nFlags) have bit 0x20000000 set: then the transform is
   already absolute world space and the parent is ignored. This matches the
   engine's world-matrix updater (Jaws.exe 0x696EA0), which tests brick flags
   0x20000000 and skips parent composition. Seen on e.g. FISH `fenyo` pine trees
   and their `Box0N` foliage-card children (flags 0x2000005A), 92 nested nodes
   in FISH. Composing those through the parent sent them ~7,400 units away.

2. Reference instancing, PROP 0x080017F0 = target node ID. A reference node
   places a copy of the target's whole subtree. "Replace" semantics: the copy's
   root takes the reference node's own world transform, and the target's own
   transform is ignored. The target's descendants compose beneath it as usual.
   Evidence: OPEN_S `Starfish01` (authored at y=-27.6) and its 10 references.
   Replace puts every copy at seafloor depth (y -28..-33), compose would bury
   them at y -55..-61, and each reference carries its own random rotation.
   FISH `molo` (pier, authored at dock height y=3.59) and its 12 references
   (at y 3.4-4.3) agree. Templates (reference targets) still exist as nodes at
   their authored spot. Some render there in-game, but most don't (per-object;
   see docs/terrain_and_water_bounds.md), so they're emitted with
   is_template=True.

3. Mission relocation, PROP 0x08000AE5 = MSMineAllMineMission.m_WhaleID.
   The mission root positions the whale's top-level node relative to itself
   ("compose": whale_world = root_world o whale_authored_local). Verified
   in-game: FISH whale predicted at (2081,-20,-3722), and the user teleported
   there and landed against the carcass. The whale is moved, not copied, so its
   authored placement is not emitted.

Transform layout (same as BRTR PROP 0x080017DA): 12 floats, xf[0:3] / [3:6] /
[6:9] = X / Y / Z basis vectors, xf[9:12] = translation;
world_point = x*X + y*Y + z*Z + T.
"""

import struct

PROP_NAME      = 0x080017D8
PROP_FLAGS     = 0x080017D9
PROP_XF        = 0x080017DA
PROP_AABB      = 0x080017DF
PROP_REF       = 0x080017F0
PROP_MESH      = 0x08001873
PROP_VCOLS     = 0x0800187A
PROP_MAM_WHALE = 0x08000AE5   # MSMineAllMineMission.m_WhaleID

FLAG_ABSOLUTE  = 0x20000000   # transform is world space; don't compose with parent

IDENTITY = (1.0, 0.0, 0.0,  0.0, 1.0, 0.0,  0.0, 0.0, 1.0,  0.0, 0.0, 0.0)


def u32(data, off):
    return struct.unpack_from('<I', data, off)[0]


def align4(n):
    return (n + 3) & ~3


def xf_compose(parent, child):
    """world = parent o child, both 12-float transforms."""
    def basis(v):
        x, y, z = v
        return (parent[0]*x + parent[3]*y + parent[6]*z,
                parent[1]*x + parent[4]*y + parent[7]*z,
                parent[2]*x + parent[5]*y + parent[8]*z)
    X = basis(child[0:3]); Y = basis(child[3:6]); Z = basis(child[6:9])
    t = basis(child[9:12])
    T = (t[0] + parent[9], t[1] + parent[10], t[2] + parent[11])
    return X + Y + Z + T


def find_brtr(data):
    """Real top-level BRTR: largest candidate with the right magic/root/PRPS
    (naive find() hits false positives in RSRC on 8/20 GDWs, and embedded
    loading-screen sub-archives have their own small BRTR)."""
    cands = []
    pos = 0
    while True:
        idx = data.find(b'BRTR', pos)
        if idx == -1:
            break
        if (idx + 20 <= len(data) and u32(data, idx+8) == 0x01025024
                and u32(data, idx+12) == 1 and data[idx+16:idx+20] == b'PRPS'):
            cands.append((u32(data, idx+4), idx))
        pos = idx + 4
    if not cands:
        raise RuntimeError('BRTR chunk not found')
    size, pos = max(cands)
    return pos, size


def _parse_props(data, start, end):
    props = {}
    p = start
    while p < end - 8:
        if data[p:p+4] != b'PROP':
            p += 1
            continue
        psz = u32(data, p+4)
        props[u32(data, p+8)] = data[p+12:p+8+psz]
        p += 8 + psz
    return props


def _u32_prop(props, pid):
    d = props.get(pid)
    return u32(d, 0) if d is not None and len(d) >= 4 else 0


def compose_node(parent_world, node):
    """World transform of `node` placed under a parent with `parent_world`."""
    if node['flags'] & FLAG_ABSOLUTE:
        return node['local_xf']
    return xf_compose(parent_world, node['local_xf'])


def load_nodes(data):
    """Parse every CHBR into {node_id: node}. Returns (nodes, top_level_ids,
    root_xf) -- root_xf is the root "World" PRPS transform (identity in every
    GDW checked, but applied anyway). Node fields: name, props (raw bytes by
    prop id), local_xf, flags, parent, children, depth."""
    brtr_pos, brtr_size = find_brtr(data)
    root = brtr_pos + 16                       # past tag, size, magic, root_count
    root_props = _parse_props(data, root + 8, root + 8 + u32(data, root + 4))
    xf = root_props.get(PROP_XF)
    root_xf = struct.unpack_from('<12f', xf) if xf and len(xf) >= 48 else IDENTITY
    first_child = align4(root + 8 + u32(data, root + 4))
    end = brtr_pos + 8 + brtr_size
    nodes = {}
    top = []

    def walk(start, stop, parent, depth):
        pos = start
        while pos < stop - 8:
            tag = data[pos:pos+4]
            sz = u32(data, pos+4)
            ps, pe = pos + 8, pos + 8 + sz
            if tag == b'CHBR':
                nid = u32(data, ps + 4)
                inner = ps + 8
                if data[inner:inner+4] == b'PRPS':
                    psz = u32(data, inner + 4)
                    a, b = inner + 8, inner + 8 + psz
                    props = _parse_props(data, a, b)
                    name = ''
                    d = props.get(PROP_NAME)
                    if d and len(d) >= 4:
                        n = u32(d, 0)
                        if n and n <= len(d) - 4:
                            name = d[4:4+n].decode('utf-8', 'replace').strip('\x00').strip()
                    xf = props.get(PROP_XF)
                    local = struct.unpack_from('<12f', xf) if xf and len(xf) >= 48 else IDENTITY
                    nodes[nid] = {'id': nid, 'name': name, 'props': props, 'local_xf': local,
                                  'flags': _u32_prop(props, PROP_FLAGS),
                                  'parent': parent, 'children': [], 'depth': depth}
                    if parent is None:
                        top.append(nid)
                    else:
                        nodes[parent]['children'].append(nid)
                    walk(align4(b), pe, nid, depth + 1)
            pos = align4(pe)

    walk(first_child, end, None, 0)
    return nodes, top, root_xf


def authored_world(nodes, root_xf=IDENTITY):
    """World transform of every node at its authored spot (nesting only)."""
    out = {}
    def rec(nid, parent_world):
        w = compose_node(parent_world, nodes[nid])
        out[nid] = w
        for c in nodes[nid]['children']:
            rec(c, w)
    for nid, n in nodes.items():
        if n['parent'] is None:
            rec(nid, root_xf)
    return out


def resolve_instances(data):
    """Return (nodes, instances). Each instance is a dict:
      node_id, name, world_xf, depth (within its placement), via_ref (id of
      the reference node that placed this copy, innermost; None for an
      original), ref_chain (all reference ids, outermost first),
      is_template (this placement is a reference target or inside one, at
      its authored spot), relocated_by (mission node id for relocated
      objects, else None).
    """
    nodes, top, root_xf = load_nodes(data)
    authored = authored_world(nodes, root_xf)

    ref_target = {}
    for nid, n in nodes.items():
        t = _u32_prop(n['props'], PROP_REF)
        if t and t in nodes and t != nid:
            ref_target[nid] = t
    targets = set(ref_target.values())

    relocate = {}   # whale top-level node id -> mission root id
    for nid, n in nodes.items():
        w = _u32_prop(n['props'], PROP_MAM_WHALE)
        if w and w in nodes:
            relocate[w] = nid

    instances = []

    def emit(nid, world, depth, ref_chain, in_template, relocated_by):
        n = nodes[nid]
        tmpl = in_template or (nid in targets and not ref_chain)
        instances.append({
            'node_id': nid, 'name': n['name'], 'world_xf': world, 'depth': depth,
            'via_ref': ref_chain[-1] if ref_chain else None, 'ref_chain': list(ref_chain),
            'is_template': tmpl, 'relocated_by': relocated_by,
        })
        for c in n['children']:
            emit(c, compose_node(world, nodes[c]), depth + 1, ref_chain, tmpl, relocated_by)
        t = ref_target.get(nid)
        chain_targets = {ref_target[r] for r in ref_chain}
        if t is not None and t not in chain_targets and len(ref_chain) < 8:
            # Replace semantics: the copy's root sits exactly at this node's world transform.
            emit(t, world, depth + 1, ref_chain + [nid], False, relocated_by)

    for nid in top:
        if nid in relocate:
            anchor = relocate[nid]
            world = xf_compose(authored[anchor], nodes[nid]['local_xf'])
            emit(nid, world, 0, [], False, anchor)
        else:
            emit(nid, compose_node(root_xf, nodes[nid]), 0, [], False, None)

    return nodes, instances


def resolve_nodes(data):
    """Per-node view (one entry per CHBR, no reference copies), for
    resolve_brtr_hierarchy.py. Returns {node_id: dict} with world_pos at the
    authored spot, plus ref_target / is_template / relocated_world_pos."""
    nodes, top, root_xf = load_nodes(data)
    authored = authored_world(nodes, root_xf)
    ref_target = {nid: _u32_prop(n['props'], PROP_REF) for nid, n in nodes.items()}
    targets = {t for t in ref_target.values() if t in nodes}
    relocate = {}
    for nid, n in nodes.items():
        w = _u32_prop(n['props'], PROP_MAM_WHALE)
        if w in nodes:
            relocate[w] = nid

    def in_template(nid):
        while nid is not None:
            if nid in targets:
                return True
            nid = nodes[nid]['parent']
        return False

    def relocated(nid):
        """World xf if nid sits under a relocated top-level node, else None."""
        chain = []
        k = nid
        while k is not None:
            chain.append(k)
            k = nodes[k]['parent']
        top_id = chain[-1]
        if top_id not in relocate:
            return None
        w = xf_compose(authored[relocate[top_id]], nodes[top_id]['local_xf'])
        for k in reversed(chain[:-1]):
            w = compose_node(w, nodes[k])
        return w

    out = {}
    for nid, n in nodes.items():
        d = n['props'].get(PROP_MESH)
        rel = relocated(nid)
        rt = ref_target[nid]
        out[nid] = {
            'name':        n['name'],
            'local_pos':   list(n['local_xf'][9:12]),
            'world_pos':   list(authored[nid][9:12]),
            'mesh_id':     u32(d, 4) if d is not None and len(d) >= 8 else None,
            'parent_id':   n['parent'],
            'depth':       n['depth'],
            'absolute_xf': bool(n['flags'] & FLAG_ABSOLUTE),
            'ref_target':  rt if rt in nodes else None,
            'is_template': in_template(nid),
            'relocated_world_pos': list(rel[9:12]) if rel else None,
        }
    return out

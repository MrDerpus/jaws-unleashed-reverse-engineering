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

"""Add a scripted trigger to a level: break an object -> things disappear.

    python3 scripts/add_trigger.py BASE.GDW OUT.GDW

Edit the CONFIG block below. What gets built (all appended to BRTR):
  1. TRIGGER: a copy of a breakable template subtree (default: FISH's pier
     post, Torheto_pozna 1, node 130) with fresh IDs, placed directly in the
     level (not through a reference node), optionally scaled and tinted.
     Its destructible block (MBRombolhato) gets its hook set:
       m_robbcontrol  (PROP 0x08000673)  runs a control when it's destroyed
       m_megutcontrol (PROP 0x0800067C)  runs a control on every non-fatal hit
  2. TARGETS: new objects the trigger acts on (template node + mesh +
     collision + position + tint), plus any EXISTING node IDs listed.
  3. CONTROL: a GDControl (copied from START's SeaSeekerQuestEventControl)
     whose steps act on the targets, attached to the TRIGGER's root node.

Rules found the hard way (2026-10-03, see docs/brtr_editing.md "Scripted
triggers"):
  - A hook starts the control's LIVE instance (lookup FUN_006C3010 returns
    registered object +0x24). Only group-type nodes (classes 0x010B10AA,
    0x010AA0A4) instantiate their actions at load; on a plain model brick
    (0x0107402F) the control never gets an instance and the hook does
    nothing. So the control lives on the trigger's root (class 0x010B10AA),
    like every shipped hook target.
  - New IDs must be unused and below 0x100000: the engine numbers its own
    runtime objects from about 0x100000, and objects with IDs up there
    vanish. This script allocates from ID_BASE (0xF000).
  - Template copies via reference nodes resolve fine too, but placing the
    copy directly keeps one specific trigger object separate from the
    template's other copies.
"""
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(globals().get('__file__', 'scripts/add_trigger.py')).resolve().parent))
import brtr_scene_graph as g
from gdw_grow import append_to_chunk, find_brtr, u32
from insert_brtr_node import top_level_nodes, build_node, mesh_positions, prop_offsets

# ============================================================
# CONFIG
# ============================================================

START_GDW = Path(__file__).resolve().parent.parent / 'GAME_GDWs' / 'START.GDW'

TRIGGER = {
    'template': 130,             # breakable subtree root to copy (FISH: Torheto_pozna 1)
    'replace_ref': 150,          # take this reference node's transform and park it below
                                 # the map (FISH: GDReference 7, a post near the pier);
                                 # None = use 'xf' instead
    'xf': None,                  # 12 floats (column-major 4x3) when replace_ref is None
    'scale': 1.3,
    'tint': (1.0, 0.25, 0.75, 1.0),   # m_ModelColor of every mesh in the copy (None = keep)
    'hooks': ('destroy',),       # 'destroy' (m_robbcontrol) and/or 'hit' (m_megutcontrol)
    'hitpoints': None,           # m_maxhitpoint; None = keep the template's (posts: 15)
}

# New target objects: template node (needs a PRIM if 'mreg' is given), mesh,
# collision region, world position (y=None: sit on top of the water), tint.
TARGETS = [
    {'template': 77, 'mesh': 0xB13, 'mreg': 0xB14, 'pos': (2110.0, None, -3960.0),
     'tint': (1.0, 0.1, 0.1, 1.0)},      # red Suzanne (see docs: monkey mesh)
]
EXISTING_TARGETS = []                     # node IDs already in the level

# Control steps (GDControl action words, see docs/exe_analysis.md "GDControl").
# Each entry is (word, name) for all targets, or (word, name, [target indices])
# to act only on those entries of TARGETS + EXISTING_TARGETS (in that order).
# Tested one step per target (2026-10-03, user-confirmed), effect on a plain
# model node:
#   0x4B000400 suspend             invisible + not solid
#   0x8F000100 hide                invisible + not solid
#   0x4F000040 collision bits off  invisible + not solid
#   0x0F000008 kill                invisible but STILL SOLID (don't use alone)
# Suspend alone is the default: a complete removal, and what START's tunnel
# boulder uses.
STEPS = [
    (0x4B000400, 'suspend'),
]
DELAY = -1      # ticks before the steps run. -1 = in the same instant the control is
                # started (FUN_006B68A0 runs one pass with the counter at -1). Needed for
                # 'destroy': posts have m_killparent = 1, so breaking one deletes its root,
                # and the control on it, before a t=0 step would run on the next tick.

ID_BASE = 0xF000
ID_LIMIT = 0x100000

P_REF, P_XF, P_AABB, P_COLOR = 0x080017F0, 0x080017DA, 0x080017DF, 0x08001879
P_ROBB, P_MEGUT, P_MAXHP = 0x08000673, 0x0800067C, 0x08000663
P_INNER_REFS = (0x080018CB, 0x08000D05)   # post subtree: mesh->destructible, bite target->mesh
ROMB_CLASS, CTRL_CLASS = 0x02169168, 0x0203B039
START_CONTROL = 2084                      # START.GDW SeaSeekerQuestEventControl


def chunk_headers(buf, lo, hi):
    """(offset, tag) of every CHBR/ACTN header (followed by PRPS) in buf[lo:hi]."""
    out = []
    for tag in (b'CHBR', b'ACTN'):
        p = lo
        while (p := buf.find(tag, p, hi)) != -1:
            if buf[p + 16:p + 20] == b'PRPS':
                out.append((p, tag))
            p += 4
    return sorted(out)


def prop_values(buf, lo, hi):
    """[(value offset, prop id, value length)] for every PROP in buf[lo:hi]."""
    out, p = [], lo
    while (p := buf.find(b'PROP', p, hi)) != -1:
        out.append((p + 12, u32(buf, p + 8), u32(buf, p + 4) - 4))
        p += 4
    return out


def m4(xf):
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = xf[0:3], xf[3:6], xf[6:9], xf[9:12]
    return m


class Ids:
    def __init__(self, d):
        self.used = {u32(d, p + 12) for p, _ in chunk_headers(d, 0, len(d))}
        self.next = ID_BASE

    def new(self):
        while self.next in self.used:
            self.next += 1
        if self.next >= ID_LIMIT:
            raise SystemExit('ran out of IDs below 0x100000')
        self.used.add(self.next)
        return self.next


def clone_subtree(d, off, size, ids):
    """Copy a CHBR subtree with fresh IDs for every CHBR/ACTN and the known
    internal references remapped. Returns (bytes, {old: new})."""
    sub = bytearray(d[off:off + 8 + size])
    sub += b'\0' * (-len(sub) % 4)
    heads = chunk_headers(sub, 0, len(sub))
    remap = {u32(sub, p + 12): ids.new() for p, _ in heads}
    for p, _ in heads:
        struct.pack_into('<I', sub, p + 12, remap[u32(sub, p + 12)])
    for vo, pid, ln in prop_values(sub, 0, len(sub)):
        if pid in P_INNER_REFS and ln == 4 and u32(sub, vo) in remap:
            struct.pack_into('<I', sub, vo, remap[u32(sub, vo)])
    return sub, remap


def place_subtree(sub, xf):
    """Set the subtree root's transform to xf and map every AABB along."""
    root_pv = {pid: vo for vo, pid, _ in prop_values(sub, 24, 24 + u32(sub, 20))}
    old = m4(struct.unpack_from('<12f', sub, root_pv[P_XF]))
    struct.pack_into('<12f', sub, root_pv[P_XF], *xf)
    M = m4(xf) @ np.linalg.inv(old)
    for vo, pid, ln in prop_values(sub, 0, len(sub)):
        if pid == P_AABB and ln == 24:
            b = struct.unpack_from('<6f', sub, vo)
            c = np.array([[x, y, z, 1] for x in (b[0], b[3]) for y in (b[1], b[4]) for z in (b[2], b[5])]) @ M.T
            struct.pack_into('<6f', sub, vo, *c[:, :3].min(0), *c[:, :3].max(0))


def make_control(ctrl_id, target_ids):
    """START's SeaSeekerQuestEventControl ACTN with a new ID and STEPS on target_ids
    (all of them, or the indices a step lists)."""
    s = START_GDW.read_bytes()
    sb = find_brtr(s)
    p = sb
    while (p := s.find(b'ACTN', p, sb + 8 + u32(s, sb + 4))) != -1:
        if u32(s, p + 8) == CTRL_CLASS and u32(s, p + 12) == START_CONTROL:
            break
        p += 4
    else:
        raise SystemExit('template control not found in START.GDW')
    actn = bytearray(s[p:p + 8 + u32(s, p + 4)])
    struct.pack_into('<I', actn, 12, ctrl_id)
    r, rend, props = 24, 24 + u32(actn, 20), []
    while r < rend:
        sz = u32(actn, r + 4)
        props.append([u32(actn, r + 8), bytes(actn[r + 12:r + 8 + sz])])
        r += 8 + ((sz + 3) & ~3)
    idx = {pid: i for i, (pid, _) in enumerate(props)}
    if len(STEPS) > 8:
        raise SystemExit('a GDControl has 8 step slots')
    for k in range(8):
        w0 = STEPS[k][0] if k < len(STEPS) else 0
        lst = []
        if k < len(STEPS):
            lst = [target_ids[i] for i in STEPS[k][2]] if len(STEPS[k]) > 2 else target_ids
        props[idx[0x08001819 + 3 * k]][1] = struct.pack('<Iii', w0, DELAY, 0)
        props[idx[0x0800181A + 3 * k]][1] = struct.pack('<I', len(lst)) + b''.join(struct.pack('<I', i) for i in lst)
    body = b''
    for pid, v in props:
        e = b'PROP' + struct.pack('<II', 4 + len(v), pid) + v
        body += e + b'\0' * (-len(e) % 4)
    out = bytearray(actn[:16]) + b'PRPS' + struct.pack('<I', len(body)) + body
    struct.pack_into('<I', out, 4, len(out) - 8)
    return bytes(out)


def main(base, out):
    d = bytearray(Path(base).read_bytes())
    brtr = find_brtr(d)
    tops, _ = top_level_nodes(d, brtr)
    ids = Ids(d)

    # ---- trigger transform (and park the reference it replaces) ----
    pos_b, size_b = g.find_brtr(bytes(d))
    xf = TRIGGER['xf']
    if TRIGGER['replace_ref'] is not None:
        for p, t in chunk_headers(d, pos_b, pos_b + 8 + size_b):
            if t == b'CHBR' and u32(d, p + 12) == TRIGGER['replace_ref']:
                pv = {pid: vo for vo, pid, _ in prop_values(d, p + 24, p + 24 + u32(d, p + 20))}
                xf = list(struct.unpack_from('<12f', d, pv[P_XF]))
                parked = list(xf)
                parked[10] -= 50000.0
                struct.pack_into('<12f', d, pv[P_XF], *parked)
                if P_AABB in pv:
                    b = list(struct.unpack_from('<6f', d, pv[P_AABB]))
                    b[1] -= 50000.0; b[4] -= 50000.0
                    struct.pack_into('<6f', d, pv[P_AABB], *b)
                break
    xf = list(xf)
    xf[:9] = [v * TRIGGER['scale'] for v in xf[:9]]

    # ---- targets ----
    target_blob, target_ids = b'', []
    for t in TARGETS:
        tid = ids.new()
        y = t['pos'][1]
        if y is None:
            y = 2.0 - min(v[1] for v in mesh_positions(d, t['mesh']))
        over = {'prim_region': t['mreg']} if t.get('mreg') else {}
        node = bytearray(build_node(d, tops[t['template']], tid, (t['pos'][0], y, t['pos'][2]), t['mesh'], over))
        if t.get('tint'):
            struct.pack_into('<4f', node, prop_offsets(node)[P_COLOR], *t['tint'])
        target_blob += bytes(node)
        target_ids.append(tid)
    target_ids += list(EXISTING_TARGETS)

    # ---- trigger: clone, hook, control on its root ----
    off, size = tops[TRIGGER['template']]
    trig, remap = clone_subtree(d, off, size, ids)
    ctrl_id = ids.new()
    hooks = {'destroy': P_ROBB, 'hit': P_MEGUT}
    for p, t in chunk_headers(trig, 0, len(trig)):
        if t == b'ACTN' and u32(trig, p + 8) == ROMB_CLASS:
            for vo, pid, ln in prop_values(trig, p, p + 8 + u32(trig, p + 4)):
                if pid in (P_ROBB, P_MEGUT):
                    struct.pack_into('<I', trig, vo, ctrl_id if pid in [hooks[h] for h in TRIGGER['hooks']] else 0)
                elif pid == P_MAXHP and TRIGGER.get('hitpoints') is not None:
                    struct.pack_into('<I', trig, vo, TRIGGER['hitpoints'])
    if TRIGGER['tint']:
        for vo, pid, ln in prop_values(trig, 0, len(trig)):
            if pid == P_COLOR and ln == 16:
                struct.pack_into('<4f', trig, vo, *TRIGGER['tint'])
    place_subtree(trig, xf)
    actn = make_control(ctrl_id, target_ids)
    q = g.align4(24 + u32(trig, 20))
    while trig[q:q + 4] == b'ACTN':                    # after the root's own ACTNs
        q = g.align4(q + 8 + u32(trig, q + 4))
    trig = trig[:q] + actn + trig[q:]
    struct.pack_into('<I', trig, 4, u32(trig, 4) + len(actn))

    append_to_chunk(d, brtr, bytes(trig) + target_blob)
    Path(out).write_bytes(d)
    print(f'trigger {remap[TRIGGER["template"]]:#x} at {[round(v, 1) for v in xf[9:]]} '
          f'(hooks: {", ".join(TRIGGER["hooks"])}); control {ctrl_id:#x}; '
          f'targets {[hex(i) for i in target_ids]}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])

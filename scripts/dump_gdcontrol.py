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

"""Print a level's GDControl scripting in readable form (decoded 2026-10-03).

    python3 scripts/dump_gdcontrol.py GAME_GDWs/START.GDW [REGEX]

REGEX (optional, case-insensitive) keeps only controls whose instance name,
owner node or target names match.

List entries are BRTR node IDs or ACTN IDs (every ACTN block has its own ID,
the second u32 of its header), so a step can address one logic block
directly. Action targets print as "act:<instance name>@<owner node>".
IDs defined nowhere in the file print as "missing#<id>": dangling references
(probably objects deleted during development; the interpreter skips them).

GDControl is the ACTN action (class header 0x0203B039) behind most level
scripting: a timeline of up to 8 steps, m_Ctrl1..8 (PROP 0x08001819 + 3k) with
target lists m_List1..8 (PROP 0x0800181A + 3k). Each m_Ctrl is [w0, w1, w2]:
w0 = action bits (low 16) + scope bits (high 16), and the step fires
w1 + random(0 .. w2 - w1) ticks after the control starts (exactly w1 when
w2 <= w1). w1 is signed: the counter starts at -1, so t=-1 fires the moment
the control starts, one tick before t=0. Engine code: start 0x6B68A0, per-tick executor 0x6B6C00,
interpreter 0x6B6DB0. Full tables in docs/exe_analysis.md ("GDControl").

Output, one block per control:
    [node 2083 "TunnelBlockingDust"] SeaSeekerQuestEventControl  (started by: ...)
      t=0    0x4B000400 suspend               -> TunnelBlockingDust
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brtr_scene_graph as g

u32 = g.u32

GDCONTROL = 0x0203B039
PROP_INSTANCE_NAME = 0x080017C3
PROP_CTRL1, PROP_LIST1 = 0x08001819, 0x0800181A
PROP_DEACT = 0x08001831

# Action bits, in the order the interpreter (0x6B6DB0) tests them.
OPS = [
    (0x0001, 'start'), (0x0002, 'stop'), (0x0004, 'add'), (0x0008, 'kill'),
    (0x0010, 'flags+0x40-0x10'), (0x0020, 'flags+0x10-0x40'), (0x0040, 'flags-0x50'),
    (0x0080, 'show'), (0x0100, 'hide'), (0x0200, 'spawn-copy'),
    (0x0400, 'suspend'), (0x0800, 'resume'), (0x1000, 'add(stored-list)'),
    (0x2000, 'node+0x400000'), (0x4000, 'node-0x400000'),
]
# Modifier bits in the high half that change an action (scope bits aren't printed).
MODS = [(0x00010000, 'restart'), (0x00020000, 'mode4'), (0x00200000, 'at-self'),
        (0x00400000, 'recurse'), (0x00800000, 'recurse')]


def describe(w0):
    ops = [n for b, n in OPS if w0 & b]
    mods = sorted({n for b, n in MODS if w0 & b})
    return ' + '.join(ops) + (f' ({", ".join(mods)})' if mods else '')


def instance_name(props):
    d = props.get(PROP_INSTANCE_NAME, b'')
    return d[4:4+u32(d, 0)].split(b'\0')[0].decode('latin1') if len(d) >= 4 else ''


def controls(data, nodes, actions):
    """Yield (owner_id, action_id, instance_name, steps, deact) for every
    GDControl ACTN, and fill `actions` with {action_id: (owner, name)} for
    every ACTN of any class. steps = [(slot, w0, w1, w2, [target ids])]."""
    pos, size = g.find_brtr(data)

    def walk(start, stop, owner):
        p = start
        while p < stop - 8:
            tag, sz = data[p:p+4], u32(data, p+4)
            a, b = p + 8, p + 8 + sz
            if tag == b'CHBR':
                yield from walk(a + 8, b, u32(data, a + 4))
            elif tag == b'ACTN' and data[a+8:a+12] == b'PRPS':
                props = g._parse_props(data, a + 16, a + 16 + u32(data, a + 12))
                name, aid = instance_name(props), u32(data, a + 4)
                actions[aid] = (owner, name)
                if u32(data, a) != GDCONTROL:
                    p = g.align4(b)
                    continue
                steps = []
                for k in range(8):
                    c, lst = props.get(PROP_CTRL1 + 3*k), props.get(PROP_LIST1 + 3*k)
                    if not c or len(c) < 12:
                        continue
                    w0, w1, w2 = struct.unpack_from('<Iii', c)
                    if w0 & 0xFFFF == 0:      # the interpreter ignores these
                        continue
                    ids = [u32(lst, 4 + 4*i) for i in range(u32(lst, 0))] if lst and len(lst) >= 4 else []
                    steps.append((k + 1, w0, w1, w2, ids))
                yield owner, aid, name, steps, u32(props.get(PROP_DEACT, bytes(4)), 0)
            p = g.align4(b)

    yield from walk(pos + 16, pos + 8 + size, None)


def main(path, pattern=None):
    data = Path(path).read_bytes()
    nodes, _, _ = g.load_nodes(data)
    actions = {}
    ctrls = list(controls(data, nodes, actions))

    def nm(i):
        if i in nodes:
            return nodes[i]['name']
        if i in actions:
            owner, name = actions[i]
            return f'act:{name}@{nodes[owner]["name"] if owner in nodes else "root"}'
        return f'missing#{i}' if i else 'null'

    # Who starts whom: a 'start' step targeting node X (or the action itself)
    # starts X's control.
    started_by = {}
    for owner, aid, name, steps, _ in ctrls:
        for _, w0, _, _, ids in steps:
            if w0 & 1:
                for i in ids:
                    started_by.setdefault(i, []).append(name or nm(owner))

    rx = re.compile(pattern, re.I) if pattern else None
    shown = 0
    for owner, aid, name, steps, deact in ctrls:
        if rx and not any(rx.search(s) for s in [name, nm(owner)] + [nm(i) for st in steps for i in st[4]]):
            continue
        shown += 1
        sb = started_by.get(owner, []) + started_by.get(aid, [])
        head = (f'[node {owner} "{nm(owner)}"] {name}' if owner is not None else f'[root] {name}') + f'  (act {aid})'
        print(head + (f'  (started by: {", ".join(sorted(set(sb)))})' if sb else ''))
        for slot, w0, w1, w2, ids in steps:
            t = f'{w1}..{w2}' if w2 > w1 else f'{w1}'
            tgt = ', '.join(nm(i) for i in ids) or '(none)'
            print(f'  {slot}: t={t:<8} {w0:#010x} {describe(w0):<24} -> {tgt}')
        if deact:
            print(f'  m_DeactProps={deact}')
    print(f'# {shown} of {len(ctrls)} GDControl blocks shown', file=sys.stderr)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)

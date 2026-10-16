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

"""Audit which extracted audio samples the game can play (read-only).

    python3 scripts/audit_audio.py [NAME ...]      (default: all GDWs)

Sounds are played by name, never by sample ID (2026-10-15):

    request 'Group.Name'  ->  sound bank node  ->  GSFX trigger  ->  GSMP sample
    (Jaws.exe string, or       PROP 0x08001939 group,       last field =
     a level PROP string)      0x0800193A names,            sample ID
                               0x0800193B/C ['GSFX'][id]
                               (above / under water)

A bank repeats a name for random variants (FISH 'Human' lists 'Cry' 9 times).
Requests found so far: hardcoded strings in Jaws.exe (~200, e.g. Jaws.Chew,
Human.Fear) and PROP strings in the level: 0x0800192B (sound object node),
0x08001920 and 0x08001936 (sound-event actions). Any other PROP string that
exactly matches a bank's Group.Name is counted too. A GSFX named by a typed
['GSFX'][id] outside a bank (e.g. a class field) counts as used as well.

Status per extracted file in audio/<NAME>/:
  used         a bank name for it is requested (by the exe or this level)
  unrequested  in a bank, but nothing asks for any of its names -> likely unused
  no_bank      has a GSFX trigger, but no bank or other data names it -> unused
  no_gsfx      no GSFX trigger points at it -> unused

Limits: a request only proves the sound can be asked for; the requesting
object or action may itself never run (check with dump_gdcontrol.py). Names
the exe builds at run time from pieces would be missed (none found: no '%s.'
format strings). The whole file is scanned, so the embedded loading-screen
archives are merged with the main one.

Output: audio/audio_audit.csv (one row per file) and audio/audio_audit.txt
(summary + every file that isn't 'used').
"""
import collections
import csv
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GDW_DIR = ROOT / 'GAME_GDWs'
AUDIO = ROOT / 'audio'
EXE = ROOT / 'game_binary' / 'Jaws.exe'

P_GROUP, P_NAMES, P_SFX_AW, P_SFX_UW = 0x08001939, 0x0800193A, 0x0800193B, 0x0800193C
P_OBJ_NAME, P_ACT_NAME = 0x080017D8, 0x080017C3          # node / action names: not requests
BANK_PROPS = {P_GROUP, P_NAMES, P_SFX_AW, P_SFX_UW}
FILE_RE = re.compile(r'_(smpb_|smpc_)?id(\d+)_')
STR_RE = re.compile(rb'PROP(....)(....)(....)([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)\0', re.S)


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def strlist(v):
    out, o = [], 4
    for _ in range(u32(v, 0)):
        n = u32(v, o)
        out.append(v[o + 4:o + 4 + n].split(b'\0')[0].decode('latin-1'))
        o += 4 + ((n + 3) & ~3)
    return out


def gsfx_list(v):
    """['GSFX'][id] per entry; 0 = no sound for that entry."""
    if not v:
        return []
    return [u32(v, 8 + 8 * k) if v[4 + 8 * k:8 + 8 * k] == b'GSFX' else 0 for k in range(u32(v, 0))]


def exe_strings():
    """{'group.name' lowercase: VA} for the exe's hardcoded sound names."""
    d = EXE.read_bytes()
    pe = u32(d, 0x3C)
    nsec, opt = struct.unpack_from('<H', d, pe + 6)[0], struct.unpack_from('<H', d, pe + 20)[0]
    base = u32(d, pe + 52)
    secs = []
    for k in range(nsec):
        s = pe + 24 + opt + 40 * k
        va, raw_size, raw = u32(d, s + 12), u32(d, s + 16), u32(d, s + 20)
        secs.append((raw, raw + raw_size, va))

    def to_va(off):
        for a, z, va in secs:
            if a <= off < z:
                return base + va + off - a
        return None
    out = {}
    # names are often glued to preceding bytes ('JCdSndEv3Jaws.Chew'), so keep every suffix
    for m in re.finditer(rb'([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\0', d):
        g, n = m.group(1), m.group(2)
        for k in range(len(g)):
            key = (g[k:] + b'.' + n).decode('latin-1').lower()
            out.setdefault(key, to_va(m.start(1) + k))
    return out


def owner(d, at):
    """'CHBR 1234 "name"' / 'ACTN 5678 "name"' for the block holding offset `at`."""
    c, a = d.rfind(b'CHBR', 0, at), d.rfind(b'ACTN', 0, at)
    p = max(c, a)
    if p < 0:
        return '?'
    tag, oid = d[p:p + 4].decode(), u32(d, p + 12)
    name, q = '', p + 16
    if d[q:q + 4] == b'PRPS':
        r, end = q + 8, q + 8 + u32(d, q + 4)
        while r < end and d[r:r + 4] == b'PROP':
            s = u32(d, r + 4)
            if u32(d, r + 8) in (P_OBJ_NAME, P_ACT_NAME):
                name = d[r + 16:r + 8 + s].split(b'\0')[0].decode('latin-1')
                break
            r += 8 + ((s + 3) & ~3)
    return f'{tag} {oid}' + (f' "{name}"' if name else '')


def scan_level(d):
    """Returns (gsfx {id: {sample ids}}, banks [(group, name, gsfx_aw, gsfx_uw, offset)],
    requests {'group.name': [(prop id, owner)]}, direct GSFX refs {gsfx id: [where]})."""
    gsfx, heads, p = collections.defaultdict(set), set(), 0
    while (p := d.find(b'GSFX', p)) != -1:
        if p % 4 == 0 and u32(d, p + 4) == 68 and d[p + 68:p + 72] == b'GSMP':
            gsfx[u32(d, p + 8)].add(u32(d, p + 72))
            heads.add(p)
        p += 4

    banks, bank_spans, p = [], [], 0
    pat = struct.pack('<I', P_GROUP)
    while (p := d.find(b'PROP', p)) != -1:
        if d[p + 8:p + 12] == pat:
            q, pr = p, {}
            while d[q:q + 4] == b'PROP':
                s = u32(d, q + 4)
                pr[u32(d, q + 8)] = d[q + 12:q + 8 + s]
                q += 8 + ((s + 3) & ~3)
            if P_NAMES in pr:
                bank_spans.append((p, q))
                grp = pr[P_GROUP][4:].split(b'\0')[0].decode('latin-1')
                aw, uw = gsfx_list(pr.get(P_SFX_AW)), gsfx_list(pr.get(P_SFX_UW))
                for k, nm in enumerate(strlist(pr[P_NAMES])):
                    banks.append((grp, nm, aw[k] if k < len(aw) else 0,
                                  uw[k] if k < len(uw) else 0, p))
            p = q
        else:
            p += 4

    requests = collections.defaultdict(list)
    for m in STR_RE.finditer(d):
        pid = u32(m.group(2), 0)
        if pid in BANK_PROPS or pid in (P_OBJ_NAME, P_ACT_NAME):
            continue
        requests[m.group(4).decode('latin-1').lower()].append((pid, owner(d, m.start())))

    direct = collections.defaultdict(list)
    p = 0
    while (p := d.find(b'GSFX', p)) != -1:
        if p % 4 == 0 and p not in heads:
            i = u32(d, p + 4)
            if i in gsfx and not any(a <= p < z for a, z in bank_spans):
                direct[i].append(owner(d, p))
        p += 4
    return gsfx, banks, requests, direct


def audit(name, exe, all_requests):
    d = (GDW_DIR / f'{name}.GDW').read_bytes()
    gsfx, banks, requests, direct = scan_level(d)
    all_requests[name] = set(requests)
    by_sample = collections.defaultdict(lambda: {'gsfx': set(), 'names': [], 'by': [], 'banked': False})
    for g, samples in gsfx.items():
        for s in samples:
            by_sample[s]['gsfx'].add(g)
    for grp, nm, aw, uw, _ in banks:
        full = f'{grp}.{nm}'
        key = full.lower()
        who = []
        if key in exe:
            who.append(f'exe 0x{exe[key]:X}')
        who += [f'{o} (PROP 0x{pid:08X})' for pid, o in requests.get(key, [])[:3]]
        for g, side in ((aw, 'aw'), (uw, 'uw')):
            for s in gsfx.get(g, ()):
                e = by_sample[s]
                e['banked'] = True
                tag = f'{full}[{side}]'
                if tag not in e['names']:
                    e['names'].append(tag)
                for w in who:
                    if w not in e['by']:
                        e['by'].append(w)
    for g, where in direct.items():
        for s in gsfx[g]:
            for w in where[:3]:
                if f'GSFX {g} in {w}' not in by_sample[s]['by']:
                    by_sample[s]['by'].append(f'GSFX {g} in {w}')
    return by_sample, banks


def main(names):
    exe = exe_strings()
    rows, all_requests, bank_names = [], {}, {}
    for name in names:
        files = sorted((AUDIO / name).glob('*.wav')) if (AUDIO / name).is_dir() else []
        if not files:
            continue
        by_sample, banks = audit(name, exe, all_requests)
        bank_names[name] = {f'{g}.{n}'.lower() for g, n, *_ in banks}
        for f in files:
            m = FILE_RE.search(f.name)
            if not m:
                continue
            sid = int(m.group(2))
            kind = {'smpb_': 'SMPB', 'smpc_': 'SMPC'}.get(m.group(1), 'GSMP')
            e = by_sample.get(sid)
            if e is None or not e['gsfx']:
                status = 'no_gsfx'
            elif e['by']:
                status = 'used'
            elif e['banked']:
                status = 'unrequested'
            else:
                status = 'no_bank'
            rows.append({'gdw': name, 'file': f.relative_to(ROOT).as_posix(), 'sample': sid, 'kind': kind,
                         'status': status, 'gsfx': ' '.join(map(str, sorted(e['gsfx']))) if e else '',
                         'names': ' '.join(e['names']) if e else '',
                         'requested_by': '; '.join(e['by']) if e else ''})
        c = collections.Counter(r['status'] for r in rows if r['gdw'] == name)
        print(f'{name:9} {sum(c.values()):4} files  ' + '  '.join(f'{k} {c[k]}' for k in
              ('used', 'unrequested', 'no_bank', 'no_gsfx')))

    # names asked for only in another level (the bank there may differ, so just a note)
    for r in rows:
        if r['status'] == 'unrequested':
            elsewhere = set()
            for tag in r['names'].split():
                key = tag.rsplit('[', 1)[0].lower()
                elsewhere |= {n for n, req in all_requests.items() if n != r['gdw'] and key in req}
            r['note'] = ('name requested in ' + ' '.join(sorted(elsewhere))) if elsewhere else ''

    fields = ['gdw', 'file', 'sample', 'kind', 'status', 'gsfx', 'names', 'requested_by', 'note']
    with open(AUDIO / 'audio_audit.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})

    c = collections.Counter(r['status'] for r in rows)
    out = [f'# Audio audit ({len(rows)} files): ' + ', '.join(f'{k} {c[k]}' for k in
           ('used', 'unrequested', 'no_bank', 'no_gsfx')),
           '# Made by scripts/audit_audio.py. Statuses: see the script docstring. Full table: audio_audit.csv',
           '']
    for status, title in (('unrequested', 'In a sound bank, but no request for its name (likely unused)'),
                          ('no_bank', 'GSFX trigger exists, but nothing names it (unused)'),
                          ('no_gsfx', 'No GSFX trigger points at it (unused)')):
        sel = [r for r in rows if r['status'] == status]
        out += [f'## {title}: {len(sel)}', '']
        for r in sel:
            extra = f'  {r["names"]}' if r['names'] else ''
            note = f'  ({r["note"]})' if r.get('note') else ''
            out.append(f'{r["file"]}{extra}{note}')
        out.append('')
    (AUDIO / 'audio_audit.txt').write_text('\n'.join(out), encoding='utf-8')
    print('total ' + ', '.join(f'{k} {c[k]}' for k in ('used', 'unrequested', 'no_bank', 'no_gsfx')))
    print(f'wrote {AUDIO / "audio_audit.csv"} and {AUDIO / "audio_audit.txt"}')


if __name__ == '__main__':
    main(sys.argv[1:] or sorted(p.stem for p in GDW_DIR.glob('*.GDW')))

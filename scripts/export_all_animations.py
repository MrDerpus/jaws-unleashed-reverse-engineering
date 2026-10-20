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

"""Export every distinct animated rig to its own .blend (2026-10-20).

Run from the project root (needs Blender on PATH and skeletons/ from
scripts/rip_skeletons.py, models/ and scenes/ from the mesh/scene rippers):
    python3 scripts/export_all_animations.py [--jobs 3] [--only SUBSTR] [--force]

Skeletons with named clips are grouped by (bone count, vertex count, clip
names); each group is one rig, exported once from the first level whose copy
imports cleanly, via scripts/import_skeleton_blender.py. Output:
animations/<Rig>_<LEVEL>_skel<ID>.blend plus animations/index.json and
index.txt (clips, frame counts, every level/skeleton the rig appears in).

Clip-only rigs (a 3-114 vertex placeholder mesh, >= 24 bones: the shared
human clip sets, movie shark/squid/Shaw rigs) get their clips put on a real
body with the identical bone hierarchy, preferring the same level, so the
animation is visible. The placeholder is recorded in the index.
"""
import argparse
import collections
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMPORTER = ROOT / 'scripts' / 'import_skeleton_blender.py'
OUT = ROOT / 'animations'
PREFERRED_HUMAN = ('FISH', 1858)          # MartinWalker, a full 24-bone human body


def load_all():
    sk = {}
    for f in sorted((ROOT / 'skeletons').glob('*/_summary.json')):
        for s in json.load(open(f)):
            sk[(f.parent.name, s['skel_id'])] = s
    return sk


_parents = {}


def parents(key):
    if key not in _parents:
        s = json.load(open(ROOT / 'skeletons' / key[0] / f'skel_{key[1]:05d}.json'))
        _parents[key] = tuple(b['parent'] for b in sorted(s['bones'], key=lambda b: b['index']))
    return _parents[key]


def is_placeholder(s):
    return s['bone_count'] >= 24 and s['vertex_count'] <= 114


def body_candidates(key, sk):
    """Real bodies with the same bone hierarchy as a placeholder clip rig."""
    s = sk[key]
    out = [k for k, t in sk.items()
           if t['meshes'] and t['bone_count'] == s['bone_count']
           and t['vertex_count'] > 200 and parents(k) == parents(key)]
    out.sort(key=lambda k: (k != PREFERRED_HUMAN, k[0] != key[0], -sk[k]['vertex_count'], k))
    return out


def rig_name(s):
    n = s['meshes'][0]['node_name'] if s['meshes'] else s['clip_names'][0]
    n = re.sub(r'\s+\d+$', '', n)
    return re.sub(r'[^A-Za-z0-9]+', '_', n).strip('_') or 'rig'


def plan(sk):
    groups = collections.defaultdict(list)
    for k, s in sk.items():
        if s['clip_names']:
            groups[(s['bone_count'], s['vertex_count'], tuple(s['clip_names']))].append(k)
    jobs = []
    for gkey, members in groups.items():
        members.sort(key=lambda k: (not sk[k]['meshes'], k))
        attempts = []
        for m in members:
            if is_placeholder(sk[m]):
                attempts += [(b, m) for b in body_candidates(m, sk)[:3]]
            elif sk[m]['meshes']:
                attempts.append((m, None))
        jobs.append({'group': gkey, 'members': members, 'attempts': attempts})
    jobs.sort(key=lambda j: (rig_name(sk[j['members'][0]]), j['members'][0]))
    return jobs


def run_job(job, sk, force):
    log = []
    for body, anim in job['attempts']:
        src = anim or body
        name = f"{rig_name(sk[src])}_{src[0]}_skel{src[1]}"
        dst = OUT / f'{name}.blend'
        if dst.exists() and not force:
            return {'file': dst.name, 'body': body, 'anim': anim, 'status': 'exists'}
        cmd = ['systemd-run', '--user', '--scope', '--quiet', '-p', 'MemoryMax=5G',
               'blender', '-b', '--factory-startup', '--python', str(IMPORTER), '--',
               '--root', str(ROOT), '--name', body[0], '--skel', str(body[1]), '--save', str(dst)]
        if anim:
            cmd += ['--anim-skel', str(anim[1]), '--anim-name', anim[0]]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            ok = r.returncode == 0 and dst.exists()
            tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        except subprocess.TimeoutExpired:
            ok, tail = False, ['timeout']
        if ok:
            return {'file': dst.name, 'body': body, 'anim': anim, 'status': 'ok'}
        log.append(f'{body}/{anim}: ' + ' | '.join(tail))
    return {'file': None, 'status': 'failed', 'log': log}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=int, default=3)
    ap.add_argument('--only', help='only rigs whose name or first clip contains this')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    sk = load_all()
    jobs = plan(sk)
    if a.only:
        jobs = [j for j in jobs if a.only.lower() in (rig_name(sk[j['members'][0]]) + ' '
                                                      + ' '.join(j['group'][2])).lower()]
    OUT.mkdir(exist_ok=True)
    print(f'{len(jobs)} rigs, {sum(len(j["group"][2]) for j in jobs)} clips')
    with ThreadPoolExecutor(a.jobs) as ex:
        futs = [ex.submit(run_job, j, sk, a.force) for j in jobs]
        results = []
        for i, (j, f) in enumerate(zip(jobs, futs), 1):
            r = f.result()
            results.append((j, r))
            print(f'[{i}/{len(jobs)}] {r["status"]:7} {r.get("file") or j["members"][0]}', flush=True)

    index = []
    for j, r in results:
        src = r.get('anim') or r.get('body') or j['members'][0]
        s = json.load(open(ROOT / 'skeletons' / src[0] / f'skel_{src[1]:05d}.json'))
        index.append({
            'file': r.get('file'), 'status': r['status'],
            'rig': rig_name(sk[src]), 'bones': j['group'][0], 'vertices': j['group'][1],
            'clips_from': list(src),
            'body': list(r['body']) if r.get('anim') else None,
            'clips': [{'name': c['name'], 'frames': c['end_frame'] - c['start_frame'] + 1}
                      for c in s['animations']],
            'found_in': [list(m) for m in j['members']],
            'log': r.get('log'),
        })
    json.dump(index, open(OUT / 'index.json', 'w'), indent=1)
    with open(OUT / 'index.txt', 'w') as f:
        for e in index:
            f.write(f"{e['file'] or 'FAILED ' + e['rig']}\n"
                    f"  {e['bones']} bones, {e['vertices']} verts, clips from "
                    f"{e['clips_from'][0]} SKEL {e['clips_from'][1]}"
                    + (f", shown on body {e['body'][0]} SKEL {e['body'][1]}" if e['body'] else '') + '\n'
                    f"  in: {', '.join(f'{l} {i}' for l, i in e['found_in'])}\n")
            for c in e['clips']:
                f.write(f"    {c['name']} ({c['frames']} frames)\n")
    bad = [e for e in index if e['status'] == 'failed']
    print(f'done: {len(index) - len(bad)} exported, {len(bad)} failed (see animations/index.json)')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

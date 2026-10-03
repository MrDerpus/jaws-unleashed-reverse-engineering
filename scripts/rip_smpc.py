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

"""Extract captioned voice lines (GSMP 'SMPC' samples) with their subtitles.

    python3 scripts/rip_smpc.py [NAME ...]      (default: all GDWs)

Found 2026-10-03: the in-engine cutscene dialogue lives in GSMP blocks whose
OBPR type tag is 'SMPC' (sample with caption) instead of 'SMPB'. Each one
carries its subtitle text twice, in the OBPR and in the sample header:

    GSMP [size]
      [u32 sample_id][u32 flags 0x21]
      OBPR [n]                      n is not 4-aligned; pad to 4 after it
        PROP [..] [u32 0x04000025] 'SMPC' [u32 len][caption, NUL-padded]
      [u32 0x013131B1][u32 0x22]    0x20 = has caption
      [u32 len][caption, padded to 4]
      [u32 duration_ms][u32 sample_rate][u32 byte_count][u32 pad]
      [byte_count bytes of signed 16-bit mono PCM]

Cutscenes name their sounds ("Movie2.Mayor3"); a sound-bank node in BRTR
(PROP 0x08001939 group name, 0x0800193A names, 0x0800193B/0x0800193C parallel
lists of ['GSFX'][id]) maps each name to a GSFX trigger, whose last field is
the sample ID. That name is written next to each line when it resolves.

Output: audio/<NAME>/<NAME>_smpc_id<id>_<rate>hz_<dur>s.wav and
audio/<NAME>/<NAME>_captions.txt (one line per sample: id, duration, sound
name(s), caption).
"""
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(globals().get('__file__', 'scripts/rip_smpc.py')).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import brtr_scene_graph as g

GDW_DIR = ROOT / 'GAME_GDWs'
OUT_DIR = ROOT / 'audio'
MAGIC = 0x013131B1
P_GROUP, P_NAMES, P_SFX_A, P_SFX_B = 0x08001939, 0x0800193A, 0x0800193B, 0x0800193C


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def smpc_blocks(d):
    """Yield (sample_id, rate, duration_ms, caption, pcm) for every SMPC sample."""
    p = 0
    while (p := d.find(b'GSMP', p)) != -1:
        try:
            size = u32(d, p + 4)
            if not (64 < size < 50_000_000) or d[p + 16:p + 20] != b'OBPR':
                continue
            obpr = u32(d, p + 20)
            tag = d.find(b'SMPC', p + 24, p + 24 + min(obpr, 64))
            if tag == -1:
                continue
            x = (p + 24 + obpr + 3) & ~3
            if u32(d, x) != MAGIC or not u32(d, x + 4) & 0x20:
                continue
            tl = u32(d, x + 8)
            caption = d[x + 12:x + 12 + tl].split(b'\0')[0].decode('latin-1').strip()
            y = x + 12 + ((tl + 3) & ~3)
            dur, rate, count = u32(d, y), u32(d, y + 4), u32(d, y + 8)
            start = y + 16
            if not (4000 <= rate <= 48000) or start + count > p + 8 + size:
                continue
            yield u32(d, p + 8), rate, dur, caption, d[start:start + count]
        finally:
            p += 4


def sound_names(d):
    """{sample_id: ['Group.Name', ...]} from the sound-bank nodes and GSFX triggers."""
    gsfx, p = {}, 0
    while (p := d.find(b'GSFX', p)) != -1:
        if u32(d, p + 4) == 68 and d[p + 68:p + 72] == b'GSMP':
            gsfx[u32(d, p + 8)] = u32(d, p + 72)
        p += 4
    out = {}
    try:
        nodes, _, _ = g.load_nodes(d)
    except RuntimeError:
        return out
    for n in nodes.values():
        pr = n['props']
        if P_GROUP not in pr or P_NAMES not in pr:
            continue
        group = pr[P_GROUP][4:].split(b'\0')[0].decode('latin-1')
        v, names, o = pr[P_NAMES], [], 4
        for _ in range(u32(v, 0)):
            ln = u32(v, o)
            names.append(v[o + 4:o + 4 + ln].split(b'\0')[0].decode('latin-1'))
            o += 4 + ((ln + 3) & ~3)
        for key in (P_SFX_A, P_SFX_B):
            lst = pr.get(key)
            if not lst:
                continue
            for i in range(min(u32(lst, 0), len(names))):
                sid = gsfx.get(u32(lst, 8 + 8 * i))
                if sid is not None:
                    tag = f'{group}.{names[i]}'
                    if tag not in out.setdefault(sid, []):
                        out[sid].append(tag)
    return out


def main(names):
    total = 0
    for name in names:
        path = GDW_DIR / f'{name}.GDW'
        d = path.read_bytes()
        lines = list(smpc_blocks(d))
        if not lines:
            print(f'{name}: 0 captioned samples')
            continue
        snd = sound_names(d)
        out = OUT_DIR / name
        out.mkdir(parents=True, exist_ok=True)
        seen, rows = set(), []
        for sid, rate, dur, caption, pcm in sorted(lines):
            if sid in seen:                           # second embedded archive repeats some
                continue
            seen.add(sid)
            secs = len(pcm) / (rate * 2)
            with wave.open(str(out / f'{name}_smpc_id{sid:04d}_{rate}hz_{secs:.2f}s.wav'), 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(rate)
                w.writeframes(pcm)
            rows.append(f'{sid:5}  {secs:6.2f}s  {", ".join(snd.get(sid, ["-"])):32}  {caption}')
        (out / f'{name}_captions.txt').write_text(
            f'# {name}: {len(rows)} captioned voice samples (GSMP SMPC). id, duration, sound name(s), caption\n'
            + '\n'.join(rows) + '\n', encoding='utf-8')
        total += len(rows)
        print(f'{name}: {len(rows)} captioned samples, {sum(1 for s in seen if s in snd)} with a sound-bank name')
    print(f'total {total}')


if __name__ == '__main__':
    args = sys.argv[1:] or sorted(p.stem for p in GDW_DIR.glob('*.GDW'))
    main(args)

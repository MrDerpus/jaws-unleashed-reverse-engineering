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

"""Stage the Ecco sonar files the mod's Ecco mode loads (mod/src/sonar.h).

    python3 scripts/stage_ecco_sonar.py [--sound WAV] [--drive-c DIR]

Writes, into the Wine prefix's drive_c (default: the Jaws Unleashed Proton
prefix):
  jaws_sonar_cone.obj  Ecco 120NORTH cone Cone01#1 (node 2435), along +Z
  jaws_sonar_wave.obj  the normal-sonar wave: OilTank01#1 (node 2445) plus its
                       child OilTank01#2 (node 2454: scale 0.5, 0.8 along the
                       axis), axis Y = direction of travel (node 2445's local
                       rotation turns mesh Y onto the mover's Z)
  jaws_sonar.wav       the pulse sound (default ECCOCORE sample 15, a guess:
                       the bank has no names; pass --sound to try another)
Inputs come from the extracted Ecco files in ~/Projects/ECCO. The mod reads
them when Ecco mode (Shift+F2) is switched on.
"""
import argparse
import shutil
from pathlib import Path

ECCO = Path.home() / 'Projects' / 'ECCO'
MODELS = ECCO / 'models' / '120NORTH'
DEFAULT_SOUND = ECCO / 'audio' / 'sfx' / 'ECCOCORE' / 'ECCOCORE_15_11025hz.wav'
DEFAULT_DRIVE_C = Path.home() / '.steam/steam/steamapps/compatdata/2342933845/pfx/drive_c'


def read_obj(path):
    verts, faces = [], []
    for line in path.read_text().splitlines():
        f = line.split()
        if not f:
            continue
        if f[0] == 'v':
            verts.append(tuple(float(x) for x in f[1:4]))
        elif f[0] == 'f':
            faces.append([int(c.split('/')[0]) - 1 for c in f[1:]])
    return verts, faces


def write_obj(path, parts, header):
    out = [f'# {header}']
    base = 0
    for verts, faces in parts:
        out += [f'v {x:.6f} {y:.6f} {z:.6f}' for x, y, z in verts]
        out += ['f ' + ' '.join(str(base + i + 1) for i in face) for face in faces]
        base += len(verts)
    path.write_text('\n'.join(out) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--sound', type=Path, default=DEFAULT_SOUND)
    ap.add_argument('--drive-c', type=Path, default=DEFAULT_DRIVE_C)
    a = ap.parse_args()

    cone = read_obj(MODELS / 'sonarkup__Cone01_1.obj')
    outer = read_obj(MODELS / 'sonar__OilTank01_1.obj')
    v2, f2 = read_obj(MODELS / 'sonar__OilTank01_2.obj')
    inner = ([(0.5 * x, 0.5 * y + 0.8, 0.5 * z) for x, y, z in v2], f2)

    write_obj(a.drive_c / 'jaws_sonar_cone.obj', [cone], 'Ecco 120NORTH Cone01#1 (sonar cone)')
    write_obj(a.drive_c / 'jaws_sonar_wave.obj', [outer, inner], 'Ecco 120NORTH OilTank01#1 + #2 (sonar wave)')
    shutil.copyfile(a.sound, a.drive_c / 'jaws_sonar.wav')
    print(f'staged cone ({len(cone[0])} v), wave ({len(outer[0]) + len(inner[0])} v), sound {a.sound.name} -> {a.drive_c}')


if __name__ == '__main__':
    main()

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

import os
import struct
import sys
from pathlib import Path
try:
    from gdw_materials import MaterialResolver
except ImportError:          # run via exec() from scripts/ or the project root
    sys.path.insert(0, '.'); sys.path.insert(0, 'scripts')
    from gdw_materials import MaterialResolver

# =====================================
# CONFIG
# =====================================

NAME = 'FISH'
INPUT_FILE = f'../GAME_GDWs/{NAME}.GDW'
OUTPUT_DIR = Path(f'../models/{NAME}')
TEXTURES_ROOT = '../textures'
MTL_NAME = f'{NAME}_materials.mtl'   # shared by every mesh OBJ in OUTPUT_DIR


# =====================================
# HELPERS
# =====================================

def read_u32(data, offset):
    try:
        return struct.unpack('<I', data[offset:offset + 4])[0]
    except:
        return None

def read_f32(data, offset):
    try:
        return struct.unpack('<f', data[offset:offset + 4])[0]
    except:
        return None

def find_tag(data, tag, start, end):
    p = data.find(tag, start, end)
    if p == -1:
        return None, None
    return p, read_u32(data, p + 4)


# =====================================
# MAIN
# =====================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(INPUT_FILE, 'rb') as f:
        data = f.read()

    print(f'Loaded {len(data):,} bytes from {INPUT_FILE}')
    resolver = MaterialResolver(data, NAME, TEXTURES_ROOT)
    used_textures = {}   # tex_id -> png Path

    offset    = 0
    mesh_idx  = 0
    extracted = 0
    skipped   = 0

    while True:
        pos = data.find(b'GMDL', offset)
        if pos == -1:
            break

        gmdl_size = read_u32(data, pos + 4)
        if not gmdl_size or gmdl_size > 5_000_000:
            offset = pos + 4
            continue

        gmdl_end = pos + 8 + gmdl_size

        posi_pos, posi_sz = find_tag(data, b'POSI', pos, gmdl_end)
        norm_pos, norm_sz = find_tag(data, b'NORM', pos, gmdl_end)
        uvuv_pos, uvuv_sz = find_tag(data, b'UVUV', pos, gmdl_end)
        vind_pos, vind_sz = find_tag(data, b'VIND', pos, gmdl_end)

        if None in (posi_pos, vind_pos) or not posi_sz or not vind_sz:
            mesh_idx += 1
            offset = pos + 4
            skipped += 1
            continue

        n_verts   = posi_sz // 12
        n_indices = vind_sz // 2

        if n_verts < 3 or n_indices < 3:
            mesh_idx += 1
            offset = pos + 4
            skipped += 1
            continue

        indices = struct.unpack_from(f'<{n_indices}H', data, vind_pos + 8)
        if max(indices) >= n_verts:
            mesh_idx += 1
            offset = pos + 4
            skipped += 1
            continue

        # Positions
        verts = []
        for i in range(n_verts):
            base = posi_pos + 8 + i * 12
            verts.append((read_f32(data, base),
                          read_f32(data, base + 4),
                          read_f32(data, base + 8)))

        # Normals
        norms = []
        if norm_pos and norm_sz == posi_sz:
            for i in range(n_verts):
                base = norm_pos + 8 + i * 12
                norms.append((read_f32(data, base),
                               read_f32(data, base + 4),
                               read_f32(data, base + 8)))

        # UVs
        uvs = []
        if uvuv_pos and uvuv_sz == n_verts * 8:
            for i in range(n_verts):
                base = uvuv_pos + 8 + i * 8
                uvs.append((read_f32(data, base),
                             1.0 - read_f32(data, base + 4)))

        # Write OBJ
        fname = OUTPUT_DIR / f'{NAME}_mesh_{mesh_idx:04d}.obj'
        with open(fname, 'w') as f:
            f.write(f'# GMDL @ 0x{pos:X}  verts={n_verts}  tris={n_indices // 3}\n')
            f.write(f'mtllib {MTL_NAME}\n')
            # Per-triangle material from TSET submeshes + MATS -> GMAT -> TEXP
            # (see gdw_materials.py). One usemtl per submesh run.
            tri_mat = ['none'] * (n_indices // 3)
            for first, count, tid, png in resolver.submesh_textures(pos, gmdl_end):
                if png is not None:
                    used_textures[tid] = png
                    for t in range(first, min(first + count, len(tri_mat))):
                        tri_mat[t] = f'mat_{tid}'
            # Handedness: the game is DirectX LEFT-handed (X right, Y up, Z
            # forward -- the shark's right fin "Jobb..." sits at +X); OBJ is
            # RIGHT-handed. Writing raw coordinates mirrors every model, and no
            # rotation can undo a mirror. Negate Z on positions and normals
            # (2026-10-01; replaces the 2026-08-17 winding-swap-only "fix").
            for x, y, z in verts:
                f.write(f'v {x:.6f} {y:.6f} {-z:.6f}\n')
            for nx, ny, nz in norms:
                f.write(f'vn {nx:.6f} {ny:.6f} {-nz:.6f}\n')
            for u, v in uvs:
                f.write(f'vt {u:.6f} {v:.6f}\n')
            has_uv = bool(uvs)
            has_n  = bool(norms)
            cur_mat = None
            for i in range(0, n_indices - 2, 3):
                if tri_mat[i // 3] != cur_mat:
                    cur_mat = tri_mat[i // 3]
                    f.write(f'usemtl {cur_mat}\n')
                # Original VIND order. With Z mirrored (above), the game's own
                # order is already counter-clockwise-front: verified 2026-10-01,
                # 2307/2363 sampled FISH triangles' cross-product normals agree
                # with the stored NORM data in mirrored space with the original
                # order (8/2363 with the old b<->c swap). The 2026-08-17 swap was
                # only right for raw, un-mirrored coordinates.
                a = indices[i] + 1
                b = indices[i + 1] + 1
                c = indices[i + 2] + 1
                if has_uv and has_n:
                    f.write(f'f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n')
                elif has_n:
                    f.write(f'f {a}//{a} {b}//{b} {c}//{c}\n')
                else:
                    f.write(f'f {a} {b} {c}\n')

        print(f'  [{mesh_idx:04d}] {fname.name}  verts={n_verts}  tris={n_indices // 3}')
        extracted += 1
        mesh_idx  += 1
        offset = pos + 4

    # Shared material library for this GDW's mesh OBJs
    with open(OUTPUT_DIR / MTL_NAME, 'w') as fm:
        fm.write(f'# Jaws Unleashed -- {NAME} mesh materials (base texture per GMAT, same-GDW textures only)\n')
        fm.write('newmtl none\nKd 0.6 0.6 0.6\n\n')
        for tid, png in sorted(used_textures.items()):
            rel = os.path.relpath(png, OUTPUT_DIR)
            fm.write(f'newmtl mat_{tid}\nKa 1.0 1.0 1.0\nKd 1.0 1.0 1.0\nmap_Kd {Path(rel).as_posix()}\n\n')
    print(f'Materials : {len(used_textures)} textures -> {OUTPUT_DIR / MTL_NAME}')

    print(f'\nExtracted : {extracted}')
    print(f'Skipped   : {skipped}')
    print(f'Output    : {OUTPUT_DIR}')


if __name__ == '__main__':
    main()

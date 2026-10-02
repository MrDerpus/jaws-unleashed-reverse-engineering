"""
Mesh -> texture resolution for GDW meshes (decoded 2026-10-01).

How a GMDL mesh is textured:

  GMDL
    MATS  [uint32 n] then n x ['GMAT' 4-byte tag][uint32 gmat_resource_id]
    TSET  [uint32 n] then n x [set_idx, first_vert, vert_count, first_tri, tri_count]
          -> triangle SETS (submeshes), not texture IDs. Record i covers
             triangles first_tri .. first_tri+tri_count-1 of the VIND list.
             Its material is MATS entry i (n matches on 383/384 FISH meshes).
  GMAT resource block (elsewhere in RSRC):
    ['GMAT'][size][uint32 id][uint32 flags]['OBPR'][...] ... sub-chunks incl.
    TEXP  [uint32 n] then n x ['GTEX' 4-byte tag][uint32 texture_id]
          -> first entry is the base (diffuse) texture; extra entries are
             further layers (e.g. detail/environment), not used here.

Before this, rip_brtr_scene.py read TSET's vertex counts as texture IDs, so
every texture it assigned was a coincidental ID collision.

Textures are looked up only among the PNGs extracted from the SAME GDW:
texture IDs collide across GDWs (same ID, unrelated image), so borrowing from
another GDW gives wrong results. A texture ID with no PNG in the GDW, or whose
PNG is a flat single color (an unfilled runtime render target), resolves to
None.
"""

import re
import struct
from functools import lru_cache
from pathlib import Path


def _u32(data, off):
    return struct.unpack_from('<I', data, off)[0]


def build_gmat_index(data):
    """{gmat_id: [texture_id, ...]} from every GMAT resource block's TEXP.
    First occurrence of an id wins (the primary archive comes before the
    embedded loading-screen sub-archives in the file)."""
    out = {}
    q = 0
    while True:
        q = data.find(b'GMAT', q)
        if q == -1:
            break
        size = _u32(data, q + 4)
        if 0 < size < 100_000 and data[q+16:q+20] == b'OBPR':
            gid = _u32(data, q + 8)
            if gid not in out:
                end = q + 8 + size
                t = data.find(b'TEXP', q, end)
                ids = []
                if t != -1:
                    tsz = _u32(data, t + 4)
                    n = _u32(data, t + 8)
                    if n and 4 + n * 8 <= tsz:
                        for i in range(n):
                            tag, tid = struct.unpack_from('<4sI', data, t + 12 + 8*i)
                            if tag == b'GTEX':
                                ids.append(tid)
                out[gid] = ids
        q += 4
    return out


def mesh_submeshes(data, gmdl_pos, gmdl_end):
    """[(first_tri, tri_count, gmat_id_or_None), ...] for one GMDL, or [] if it
    has no usable TSET."""
    t = data.find(b'TSET', gmdl_pos, gmdl_end)
    if t == -1:
        return []
    n = _u32(data, t + 8)
    if not n or n > 256 or _u32(data, t + 4) != (1 + n * 5) * 4:
        return []
    mats = []
    m = data.find(b'MATS', gmdl_pos, gmdl_end)
    if m != -1:
        mn = _u32(data, m + 8)
        if 0 < mn <= 256 and _u32(data, m + 4) == 4 + mn * 8:
            for i in range(mn):
                tag, gid = struct.unpack_from('<4sI', data, m + 12 + 8*i)
                mats.append(gid if tag == b'GMAT' else None)
    subs = []
    for i in range(n):
        _, _, _, first_tri, tri_count = struct.unpack_from('<5I', data, t + 12 + 20*i)
        subs.append((first_tri, tri_count, mats[i] if i < len(mats) else None))
    return subs


def texture_files(textures_root, gdw_name):
    """{texture_id: Path} for PNGs extracted from this GDW only
    (textures/<NAME>/gtex/*_id<hex>_*.png and textures/<NAME>/gtext/...).
    GTEX is preferred when both exist for an id."""
    out = {}
    base = Path(textures_root) / gdw_name
    for sub in ('gtext', 'gtex'):              # gtex second, so it wins
        for p in sorted((base / sub).glob('*.png')):
            m = re.search(r'_id([0-9a-f]{8})_', p.name)
            if m:
                out[int(m.group(1), 16)] = p
    return out


@lru_cache(maxsize=None)
def is_blank_png(path):
    """True if the PNG is a single flat color (unfilled runtime render target)."""
    try:
        from PIL import Image
    except ImportError:
        return False
    with Image.open(path) as im:
        lo_hi = im.convert('RGBA').getextrema()
    return all(lo == hi for lo, hi in lo_hi)


class MaterialResolver:
    """Per-GDW: resolves a GMDL's submeshes to texture PNGs."""

    def __init__(self, data, gdw_name, textures_root='textures'):
        self.data = data
        self.gmat = build_gmat_index(data)
        self.files = texture_files(textures_root, gdw_name)

    def texture_for_gmat(self, gid):
        """(texture_id, Path) for a material's base texture, or (tid_or_None, None)."""
        ids = self.gmat.get(gid) or []
        if not ids:
            return None, None
        tid = ids[0]
        p = self.files.get(tid)
        if p is None or is_blank_png(str(p)):
            return tid, None
        return tid, p

    def submesh_textures(self, gmdl_pos, gmdl_end):
        """[(first_tri, tri_count, texture_id_or_None, Path_or_None), ...]"""
        out = []
        for first, count, gid in mesh_submeshes(self.data, gmdl_pos, gmdl_end):
            tid, p = self.texture_for_gmat(gid) if gid is not None else (None, None)
            out.append((first, count, tid, p))
        return out

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

"""Blender -> Jaws Unleashed scene export.

Run in Blender's Scripting workspace (or `blender -b file.blend --python this`).
Exports every mesh object in the collection named COLLECTION (or, if there
is no such collection, the selected objects) to EXPORT_DIR (default: a
'blender_export' folder next to the saved .blend file):
    <mesh>.obj        one per unique mesh (linked duplicates share one)
    manifest.json     objects with game-space transforms, for build_scene.py
Then on the game side:
    python3 scripts/build_scene.py BASE.GDW OUT.GDW EXPORT_DIR [--deploy]

Coordinates: the game is left-handed, Y up; Blender is right-handed, Z up.
game = C . blender with C = swap Y and Z (same mapping as
scenes/import_fish_blender.py's CONV). Blender's origin lands at GAME_ORIGIN
and Blender units are multiplied by GAME_SCALE.

Each object's scale (and GAME_SCALE) is baked into its exported mesh; the
game node gets only rotation + translation, so collision regions are built at
the final size.

Per-object custom properties (Object Properties > Custom Properties):
    jaws_collision  0 to make the object non-solid (default: solid)
    jaws_gmat       game material ID for faces with no usable Blender
                    material (default DEFAULT_GMAT)
    jaws_exit       1 = not geometry but an exit zone: swimming into it
                    leaves the level the way the base level's own exit does
                    (FISH/TEST: back to Open Ocean South). An Empty's radius
                    is its display size x its largest X/Y scale; a mesh's is
                    half its largest X/Y size. Zones are vertical columns
                    (any depth). Written to the manifest as 'exits'. Its
                    material's colour (Base Color, or Viewport Display) is
                    the colour of build_scene.py's --show-exits marker.

Materials: a material named gmat_<id> / mat_<texture id> uses that game
material (a Blender duplicate suffix like mat_272.001 is ignored). Any other material with an Image Texture node (preferably feeding
Principled Base Color) becomes a new game texture + material: the image is
copied (file on disk) or saved as PNG (packed/generated) into EXPORT_DIR, and
build_scene.py converts it. Materials without an image fall back to jaws_gmat.
Transparency follows the material's Blend Mode and Backface Culling settings:
Opaque -> 24-bit texture; Alpha Blend -> smooth blending; Alpha Clip/Hashed ->
cut-out (on/off per pixel, like the game's seaweed). Images keep their alpha
only when the Blend Mode isn't Opaque.
"""
import json
import os
import re
import shutil

import bpy

COLLECTION = 'JAWS'
EXPORT_DIR = ''   # '' = a 'blender_export' folder next to the saved .blend (else ~/blender_export)
GAME_ORIGIN = (2160.0, -25.0, -3650.0)  # FISH/TEST: open water next to the whale
GAME_SCALE = 15.0
DEFAULT_GMAT = 1073                       # FISH rock-wall material


def swap_yz(v):
    return (v[0], v[2], v[1])


def corner_normals(mesh):
    # Blender 4.1+ fills corner_normals; 4.0 has the attribute but leaves it
    # empty, and needs calc_normals_split() + loop.normal instead.
    if len(getattr(mesh, 'corner_normals', ())) == len(mesh.loops):
        return [tuple(n.vector) for n in mesh.corner_normals]
    mesh.calc_normals_split()
    return [tuple(l.normal) for l in mesh.loops]


def material_image(mat):
    """The image a material shows: the Image Texture feeding Base Color, else any."""
    if not (mat and mat.use_nodes and mat.node_tree):
        return None
    nodes = [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
    for n in nodes:
        if any(l.to_socket.name == 'Base Color' for l in n.outputs['Color'].links):
            return n.image
    return nodes[0].image if nodes else None


def export_image(img, dest_dir, stem):
    """Copy an on-disk image, or save a packed/generated one as PNG."""
    src = bpy.path.abspath(img.filepath) if img.filepath else ''
    if src and os.path.isfile(src) and not img.packed_file:
        fname = stem + os.path.splitext(src)[1].lower()
        shutil.copyfile(src, os.path.join(dest_dir, fname))
        return fname
    fname = stem + '.png'
    old_path, old_fmt = img.filepath_raw, img.file_format
    try:
        img.filepath_raw = os.path.join(dest_dir, fname)
        img.file_format = 'PNG'
        img.save()
    finally:
        img.filepath_raw, img.file_format = old_path, old_fmt
    return fname


def alpha_mode(mat):
    """'OPAQUE', 'BLEND' or 'CLIP' from the material's Blend Mode."""
    method = getattr(mat, 'blend_method', 'OPAQUE')           # Blender <= 4.1
    if hasattr(mat, 'surface_render_method') and method == 'OPAQUE':
        method = 'BLEND' if mat.surface_render_method == 'BLENDED' else method   # 4.2+
    return {'BLEND': 'BLEND', 'CLIP': 'CLIP', 'HASHED': 'CLIP'}.get(method, 'OPAQUE')


def material_tokens(objs, dest_dir, materials):
    """{blender material name: usemtl token}; fills `materials` (manifest)."""
    tokens, images = {}, {}
    for obj in objs:
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or mat.name in tokens:
                continue
            # Blender's duplicate suffix (mat_272.001) still means game material 272
            m = re.fullmatch(r'(gmat_(0x[0-9a-fA-F]+|\d+)|mat_\d+)(\.\d+)?', mat.name)
            if m:
                tokens[mat.name] = m.group(1)
                continue
            img = material_image(mat)
            if img is None:
                tokens[mat.name] = '_default'
                continue
            if img.name not in images:
                images[img.name] = export_image(img, dest_dir, f'tex_{len(images):03d}')
            tok = f'bmat_{len(materials):03d}'
            materials[tok] = {'blender_material': mat.name, 'image': images[img.name],
                              'alpha': alpha_mode(mat), 'backface_culling': bool(mat.use_backface_culling)}
            tokens[mat.name] = tok
    return tokens


def write_obj(path, obj, mesh, scale, tokens):
    """Write `mesh` (object-local, scale baked in) as OBJ in OBJ/Blender-export
    convention: OBJ (x, y, z) = Blender (x, z, -y)."""
    sx, sy, sz = (scale * s for s in obj.matrix_world.to_scale())
    mirrored = sx * sy * sz < 0
    mesh.calc_loop_triangles()
    norms = corner_normals(mesh)
    uv = mesh.uv_layers.active.data if mesh.uv_layers.active else None
    slots = [tokens.get(s.material.name, '_default') if s.material else '_default' for s in obj.material_slots]
    lines = [f'# {obj.name} ({mesh.name}), scale {sx:.4f} {sy:.4f} {sz:.4f}']
    groups = {}
    for tri in mesh.loop_triangles:
        groups.setdefault(slots[tri.material_index] if tri.material_index < len(slots) else '_default', []).append(tri)
    vi = 0
    for mat, tris in groups.items():
        lines.append(f'usemtl {mat}')
        for tri in tris:
            loops = list(tri.loops)
            if mirrored:
                loops.reverse()
            face = []
            for li in loops:
                x, y, z = mesh.vertices[mesh.loops[li].vertex_index].co
                x, y, z = x * sx, y * sy, z * sz
                nx, ny, nz = norms[li]
                nx, ny, nz = nx / sx, ny / sy, nz / sz        # inverse-transpose of the scale
                ln = (nx * nx + ny * ny + nz * nz) ** 0.5 or 1.0
                u, v = uv[li].uv if uv else (0.0, 0.0)
                lines.append(f'v {x:.6f} {z:.6f} {-y:.6f}')
                lines.append(f'vn {nx/ln:.6f} {nz/ln:.6f} {-ny/ln:.6f}')
                lines.append(f'vt {u:.6f} {v:.6f}')
                vi += 1
                face.append(vi)
            lines.append('f ' + ' '.join(f'{i}/{i}/{i}' for i in face))
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def game_transform(obj):
    """12 floats, column-major 4x3 like BRTR PROP 0x080017DA: rotation only
    (scale is baked into the mesh), translation mapped to game space."""
    loc, rot, _ = obj.matrix_world.decompose()
    R = rot.to_matrix()
    # Columns of C.R.C: column j of the game basis = C(R[:, C(j)]).
    cols = []
    for j in (0, 2, 1):
        cols += list(swap_yz([R[0][j], R[1][j], R[2][j]]))
    t = swap_yz(loc)
    return cols + [GAME_ORIGIN[i] + GAME_SCALE * t[i] for i in range(3)]


def exit_zone(obj):
    """Exit-zone object -> {'name', 'pos' (game space), 'radius' (game units)}."""
    mw = obj.matrix_world
    if obj.type == 'EMPTY':
        sc = mw.to_scale()
        r = obj.empty_display_size * max(abs(sc.x), abs(sc.y))
        c = mw.translation
    else:
        pts = [mw @ v.co for v in obj.data.vertices]
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        r = max(hi[0] - lo[0], hi[1] - lo[1]) / 2
        c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    t = swap_yz(c)
    zone = {'name': obj.name, 'pos': [GAME_ORIGIN[i] + GAME_SCALE * t[i] for i in range(3)],
            'radius': GAME_SCALE * r}
    col = marker_colour(obj)
    if col:
        zone['colour'] = col
    return zone


def marker_colour(obj):
    """sRGB 0-255 RGBA of an exit object's first material (for build_scene's
    --show-exits markers): Principled Base Color + Alpha when not driven by a
    texture, else the material's Viewport Display colour. None = no material."""
    mat = next((sl.material for sl in obj.material_slots if sl.material), None)
    if mat is None:
        return None
    rgba = list(mat.diffuse_color)
    if mat.use_nodes:
        bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf:
            if not bsdf.inputs['Base Color'].is_linked:
                rgba[:3] = list(bsdf.inputs['Base Color'].default_value)[:3]
            if not bsdf.inputs['Alpha'].is_linked:
                rgba[3] = bsdf.inputs['Alpha'].default_value

    def srgb(c):
        c = max(0.0, min(1.0, c))
        return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return [round(255 * srgb(c)) for c in rgba[:3]] + [round(255 * max(0.0, min(1.0, rgba[3])))]


def export_dir():
    if EXPORT_DIR:
        return EXPORT_DIR
    if bpy.data.filepath:
        return os.path.join(os.path.dirname(bpy.data.filepath), 'blender_export')
    return os.path.join(os.path.expanduser('~'), 'blender_export')


def main():
    global EXPORT_DIR
    EXPORT_DIR = export_dir()
    coll = bpy.data.collections.get(COLLECTION)
    every = list(coll.all_objects if coll else bpy.context.selected_objects)
    exits = [exit_zone(o) for o in every if o.get('jaws_exit') and o.type in ('MESH', 'EMPTY')]
    objs = [o for o in every if o.type == 'MESH' and not o.get('jaws_exit')]
    if not objs:
        raise SystemExit(f'nothing to export: make a collection named {COLLECTION!r} or select mesh objects')
    os.makedirs(EXPORT_DIR, exist_ok=True)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    meshes, objects, materials = {}, [], {}
    tokens = material_tokens(objs, EXPORT_DIR, materials)
    for obj in objs:
        s = tuple(round(GAME_SCALE * c, 5) for c in obj.matrix_world.to_scale())
        # Linked duplicates without modifiers share one game mesh.
        key = obj.name if obj.modifiers else f'{obj.data.name}@{s}'
        gmat = int(obj.get('jaws_gmat', DEFAULT_GMAT))
        if key not in meshes:
            fname = f'mesh_{len(meshes):03d}.obj'
            ev = obj.evaluated_get(depsgraph)
            m = ev.to_mesh()
            write_obj(os.path.join(EXPORT_DIR, fname), obj, m, GAME_SCALE, tokens)
            ev.to_mesh_clear()
            used = sorted({tokens.get(sl.material.name, '_default') if sl.material else '_default'
                           for sl in obj.material_slots})
            meshes[key] = {'obj': fname, 'gmat': gmat, 'source': obj.name, 'tokens': used}
        objects.append({
            'name': obj.name,
            'mesh': key,
            'xf': game_transform(obj),
            'collision': bool(obj.get('jaws_collision', 1)),
        })
    manifest = {'game_origin': GAME_ORIGIN, 'game_scale': GAME_SCALE, 'meshes': meshes,
                'materials': materials, 'objects': objects, 'exits': exits}
    with open(os.path.join(EXPORT_DIR, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1)
    print(f'exported {len(objects)} objects, {len(meshes)} meshes, {len(materials)} textured materials, '
          f'{len(exits)} exit zones to {EXPORT_DIR}')


main()

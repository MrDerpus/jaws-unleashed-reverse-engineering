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

"""Import a skinned, animated Jaws Unleashed model into Blender (2026-10-03).

Builds an armature, a skinned mesh (textured), and one Blender action per
named animation clip from skeletons/<NAME>/skel_<ID>.json (written by
scripts/rip_skeletons.py) plus the model's OBJ in models/<NAME>/.

Run headless:
    blender -b --python scripts/import_skeleton_blender.py -- \\
        --name FISH --skel 1766 [--anim-skel 1770] [--no-root-motion] \\
        [--root /path/to/JAWS] [--save out.blend]
Or open it in Blender's Scripting workspace, edit CONFIG and press Run.

Without --skel, every skeleton in skeletons/<NAME>/ that is used by a scene
node is listed. The great white is FISH 1766 (73 clips). Human bodies have no
clips of their own: borrow them from the shared rig, e.g.
    --name FISH --skel 1858 --anim-skel 1770      (MartinWalker + 75 clips)

Math (see rip_skeletons.py): world_i = world_parent @ [R(q)^T | TRAN_i],
skin_i = world_i @ MTOB_i, v' = sum w_i skin_i v. The game is left-handed,
so every point is mapped with C (Blender X,Y,Z = game X,Z,Y) and every
matrix as C @ M @ C, the same convention as the scene importer. Bones are
created at their rest pose inverse(MTOB); per frame each bone's
matrix_basis is solved so Blender's skinning equals the engine's exactly.
Bones have no names in the data, so they're called bone_00, bone_01, ...
"""
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

# ============================================================
# CONFIG (used when run from Blender's text editor)
# ============================================================

JAWS_ROOT   = ""          # project folder; empty = the folder above this script
NAME        = "FISH"      # GDW stem
SKEL_ID     = 1766        # skeleton to import (FISH 1766 = great white)
ANIM_SKEL   = None        # take clips from another skeleton (humans: 1770)
ROOT_MOTION = True        # move the armature by the clip's root motion
FPS         = 30          # playback rate (engine tick rate not confirmed)
DEFAULT_CLIP = "Uszas"    # first clip whose name contains this becomes active

C = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))   # game <-> Blender


def g2b(m):
    return C @ m @ C


def mat12(xf):
    """12 floats, column-major 4x3 (3 basis columns + translation) -> 4x4."""
    return Matrix(((xf[0], xf[3], xf[6], xf[9]),
                   (xf[1], xf[4], xf[7], xf[10]),
                   (xf[2], xf[5], xf[8], xf[11]),
                   (0, 0, 0, 1)))


def local_matrix(q, tran):
    """Engine bone-local transform: R(q)^T with translation TRAN. R(q)^T is
    the rotation of the conjugate quaternion."""
    x, y, z, w = q
    m = Quaternion((w, -x, -y, -z)).to_matrix().to_4x4()
    m.translation = Vector(tran)
    return m


def world_pose(bones, rots_of, frame):
    """Engine world matrices (game space) for every bone at a pool frame."""
    out = [None] * len(bones)
    for b in bones:                         # engine order lists parents first
        m = local_matrix(rots_of[b['index']][frame], b['tran'])
        out[b['index']] = m if b['parent'] < 0 else out[b['parent']] @ m
    return out


def resolve_root():
    if JAWS_ROOT:
        return Path(JAWS_ROOT)
    here = Path(__file__).resolve()
    for p in [here.parent.parent, Path.cwd()]:
        if (p / 'skeletons').is_dir() and (p / 'models').is_dir():
            return p
    raise SystemExit('Set JAWS_ROOT (or --root) to the project folder')


def find_mesh_obj(root, name, mesh_id):
    """models/<NAME>/<NAME>_mesh_XXXX.obj for a GMDL mesh id, via the scene manifest."""
    man = json.load(open(root / 'scenes' / f'{name}_brtr.json'))
    ents = man if isinstance(man, list) else man.get('instances', man)
    for e in ents:
        if e.get('mesh_id') == mesh_id:
            return root / 'models' / name / f"{name}_mesh_{e['mesh_idx']:04d}.obj"
    raise SystemExit(f'mesh {mesh_id} not found in scenes/{name}_brtr.json')


def read_obj(path):
    """Faces (0-based vertex indices), per-vertex UVs and per-face material
    names, in OBJ vertex order (= GMDL = SKEL vertex order)."""
    uvs, faces, face_mat, mtllib, cur = [], [], [], None, None
    for line in open(path):
        p = line.split()
        if not p:
            continue
        if p[0] == 'vt':
            uvs.append((float(p[1]), float(p[2])))
        elif p[0] == 'f':
            faces.append(tuple(int(t.split('/')[0]) - 1 for t in p[1:]))
            face_mat.append(cur)
        elif p[0] == 'usemtl':
            cur = p[1]
        elif p[0] == 'mtllib':
            mtllib = path.parent / p[1]
    return faces, uvs, face_mat, mtllib


def read_mtl(path):
    tex, cur = {}, None
    if path and path.exists():
        for line in open(path):
            p = line.split(None, 1)
            if len(p) < 2:
                continue
            if p[0] == 'newmtl':
                cur = p[1].strip()
            elif p[0] == 'map_Kd' and cur:
                tex[cur] = (path.parent / p[1].strip()).resolve()
    return tex


def make_material(name, png):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if png and png.exists() and not mat.use_nodes:
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = nt.nodes.get('Principled BSDF')
        img = nt.nodes.new('ShaderNodeTexImage')
        img.location = (-400, 200)
        img.image = bpy.data.images.load(str(png), check_existing=True)
        nt.links.new(img.outputs['Color'], bsdf.inputs['Base Color'])
        if png.name.endswith('_rgba32.png'):
            nt.links.new(img.outputs['Alpha'], bsdf.inputs['Alpha'])
    return mat


def build(root, name, skel_id, anim_skel=None, root_motion=True, fps=30):
    sk = json.load(open(root / 'skeletons' / name / f'skel_{skel_id:05d}.json'))
    an = json.load(open(root / 'skeletons' / name / f'skel_{anim_skel:05d}.json')) if anim_skel else sk
    bones = sk['bones']
    if len(an['bones']) != len(bones):
        raise SystemExit(f'animation skeleton has {len(an["bones"])} bones, model has {len(bones)}')
    if not sk['meshes']:
        raise SystemExit(f'skeleton {skel_id} is not used by any scene node')
    user = sk['meshes'][0]
    label = f"{user['node_name']}_{skel_id}"
    obj_path = find_mesh_obj(root, name, user['mesh_id'])
    faces, uvs, face_mat, mtllib = read_obj(obj_path)
    if len(uvs) != sk['vertex_count']:
        raise SystemExit(f'{obj_path.name}: {len(uvs)} vertices, skeleton has {sk["vertex_count"]}')

    scene = bpy.context.scene
    scene.render.fps = fps

    # ---- armature at rest pose inverse(MTOB) ----
    arm_data = bpy.data.armatures.new(label + '_rig')
    arm = bpy.data.objects.new(label + '_rig', arm_data)
    scene.collection.objects.link(arm)
    arm.show_in_front = True
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    rest_target = [g2b(mat12(b['inv_bind']).inverted()) for b in bones]
    heads = [m.translation.copy() for m in rest_target]
    size = max((h - heads[0]).length for h in heads) or 1.0
    names = [f'bone_{b["index"]:02d}' for b in bones]
    ebs = []
    for b, m in zip(bones, rest_target):
        eb = arm_data.edit_bones.new(names[b['index']])
        # Display length only (the rest matrix sets position and orientation):
        # nearest child, clamped, since some helper bones' children sit far away.
        kids = [heads[c['index']] for c in bones if c['parent'] == b['index']]
        length = min(((k - heads[b['index']]).length for k in kids), default=0.0)
        length = min(max(length, 0.03 * size), 0.15 * size) if length > 0.02 * size else 0.06 * size
        eb.head = (0, 0, 0)
        eb.tail = (0, length, 0)
        mm = m.copy()
        mm.translation = (0, 0, 0)
        eb.matrix = Matrix.Translation(m.translation) @ mm.to_3x3().normalized().to_4x4()
        ebs.append(eb)
    for b in bones:
        if b['parent'] >= 0:
            ebs[b['index']].parent = ebs[b['parent']]
    bpy.ops.object.mode_set(mode='OBJECT')
    rest = [arm_data.bones[n].matrix_local.copy() for n in names]

    # ---- skinned mesh at the rest positions ----
    verts = [(C @ Vector((*p, 1.0))).xyz for p in sk['positions']]
    me = bpy.data.meshes.new(label)
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    tex = read_mtl(mtllib)
    slots = {}
    for i, mname in enumerate(face_mat):
        if mname not in slots:
            slots[mname] = len(slots)
            me.materials.append(make_material(f'{name}_{mname}', tex.get(mname)))
        me.polygons[i].material_index = slots[mname]
    for poly in me.polygons:
        poly.use_smooth = True
    me.update()
    mesh = bpy.data.objects.new(label, me)
    scene.collection.objects.link(mesh)
    mesh.parent = arm
    groups = [mesh.vertex_groups.new(name=n) for n in names]
    for v, ws in enumerate(sk['weights']):
        for bi, w in ws:
            groups[bi].add([v], w, 'ADD')
    mod = mesh.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm

    # ---- one action per clip ----
    rots = {b['index']: b['rotations'] for b in an['bones']}
    inv_bind = [mat12(b['inv_bind']) for b in bones]
    parent_rel = [None] * len(bones)
    for b in bones:
        i, p = b['index'], b['parent']
        parent_rel[i] = (rest[p].inverted() @ rest[i]) if p >= 0 else rest[i]
    track = an.get('track_b') or []
    clips = an['animations'] or [{'name': 'pose', 'start_frame': 0, 'end_frame': 0}]
    arm.rotation_mode = 'QUATERNION'
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    actions = []
    for clip in clips:
        act = bpy.data.actions.new(clip['name'])
        act.use_fake_user = True
        frames = list(range(clip['start_frame'], clip['end_frame'] + 1))
        keys = {}                                # data_path, index -> [(frame, value)]
        prev_q = [None] * len(bones)
        for k, f in enumerate(frames, start=1):
            W = world_pose(bones, rots, f)
            pose = [g2b(W[i] @ inv_bind[i]) @ rest[i] for i in range(len(bones))]
            for b in bones:
                i, p = b['index'], b['parent']
                basis = parent_rel[i].inverted() @ (pose[p].inverted() if p >= 0 else Matrix()) @ pose[i]
                loc, q, _ = basis.decompose()
                if prev_q[i] is not None and q.dot(prev_q[i]) < 0:
                    q.negate()
                prev_q[i] = q
                base = f'pose.bones["{names[i]}"]'
                for j in range(3):
                    keys.setdefault((base + '.location', j, names[i]), []).append((k, loc[j]))
                for j in range(4):
                    keys.setdefault((base + '.rotation_quaternion', j, names[i]), []).append((k, q[j]))
            if root_motion and track:
                d = C @ (Vector(track[f]) - Vector(track[frames[0]])).to_4d()
                for j in range(3):
                    keys.setdefault(('location', j, 'Root motion'), []).append((k, d[j]))
        for (path, j, grp), pts in keys.items():
            fc = act.fcurves.new(path, index=j, action_group=grp)
            fc.keyframe_points.add(len(pts))
            fc.keyframe_points.foreach_set('co', [c for pt in pts for c in pt])
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
            fc.update()
        actions.append((act, len(frames)))

    pick = next((a for a in actions if DEFAULT_CLIP and DEFAULT_CLIP in a[0].name), actions[0])
    arm.animation_data_create().action = pick[0]
    scene.frame_start, scene.frame_end = 1, pick[1]
    scene.frame_set(1)
    print(f'Imported {label}: {len(bones)} bones, {len(verts)} verts, {len(actions)} clips '
          f'(active: {pick[0].name}). Switch clips in the Action Editor.')
    return arm, mesh, actions


def list_skeletons(root, name):
    for f in sorted((root / 'skeletons' / name).glob('skel_*.json')):
        s = json.load(open(f))
        users = ', '.join(m['node_name'] for m in s.get('meshes', [])) or '-'
        print(f"  {s['skel_id']}: {s['bone_count']} bones, {s['vertex_count']} verts, "
              f"{len(s['animations'])} clips, used by {users}")


def main():
    global JAWS_ROOT, NAME, SKEL_ID, ANIM_SKEL, ROOT_MOTION
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    save = None
    if argv:
        SKEL_ID = None
    it = iter(argv)
    for a in it:
        if a == '--name': NAME = next(it)
        elif a == '--skel': SKEL_ID = int(next(it))
        elif a == '--anim-skel': ANIM_SKEL = int(next(it))
        elif a == '--no-root-motion': ROOT_MOTION = False
        elif a == '--root': JAWS_ROOT = next(it)
        elif a == '--save': save = next(it)
    root = resolve_root()
    if SKEL_ID is None:
        print(f'Skeletons in {NAME}:')
        list_skeletons(root, NAME)
        return
    build(root, NAME, SKEL_ID, ANIM_SKEL, ROOT_MOTION, FPS)
    if save:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(save).resolve()))
        print('saved', save)


if __name__ == '__main__':
    main()

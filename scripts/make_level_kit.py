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

"""Create the custom-level kit in levels/custom_fish/ from your own game files
(2026-10-04). See docs/custom_level_tutorial.md.

    python3 scripts/make_level_kit.py [--force] [--kit DIR]
    (default DIR: levels/custom_fish)

Needs GAME_GDWs/FISH.GDW and FISH's extracted textures in textures/FISH/
(scripts/rip_textures.py + scripts/rip_gtex.py), and Blender on the PATH.
Writes, skipping files that already exist unless --force:
  levels/custom_fish/FISH_blank_base.GDW   stock FISH stripped with
                     strip_level.py --blank: only water, sky, sun, shark,
                     HUD and engine plumbing are left, centred on the world
                     origin, stock exit disabled (the build's base level)
  levels/custom_fish/custom_fish.blend       starter scene: a 100x100-unit
                     seafloor in collection JAWS, plus non-exported helpers
                     (water plane, origin) and a palette of FISH materials
                     (mat_<id>); in JAWS also a shark-sized cone with
                     jaws_spawn = 1: move/turn it to set the spawn
  levels/custom_fish/music/<track>.wav      test tones for MUSIC=custom in
                     build.sh (calm_above, calm_under: soft hums; suspense:
                     buzzing drone; action: siren), only if music/ is empty
--force rebuilds both, overwriting custom_fish.blend: keep a copy of your
work first. In the game the level is loaded by the mod (F9, custom_levels/);
no game file is edited.

Run by Blender itself (blender -b --python make_level_kit.py -- OUT.blend),
the same file builds the .blend.
"""
import glob
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
KIT = os.path.join(PROJ, 'levels', 'custom_fish')
ORIGIN = (0.0, -25.0, 0.0)          # = blender_export_scene.GAME_ORIGIN
SCALE = 15.0                        # = blender_export_scene.GAME_SCALE
FLOOR_GAME_Y = -70.0
SIZE = 100.0                        # Blender units (1500 game units)
SPAWN = (0.0, -6.5, 0.0)            # blank base's shark spawn (strip_level.py --blank)
PALETTE = [  # FISH texture id, label
    (272, 'seafloor_sand_green'), (501, 'seafloor_moss'), (153, 'seafloor_dark_moss'),
    (236, 'dry_sand'), (276, 'mussel_bed'), (193, 'rock_mossy'), (238, 'rock_murky'),
    (194, 'cliff_rock_A_top_edge'), (195, 'cliff_rock_B_top_edge'),
    (235, 'shore_sand_grass_edge'), (237, 'shore_rock_grass_edge'), (586, 'canal_grass_edge'),
    (209, 'wood_planks'), (210, 'wood_post'), (232, 'concrete_metal'),
]


def texture_file(tid):
    hits = sorted(glob.glob(os.path.join(PROJ, 'textures', 'FISH', '*', f'*_id{tid:08x}_*.png')))
    if not hits:
        raise SystemExit(f'FISH texture {tid} not found in textures/FISH/: run scripts/rip_textures.py '
                         'and scripts/rip_gtex.py for FISH first')
    return hits[0]


def game_to_blender(x, y, z):
    return ((x - ORIGIN[0]) / SCALE, (z - ORIGIN[2]) / SCALE, (y - ORIGIN[1]) / SCALE)


def build_blend(out):
    """Runs inside Blender."""
    import bpy
    kit = os.path.dirname(out)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'

    def make_material(tid):
        mat = bpy.data.materials.new(f'mat_{tid}')
        mat.use_nodes = True
        mat.use_fake_user = True
        nt = mat.node_tree
        nt.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.location = (-400, 300)
        img = bpy.data.images.load(texture_file(tid))
        img.pack()
        tex.image = img
        nt.links.new(tex.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
        return mat

    mats = {tid: make_material(tid) for tid, _ in PALETTE}
    jaws = bpy.data.collections.new('JAWS')
    ref = bpy.data.collections.new('REFERENCE (not exported)')
    scene.collection.children.link(jaws)
    scene.collection.children.link(ref)

    def move_to(obj, coll):
        for c in obj.users_collection:
            c.objects.unlink(obj)
        coll.objects.link(obj)
        return obj

    # Seafloor: gently uneven grid, texture tiled every 4 units
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=80, y_subdivisions=80, size=SIZE,
                                    location=(0, 0, (FLOOR_GAME_Y - ORIGIN[1]) / SCALE))
    floor = move_to(bpy.context.object, jaws)
    floor.name = 'Seafloor'
    tex = bpy.data.textures.new('dunes', 'CLOUDS')
    tex.noise_scale = 1.4
    disp = floor.modifiers.new('Dunes', 'DISPLACE')
    disp.texture, disp.strength, disp.mid_level, disp.texture_coords = tex, 0.8, 0.5, 'GLOBAL'
    bpy.context.view_layer.objects.active = floor
    bpy.ops.object.modifier_apply(modifier='Dunes')
    uv = floor.data.uv_layers.active.data
    for loop in floor.data.loops:
        co = floor.data.vertices[loop.vertex_index].co
        uv[loop.index].uv = (co.x / 4.0, co.y / 4.0)
    floor.data.materials.append(mats[272])
    for p in floor.data.polygons:
        p.use_smooth = True

    # Helpers (not exported)
    bpy.ops.mesh.primitive_plane_add(size=SIZE, location=(0, 0, -ORIGIN[1] / SCALE))
    water = move_to(bpy.context.object, ref)
    water.name = 'REF_WaterSurface (game Y=0)'
    water.display_type = 'WIRE'
    water.hide_render = True
    # shark: ~17 x 8.6 x 5.5 game units, facing game -Z
    bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.29, depth=1.13, location=game_to_blender(*SPAWN),
                                    rotation=(math.radians(90), 0, 0))
    shark = move_to(bpy.context.object, jaws)
    shark.name = 'SPAWN_Shark (nose = -Y)'
    shark.scale = (1.0, 0.64, 1.0)
    shark['jaws_spawn'] = 1
    origin = bpy.data.objects.new('REF_Origin = game (0, -25, 0)', None)
    origin.empty_display_type = 'ARROWS'
    origin.empty_display_size = 2.0
    ref.objects.link(origin)

    for i, (tid, label) in enumerate(PALETTE):
        x = -42 + i * 6
        bpy.ops.mesh.primitive_cube_add(size=4, location=(x, -58, 0))
        cube = move_to(bpy.context.object, ref)
        cube.name = f'PAL_mat_{tid}_{label}'
        cube.data.materials.append(mats[tid])
        bpy.ops.object.text_add(location=(x - 2, -61, -2), rotation=(math.radians(90), 0, 0))
        t = move_to(bpy.context.object, ref)
        t.data.body = f'{tid}\n{label}'
        t.data.size = 0.55
        t.name = f'PAL_label_{tid}'

    readme = os.path.join(kit, 'README.txt')
    if os.path.exists(readme):
        bpy.data.texts.new('README').write(open(readme).read())
    bpy.data.texts.new('blender_export_scene.py').write(
        open(os.path.join(HERE, 'blender_export_scene.py')).read())
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.clip_end = 2000
                        space.shading.color_type = 'TEXTURE'
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print(f'saved {out}')


def write_test_tones(folder):
    """Four 16 s stereo 22050 Hz test tones, one per music layer. Calm layers
    are soft so the harsh suspense/action layers stand out (they're mixed in
    on top, see docs/custom_level_tutorial.md Part 5)."""
    import struct
    import wave
    rate, secs = 22050, 16

    def sq(x):
        return 1.0 if x % 1.0 < 0.5 else -1.0

    def saw(x):
        return 2.0 * (x % 1.0) - 1.0

    def calm(f, pulse):
        return lambda t: (3000 * (0.5 + 0.5 * math.cos(2 * math.pi * pulse * t)) * math.sin(2 * math.pi * f * t),) * 2

    def suspense(t):
        env = 0.6 + 0.4 * sq(2 * t)
        return 28000 * env * saw(110 * t), 28000 * env * saw(111 * t)

    def action(t):
        v = 30000 * sq(600 * t + 600 * (t - math.floor(t * 2) / 2) ** 2 * 2)
        return v, v

    os.makedirs(folder, exist_ok=True)
    for name, gen in (('calm_above', calm(220, 0.5)), ('calm_under', calm(330, 1)),
                      ('suspense', suspense), ('action', action)):
        frames = bytearray()
        for i in range(rate * secs):
            frames += struct.pack('<hh', *(max(-32767, min(32767, int(v))) for v in gen(i / rate)))
        with wave.open(os.path.join(folder, name + '.wav'), 'wb') as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(bytes(frames))


def main(force, kit):
    os.makedirs(kit, exist_ok=True)
    base = os.path.join(kit, 'FISH_blank_base.GDW')
    blend = os.path.join(kit, 'custom_fish.blend')
    if force or not os.path.exists(base):
        sys.path.insert(0, HERE)
        from strip_level import main as strip
        strip(os.path.join(PROJ, 'GAME_GDWs', 'FISH.GDW'), base, blank=True)
        print(f'wrote {base}')
    else:
        print(f'kept existing {base}')
    if force or not os.path.exists(blend):
        for tid, _ in PALETTE:
            texture_file(tid)   # fail early, outside Blender
        r = subprocess.run(['blender', '-b', '--python', os.path.abspath(__file__), '--', blend],
                           capture_output=True, text=True)
        if r.returncode or not os.path.exists(blend):
            print(r.stdout[-2000:], r.stderr[-2000:])
            raise SystemExit('Blender failed to build the starter file')
        print(f'wrote {blend}')
    else:
        print(f'kept existing {blend} (your work)')
    music = os.path.join(kit, 'music')
    if not glob.glob(os.path.join(music, '*')):
        write_test_tones(music)
        print(f'wrote test tones to {music}')
    else:
        print(f'kept existing {music} (your music)')


if __name__ == '__main__':
    if '--' in sys.argv:            # inside Blender
        build_blend(sys.argv[sys.argv.index('--') + 1])
    else:
        kit = sys.argv[sys.argv.index('--kit') + 1] if '--kit' in sys.argv else KIT
        main('--force' in sys.argv, os.path.abspath(kit))

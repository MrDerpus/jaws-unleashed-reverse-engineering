CUSTOM FISH LEVEL
=================

Full step-by-step tutorial: docs/custom_level_tutorial.md

Quick version:
  1. Model in custom_fish.blend, inside the JAWS collection. Save.
  2. ./build.sh            (add --show-exits to see exit zones as coloured columns)
  3. In the game: F9, pick the level (CUSTOM_FISH), Enter. F10 reloads it.
     build.sh installs it as custom_levels/<LEVEL_NAME>.GDW next to Jaws.exe.
  Custom text: jaws_messages.txt (copy it to the Wine prefix's drive_c).
  Music: MUSIC= in build.sh: keep, none, or custom (files in music/ named
  calm_above, calm_under, suspense, action; any format; one calm_above is enough).

Notes:

Scale and position
  1 Blender unit = 15 game units. Blender Z (up) = game Y.
  Blender origin = game (0, -25, 0). The shark spawns at the jaws_spawn
  object (SPAWN_Shark in new kits), else just above the origin.
  The shark is about 1.1 x 0.6 x 0.4 Blender units.
  Water surface = Blender Z 1.67 (REF_WaterSurface). Seafloor sits at
  Blender Z -3 (game Y -70). Move it if you want deeper or shallower water.

What gets exported
  Only objects in the JAWS collection. Everything in
  "REFERENCE (not exported)" is just there to help you.
  The play area is 100 x 100 Blender units (1500 game units). The stripped
  level has no ocean floor of its own, so past the edge of your floor the
  shark can swim into the void. Add walls or rocks if you want a boundary.

Materials
  Easiest: use the mat_<number> materials (see the palette cubes south of
  the area). They map straight to FISH's own game materials, so no new
  textures are added. Keep the names (mat_272 etc.); a Blender copy suffix
  like mat_272.001 is fine.
  Any other material with an Image Texture becomes a new game texture
  (power-of-two resize, max 1024). Its Blend Mode (Opaque / Alpha Blend /
  Alpha Clip) and Backface Culling carry over.
  Tip: textures repeat with the UVs. The seafloor tiles every 4 units.

Per-object options (Object Properties > Custom Properties)
  jaws_collision = 0   swim-through (default: solid)
  jaws_exit = 1        not geometry: an exit zone. Swimming into it leaves
                       to Open Ocean South. Use an Empty (radius = its
                       display size x scale) or a cylinder (radius = half
                       its width). Zones are columns of any depth. The
                       blank base has no exit of its own: add at least one.
  jaws_spawn = 1       not geometry: the shark starts at its origin, facing
                       its -Y. One at most.

Limits
  Big objects are fine: the build cuts anything wider than 300 game units
  (20 Blender units) into tiles of up to 200 game units. One huge object
  would otherwise fade out whenever the shark looks away from it.
  Small but very dense objects (under 20 units across) still have a limit
  of about 21,000 triangles each.
  Apply or keep modifiers as you like (the exporter uses the evaluated mesh).
  Negative scale (mirroring) isn't supported. Apply it first.
  Linked duplicates (Alt+D) share one mesh in-game, which keeps the file small.

When you're done
  Save the .blend, then tell Claude. The export script is included in the
  Text Editor (blender_export_scene.py); Claude can also run it headless.

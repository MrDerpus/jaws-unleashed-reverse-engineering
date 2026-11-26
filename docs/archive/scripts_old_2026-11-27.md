# Scripts

All tools are standalone Python 3 files in `scripts/` (Pillow is the only dependency outside the standard library). They expect your own copy of the game next to them: `GAME_GDWs/` (the 20 `.GDW` files, optionally a PS2 dump in `GAME_GDWs/ps2/`) and, for executable analysis, `game_binary/Jaws.exe`.

## Extraction

Each extraction script has a hard-coded target level (a `NAME` or `name` variable near the top) that you edit before running. Some use relative paths and must be run from a specific folder:

```bash
# From the project root
python3 scripts/rip_meshes.py                # geometry → models/<NAME>/*.obj (+ .mtl)
python3 scripts/rip_brtr_scene.py            # scene graph → scenes/<NAME>_brtr.{obj,mtl,json}
python3 scripts/resolve_brtr_hierarchy.py    # world-space positions for nested scene nodes
python3 scripts/build_texture_db.py          # rebuild textures/texture_db.json after re-extracting
python3 scripts/rip_smpb.py                  # SMPB NPC voice barks → audio/
python3 scripts/rip_smpc.py NAME             # SMPC cutscene dialogue + captions → audio/<NAME>/
python3 scripts/rip_skeletons.py             # skeletons + animation clips → skeletons/<NAME>/*.json
python3 scripts/export_all_animations.py     # every rig and clip → animations/*.blend (needs Blender)

# rip_textures.py and rip_gtex.py must run from scripts/ (they use a ../GAME_GDWs/ relative path)
cd scripts && python3 rip_textures.py && python3 rip_gtex.py   # textures → textures/<NAME>/gtext/ and gtex/

# PS2 asset dump (GAME_GDWs/ps2/)
python3 scripts/rip_gtext_ps2.py             # PS2 native textures (PSMCT32/16, PSMT8)
python3 scripts/rip_meshes_ps2.py            # PS2 triangle-strip meshes
cd scripts && python3 rip_gtex_ps2.py        # PS2 GTEX-tagged sprite/overlay textures → textures/<NAME>_PS2/gtex/ (run from scripts/)
```

To run a per-level script over all 20 levels, see the loop snippets in [`CLAUDE.md`](../CLAUDE.md#running-scripts).

## Analysis

```bash
python3 scripts/audit_audio.py               # which samples anything can request → audio/audio_audit.{csv,txt}
python3 scripts/dump_class_fields.py OUT.json  # the exe's reflection table: every class field
python3 scripts/dump_messages.py             # the exe's on-screen messages with slot numbers → docs/game_messages.txt (local only)
python3 scripts/dump_gdcontrol.py LEVEL.GDW [REGEX]   # a level's scripting (GDControl timelines), readable

# Game World Builder format versions (Ecco: Defender / Sentinels / Jaws); read-only, use python3 -I
python3 -I scripts/gded_lineage.py info FILE...              # version, top-level chunks, class-table sizes
python3 -I scripts/gded_lineage.py prop LEVEL.GDW 0x080017E3 # name any PROP ID from the level's own field table
python3 -I scripts/gded_lineage.py compare A=GLOB B=GLOB     # class-name overlaps between games
python3 -I scripts/gded_lineage.py fields A=GLOB B=GLOB      # per-class field differences
python3 -I scripts/gded_lineage.py placed FILE [CLASS...]    # how often classes are placed in a level
python3 -I scripts/gdrom_ls.py DISC_DIR [--extract OUT REGEX] # list a Dreamcast GD-ROM dump with dates and versions
python3 -I scripts/gdi_raw2iso.py SRC_DIR DST_DIR           # raw 2352-byte GDI data tracks -> 2048-byte .iso tracks for gdrom_ls.py
python3 -I scripts/sh4_asserts.py 1ST_READ.BIN             # 1999 Ecco SH-4 program: GDASSERT call sites with source file + line
python3 -I scripts/ecco1999_match.py ECCO.ELF 0.map 1ST_READ.BIN FUNCS.tsv OUT.tsv  # name 1999 Ecco functions from the 2000 ELF (group-aligned vtables, call graph); also OUT_files.tsv (source file per function); FUNCS.tsv from scripts/ghidra/FuncRanges.java
python3 -I scripts/pvr_decode.py LEVEL.GDE OUTDIR [REGEX]     # Dreamcast PVR textures (Ecco Defender DC, Sentinels) -> PNG; also a library (decode, gde_textures)
python3 -I scripts/dwarf1_classes.py ECCO.ELF [CLASS...|--list] # class layouts from Defender's DWARF v1 debug info → docs/ecco_defender_classes.txt
# Name Jaws.exe functions from Defender's ECCO.ELF (docs/exe_analysis.md "Ecco: Defender debug symbols"):
#   Ghidra: -postScript FuncRanges.java funcs.tsv (scripts/ghidra) and JawsFactories.java → jaws_objects.tsv
python3 -I scripts/ecco_jaws_vtables.py ECCO.ELF game_binary/Jaws.exe jaws_objects.tsv OUTDIR   # vtable slots → OUTDIR/jaws_vnames.tsv
python3 -I scripts/ecco_jaws_strings.py ECCO.ELF game_binary/Jaws.exe funcs.tsv strings.tsv      # shared strings/constants
python3 -I scripts/ecco_jaws_callgraph.py --map 0.MAP ECCO.ELF game_binary/Jaws.exe funcs.tsv names.tsv OUTDIR/jaws_vnames.tsv strings.tsv
#   → names.tsv (result: docs/jaws_function_names.tsv); apply with ApplyLabels.java (address<TAB>Class::name)
```

`scripts/ghidra/` holds headless Ghidra helpers (decompile at an address, string references, functions referencing an address: `RefsDecomp.java`; `AssertMap.java` decompiles every function using a "GDASSERT failed on:" string, for the 1999 SH-4 programs; for SH-4 (Dreamcast) programs also `SetFpscrZero.java` + `sh4_fpmode_filter.py` (drop the FPU-mode forks from decompiled text), `SplitReadOnly.java` / `SetWritable.java` (read-only code so constant-pool values fold), `CreateFuncs.java` (create functions at listed addresses), `UnapplyNames.java` (undo `ApplyLabels`/`ApplyComments`); `DecompAtX.java` respects read-only memory).

## Level editing

These share small libraries and take command-line arguments; run them from `scripts/`. The step-by-step guide is [`custom_level_tutorial.md`](custom_level_tutorial.md); formats, limits and test history are in [`brtr_editing.md`](brtr_editing.md).

| Script | Does |
|---|---|
| `blender_export_scene.py` | runs **in Blender**: exports the `JAWS` collection (meshes, transforms, images, material settings) |
| `build_scene.py BASE OUT EXPORT_DIR [--deploy NAME] [--show-exits] [--tile N]` | one-command level build from a Blender export (large meshes tiled, exit zones built), verified, optionally deployed |
| `strip_level.py IN OUT [--minimal\|--blank]` | blank base level: removes scenery, keeps the gameplay layer and anything it references; `--minimal` also removes NPCs, animals, missions and collectibles; `--blank` (the kit's base) also recentres on the origin and disables the stock exit |
| `prune_level.py IN OUT` | drop resources nothing in the level uses (blank base 127 → 106 MB) |
| `gdw_music.py IN OUT none\|DIR` | replace or silence a level's four music layers |
| `gdw_to_text.py LEVEL.GDW jaws_gdfile_trace.bin OUT.GDW` | rewrite a level in the editor's GDED text format (it loads in-game). Make the trace first: create `jaws_gdfile_trace.on` in the game folder, start the game, load the level (F9), quit, delete the `.on` file. See `docs/exe_analysis.md` "GDED text format" |
| `make_level_kit.py [--force]` | run from the project root: creates `levels/custom_fish/` (minimal base level + starter `.blend`) from your game files |
| `redirect_stage.py IN OUT FROM TO` | make a level entrance load another `.GDW`; no longer needed for custom levels (mod F9) |
| `add_trigger.py BASE OUT` | breakable-object trigger that removes target objects (edit its `CONFIG`) |
| `obj_to_gmdl.py IN OUT model.obj [--gmat ID --scale S --collision]` | single OBJ → game mesh (+ collision) |
| `insert_brtr_node.py IN OUT` | add copies of existing scene nodes (edit `SPECS`) |
| `patch_texture.py ORIG.png NEW.png OUT_DIR [GDW ...]` | replace a texture in place (same size) |
| `edit_fish_wreck_whale.py` | one-off example edit: rotates FISH's ship wreck and shrinks the whale carcass |
| `build_pursuit_test.py [--deploy NAME]` | the cut **Hot Pursuit** stage, playable, built into a copy of MINEMSHA |
| `build_fishball_test.py [--deploy NAME]` | Ecco's unused `MLHalRaj` fish schools placed in a test level |
| `build_ecco_dolphin.py [--deploy NAME]` | Ecco's dolphin model as the player shark's body (pairs with the mod's Ecco mode) |
| `stage_ecco_sonar.py` | copies the sonar meshes and sound for the mod's Ecco-mode sonar |
| `import_skeleton_blender.py` | runs **in Blender**: imports a skinned, animated model |

## Libraries and helpers

| Script | Does |
|---|---|
| `gdw_grow.py` | resize a chunk and fix `FSIZ`/`SKIP`/`FDIR` after it |
| `gdw_textures.py`, `gdw_materials.py` | write new textures/materials; look up a mesh's materials |
| `brtr_scene_graph.py` | shared scene-graph reading (nesting, instancing, transforms) |
| `colours.py` | terminal colour codes used by some scripts' output |
| `md5-texture-assets.py SETTINGS.json` | find extracted texture files with a given MD5 hash (settings: base folder, level folders, hash) |

`scripts/archive/` holds earlier exploration scripts kept for reference; they aren't maintained.

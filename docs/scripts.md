# Scripts

**In short:** every tool is a standalone Python 3 file in `scripts/`. Pillow is the only dependency outside the standard library. The tools fall into four groups: extraction, analysis, level editing, and shared libraries.

**You need your own copy of the game:**
- `GAME_GDWs/`: the 20 `.GDW` files (optionally the PS2 files in `GAME_GDWs/ps2/`);
- `game_binary/Jaws.exe`, for the exe analysis.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/scripts_old_2026-11-27.md`.

---

## Contents

1. [Extraction](#1-extraction)
2. [Analysis](#2-analysis)
3. [Engine history and other games](#3-engine-history-and-other-games)
4. [Naming `Jaws.exe` functions from Defender](#4-naming-jawsexe-functions-from-defender)
5. [Ghidra helpers](#5-ghidra-helpers)
6. [Level editing](#6-level-editing)
7. [Libraries and helpers](#7-libraries-and-helpers)

---

## 1. Extraction

Most extraction scripts have a hard-coded target level: a `NAME` or `name` variable near the top. Edit it before running. To run one over all 20 levels, use the loops in [`CLAUDE.md`](../CLAUDE.md#running-scripts).

**From the project root:**

| Command | Output |
|---|---|
| `python3 scripts/rip_meshes.py` | Meshes → `models/<NAME>/*.obj` (+ `.mtl`) |
| `python3 scripts/rip_brtr_scene.py` | Scene → `scenes/<NAME>_brtr.{obj,mtl,json}` |
| `python3 scripts/resolve_brtr_hierarchy.py` | World positions of nested scene nodes |
| `python3 scripts/build_texture_db.py` | Rebuilds `textures/texture_db.json` after re-extracting |
| `python3 scripts/rip_smpb.py` | `SMPB` NPC voice barks → `audio/` |
| `python3 scripts/rip_smpc.py NAME` | `SMPC` cutscene dialogue + captions → `audio/<NAME>/` |
| `python3 scripts/rip_skeletons.py` | Skeletons and clips → `skeletons/<NAME>/*.json` |
| `python3 scripts/export_all_animations.py` | Every rig and clip → `animations/*.blend` (needs Blender) |

**From `scripts/`** (they use `../GAME_GDWs/`):

```bash
cd scripts && python3 rip_textures.py && python3 rip_gtex.py    # → textures/<NAME>/gtext/ and gtex/
```

**PS2** (`GAME_GDWs/ps2/`):

| Command | Output |
|---|---|
| `python3 scripts/rip_gtext_ps2.py` | PS2 textures (PSMCT32/16, PSMT8) |
| `python3 scripts/rip_meshes_ps2.py` | PS2 triangle-strip meshes |
| `cd scripts && python3 rip_gtex_ps2.py` | PS2 `GTEX` textures → `textures/<NAME>_PS2/gtex/` (run from `scripts/`) |

Formats: `docs/texture_format.md`, `docs/rsrc_formats.md`, `docs/animation_system.md`, `docs/audio_format.md`, `docs/ps2_asset_extraction.md`.

---

## 2. Analysis

| Command | Does |
|---|---|
| `python3 scripts/audit_audio.py` | Which samples anything can request → `audio/audio_audit.{csv,txt}` (`docs/audio_leads.md`) |
| `python3 scripts/dump_class_fields.py OUT.json` | The exe's reflection table: every class field |
| `python3 scripts/dump_messages.py` | The exe's on-screen messages with slot numbers → `docs/game_messages.txt` (local only) |
| `python3 scripts/dump_gdcontrol.py LEVEL.GDW [REGEX]` | A level's scripting (`GDControl` timelines), readable |

---

## 3. Engine history and other games

Read-only; run with `python3 -I`. Background: `docs/gwb_lineage.md`.

**`gded_lineage.py`**, Game World Builder format versions (Ecco: Defender / Sentinels / Jaws):

| Command | Does |
|---|---|
| `gded_lineage.py info FILE...` | Version, top-level chunks, class-table sizes |
| `gded_lineage.py prop LEVEL.GDW 0x080017E3` | Names any `PROP` ID from the level's own field table |
| `gded_lineage.py compare A=GLOB B=GLOB` | Class-name overlaps between games |
| `gded_lineage.py fields A=GLOB B=GLOB` | Per-class field differences |
| `gded_lineage.py placed FILE [CLASS...]` | How often classes are placed in a level |

**Discs, textures and old programs:**

| Command | Does |
|---|---|
| `gdrom_ls.py DISC_DIR [--extract OUT REGEX]` | Lists a Dreamcast GD-ROM dump with dates and versions |
| `gdi_raw2iso.py SRC_DIR DST_DIR` | Raw 2352-byte GDI data tracks → 2048-byte `.iso` tracks for `gdrom_ls.py` |
| `pvr_decode.py LEVEL.GDE OUTDIR [REGEX]` | Dreamcast PVR textures (Defender DC, Sentinels) → PNG; also a library (`decode`, `gde_textures`) |
| `dwarf1_classes.py ECCO.ELF [CLASS...\|--list]` | Class layouts from Defender's DWARF v1 debug info → `docs/ecco_defender_classes.txt` |
| `sh4_asserts.py 1ST_READ.BIN` | 1999 Ecco SH-4 program: `GDASSERT` call sites with source file and line |
| `ecco1999_match.py ECCO.ELF 0.map 1ST_READ.BIN FUNCS.tsv OUT.tsv` | Names 1999 Ecco functions from the 2000 ELF (group-aligned vtables, call graph); also writes `OUT_files.tsv` (source file per function). `FUNCS.tsv` comes from `scripts/ghidra/FuncRanges.java`. |

---

## 4. Naming `Jaws.exe` functions from Defender

How it works: `docs/exe_analysis.md` §2 "Ecco: Defender debug symbols". Run with `python3 -I`.

1. **In Ghidra:** `-postScript FuncRanges.java funcs.tsv` and `JawsFactories.java` → `jaws_objects.tsv`.
2. **Vtables:**
   ```bash
   python3 -I scripts/ecco_jaws_vtables.py ECCO.ELF game_binary/Jaws.exe jaws_objects.tsv OUTDIR
   ```
   → `OUTDIR/jaws_vnames.tsv`
3. **Shared strings and constants:**
   ```bash
   python3 -I scripts/ecco_jaws_strings.py ECCO.ELF game_binary/Jaws.exe funcs.tsv strings.tsv
   ```
4. **Call graph:**
   ```bash
   python3 -I scripts/ecco_jaws_callgraph.py --map 0.MAP ECCO.ELF game_binary/Jaws.exe \
       funcs.tsv names.tsv OUTDIR/jaws_vnames.tsv strings.tsv
   ```
   → `names.tsv` (the result is `docs/jaws_function_names.tsv`)
5. **Apply in Ghidra** with `ApplyLabels.java` (`address<TAB>Class::name`).

---

## 5. Ghidra helpers

In `scripts/ghidra/`. Headless use and paths: `docs/exe_analysis.md` §1.

| Script | Does |
|---|---|
| `DecompAt.java` | Decompiles the function at an address |
| `DecompAtX.java` | The same, respecting read-only memory |
| `DecompStringRefs.java` | Decompiles every function referencing a string |
| `RefsDecomp.java` | Decompiles every function referencing an address |
| `CreateDecomp.java` | Creates functions Ghidra missed (e.g. reached only through a vtable), then decompiles |
| `FuncRanges.java` | Function list |
| `UnapplyNames.java` | Undo `ApplyLabels` / `ApplyComments` |
| `AssertMap.java` | Decompiles every function using a `GDASSERT failed on:` string (1999 SH-4 programs) |
| `CreateFuncs.java` | Creates functions at listed addresses |

**Only in the local `~/tools/ghidra_scripts/`** (not copied to the project): `JawsFactories.java` / `EccoFactories.java` (class → vtable tables), `ApplyLabels.java` / `ApplyComments.java` (apply names or comments from a file), `ApplySlotNames.java`, `ApplyThisTypes.java`.

**For SH-4 (Dreamcast) programs:**
- `SetFpscrZero.java` + `sh4_fpmode_filter.py`: drop the FPU-mode forks from decompiled text.
- `SplitReadOnly.java` / `SetWritable.java`: mark code read-only so constant-pool values fold.

---

## 6. Level editing

These take command-line arguments and share small libraries; run them from `scripts/`.
- Step-by-step guide: [`custom_level_tutorial.md`](custom_level_tutorial.md).
- Formats, limits and test history: [`brtr_editing.md`](brtr_editing.md).

**Building a level:**

| Script | Does |
|---|---|
| `blender_export_scene.py` | Runs **in Blender**: exports the `JAWS` collection (meshes, transforms, images, material settings) |
| `build_scene.py BASE OUT EXPORT_DIR [--deploy NAME] [--show-exits] [--tile N]` | One-command build from a Blender export: large meshes tiled, exit zones built, verified, optionally deployed |
| `make_level_kit.py [--force]` | Run from the project root: creates `levels/custom_fish/` (base level + starter `.blend`) from your game files |
| `strip_level.py IN OUT [--minimal\|--blank]` | Blank base level (below) |
| `prune_level.py IN OUT` | Drops resources nothing in the level uses (blank base: 127 → 106 MB) |
| `gdw_music.py IN OUT none\|DIR` | Replaces or silences a level's four music layers |

**`strip_level.py` modes:**
- default: removes scenery, keeps the gameplay layer and anything it references;
- `--minimal`: also removes NPCs, animals, missions and collectibles;
- `--blank` (the kit's base): also recentres on the origin and disables the stock exit.

**Smaller edits:**

| Script | Does |
|---|---|
| `obj_to_gmdl.py IN OUT model.obj [--gmat ID --scale S --collision]` | One OBJ → game mesh (+ collision) |
| `insert_brtr_node.py IN OUT` | Adds copies of existing scene nodes (edit `SPECS`) |
| `patch_texture.py ORIG.png NEW.png OUT_DIR [GDW ...]` | Replaces a texture in place (same size) |
| `add_trigger.py BASE OUT` | A breakable object that removes target objects (edit its `CONFIG`) |
| `redirect_stage.py IN OUT FROM TO` | Makes a level entrance load another `.GDW`. No longer needed for custom levels (mod F9). |
| `edit_fish_wreck_whale.py` | One-off example: rotates FISH's shipwreck and shrinks the whale carcass |

**`gdw_to_text.py LEVEL.GDW jaws_gdfile_trace.bin OUT.GDW`:** rewrites a level in the editor's text format (it loads in-game). Make the trace first:
1. create `jaws_gdfile_trace.on` in the game folder;
2. start the game and load the level (F9);
3. quit, and delete the `.on` file.

See `docs/exe_analysis.md` §3 "GDED text format".

**Restorations and experiments:**

| Script | Does |
|---|---|
| `build_pursuit_test.py [--deploy NAME]` | The cut **Hot Pursuit** stage, playable, built into a copy of MINEMSHA |
| `build_fishball_test.py [--deploy NAME]` | Ecco's unused `MLHalRaj` fish schools in a test level |
| `build_ecco_dolphin.py [--deploy NAME]` | Ecco's dolphin model as the player's body (pairs with the mod's Ecco mode) |
| `stage_ecco_sonar.py` | Copies the sonar meshes and sound for the mod's Ecco sonar |
| `import_skeleton_blender.py` | Runs **in Blender**: imports a skinned, animated model |

---

## 7. Libraries and helpers

| Script | Does |
|---|---|
| `gdw_grow.py` | Resizes a chunk and fixes `FSIZ`/`SKIP`/`FDIR` after it; `find_brtr` |
| `gdw_textures.py` | Writes new textures and materials |
| `gdw_materials.py` | Looks up a mesh's materials and textures |
| `brtr_scene_graph.py` | Shared scene-graph reading (nesting, instancing, transforms) |
| `colours.py` | Terminal colour codes for some scripts' output |
| `md5-texture-assets.py SETTINGS.json` | Finds extracted texture files with a given MD5 (settings: base folder, level folders, hash) |

`scripts/archive/` holds earlier exploration scripts, kept for reference and not maintained.

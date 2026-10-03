# JAWS — Jaws Unleashed Reverse Engineering

A reverse-engineering project for **Jaws Unleashed** (PC, 2006, Appaloosa Interactive / Majesco). The goal is to fully decode the game's `.GDW` archive format and extract its assets (textures, meshes, animations, audio, and the built scene graph for every level), reconstruct levels in Blender, and understand enough of the engine to mod it. As of October 2026 that last goal includes **building your own levels in Blender and playing them in the running game** (see [the tutorial](docs/custom_level_tutorial.md)).

The PC build runs under Wine/Proton on Linux and uses **DirectX 8** (`d3d8.dll`). A companion PS2 asset dump (`_FISH.GDE` and a full PS2 release) is used as a cross-reference for cut content and format differences.

> **Disclaimer:** This is an unofficial, non-commercial fan research project. *Jaws Unleashed* and all its assets, code, and trademarks are the property of their respective rights holders (Appaloosa Interactive, Majesco Entertainment, Universal Studios). **This repository contains no game files or extracted assets** — only original research tooling (Python scripts), documentation, and the mod source. You need your own legitimate copy of the game to use any of these tools.

## Status at a glance

- **Archive format** — fully mapped: chunk structure, file header, `FDIR` offset index, the concatenated second embedded archive (loading-screen sub-levels), and sector-alignment padding (`SKIP`) are all decoded, and files can be safely **resized and rewritten**.
- **Textures** — fully decoded and extracted, including a rare 8bpp indexed/CLUT format: **4,923 + 2,787 textures** across all 20 GDWs, indexed by a shared texture-ID database (`textures/texture_db.json`). Every texture is a `GTEX` chunk with one of two payload variants. The long-used name "GTEXT" turned out to be `GTEX` followed by a size byte that reads as `T`. New textures can be written byte-exactly.
- **Meshes** — geometry pipeline fully working: **11,948 `.obj` files** extracted across all levels, with per-submesh textures (`TSET` submeshes → `MATS` → `GMAT` → `TEXP`). Meshes can also be **written**: rebuilt shipped meshes come out byte-identical.
- **Scene graph (`BRTR`)** — the pre-built level layout (every placed object, world transform, mesh reference, baked lighting) is fully decoded, including nested transforms, reference instancing and absolute-transform flags, with a working Blender import script. **New objects can be added** and existing scenery can be stripped.
- **Collision (`MREG`)** — the bounding-box tree (`BREG`), triangle order (`STRI`) and node link (`PRIM`) are fully decoded and verified against every collision block in FISH. Collision for new meshes is **generated** and works in-game.
- **Audio** — all sample variants extracted (`GSMP` raw PCM, `SMPB` short NPC barks, and `SMPC`: the **in-engine cutscene voice acting, 49 lines with their subtitle text**), along with the `GSFX` trigger blocks that link sounds to gameplay, plus the pre-rendered `.wmv` cutscene audio.
- **Skeletal animation** — fully decoded: bind mesh, per-vertex bone weights, recursive bone hierarchy, and per-bone quaternion keyframes sliced into named clips (`SKEL`/`BONE`/`WGHT`/`ROTS`/`ANIM`). The skinning math is verified against the shipped meshes, and skinned, animated characters import into Blender (`scripts/import_skeleton_blender.py`).
- **Executable (`Jaws.exe`)** — decompiled in Ghidra: player shark state, scene-object layout, death paths, the reflection/field table, the stage loader, the scene and collision loaders, level scripting (`GDControl`), and the on-screen message tables.
- **PS2 cross-reference** — PS2-native texture (`ZIPN`/GS pixel formats) and mesh (triangle-strip `STRP`) formats fully decoded and extracted for comparison.
- **Live mod** — a `d3d8.dll` proxy (`mod/`) with an XYZ/heading overlay, teleport with bookmarks, invincibility, freecam, fog/sim-pause/foliage toggles, **F10 to reload the current level from disk**, and **per-level replacement of the game's on-screen text** from a text file (no exe patch).
- **Level scripting and triggers** — `GDControl` timelines, breakable-object triggers, and **area triggers** (level entrances/exits) decoded; custom triggers and exit zones work in-game.
- **Cut content** — unshipped missions, an unused map area, a cut collectible and a cut character identified from strings, classes and level data (see [Cut content](#cut-content)).

See [`CLAUDE.md`](CLAUDE.md) for the full, continuously updated technical reference: every format detail, byte offset, and open question lives there. This README is a map of the repo; `CLAUDE.md` is the format spec.

## Building levels in Blender

**Start here: [`docs/custom_level_tutorial.md`](docs/custom_level_tutorial.md)**, a step-by-step tutorial. Confirmed working in-game in October 2026. In short:

1. **Set up once:** `scripts/make_level_kit.py` creates the level kit in `levels/custom_fish/` from your own game files: an empty base level (only water, sky and the shark are left) and a starter `.blend` with a seafloor and a palette of the game's materials. `scripts/redirect_stage.py` makes the game's Fisherman's Isle entrance load your level (`TEST.GDW`) instead, with no executable patching.
2. **Model in Blender**, in a collection named `JAWS`. Textures (the game's own `mat_<id>` materials or your images), transparency, position, rotation and scale all carry over; big objects are cut into tiles automatically. Custom properties: `jaws_collision = 0` makes an object swim-through, `jaws_exit = 1` makes it an **exit zone**.
3. **Build and install** with `levels/custom_fish/build.sh` (`--show-exits` shows exit zones as coloured columns), then press **F10** in-game (mod).
4. **Custom text:** the mod replaces the game's messages per level, for example the exit question, from `C:\jaws_messages.txt`.

The underlying tools (`blender_export_scene.py`, `build_scene.py`, `strip_level.py`, `obj_to_gmdl.py`, `add_trigger.py`), formats, limits and the test history are in [`docs/brtr_editing.md`](docs/brtr_editing.md).

## Repository structure

This repository is **tooling and documentation only** — no game files, extracted assets, or third-party copyrighted text are included. To use the scripts, supply your own copy of the game's `.GDW` files (and, optionally, a PS2 asset dump) locally.

```
JAWS/
├── CLAUDE.md              # Full technical reference: GDW format spec, all decoded chunk
│                           # layouts, scene system, editing rules, mission mapping, cut content
├── docs/                  # Topic write-ups: brtr_editing.md (level editing + Blender pipeline),
│                           # exe_analysis.md (Ghidra findings), cut_content.md, mission_system.md,
│                           # GDW_FORMAT.md, ps2_*.md, etc. CLAUDE.md wins where they conflict
├── levels/custom_fish/    # Custom-level kit: build.sh, README.txt, jaws_messages.txt (the base
│                           # level and starter .blend are generated locally by make_level_kit.py)
├── scripts/               # Extraction and level-editing tools — see "Scripts" below
│   ├── ghidra/            # Headless Ghidra helper scripts (decompile at address / string refs)
│   └── archive/           # Superseded/exploratory scripts kept for reference, not maintained
└── mod/                   # d3d8.dll proxy mod — see mod/README.md for controls, build, deploy
```

Running the scripts produces local output directories that aren't part of the distributed project: `textures/`, `models/`, `scenes/`, `skeletons/`, `audio/`, `dumps/` and `blender_export/`, all generated from your own copy of `GAME_GDWs/` and `game_binary/Jaws.exe`.

## Requirements

- Python 3.9+
- [`Pillow`](https://pypi.org/project/Pillow/) for image input/output: `pip install Pillow`
- No other Python dependencies beyond the standard library.
- Blender 4.0+ for the Blender exporter (`scripts/blender_export_scene.py`); the importer is `scenes/import_fish_blender.py`.
- The `mod/` proxy additionally requires `i686-w64-mingw32-g++` (32-bit MinGW) and `make` — see `mod/README.md`.
- Optional: Ghidra 12.x (JDK 21) for the executable analysis helpers.

## Scripts

The scripts expect your own copy of the game's data alongside them: a `GAME_GDWs/` directory (the 20 `.GDW` files, plus optionally a PS2 asset dump) and, for binary analysis, `game_binary/Jaws.exe`. Place them at the project root next to `scripts/`.

**Extraction** scripts are standalone, each with a hardcoded target GDW (a `NAME`/`name` variable near the top) that you edit before running. Some use relative paths and must be run from a specific directory:

```bash
# From the project root
python3 scripts/rip_meshes.py                # geometry → models/<NAME>/*.obj (+ .mtl)
python3 scripts/rip_brtr_scene.py            # scene graph → scenes/<NAME>_brtr.{obj,mtl,json}
python3 scripts/resolve_brtr_hierarchy.py    # world-space positions for nested scene nodes
python3 scripts/build_texture_db.py          # rebuild textures/texture_db.json after re-extracting
python3 scripts/rip_smpb.py                  # SMPB NPC voice barks → audio/
python3 scripts/rip_smpc.py NAME             # SMPC cutscene dialogue + captions → audio/<NAME>/
python3 scripts/rip_skeletons.py             # skeletons + animation clips → skeletons/<NAME>/*.json
python3 scripts/dump_messages.py             # the exe's on-screen messages with slot numbers → docs/game_messages.txt (local, not in the repo)

# rip_textures.py and rip_gtex.py must run from scripts/ (they use a ../GAME_GDWs/ relative path)
cd scripts && python3 rip_textures.py && python3 rip_gtex.py   # textures → textures/<NAME>/gtext/ and gtex/

# Scripts that reference FISH.GDW directly need to run from GAME_GDWs/
cd GAME_GDWs && python3 ../scripts/archive/object_parser.py   # archived exploration script

# PS2 asset dump (_FISH.GDE / GAME_GDWs/ps2/)
python3 scripts/rip_gtext_ps2.py             # PS2 native textures (PSMCT32/16, PSMT8)
python3 scripts/rip_meshes_ps2.py            # PS2 triangle-strip meshes
```

To re-run the per-GDW scripts across **all 20 archives**, see the batch loop snippets in [`CLAUDE.md`](CLAUDE.md#running-scripts).

**Level-editing** tools share small libraries and take command-line arguments; run them from `scripts/`:

| Script | Does |
|---|---|
| `blender_export_scene.py` | runs **in Blender**: exports the `JAWS` collection (meshes, transforms, images, material settings) |
| `build_scene.py BASE OUT EXPORT_DIR [--deploy NAME] [--show-exits] [--tile N]` | one-command level build from a Blender export (large meshes tiled, exit zones built), verified, optionally deployed |
| `strip_level.py IN OUT [--minimal]` | blank base level: removes scenery, keeps the gameplay layer and anything it references; `--minimal` also removes NPCs, animals, missions and collectibles |
| `make_level_kit.py [--force]` | run from the project root: creates `levels/custom_fish/` (minimal base level + starter `.blend`) from your game files |
| `redirect_stage.py IN OUT FROM TO` | make a level entrance load another `.GDW` (e.g. OPEN_S: `FISH` → `TEST`) |
| `add_trigger.py BASE OUT` | breakable-object trigger that removes target objects (edit its `CONFIG`) |
| `dump_gdcontrol.py LEVEL.GDW [REGEX]` | print a level's scripting (`GDControl` timelines) readably |
| `obj_to_gmdl.py IN OUT model.obj [--gmat ID --scale S --collision]` | single OBJ → game mesh (+ collision) |
| `insert_brtr_node.py IN OUT` | add copies of existing scene nodes (edit `SPECS`) |
| `patch_texture.py ORIG.png NEW.png OUT_DIR [GDW ...]` | replace a texture in place (same size) |
| `gdw_grow.py`, `gdw_textures.py`, `gdw_materials.py` | shared libraries: chunk resizing, texture/material writing, material lookup |

`scripts/archive/` holds earlier exploration scripts kept for reference; their one-off output lives in `dumps/`.

## The GDW format, in brief

`.GDW` files are little-endian, chunk-based binary containers: a 44-byte text preamble, then a chain of `[4-byte tag][uint32 size][payload]` chunks (`FSIZ`, `VERS`, `CLAS`, `RSRC`, `BRTR`, `SCRT`, `SKIP`, `FDIR`, `ENDF`, ...), followed by embedded loading-screen sub-archives that `FDIR` points at. The two largest chunks carry almost everything:

- **`RSRC`** — every raw resource, in one shared ID space: textures (`GTEX`), materials (`GMAT`), meshes (`GMDL`), audio (`GSMP`/`GSFX`), skeletons (`SKEL`), collision (`MREG`), and AI behavior data (`GMOA`/`GSQD`).
- **`BRTR`** — the fully built scene graph: every placed object instance in the level, with world transforms, mesh references, baked vertex lighting, collision links, and the stage logic (`ACTN`).

Growing or shrinking either chunk means fixing `FSIZ`, `SKIP` and the `FDIR` offsets; `scripts/gdw_grow.py` does that. Full byte-level layouts, the coordinate system (the game is left-handed), transform math and the Blender pipelines are documented in [`CLAUDE.md`](CLAUDE.md).

## The mod (`mod/`)

A `d3d8.dll` proxy that hooks the PC build's DirectX 8 device. It reads the player shark's real position from game memory (overlay with XYZ and heading), and adds:
- **F8** teleport, with bookmark slots saved to a hand-editable file;
- **F11** invincibility and infinite hunger;
- **F10** reload of the current level from disk;
- **message overrides**: replace any on-screen message, per level, from `C:\jaws_messages.txt` (slot list: run `scripts/dump_messages.py`, which writes `docs/game_messages.txt` locally);
- **F2** freecam, **F3** screenshots, and **F4/F5/F6** fog, sim-pause and foliage toggles.

See [`mod/README.md`](mod/README.md) for controls, build steps, and Proton deploy instructions (`WINEDLLOVERRIDES="d3d8=native,builtin"`).

## Cut content

Analysis of `game_binary/Jaws.exe`, the PS2 build and the level data found:
- **Hot Pursuit**: a cut story stage between M10 and M11, a jet-ski chase with leftovers placed in `MINEMSHA.GDW` and `OPEN_NE.GDW`.
- **Down the Hatch**: a cut side challenge.
- At least three more removed side challenges, inferred from gaps in the class numbering.
- **Candy Wilson**: a cut character, the Amity Police Chief, in PC-only text.
- **Highlands Bay**: an unused map location.
- **The Trident**: the only collectible category never placed in any level.
- Leftovers such as loose boss-orca meshes and a stray cage gate in `AQUARIUM.GDW`, an unused alternate voice take in `TOWN.GDW`, and hundreds of script references to deleted objects.
- Investigated and ruled out: the suspected "destroy the sub to clear the boulders" objective in `BEACH.GDW` (a deliberately stationary SeaSeeker next to an unfinished canyon).

Full details and evidence are in [`docs/cut_content.md`](docs/cut_content.md), [`docs/mission_system.md`](docs/mission_system.md) and [`CLAUDE.md`](CLAUDE.md#cut-content--missions-and-areas).

## Open problems

Still unresolved:
- The `MOIL` AI sub-chunk.
- Bone names, and how human bodies bind to the shared animation clips at runtime.
- Several property IDs, and the exact meaning of the per-triangle `TFLG` flags.
- The exact test behind the engine's fade-out of very large objects (worked around by tiling).
- Per-level keep/remove lists for stripping levels other than FISH; exits to destinations other than the level's own.

The full list with context is in [`CLAUDE.md`'s Open Problems section](CLAUDE.md#open-problems).

## License

Licensed under the [GNU General Public License, version 3 or (at your option) any later version](LICENSE) (`GPL-3.0-or-later`). Copyright (C) 2026 MrDerpus and contributors. Each source file carries the standard GPL notice. This keeps the project and any derivative tools fully open source — anyone can use, study, modify, and redistribute this code, but redistributed versions (including modified ones) must remain under the GPL and stay source-available. It does not cover the game itself or any of its assets; see the disclaimer above.

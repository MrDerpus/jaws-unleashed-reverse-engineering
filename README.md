# JAWS — Jaws Unleashed Reverse Engineering

A reverse-engineering project for **Jaws Unleashed** (PC, 2006, Appaloosa Interactive / Majesco). The goal is to fully decode the game's `.GDW` archive format and extract its assets (textures, meshes, animations, audio, and the built scene graph for every level), reconstruct levels in Blender, and understand enough of the engine to mod it. As of October 2026 that last goal includes **building new level content in Blender and loading it into the running game**.

The PC build runs under Wine/Proton on Linux and uses **DirectX 8** (`d3d8.dll`). A companion PS2 asset dump (`_FISH.GDE` and a full PS2 release) is used as a cross-reference for cut content and format differences.

> **Disclaimer:** This is an unofficial, non-commercial fan research project. *Jaws Unleashed* and all its assets, code, and trademarks are the property of their respective rights holders (Appaloosa Interactive, Majesco Entertainment, Universal Studios). **This repository contains no game files or extracted assets** — only original research tooling (Python scripts), documentation, and the mod source. You need your own legitimate copy of the game to use any of these tools.

## Status at a glance

- **Archive format** — fully mapped: chunk structure, file header, `FDIR` offset index, the concatenated second embedded archive (loading-screen sub-levels), and sector-alignment padding (`SKIP`) are all decoded, and files can be safely **resized and rewritten**.
- **Textures** — fully decoded and extracted, including a rare 8bpp indexed/CLUT format: **4,923 + 2,787 textures** across all 20 GDWs, indexed by a shared texture-ID database (`textures/texture_db.json`). Every texture is a `GTEX` chunk with one of two payload variants. The long-used name "GTEXT" turned out to be `GTEX` followed by a size byte that reads as `T`. New textures can be written byte-exactly.
- **Meshes** — geometry pipeline fully working: **11,948 `.obj` files** extracted across all levels, with per-submesh textures (`TSET` submeshes → `MATS` → `GMAT` → `TEXP`). Meshes can also be **written**: rebuilt shipped meshes come out byte-identical.
- **Scene graph (`BRTR`)** — the pre-built level layout (every placed object, world transform, mesh reference, baked lighting) is fully decoded, including nested transforms, reference instancing and absolute-transform flags, with a working Blender import script. **New objects can be added** and existing scenery can be stripped.
- **Collision (`MREG`)** — the bounding-box tree (`BREG`), triangle order (`STRI`) and node link (`PRIM`) are fully decoded and verified against every collision block in FISH. Collision for new meshes is **generated** and works in-game.
- **Audio** — both audio chunk types (`GSMP` raw PCM and the `SMPB` variant, which holds short NPC barks that *are* used in-game) extracted, along with the `GSFX` trigger blocks that link sounds to gameplay, plus cutscene `.wmv` audio.
- **Skeletal animation** — fully decoded: bind mesh, per-vertex bone weights, recursive bone hierarchy, and per-bone quaternion keyframes sliced into named clips (`SKEL`/`BONE`/`WGHT`/`ROTS`/`ANIM`). Blender armature/animation import isn't written yet.
- **Executable (`Jaws.exe`)** — decompiled in Ghidra: player shark state, scene-object layout, death paths, the reflection/field table, the stage loader, and the scene and collision loaders.
- **PS2 cross-reference** — PS2-native texture (`ZIPN`/GS pixel formats) and mesh (triangle-strip `STRP`) formats fully decoded and extracted for comparison.
- **Live mod** — a `d3d8.dll` proxy (`mod/`) with an XYZ/heading overlay, teleport with bookmarks, invincibility, freecam, fog/sim-pause/foliage toggles, and **F10 to reload the current level from disk**.
- **Cut content** — unshipped missions, an unused map area, a cut collectible and a cut character identified from strings, classes and level data (see [Cut content](#cut-content)).

See [`CLAUDE.md`](CLAUDE.md) for the full, continuously updated technical reference: every format detail, byte offset, and open question lives there. This README is a map of the repo; `CLAUDE.md` is the format spec.

## Building levels in Blender

Confirmed working in-game on 3 October 2026, using a copy of Fisherman's Isle (`FISH.GDW`) as the test level:

1. **Model in Blender** and put the objects in a collection named `JAWS`. Textures (image textures on materials), transparency (**Blend Mode**: Alpha Blend = smooth fade, Alpha Clip = cut-out; **Backface Culling** = one- or two-sided), position, rotation and scale all carry over. Per object, the custom property `jaws_collision = 0` makes it non-solid; everything else is solid.
2. **Export** by running `scripts/blender_export_scene.py` in Blender's Text Editor. It writes meshes, images and a manifest to a `blender_export/` folder next to your `.blend` file.
3. **Optionally start from a blank level**: `scripts/strip_level.py` removes the level's scenery (rocks, sand, piers, buildings, plants) and keeps the gameplay layer (water, sky, sun, lighting, the shark, NPCs, missions, exits).
4. **Build and deploy** in one command: `scripts/build_scene.py BASE.GDW OUT.GDW <path to blender_export> --deploy TEST`. It creates textures, materials, meshes, generated collision and scene nodes, then verifies the file before copying it into the game.
5. **Press F10** in-game (mod) to reload the level and see the result.

The test level loads through a renamed level transition (Fisherman's Isle → `TEST.GDW`), so no executable patching is involved. Step-by-step instructions, formats, limits and the test history are in [`docs/brtr_editing.md`](docs/brtr_editing.md).

## Repository structure

This repository is **tooling and documentation only** — no game files, extracted assets, or third-party copyrighted text are included. To use the scripts, supply your own copy of the game's `.GDW` files (and, optionally, a PS2 asset dump) locally.

```
JAWS/
├── CLAUDE.md              # Full technical reference: GDW format spec, all decoded chunk
│                           # layouts, scene system, editing rules, mission mapping, cut content
├── docs/                  # Topic write-ups: brtr_editing.md (level editing + Blender pipeline),
│                           # exe_analysis.md (Ghidra findings), cut_content.md, mission_system.md,
│                           # GDW_FORMAT.md, ps2_*.md, etc. CLAUDE.md wins where they conflict
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
python3 scripts/rip_gtex.py                 # GTEX sprite/overlay textures → textures/<NAME>/gtex/
python3 scripts/rip_meshes.py                # geometry → models/<NAME>/*.obj (+ .mtl)
python3 scripts/rip_brtr_scene.py            # scene graph → scenes/<NAME>_brtr.{obj,mtl,json}
python3 scripts/resolve_brtr_hierarchy.py    # world-space positions for nested scene nodes
python3 scripts/build_texture_db.py          # rebuild textures/texture_db.json after re-extracting
python3 scripts/rip_smpb.py                  # SMPB NPC voice barks → audio/
python3 scripts/rip_skeletons.py             # skeletons + animation clips → skeletons/<NAME>/*.json

# rip_textures.py must run from scripts/ (uses a ../GAME_GDWs/ relative path)
cd scripts && python3 rip_textures.py

# Scripts that reference FISH.GDW directly need to run from GAME_GDWs/
cd GAME_GDWs && python3 ../scripts/object_parser.py

# PS2 asset dump (_FISH.GDE / GAME_GDWs/ps2/)
python3 scripts/rip_gtext_ps2.py             # PS2 native textures (PSMCT32/16, PSMT8)
python3 scripts/rip_meshes_ps2.py            # PS2 triangle-strip meshes
```

To re-run the per-GDW scripts across **all 20 archives**, see the batch loop snippets in [`CLAUDE.md`](CLAUDE.md#running-scripts).

**Level-editing** tools share small libraries and take command-line arguments; run them from `scripts/`:

| Script | Does |
|---|---|
| `blender_export_scene.py` | runs **in Blender**: exports the `JAWS` collection (meshes, transforms, images, material settings) |
| `build_scene.py BASE OUT EXPORT_DIR [--deploy NAME]` | one-command level build from a Blender export, verified, optionally deployed |
| `strip_level.py IN OUT` | blank base level: removes scenery, keeps the gameplay layer and anything it references |
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
- A likely cut "destroy the sub to clear the boulders" objective in `BEACH.GDW`.

Full details and evidence are in [`docs/cut_content.md`](docs/cut_content.md), [`docs/mission_system.md`](docs/mission_system.md) and [`CLAUDE.md`](CLAUDE.md#cut-content--missions-and-areas).

## Open problems

Still unresolved:
- Blender armature/animation import for the decoded `SKEL` system.
- The `MOIL` AI sub-chunk.
- In-game cutscene voice acting, which hasn't been found in any extracted audio.
- Several property IDs, and the exact meaning of the per-triangle `TFLG` flags.
- Per-level keep/remove lists for stripping levels other than FISH.

The full list with context is in [`CLAUDE.md`'s Open Problems section](CLAUDE.md#open-problems).

## License

Licensed under the [GNU General Public License v3.0](LICENSE) (GPL-3.0). This keeps the project and any derivative tools fully open source — anyone can use, study, modify, and redistribute this code, but redistributed versions (including modified ones) must remain GPL-3.0 and stay source-available. It does not cover the game itself or any of its assets; see the disclaimer above.

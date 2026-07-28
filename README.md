# JAWS — Jaws Unleashed Reverse Engineering

A reverse-engineering project for **Jaws Unleashed** (PC, 2006, Appaloosa Interactive / Majesco). The goal is to fully decode the game's `.GDW` archive format and extract its assets — textures, meshes, animations, audio, and the built scene graph for every level — with an eye toward reconstructing levels in Blender and, eventually, understanding enough of the engine to support light modding.

The PC build runs under Wine/Proton on Linux and uses **DirectX 8** (`d3d8.dll`). A companion PS2 asset dump (`_FISH.GDE` and a full PS2 release) is used as a cross-reference for cut content and format differences.

> **Disclaimer:** This is an unofficial, non-commercial fan research project. *Jaws Unleashed* and all its assets, code, and trademarks are the property of their respective rights holders (Appaloosa Interactive, Majesco Entertainment, Universal Studios). **This repository contains no game files or extracted assets** — only original research tooling (Python scripts), documentation, and the mod source. You need your own legitimate copy of the game to use any of these tools.

## Status at a glance

- **Archive format** — fully mapped: chunk structure, file header, `FDIR` offset index, the concatenated second embedded archive (loading-screen sub-levels), and sector-alignment padding (`SKIP`) are all decoded.
- **Textures** — both texture systems (`GTEXT` and `GTEX`) fully decoded and extracted, including a rare 8bpp indexed/CLUT format: **4,923 GTEXT + 2,787 GTEX textures** across all 20 GDWs, indexed by a shared global texture-ID database (`textures/texture_db.json`).
- **Meshes** — geometry pipeline fully working: **11,948 `.obj` files** extracted across all levels, including materials (`GMAT`), texture-layer assignments (`TSET`), and vertex colors.
- **Scene graph (`BRTR`)** — the pre-built level layout (every placed object, world transform, mesh reference, baked lighting) is fully decoded and extracted, including nested parent/child transform composition and a working Blender import script.
- **Collision (`MREG`)** — bounding-volume-hierarchy collision data decoded and linked to visual meshes.
- **Audio** — both audio chunk types (`GSMP` raw PCM, `GSMP+SMPB` embedded/cut voice lines) extracted, plus cutscene `.wmv` audio.
- **Skeletal animation** — fully decoded: bind mesh, per-vertex bone weights, recursive bone hierarchy, and per-bone quaternion keyframes sliced into named clips (`SKEL`/`BONE`/`WGHT`/`ROTS`/`ANIM`). All 30 of FISH.GDW's skeletons extract cleanly via `scripts/rip_skeletons.py`; Blender armature/animation import not yet written.
- **PS2 cross-reference** — PS2-native texture (`ZIPN`/GS pixel formats) and mesh (triangle-strip `STRP`) formats fully decoded and extracted from the PS2 asset dump for comparison against the PC build.
- **Live mod** — a working `d3d8.dll` proxy (`mod/`) provides freecam, an in-game overlay, sim pause, and foliage hiding, and has been used to validate hand-edited `BRTR` scene data against the running game.
- **Cut content** — several unshipped missions, an unused map area, and a cut character have been identified from strings/classes in the game binary (see [Cut Content](#cut-content)).

See [`CLAUDE.md`](CLAUDE.md) for the full, continuously-updated technical reference — every format detail, byte offset, and open question in this project lives there. This README is a map of the repo; `CLAUDE.md` is the format spec.

## Repository structure

This repository is **tooling and documentation only** — no game files, extracted assets, or third-party copyrighted text are included. To use the scripts, supply your own copy of the game's `.GDW` files (and, optionally, a PS2 asset dump) locally; none of that is checked in here.

```
JAWS/
├── CLAUDE.md              # Full technical reference: GDW format spec, all decoded chunk
│                           # layouts, scene system, mission mapping, cut content, open problems
├── docs/                  # Earlier/narrower research notes (GDW_FORMAT.md, mission_system.md,
│                           # rendering_system.md, water_system.md, ps2_*.md, etc.) — CLAUDE.md
│                           # supersedes these where they conflict; kept for detailed narrative
├── scripts/                # Extraction pipeline — see "Scripts" below
│   └── archive/            # Superseded/exploratory scripts kept for reference, not maintained
└── mod/                    # d3d8.dll proxy mod (freecam, overlay, sim pause, foliage hide) —
                            # see mod/README.md for controls, build, and deploy instructions
```

Running the scripts locally will additionally produce (all gitignored, not part of this repo): `textures/`, `models/`, `scenes/`, `audio/`, and `dumps/` output directories, populated from your own local copy of `GAME_GDWs/` and `game_binary/Jaws.exe`.

## Requirements

- Python 3.9+
- [`Pillow`](https://pypi.org/project/Pillow/) for image output: `pip install Pillow`
- No other dependencies beyond the standard library.
- The `mod/` proxy additionally requires `i686-w64-mingw32-g++` (32-bit MinGW) and `make` — see `mod/README.md`.

## Scripts

The scripts expect your own copy of the game's data alongside them: a `GAME_GDWs/` directory (containing the 20 `.GDW` files, plus optionally a PS2 asset dump for the PS2-specific scripts) and, for binary-string analysis scripts, `game_binary/Jaws.exe` — neither is included in this repo. Place them at the project root next to `scripts/` to match the paths the scripts expect.

All extraction scripts live in `scripts/` and are standalone — no shared library, no CLI framework. Each has a hardcoded target GDW (a `NAME`/`name` variable near the top) that you edit before running. Some use relative paths and must be run from a specific directory:

```bash
# From the project root
python3 scripts/rip_gtex.py                 # GTEX sprite/overlay textures → textures/<NAME>/gtex/
python3 scripts/rip_meshes.py                # geometry → models/<NAME>/*.obj
python3 scripts/rip_brtr_scene.py            # scene graph → scenes/<NAME>_brtr.{obj,json}
python3 scripts/resolve_brtr_hierarchy.py    # world-space positions for nested scene nodes
python3 scripts/build_texture_db.py          # rebuild textures/texture_db.json after re-extracting
python3 scripts/rip_smpb.py                  # cut/unused NPC voice lines → audio/
python3 scripts/rip_skeletons.py             # skeletons + animation clips → skeletons/<NAME>/*.json

# rip_textures.py must run from scripts/ (uses a ../GAME_GDWs/ relative path)
cd scripts && python3 rip_textures.py

# Scripts that reference FISH.GDW directly need to run from GAME_GDWs/
cd GAME_GDWs && python3 ../scripts/object_parser.py

# PS2 asset dump (_FISH.GDE / GAME_GDWs/ps2/)
python3 scripts/rip_gtext_ps2.py             # PS2 native textures (PSMCT32/16, PSMT8)
python3 scripts/rip_meshes_ps2.py            # PS2 triangle-strip meshes
```

To re-run any of the per-GDW scripts across **all 20 archives**, see the batch loop snippets in [`CLAUDE.md`](CLAUDE.md#running-scripts).

`scripts/archive/` holds earlier, superseded exploration scripts (probes, hunters, dumpers) kept for reference — not part of the maintained pipeline, and their one-off output lives in `dumps/`.

## The GDW format, in brief

`.GDW` files are little-endian, chunk-based binary containers: a 44-byte text preamble, then a chain of `[4-byte tag][uint32 size][payload]` chunks (`FSIZ`, `VERS`, `CLAS`, `RSRC`, `BRTR`, `SCRT`, `FDIR`, `ENDF`, ...). The two largest chunks carry almost everything:

- **`RSRC`** — every raw resource: textures (`GTEXT`/`GTEX`), materials (`GMAT`), meshes (`GMDL`), audio (`GSMP`), skeletons (`SKEL`), collision (`MREG`), and AI behavior data (`GMOA`/`GSQD`).
- **`BRTR`** — the fully-built scene graph: every placed object instance in the level, with world transforms, mesh references, and baked vertex lighting.

Full byte-level layouts for every chunk type, plus the coordinate system, transform math, and the Blender import pipeline, are documented in [`CLAUDE.md`](CLAUDE.md).

## The mod (`mod/`)

A `d3d8.dll` proxy that hooks the PC build's DirectX 8 device to add a freecam, an in-game debug overlay, sim pause, and foliage hiding — useful for exploring levels and validating hand-edited `.GDW` scene data live in-game. See [`mod/README.md`](mod/README.md) for controls, build steps, and Proton deploy instructions (`WINEDLLOVERRIDES="d3d8=native,builtin"`).

## Cut content

String and class-name analysis of `game_binary/Jaws.exe` turned up several unshipped missions (**Down the Hatch**, an untitled jet-ski mission, a two-phase **Pursuit** story stage), a cut character (**Candy Wilson**, Amity Police Chief), and two unused map location names (**Highlands Bay**, **Dolphin Passage**) that never shipped in any GDW. Full details, evidence, and the complete mission-to-GDW mapping are in [`CLAUDE.md`](CLAUDE.md#cut-content--missions-and-areas) and [`docs/mission_system.md`](docs/mission_system.md).

## Open problems

Actively unresolved: Blender armature/animation import for the now-decoded `SKEL` skeleton system, the `MOIL` AI-pathfinding sub-chunk, exact `GMAT`↔`TSET` material/texture-layer linkage, in-game cutscene voice acting (not yet located in any extracted audio), and why a brand-new `BRTR` sibling node fails to render in-game even when byte-for-byte structurally valid (resource injection and repointing/relocating *existing* nodes both work). Full list with context in [`CLAUDE.md`'s Open Problems section](CLAUDE.md#open-problems).

## License

Licensed under the [GNU General Public License v3.0](LICENSE) (GPL-3.0). This keeps the project and any derivative tools fully open source — anyone can use, study, modify, and redistribute this code, but redistributed versions (including modified ones) must remain GPL-3.0 and stay source-available. It does not cover the game itself or any of its assets; see the disclaimer above.

# JAWS — Jaws Unleashed Reverse Engineering

A reverse-engineering project for **Jaws Unleashed** (PC, 2006, Appaloosa Interactive / Majesco). It decodes the game's `.GDW` level archives, extracts their assets (textures, meshes, animations, audio and each level's full scene), rebuilds levels in Blender, and documents enough of the engine to mod it, up to **building your own levels in Blender and playing them in the game** ([tutorial](docs/custom_level_tutorial.md)).

The PC build uses **DirectX 8** and runs on Linux under Proton (we use GE-Proton; see [`mod/README.md`](mod/README.md) "Deploy"). A PS2 release is used as a cross-reference.

Appaloosa made the game with its in-house **Game World Builder** editor (the `.GDW` format is its output) and **Diesel Power** engine. The same toolset made *Ecco the Dolphin: Defender of the Future*, and Jaws was built on the code of its cancelled sequel *Ecco: Sentinels of the Universe*: format versions 2.1.12.1 (every *Defender* build, 2000–2002) → 2.3.2.1 (*Sentinels*, 2001) → 2.6.3.16 (*Jaws*, 2006). After Appaloosa, its team's next game (*SmartyAnts*, 2010, as Twofish) appears to use the licensed Torque engine, so Jaws may be the last Game World Builder game ([`docs/GDW_FORMAT.md`](docs/GDW_FORMAT.md) "Engine lineage" and "Format history 2001–2006", [`docs/ecco_leftovers.md`](docs/ecco_leftovers.md)).

> **Disclaimer:** This is an unofficial, non-commercial fan research project. *Jaws Unleashed* and all its assets, code, and trademarks are the property of their respective rights holders (Appaloosa Interactive, Majesco Entertainment, Universal Studios). **This repository contains no game files or extracted assets** — only original research tooling (Python scripts), documentation, and the mod source. You need your own legitimate copy of the game to use any of these tools.

## What works

- **Archive format:** fully mapped, and files can be resized and rewritten safely. The editor's lost *text* variant still loads in the game: a level converted to text plays. → [GDW format](docs/GDW_FORMAT.md)
- **Textures:** all decoded and extracted (4,923 + 2,787 across 20 levels), and new ones can be written. → [textures](docs/texture_format.md)
- **Meshes and collision:** 11,948 meshes extracted with materials; meshes and collision can be written for new objects. → [resources](docs/rsrc_formats.md)
- **Scene graph:** every placed object, transform and baked light, with a Blender importer; objects can be added or removed, and every property ID has its real name. → [scene graph](docs/scene_graph.md)
- **Animation:** skeletons, skinning and all 754 clips of 150 rigs, exported to Blender. → [animation](docs/animation_system.md)
- **Audio:** all sample types, 49 captioned cutscene lines, an audit of 48 never-played recordings, replaceable level music. → [audio](docs/audio_format.md)
- **Custom levels:** build in Blender, play in the game. → [tutorial](docs/custom_level_tutorial.md)
- **`Jaws.exe`:** decompiled in Ghidra: shark, stage loading, level scripting, messages, collision, controls; 812 functions named from *Ecco: Defender*'s debug symbols. → [exe analysis](docs/exe_analysis.md)
- **Live mod:** a `d3d8.dll` proxy with an overlay, teleport, no-clip, invincibility, far view, custom-level loader, your own controls on every new game, and an Ecco mode. → [mod](mod/README.md)
- **Cut content:** the cut *Hot Pursuit* stage (playable again), the Aurora rope fight, unused side challenges, characters and audio. → [cut content](docs/cut_content.md)
- **Engine history:** every *Ecco: Defender* build we could find (Feb and Apr 2000 prototypes, European and US Dreamcast masters, PS2) compared with *Sentinels* and Jaws, class by class and field by field; when each format change arrived; who exported the levels (matched to the credits); three levels cut from *Defender*'s February 2000 prototype; Appaloosa's cancelled projects. → [GDW format](docs/GDW_FORMAT.md), [Ecco leftovers](docs/ecco_leftovers.md)
- **Speedrun research:** timing, win conditions, skips, collision and level-edge barriers. → [speedrun](docs/speedrun_glitches.md)
- **PS2 version:** its texture and mesh formats decoded for comparison. → [PS2](docs/ps2_asset_extraction.md)

Still unsolved: [`docs/open_problems.md`](docs/open_problems.md).

## Get started

- **Extract assets:** put your game's `.GDW` files in `GAME_GDWs/` and run the scripts in [`docs/scripts.md`](docs/scripts.md).
- **Build a level:** follow [`docs/custom_level_tutorial.md`](docs/custom_level_tutorial.md).
- **Use the mod:** build or copy `d3d8.dll` and follow [`mod/README.md`](mod/README.md). Example settings: [`mod/jaws_config.example.txt`](mod/jaws_config.example.txt).
- **Compare with Ecco:** `gded_lineage.py` (versions, class and field tables), `gdrom_ls.py` (Dreamcast GD-ROM dumps) and `pvr_decode.py` (Dreamcast textures) work on your own *Ecco: Defender* / *Sentinels* files; see [`docs/scripts.md`](docs/scripts.md).

## Documentation

| Topic | Document |
|---|---|
| Archive container, chunks, engine lineage, format versions | [`docs/GDW_FORMAT.md`](docs/GDW_FORMAT.md), [`docs/lineage_field_diff.txt`](docs/lineage_field_diff.txt), [`docs/defender_dc_ps2_field_diff.txt`](docs/defender_dc_ps2_field_diff.txt) |
| Textures | [`docs/texture_format.md`](docs/texture_format.md) |
| Meshes, materials, collision, AI blocks | [`docs/rsrc_formats.md`](docs/rsrc_formats.md) |
| Scene graph (`BRTR`), property IDs, transforms | [`docs/scene_graph.md`](docs/scene_graph.md) |
| Level editing and its rules | [`docs/brtr_editing.md`](docs/brtr_editing.md), [`docs/custom_level_tutorial.md`](docs/custom_level_tutorial.md) |
| Skeletons and animation | [`docs/animation_system.md`](docs/animation_system.md) |
| Audio, unused audio, cutscene dialogue | [`docs/audio_format.md`](docs/audio_format.md), [`docs/audio_leads.md`](docs/audio_leads.md), [`docs/cutscene_dialogue.md`](docs/cutscene_dialogue.md) |
| Rendering, draw distance, water | [`docs/rendering_system.md`](docs/rendering_system.md), [`docs/water_system.md`](docs/water_system.md), [`docs/terrain_and_water_bounds.md`](docs/terrain_and_water_bounds.md) |
| `Jaws.exe` analysis, bite system, class registry | [`docs/exe_analysis.md`](docs/exe_analysis.md), [`docs/bite_system.md`](docs/bite_system.md), [`docs/class_registry.md`](docs/class_registry.md), [`docs/serialization_format.md`](docs/serialization_format.md) |
| Missions and side challenges | [`docs/mission_system.md`](docs/mission_system.md) |
| Cut content | [`docs/cut_content.md`](docs/cut_content.md) |
| Ecco leftovers, Ecco dolphin controller, cancelled Appaloosa projects (Mermaid demo, Parrot, Smurfs), Twofish's *SmartyAnts* (2010) | [`docs/ecco_leftovers.md`](docs/ecco_leftovers.md), [`docs/ecco_dolphin_controller.md`](docs/ecco_dolphin_controller.md) |
| Speedrun research | [`docs/speedrun_glitches.md`](docs/speedrun_glitches.md) |
| PS2 version | [`docs/ps2_asset_extraction.md`](docs/ps2_asset_extraction.md), [`docs/ps2_cut_content_findings.md`](docs/ps2_cut_content_findings.md), [`docs/ps2_dataset_inventory.md`](docs/ps2_dataset_inventory.md), [`docs/ps2_disassembly_notes.md`](docs/ps2_disassembly_notes.md) |
| The mod | [`mod/README.md`](mod/README.md) |
| Scripts | [`docs/scripts.md`](docs/scripts.md) |
| Open problems | [`docs/open_problems.md`](docs/open_problems.md) |
| Historical notes (early research, superseded) | `docs/archive/` (`ai-notes.md`, `context.md`, `_findings.md`, `findings_updated.md`, plus the pre-2026-11-27 versions of every doc) |

[`CLAUDE.md`](CLAUDE.md) is a compact index of the essentials and the working rules used while researching.

## Repository structure

```
JAWS/
├── CLAUDE.md          # Compact index: essentials, rules, where each detail lives
├── docs/              # All write-ups (see the table above); sources/ holds cited press material
├── levels/custom_fish/# Custom-level kit (build.sh etc.; the base level and .blend are generated locally)
├── scripts/           # Extraction, analysis and level-editing tools (docs/scripts.md)
│   ├── ghidra/        # Headless Ghidra helpers
│   └── archive/       # Superseded exploration scripts, not maintained
└── mod/               # d3d8.dll proxy mod (mod/README.md)
```

Running the scripts creates local output folders (`textures/`, `models/`, `scenes/`, `skeletons/`, `audio/`, `animations/`, …) from your own `GAME_GDWs/` and `game_binary/Jaws.exe`; none of them are part of the repository.

## Requirements

- Python 3.9+
- [`Pillow`](https://pypi.org/project/Pillow/) for image input/output: `pip install Pillow`
- No other Python dependencies beyond the standard library.
- Blender 4.0+ for the Blender exporter (`scripts/blender_export_scene.py`), the skeleton importer and the animation export; the scene importer is `scenes/import_fish_blender.py`.
- `ffmpeg` for replacing level music (`scripts/gdw_music.py`).
- The `mod/` proxy additionally requires `i686-w64-mingw32-g++` (32-bit MinGW) and `make` — see `mod/README.md`.
- Optional: Ghidra 12.x (JDK 21) for the executable analysis helpers.

## License

Licensed under the [GNU General Public License, version 3 or (at your option) any later version](LICENSE) (`GPL-3.0-or-later`). Copyright (C) 2026 MrDerpus and contributors. Each source file carries the standard GPL notice. This keeps the project and any derivative tools fully open source — anyone can use, study, modify, and redistribute this code, but redistributed versions (including modified ones) must remain under the GPL and stay source-available. It does not cover the game itself or any of its assets; see the disclaimer above.

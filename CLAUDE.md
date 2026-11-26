# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a reverse engineering project for *Jaws Unleashed* (PC version, 2006, developed by Appaloosa Interactive). The goal is to parse and extract assets from the game's `.GDW` archive format — textures, meshes, animations, serialized gameplay objects — and eventually reconstruct scenes in Blender. The game runs on Linux via **GE-Proton11-9** (since 2026-10-16, user-confirmed: Valve's Proton 10.0 showed a placeholder for the WMV movies because it has no WMV2/WMA2 decoder for non-Steam games; the mod loads the same; see `mod/README.md` "Deploy" and `docs/exe_analysis.md` "Movie playback"). The PC version uses **DirectX 8** (`d3d8.dll`), not DX9 and not the PS2 VIF/GIF rendering pipeline.

## Running Scripts

All scripts live in `scripts/` and are standalone Python files. Run from the project root or from within `scripts/` depending on the script's hardcoded `INPUT_FILE` paths (some use relative paths like `'../GAME_GDWs/FISH.GDW'`, others use `'FISH.GDW'` meaning they expect to be run from `GAME_GDWs/`).

```bash
# From project root
python3 scripts/rip_textures.py

# Scripts that reference FISH.GDW directly need to run from GAME_GDWs/
cd GAME_GDWs && python3 ../scripts/archive/object_parser.py   # archived exploration script
```

**Dependency:** `Pillow` for image output (`pip install Pillow`). No other dependencies beyond stdlib.

**Typical script workflow:**
1. Edit `NAME` / `name` variable at top of script to target a different `.GDW`
2. Run script — outputs go to a directory specified by `OUTPUT_DIR` in the script
3. Results are `.png`, `.raw`, or `.txt` files

**Run a script across all GDWs at once:**
```bash
# rip_gtex.py uses NAME (uppercase) and, like rip_textures.py, must run from scripts/ (../GAME_GDWs/ path)
cd scripts
for name in AQUARIUM ARMADA BEACH BEACHPST CHASE DEEPSEA2 DEEPSEA DOCKS FISH GAUNTLET KATATAMA MINEMSHA OPEN_NE OPEN_NW OPEN_S START TITLE0 TITLE TOWN WRACK; do
    python3 -c "
import re; from pathlib import Path
script = Path('rip_gtex.py').read_text()
script = re.sub(r\"^NAME = .*\$\", \"NAME = '$name'\", script, flags=re.MULTILINE)
exec(compile(script, 'rip_gtex.py', 'exec'))
"
done
cd ..

# rip_textures.py uses name (lowercase) and must run from scripts/ (uses ../GAME_GDWs/ path)
cd scripts
for name in AQUARIUM ARMADA BEACH BEACHPST CHASE DEEPSEA2 DEEPSEA DOCKS FISH GAUNTLET KATATAMA MINEMSHA OPEN_NE OPEN_NW OPEN_S START TITLE0 TITLE TOWN WRACK; do
    python3 -c "
import re; from pathlib import Path
script = Path('rip_textures.py').read_text()
script = re.sub(r\"^name = .*\$\", \"name = '$name'\", script, flags=re.MULTILINE)
exec(compile(script, 'rip_textures.py', 'exec'))
"
done
cd ..
```


## Where the details live

Docs style (user, 2026-11-27): written for easy reading: a short summary first, short paragraphs, one fact per bullet, evidence at the end of a section. `docs/gwb_lineage.md` and `docs/ecco_leftovers.md` "After Appaloosa" are the model. All topic docs were rewritten this way on 2026-11-27 (old versions in `docs/archive/*_old_2026-11-27.md`); keep new text in the same style, and list superseded claims in each doc's "Old mistakes" table.

This file is kept short (target ~40k characters). Detailed notes, evidence, dates and corrections are in `docs/`. **When you learn something new, put the detail in the matching doc and add only a one-line summary here** (and update both when "document everything" is asked).

| Topic | Doc |
|---|---|
| GDW container, chunk notes (FDIR, SCRT, SKIP, embedded sub-archives), format date stamps | `docs/GDW_FORMAT.md` |
| GWB / Diesel Power history: every version and build, Defender → Sentinels → Jaws, other titles, after Jaws (readable; original notes in `docs/archive/gwb_lineage_detailed.md`) | `docs/gwb_lineage.md` |
| Ecco: Defender code in Jaws, `MLHalRaj` fish schools, Ecco leftovers, cut 1999 shark grab attack | `docs/ecco_leftovers.md` |
| Ecco dolphin controller and sonar port (a test of our engine knowledge; proved Defender PS2 resources can be moved into Jaws PC) | `docs/ecco_dolphin_controller.md` |
| Textures: GTEX plain/OBPR variants, TGAN layout, pixel formats, texture DB, ID collisions | `docs/texture_format.md` |
| RSRC layout, GMDL/TSET/MATS/GMAT, MREG/BREG/STRI collision BVH, GMOA/GSQD | `docs/rsrc_formats.md` |
| Skeletons: SKEL/BONE/WGHT/ROTS/ANIM, skinning math, Blender import, animation export | `docs/animation_system.md` |
| BRTR scene graph: node layout, PROP ID table, transforms, reference instancing, FISH layout, Hungarian names, scene extraction, Blender import | `docs/scene_graph.md` |
| Level editing: rules, custom levels, textures, collision, triggers, draw distance | `docs/brtr_editing.md`, `docs/custom_level_tutorial.md` |
| `Jaws.exe` (Ghidra): shark controller, stage loading, `GDControl`, bite, death paths, messages, reflection table | `docs/exe_analysis.md` |
| Speedrun research: timing, win conditions, cutscene skip, collision, push barriers, skips | `docs/speedrun_glitches.md` |
| Mod (d3d8 proxy): full feature list and internals | `mod/README.md` |
| Missions, side challenges, class mapping, GDW ↔ mission corrections, locations | `docs/mission_system.md` |
| Cut content (Hot Pursuit, Aurora rope, dev level-select, collectibles, AQUARIUM leftovers, old Brody…) | `docs/cut_content.md` |
| Audio formats (GSMP/SMPB/SMPC/GSFX, music), unused-audio audit, WMV movies | `docs/audio_format.md`, `docs/audio_leads.md`, `docs/cutscene_dialogue.md` |
| PS2 `.GDE` formats | `docs/ps2_asset_extraction.md` |
| Rendering, draw distance, water | `docs/rendering_system.md`, `docs/water_system.md` |
| Script reference for readers (extraction, analysis, level editing, libraries) | `docs/scripts.md` |
| Open problems (full list) | `docs/open_problems.md` |

## GDW Archive Format (essentials — full notes in `docs/GDW_FORMAT.md`)

`.GDW` files are chunk-based binary containers (little-endian), written by Appaloosa's **Game World Builder** editor (same format family as *Ecco the Dolphin: Defender of the Future*'s `.GDE`, user-confirmed lineage); the runtime engine is Appaloosa's **Diesel Power**. Jaws was built from Ecco: Defender's codebase (`docs/ecco_leftovers.md`). Version history: Defender 2.1.12.1 → cancelled *Ecco: Sentinels of the Universe* 2.3.2.1 (Feb 2001) → Jaws 2.6.3.16. Jaws was made after Sentinels was cancelled (user) and inherited its code line. Block format versions are literal YYYYMMDD dates (e.g. `SKEL` 20020410, `GTEX` 20050515); `VERS` 20030626 is a container date, not an engine freeze. **Loader version cutoffs (2026-11-26):** >2.5.7.12 = per-value alignment, >2.5.12.6 = `RSRC` header (stamp 20051208, per-resource `[id][flags]`), <2.6.1.17 rejected; dating uses the format stamps (header ~`VERS` 20030626, footer `FDIR` 20050707, `RSRC` 20051208); the idea that version numbers are dates is unconfirmed and the user doubts it. `EXBY` = exporter login (`jts`/`gyozo`/`martens`); `VERS`/`EXBY` are never read; `FSIZ`/`FDIR` have a separate handler. Sentinels `EXTR` = name→node table (`SoulContainer` soul-effect template, cloned at runtime). `docs/gwb_lineage.md` §3 and §7.

**File header:** 44-byte preamble `GDED BINARY FORMAT, VERSION 2.6.3.16.\r\n\r\n\x00\x00\x00`; chunks start at `0x2C`.

**Chunk:** `[4-byte FOURCC][uint32 size][payload]`, padded to 4 bytes before the next tag — this holds for nested chunks too, including individual `PROP` entries inside `PRPS`.

Top-level order: `FSIZ` `VERS` `EXBY` `GNRL` `WDIM` `RSPR` `CLAS` (class/reflection DB) `RSRC` (all resources) `BRTR` (scene graph) `SCRT` (screen-space overlay tree, same format as BRTR, not scripting) `SKIP` (`0xFF` padding so `FDIR` is 512-aligned) `FDIR` `ENDF`.

- **FDIR** = `[uint32 magic][uint32 count]` + 32-byte entries `[offset][size][24-byte name]`, pointing at **embedded sub-archives** (loading-screen scenes) concatenated after `ENDF`. **Any edit that grows a chunk before them must patch `FSIZ`, `SKIP` and these `FDIR` offsets by the same delta** (`scripts/gdw_grow.py` does this).
- **Locating `BRTR`:** a naive `data.find(b'BRTR')` hits false positives inside `RSRC` in 8 GDWs. Keep candidates whose payload starts `0x01025024`, root count 1, then `PRPS`, and take the largest (`gdw_grow.find_brtr`, `scene_graph.md`).
- Never trust raw tag string matches (`GTEXT`, `SCRT`, `DXTF`, …) without checking the size field; many are coincidences inside data.

## Resources (essentials — `docs/texture_format.md`, `docs/rsrc_formats.md`)

- **Textures:** every texture is a `GTEX` chunk (FISH 321). "GTEXT" is not a tag (it's `GTEX` + a size byte `0x54`). Two variants: plain `[id][flags 1][stamp 0x0131F253][0][w][h][bpp]TGAN` and one with an `OBPR` (`TEXB`/`TEXH`/`TEXD` type tag). Pixel data = fixed offset after the 18-byte TGA header (plain: block `+0x42`; GTEX/TGAN: `tgan_pos + 8 + 22`), not derived from sizes. Formats: 24bpp **BGR**, 32bpp **BGRA** (D3D `A8R8G8B8`), 8bpp = 768-byte RGB palette + indices; stored bottom-up. Chroma key cyan `#00FFFF`. Extractors `rip_textures.py` (plain, `name` var) and `rip_gtex.py` (`NAME` var), DB `scripts/build_texture_db.py` → `textures/texture_db.json`. **Texture IDs collide across GDWs** (same ID ≠ same image): look textures up in the same GDW only. The Sharpnose Shark skin (TOWN `0x152`, TITLE `0xEC`, OPEN_NE `0x15F`) has an artist's handwritten notes in its unmapped space (`texture_format.md`).
- **Meshes (`GMDL`):** `MATS` (materials) + `TSET` (submeshes: `[N]` + N×`[idx][first_vert][vert_count][first_tri][tri_count]`, `TSET[i]` ↔ `MATS[i]`) + `TANG` (`VIND` uint16 triangle list, `TNOR`, `TFLG`) + `VERT` (`POSI`, `NORM`, `UVUV`). `TANG`/`VERT` start with a uint32 count before their sub-chunks. Texture binding: `MATS[i]` → `GMAT` → `TEXP` `[n] + n×['GTEX'][id]` (first = base). `scripts/gdw_materials.py`, `scripts/rip_meshes.py` (11,948 OBJs in `models/`).
- **Handedness:** the game is DirectX **left-handed** (X right, Y up, Z forward). Exports write `(x, y, −z)` and keep the original `VIND` order; the Blender importer uses `CONV` (X=x, Y=z, Z=y, det −1) and `matrix_world = CONV @ game_world @ FLIP_Z`. User-confirmed.
- **Collision (`MREG`):** `[region_id][1]['GMDL'][mesh_id][0xFFFFFFFF] PERF BREG STRI`. `BREG` = heap-ordered binary AABB tree, `L = max(1, tris÷4)` leaves, 4 triangles per leaf in in-order traversal of the `STRI` permutation; boxes mesh-local. Nodes link to it via a `PRIM` chunk (`PROP 0x080018D8` = `['MREG'][id]`). Generated collision works (`obj_to_gmdl.py --collision`).
- **Skeletons (`SKEL`):** `BONE` root, `CHLD` = first child, `BROT` = next sibling; `MTOB` = inverse rest matrix, `TRAN` = local translation, `ROTS` = per-frame quaternions (transposed); `WGHT` 32 bytes/vertex (4 bone indices, −1 = unused, + 4 weights); `ANIM` = named clip ranges into the shared frame pool. Frame 0 reproduces the shipped `GMDL`. Humans share `GlobalSkeletonAnim`'s clips. `scripts/rip_skeletons.py`, `scripts/import_skeleton_blender.py`, all clips exported to `animations/` (`export_all_animations.py`). Details: `docs/animation_system.md`.
- **Audio:** `GSMP` = PCM sample (`[id][flags][hash][category][rate][bytes]` + PCM + `[loop start][loop end]`), variants `SMPB` (voice barks) and `SMPC` (cutscene dialogue with captions); `GSFX` = trigger → sample. Sounds are requested by `Group.Name` through sound-bank nodes. Level music = 4 layered tracks (`Calm_aw`, `Calm_uw`, `Susp`, `Act`; `scripts/gdw_music.py`). Extractors `rip_smpb.py`, `rip_smpc.py`; audit `scripts/audit_audio.py`. Details: `docs/audio_format.md`.

## Scene Graph — BRTR (essentials — `docs/scene_graph.md`)

`BRTR` = `[0x01025024][1]` + root `PRPS` ("World") + `CHBR` nodes: `[uint32 class ID][uint32 node_id] PRPS{PROP…}` (+ optional `PRIM`). Class ID low 12 bits index the level's `CLAS` name lists (`BRCM` for `0x01…` nodes, `ACCM` for `0x02…` actions). `ACTN` blocks are actions (scripts, AI, quests). **PROP ID = `0x08000000 | index` into the level's own `CLAS` `PRIM` field table** ((field, class) pairs; `gded_lineage.py prop LEVEL ID` names any ID; same table in 19 levels, `TITLE0` differs).

Most-used PROP IDs:

| ID | Meaning |
|---|---|
| `0x080017D8` | name (uint32 len + string) |
| `0x080017D9` | `m_nFlags`: `0x2` enabled, `0x10`/`0x40` in world, `0x100` not rendered, `0x20000` suspended, `0x20000000` transform is absolute (world space) |
| `0x080017DA` | transform, 12 floats column-major 4×3 (`xf[0..8]` basis columns, `xf[9..11]` translation) |
| `0x080017DD` | `m_Viewport`: `1` above water only, `0x20003` above + below |
| `0x080017DF` | world AABB, 6 floats (must be updated with the transform) |
| `0x080017F0` | reference target: node places a copy of that node's subtree ("replace" semantics) |
| `0x08001873` | mesh `['GMDL'][mesh_id]` |
| `0x08001875`/`76` | `m_StaticLights` / `m_RenderSetting` |
| `0x0800187A` | baked vertex colours (count + float4 per vertex) |
| `0x080018FF` | skeleton `['SKEL'][id]` |
| `0x080003C7` | `SharkWorld.m_teleportlist` (shark start/teleport positions; not a child list) |

The full table (camera, fog, collectibles, area triggers, creature generators, boat markers…) is in `docs/scene_graph.md`. Scene extraction: `scripts/rip_brtr_scene.py` (shared logic `scripts/brtr_scene_graph.py`) → `scenes/<NAME>_brtr.obj/.json`; Blender import `scenes/import_fish_blender.py`. Object names are Hungarian (`szikla` rock, `molo` pier, `fa` tree, `homokos` sandy, …; glossary in `scene_graph.md`).

## Level Editing (rules — narrative in `docs/brtr_editing.md`, tutorial `docs/custom_level_tutorial.md`)

The game re-reads a level's `.GDW` from disk on stage re-entry; mod F10 reloads in place, F9 loads `custom_levels\NAME.GDW` without touching stock files.

- Moving a static object: patch transform `0x080017DA` **and** AABB `0x080017DF` by the same delta. Nested: `new_local = parent_M⁻¹ @ (target_world − parent_translation)`.
- **New resource IDs = next free ID** (one shared space per level). **New node IDs must be below `0x100000`** (runtime IDs start there).
- Clone a *visibly rendered* node (not the `" 1"` hidden companion twins); use `m_Viewport` `0x20003`; swapping a mesh means resizing baked vertex colours (`insert_brtr_node.py` does it).
- Group nodes holding actions or used as markers need `m_nFlags` `0x12`. `GDControl`s triggered by destructibles must sit on a group-type node (`0x010B10AA`/`0x010AA0A4`).
- Removing an object at runtime: suspend (`0x4B000400`), hide or clearing `0x10`/`0x40` all work; kill alone leaves it solid.
- Large meshes fade out: tile anything over ~300 units (`build_scene.py --tile`).
- Transparency: 32-bit texture alpha; node render settings choose blend vs cut-out; `GMAT` `TWOS` = two-sided.
- Draw distance: `SharkCamera` `m_FarPlane` `0x08001800` + fog (fog colour `0x08001853`); underwater fog end above ~400 breaks visibility.
- Spawned boats are removed when they leave their `ANPosition` marker's AABB.

**Level-editing tools** (`scripts/`, run from there unless noted):

| Script | Does |
|---|---|
| `../levels/custom_fish/build.sh` | custom-level kit: `.blend` → export → build on `FISH_blank_base.GDW` → prune → install to `custom_levels/` |
| `blender_export_scene.py` | in Blender: exports collection `JAWS` (`jaws_collision`, `jaws_gmat`, `jaws_exit`, `jaws_spawn` props) |
| `build_scene.py BASE OUT EXPORT_DIR [--deploy NAME] [--show-exits] [--tile N] [--prune] [--music]` | textures + materials + meshes + collision + nodes + exits + spawn, verified |
| `strip_level.py IN OUT [--minimal\|--blank]` | blank base level (keeps gameplay layer; `--blank` = recentred, no exit) |
| `prune_level.py IN OUT` | drop unreferenced `RSRC` blocks |
| `make_level_kit.py` | (project root) creates `levels/custom_fish/` |
| `redirect_stage.py IN OUT FROM TO` | rewrite a `GDLoad` stage name |
| `gdw_music.py IN OUT none\|DIR` | replace level music |
| `gdw_to_text.py LEVEL.GDW TRACE.bin OUT.GDW` | rewrite a level in the GDED text format (needs a mod read trace of that level) |
| `dump_messages.py` | exe's 1,000 on-screen messages → `docs/game_messages.txt` |
| `obj_to_gmdl.py IN OUT model.obj [ID] [--gmat --scale --collision]` | OBJ → `GMDL` (+ `MREG`) |
| `insert_brtr_node.py IN OUT` | append node clones (`SPECS`) |
| `gdw_textures.py` / `gdw_grow.py` | libraries: new textures/materials; resize chunks and fix `FSIZ`/`SKIP`/`FDIR` |
| `patch_texture.py` | in-place same-size texture swap |
| `add_trigger.py BASE OUT` | breakable that removes targets via `GDControl` |
| `dump_gdcontrol.py LEVEL.GDW [REGEX]` | print a level's `GDControl` scripting |
| `build_pursuit_test.py [--deploy NAME]` | playable cut Hot Pursuit (`PURSUIT`) |
| `build_fishball_test.py [--deploy NAME]` | Ecco `MLHalRaj` fish schools (`FISHBALL`) |
| `build_ecco_dolphin.py [--deploy NAME]` | Ecco's dolphin model as the player (`DOLPHIN`) |
| `stage_ecco_sonar.py` | stage sonar assets for the mod's Ecco mode |
| `import_skeleton_blender.py` | in Blender: skinned animated model |
| `gded_lineage.py info\|compare\|placed` / `gdrom_ls.py` / `pvr_decode.py` | compare GWB versions (Ecco Defender / Sentinels / Jaws) / list a GD-ROM dump / Dreamcast PVR textures → PNG |

## Executable — `Jaws.exe` (essentials — `docs/exe_analysis.md`)

Ghidra 12.1.4 at `~/tools/ghidra_12.1.4_PUBLIC` (JDK 21), project `~/tools/ghidra_projects/JAWS.gpr`, headless helpers in `scripts/ghidra/` (`DecompAt`, `DecompStringRefs`, `RefsDecomp` = functions referencing an address; runnable copies in `~/tools/ghidra_scripts/`, paths must not contain a dash). Fixed image base `0x400000`, no ASLR. The game runs DirectX 8 at a fixed ~30 fps (lag = slow motion).

- Player shark controller = `[0x90BC04]` (null in menus); brick = `ctrl+0x50`, world position = `brick+0xA8`. Health `+0x2A8`/`+0x2B0`, hunger `+0x2AC`/`+0x2B4`, state `+0x240` (7 = dead, setter `0x65EDA0`), collision off `+0x810`, abilities `+0x72C`–`+0x73C`. Shark tick vtable slot `0x7F2944` = `0x667FB0`.
- Brick: `+0x0C` flags (`0x20` stale), `+0x14` parent, `+0x50` local 4×3, `+0x84` world 4×3.
- Engine object `[0x920E24]`; `RequestStage(flags, name)` = vtable `+0x80` (`0x6C3C50`); current stage name at `engine+0xB8`.
- `GDControl` (`ACTN` class `0x0203B039`) = level scripting: up to 8 timed steps `m_CtrlN` `[ops, delay min, delay max]` + target lists. Ops: `0x1` start, `0x2` stop, `0x4` add, `0x8` kill, `0x80`/`0x100` show/hide, `0x400`/`0x800` suspend/resume.
- On-screen messages: `[0x854D14 + 4*lang]` → 1,000-slot tables (mod overrides these).
- Field registration: stubs calling `0x70B6A0`; `scripts/dump_class_fields.py`.
- Controls: live binding arrays `0x8A0094`/`0x8A0208`/`0x8A0300` (31 dwords by action); profile `0x8D0110` (= `PROFILE<N>.sav`) +`0x5C`/`+0xA8`/`+0xF4` = 3×19 `(action<<16|key)`; load `0x539B30` copies save → arrays, new game `0x537090` copies arrays → profile; rebuild `0x483F30` on `0x8D67F8` (`docs/exe_analysis.md` "Control bindings").
- `NAPredator` is the predator-vision screen effect, not the shark (shark = `MLSharkCtrl` + `SharkConfig`).
- **Ecco: Defender symbols (2026-11-25):** the dev kit has an unstripped `ECCO.ELF` + `0.MAP` (12,156 named functions, DWARF v1 class layouts; `scripts/dwarf1_classes.py` → `docs/ecco_defender_classes.txt`). Names carry over to Jaws; offsets only partly (class-specific fields keep their spacing, `GDBrick` was reorganised: Jaws flags `+0x0C`, child `+0x1C`, sibling `+0x10`, attack/sensor masks `+0x3C`/`+0x40`, inverse world `+0xB4`). `/DEBUGBIN/0.BIN` is junk. **812 Jaws functions named from it** (vtable alignment + shared strings/constants + call graph; `docs/jaws_function_names.tsv`, applied in Ghidra; `GDAct::Execute` = slot 18, `GDBrick::Execute` = slot 22, GDW loader `GDLoadGame` `0x693180`). `docs/exe_analysis.md` "Ecco: Defender debug symbols".
- **GDED text format:** `GDFile` `+0x08` = 0 binary / 1 text; `ReadHeader` `0x6BBAC0` (from `GDLoadGame`) accepts `GDED TEXT FORMAT` levels: **a full level rewritten as text loads and plays (user-confirmed 2026-11-25, ~20 s load)**, made with `scripts/gdw_to_text.py` from a mod read trace (`jaws_gdfile_trace.on`); a hand edit (fog colour `PROP 0x08001853`) worked; not practical for editing (user), closed. Syntax: `docs/GDW_FORMAT.md` §7. The text/binary **writer is unreachable** (no game code opens a file for writing; saving was editor-only, as in Defender).

Speedrun findings (stage win conditions, cutscene skip = Enter, Shaw-first Facility skip, Arrival skip, swept collision, push barriers): `docs/speedrun_glitches.md`.

## Mod (`mod/`, d3d8 proxy) — keys (full list in `mod/README.md`)

Overlay: shark X/Y/Z, heading/pitch, speed. `F2` freecam · `F3` screenshot · `F4` fog · `F5` sim pause · `F6` foliage hide · `F7` no-clip, also skips area triggers/buoy pushes/currents and swims in the air (water-height wrappers on `0x8B2E94` wave surface / `0x8B2E9C` flat level, user-confirmed 2026-11-25) (`Shift+F7` write-watch trace) · `F8` teleport box + bookmarks (`jaws_bookmarks.txt`, `Ctrl+1..9` save) · `F9` custom level picker (`custom_levels\`) · `F10` reload stage · `F11` invincible + infinite hunger (blocked scripted deaths leave the shark invisible; accepted, don't chase) · `F12` object-ID dump · `Shift+F2` Ecco mode (+ sonar) · `Shift+F4` far view (user-confirmed). Files (all in the game folder next to `Jaws.exe` since 2026-11-25, `src/modpath.h`): `jaws_config.txt` (settings: control layout copied from a save so new games keep it, plus `key`/`mouse`/`pad <action> <button>` lines; start states of farview/fog_off/foliage_hide/noclip/invincible/ecco_mode; live layout written to `jaws_controls_current.txt` (next to `Jaws.exe`); `src/config.cpp`), `jaws_messages.txt` (message overrides), `jaws_debug.log` (game debug text), `jaws_gdfile_trace.on` → `jaws_gdfile_trace.bin` (GDFile read trace, only while the switch file exists at start). **Rule:** the game recreates its D3D device hundreds of times per session, so persistent state can't live on `DeviceProxy`. HUD is drawn in `Present` (back buffer only), not `EndScene`, which also ends render-to-texture passes (fixed 2026-11-25, user-confirmed).

## Class Namespace Conventions

The engine uses a prefix-based class registry:

| Prefix | Domain |
|---|---|
| `GD` | Generic engine / rendering (GDModel, GDLight, GDFog) |
| `NA` | Gameplay / shark systems (NABiteTarget, NAWayPoint; note `NAPredator` is the predator-vision screen effect, not the shark — see Executable Analysis section) |
| `MB` | Mission / boat systems (MBMissionBrick) |
| `MS` | Menu / spawn / scenario (MSMissionGenerator, MSKatatamaMission) |
| `ML` | Lighting / effects |
| `mc` | Mesh collections (mcMeshCollection) |
| `X` | Skeleton / bone (XSkeletonModel, XBone) |
| `AN` | Action nodes / scripted behaviours (ANSideMission21, ANSharkMsg) |
| `BG` | Background / persistent mission state (BGSetMissionCompleted) |


## Game Content (essentials — `docs/mission_system.md`, `docs/cut_content.md`)

**Story stages:** 1 The Arrival (tutorial) · 2 The Break Out · 3 The Dead of Night · 4 Hunted · 5 Predator in the Bay · 6 The Angry Armada · 7 A Taste for Blood · 8 The Deep · 9 The Facility · 10 Blood on the Beach · 11 The Final Chase. 32 side challenges (SC01–SC32); the full title list and class mapping are in `docs/mission_system.md`.

| GDW | Content |
|---|---|
| `START` | 1 The Arrival (Red Reef Valley) |
| `AQUARIUM` | 2 The Break Out (South Shore Aquarium) |
| `BEACH` / `BEACHPST` | 3 The Dead of Night (South Beach Cove; `BEACHPST` = post-mission state) |
| `DOCKS` | 4 Hunted |
| `KATATAMA` | 5 Predator in the Bay (Avril Bay: oil rigs, shipyard, Aurora boss) |
| `ARMADA` | 6 The Angry Armada (Bridgeport Sound) |
| `WRACK` | 7 A Taste for Blood (Misty Ridge) |
| `DEEPSEA` / `DEEPSEA2` | 8 The Deep / 9 The Facility (ENVIRONPLUS Mining Site; DEEPSEA chains into DEEPSEA2) |
| `TOWN` | 10 Blood on the Beach |
| `CHASE` | 11 The Final Chase |
| `FISH` | Fisherman's Isle, non-story (SC17 Mine All Mine) |
| `MINEMSHA` | Grand Occasus Canals (SC15 Up a Creek) |
| `GAUNTLET` | The Underwater Caves (SC10 The Bends, SC22 The Gauntlet) |
| `OPEN_S` / `OPEN_NE` / `OPEN_NW` | Open Ocean South / East / West free-roam zones |
| `TITLE` / `TITLE0` | Menus (`TITLE0` has no meshes) |

(Stage ↔ GDW corrected per `docs/speedrun_glitches.md`: BEACH = 3, DOCKS = 4, TOWN = 10.)

**Shared assets:** every GDW bundles a common asset pool, so an asset being present means nothing; it's only used if a `BRTR` node references it.

**Cut content (summary; evidence in `docs/cut_content.md`):** Hot Pursuit (cut story stage between 10 and 11, logic fully in the exe, playable restoration `PURSUIT`); Down the Hatch (`MSHatchMission`); the Aurora rope tug-of-war ending of the tutorial (`NAAuroraRope`, decompiled; START Brody lines 470/471); developer level-select menus in `TITLE.GDW`; Candy Wilson (text only); Highlands Bay (string only); Trident collectible (never placed); AQUARIUM loose orca insides; old Brody model on the boss Aurora; ANSideMission 26–32 gap; 327 dangling `GDControl` targets. Not cut: MINEMSHA's tiny out-of-bounds rock `k2 03` (stray shrunken open-ocean rock, tied to nothing), the BEACH "submarine objective" (a stationary SeaSeeker), Dolphin Passage, the Gauntlet mermaid.

***Sole Predator*** was the working title before Majesco licensed Jaws; it survives only in some promotional textures.

## PS2 Version Data — `.GDE` Files

The PS2 release is in `GAME_GDWs/ps2/` (all `.GDE` archives + `SLUS_210.62` exe); `GAME_GDWs/_FISH.GDE` is a PS2 file, not a PC dev build. **Full format notes are in `docs/ps2_asset_extraction.md`.** Summary:

- **Container is identical to PC `.GDW`** (same preamble and chunk walk). Only PS2-exclusive top-level chunk: `BNCH`.
- **Textures (`GTEXT`/`ZIPN`):** `ZIPN` is not compression — it's native PS2 GS pixel data: PSMCT32 (RGBA8888), PSMCT16 (RGBA5551), PSMT8 (palettized, GS-swizzled indices, RGBA or RGB palette). Extractors: `scripts/rip_gtext_ps2.py`, `scripts/rip_gtex_ps2.py`.
- **Meshes (`GMDL`):** extra `MTYP`/`MATS`/`SSET`/`STTA` wrappers; quantized `POSS` positions (`int16 * float scale`); `STRP` triangle strips (`0x7FFF` = strip break, winding flip = `(i%2==0) XOR flag(strip[i+2])`, drop degenerate triangles). Extractor: `scripts/rip_meshes_ps2.py`.
- **`SCRT`:** same tree format as PC, 14 unnamed children, PROP range `0x08001957`–`0x0800196A`.
- **`BNCH`:** shared name-interning table (3,495 names) plus ~1,272 80-byte transform records (field layout unverified).
- Open: `SSET`/`STTA` meaning, `POSS` `w` component, `BNCH` record↔name mapping.

## Key Investigation Commands

```bash
# Find texture blocks
grep -oba "GTEXT" GAME_GDWs/FISH.GDW

# Find class/reflection metadata
grep -oba "NABiteTarget" GAME_GDWs/FISH.GDW

# Hex inspect at offset
xxd -s 0x06FB5000 -l 4096 GAME_GDWs/FISH.GDW

# Find DDS texture headers (alternate embedded format)
grep -oba "DDS" GAME_GDWs/FISH.GDW

# Search for a string across all GDWs and the executable
grep -rioab "search_term" GAME_GDWs/ game_binary/
```


## Open Problems (index — details in `docs/open_problems.md`)

- `GDControl` leftovers: node flag `0x400000`, why kill keeps collision, spawn modes 3 vs 4, how quest code starts controls, dangling `missing#` targets.
- Skeletons: bone names, runtime binding to `GlobalSkeletonAnim`, playback rate, `MORF`.
- Custom levels: exact large-object fade test, `OssLoadChecker.m_type` ↔ prompts, exits to other destinations, strip lists for non-FISH bases, minimap picture, level music size.
- Draw distance: why an underwater far plane past ~400 breaks visibility; the 2500 crash.
- PROP IDs all named via the `CLAS` field table (2026-11-25); still open: value meanings (render flags of hidden companion nodes, `m_Viewport` bits, `m_RenderSetting` bits), `TFLG` flags.
- `MOIL` in `GMOA`; extra `TEXP` layers and unused `GMAT` parameters; PS2 `BNCH` record ↔ name mapping.
- Aurora rope: `NARope` base fields, placing a working rope in START. Old Brody: compare with beta media.
- Hot Pursuit: route end, several jet skis + bosses, solid gates, goal text; whether MINEMSHA and OPEN_NE sites are one mission.
- To do (user request 2026-11-25): sweep all levels for stray objects (out of bounds, odd-scale reused meshes, unreferenced; like MINEMSHA `k2 03`).
- Lineage follow-ups (user requests 2026-11-25/26): **all done 2026-11-26** (`docs/gwb_lineage.md` §3 and §7 and the build/title entries after it). Results: Sentinels `EXTR` = name→node table; header/footer dated by stamps; `EXBY` logins vs credits (`jts` = Tamás Jutasi, confirmed; `Neszta` = Neszta Volkai; `SAN` ≈ Sándor Mezei; `gyozo`/`martens`/`AnChoR` unmatched); titles: Infogrames *Wacky Races* DC = not GWB, Appaloosa PS1 *Wacky Races* = GWB resource tags only, *C: The Contra Adventure* = no GWB, so no GWB 1.x found (oldest on hand: May 1999 Defender prototypes = 2.1.1.6, 2026-11-26); the "2007 Xbox Ecco prototype" = XBLA SEGA Vintage Collection Mega Drive emulation by Digital Eclipse, not GWB; Defender builds: Feb-2000 prototype (V0.800, 3 cut levels `160_TopMidLow`/`241_Pump`/`HWGM`, `docs/ecco_leftovers.md`; localization classes added Feb→Apr 2000), Apr-2000 prototype, PAL master (2000-05), US master (2000-06/07; newer editor registry, credits "Tamás Jutasi 'JTS'"), PS2 (2001-02; adds `GDControl`, `NAPredatorModel`, `NAModelFade`, `GDMultiTexture`, `m_ExtRenderSetting` shared with Jaws; `docs/defender_dc_ps2_field_diff.txt`) — all 2.1.12.1. Small leftovers: retail DC vs dev builds in detail, PS2 Defender exe loader; testing the Feb prototype's cut levels in an emulator.
- GWB lineage (user very interested): **May 1999 Defender prototypes ("Ecco 3D" file viewer, E3 demo) = 2.1.1.6, oldest found** (2026-11-26; no `KADI`, only 1998 block stamps, `.cpp` source names in the exe (no source code; 57 asserts give file + line + expression, `docs/ecco1999_asserts.txt`, `scripts/sh4_asserts.py`, Ghidra project `ECCO99`; 2,553 functions named + 11,315 given a source file from `ECCO.ELF` via 8-byte-slot vtables (1999 action vtables are one slot shorter: `Execute` = slot 9), `scripts/ecco1999_match.py`, `docs/ecco1999_function_names.tsv`; 1999 sharks `TRSharkTank`/`Shark_1` grab and drag Ecco (`DRAG`/`PULL` messages), cut by 2000 but `DolphCtrl::EccoMessage` still handles them), 1999-only `SharkTank`/`SharkTrap`/`TRDolphCtrl`/`TRGen*` classes; `docs/gwb_lineage.md`), Defender = 2.1.12.1 (every build Jan 2000–2002), cancelled *Sentinels of the Universe* (Feb 2001) = 2.3.2.1 (padded chunks; skeletons, `MLHalRaj3`, `MLHalRaj` colours, `TRSplash`/`DDGameState` edits all date from there), Jaws = 2.6.3.16; field diffs `docs/lineage_field_diff.txt` (its "Defender" column merges DC + PS2) and `docs/defender_dc_ps2_field_diff.txt`; Sentinels `Tile` = spatial grid of model node IDs. Sentinels (= *Ecco II*) Feb 19, 2001 prototype disc (2026-11-26, `~/Projects/ECCO/ecco2_feb19_proto/`): same `0.BIN` as the dev-kit discs, older Atlantis/Ancient/Galleon; its `100_Atlantis` is the only intact one (dev-kit Feb 21 Atlantis files are corrupt: 0x158000-byte junk block + truncated `BRTR`); `MLCapaSok` = unplaced Ecco 2 shark-enemy AI added Feb 16→21, not in Jaws (`docs/gwb_lineage.md`). Defender PS2 `LDSC` = loading image (Jaws keeps a reworked unused reader); the header reader calls the format a "Game Designer file". Cancelled Appaloosa projects (user): Mermaid tech demo (videos 2001-01-05; `MBMermaid` already in the US Defender master's registry mid-2000), Parrot first-person demo (design only), *Smurfs* (©2002, PS2 dev build on video: anim viewer, party-of-Smurfs puzzles; no visible GWB link; its yellow/white star sparks resemble Jaws's `CageHitEffect` (`NAParticle2004`, texture `0x1DA`), a redraw in the style of Defender's starburst/`csillag` sprites; no exact copy in Defender DC/PS2 or Sentinels; images in `particle_compare/`, local only); after Appaloosa closed (it was not renamed), the same team worked as Twofish.hu, owned by Twofish Inc. (Annunziata + Lee Crawford; per the user's interview with Ed Annunziata, 2026-11-27): they finished the self-healing-car racer *EdgeRacers*, which was shelved; engine unknown, only portfolio renders + 4 in-engine shots (`download-check/edge-racers/`); the most likely post-Jaws GWB candidate. Twofish also made *SmartyAnts* (2010, for Smarty Ants, Inc., Burlingame CA): installers are online-only launchers (`hu.twofish`, D3D9, Java), game data gone; installer built in `c:\Torque\anttools\` = probably GarageGames' Torque engine, so GWB/Diesel Power ended with Jaws or *EdgeRacers*; `docs/ecco_leftovers.md`. Open: any Appaloosa title 2001–2005 other than these.

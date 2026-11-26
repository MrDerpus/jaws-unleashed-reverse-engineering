# GDW Format — Research Reference

Consolidated findings on the `.GDW` archive format used by *Jaws Unleashed* (PC, 2006, Appaloosa Interactive). This document covers everything confirmed, suspected, and ruled out about the format and its asset extraction pipeline.

> **Note (2026-07-17):** this snapshot dates from June 2025 and predates many later corrections. `/CLAUDE.md` at the project root is now the actively-maintained, current source of truth — cross-check findings there before trusting anything below that looks uncertain or contradicts it. Several stale claims below have been annotated in place; others may remain.

---

## Overview

`.GDW` files are the primary world/level container format for Jaws Unleashed. Each file corresponds to a game level and contains all assets that level uses — textures, serialized gameplay objects, reflection metadata, audio references, and likely geometry. There is significant texture reuse between levels.

Known level files:

| File | Level |
|---|---|
| `FISH.GDW` | Fisherman's Isle |
| `BEACH.GDW` / `BEACHPST.GDW` | Beach |
| `DOCKS.GDW` | Docks |
| `TOWN.GDW` | Town |
| `OPEN_S.GDW` / `OPEN_NE.GDW` / `OPEN_NW.GDW` | Open ocean zones |
| `DEEPSEA.GDW` / `DEEPSEA2.GDW` | Deep sea |
| `MINEMSHA.GDW` | Grand Occasus Canals (SC15 "Up a Creek") — identified 2026-08-12, see `mission_system.md`; "Menemsha" is just the internal dev filename |
| `AQUARIUM.GDW` | Aquarium |
| `ARMADA.GDW` | Armada |
| `CHASE.GDW` | Chase |
| `GAUNTLET.GDW` | Gauntlet |
| `KATATAMA.GDW` | Katatama |
| `WRACK.GDW` | Wrack |
| `START.GDW` | Start/hub |
| `TITLE.GDW` / `TITLE0.GDW` | Title screen |

**Special files:**
- `TITLE0.GDW` — not a level. Contains the full engine class registry and title screen model references. No extractable textures. Useful as a reference for the complete class list.
- `OPEN_S.GDW` / `OPEN_NE.GDW` / `OPEN_NW.GDW` — open ocean zones. Much larger (337–432MB vs ~120–150MB for regular levels) due to `NATerrain` and `NAWater2004` data. Internally structured differently — the unusual repeating chunk tags (`HHHH`, `TTDT`, `DTTD`, `XXHX` etc.) were guessed here as terrain/water grid data. **Flagged as needing re-verification (2026-07-17), not confirmed either way this session:** CLAUDE.md later established (2025-06-29) that ALL static terrain/rocks/water-planes/dock geometry is present as regular named `BRTR` mesh instances with no separate BSP/heightmap container — it's unclear whether that finding is in tension with this HHHH/TTDT claim (e.g. these tags could be a real but separate open-world-only LOD/streaming system unrelated to the base terrain mesh instances) or whether this claim was simply wrong. Not independently re-checked.
- `_FISH.GDE` — from the **North American PlayStation 2 release**. Produced by the engine's built-in `PS2ExportSettings` pipeline. Likely transformed for PS2 hardware and may not be directly parseable with the same tools as the PC `.GDW` files.

---

## Engine lineage

*Jaws Unleashed* was made with Appaloosa's **Game World Builder (GWB)** editor, the same tool as *Ecco the Dolphin: Defender of the Future*. The game engine is **Diesel Power**.

| When | Game | Version |
|---|---|---|
| May 1999 | *Ecco: Defender* prototypes | 2.1.1.6 |
| 2000–2002 | *Ecco: Defender* (Dreamcast, PS2) | 2.1.12.1 |
| Feb 2001 | *Ecco: Sentinels of the Universe* (cancelled) | 2.3.2.1 |
| 2006 | *Jaws Unleashed* | 2.6.3.16 |

The full history is in **`docs/gwb_lineage.md`**: the names, the proof, what changed in each version, every build checked, other games and what came after Jaws. The original detailed notes are archived in `docs/archive/gwb_lineage_detailed.md`.

---

## Archive Structure

**Engine version:** All 20 GDW files share the identical header `GDED BINARY FORMAT, VERSION 2.6.3.16` with an internal date of `20030626` (June 26, 2003), stored as a string in the `VERS` chunk (`Jaws.exe` holds the same string, next to `misc_core_open`). **Correction (2026-10-21):** this is the container format's version date, not an engine freeze. Individual block formats kept changing until December 2005 (see "Block format date stamps" below).

### Text variant: `GDED TEXT FORMAT` (2026-11-25, loads in-game)

The same container exists as text, the format the Game World Builder editor could save. Jaws can't write it (writer code is dead), but `GDLoadGame` still reads it: a full level converted to text loaded and played, and a hand-edited fog colour took effect (user-confirmed). Syntax, from the readers' text branches:

```
GDED TEXT FORMAT, VERSION 2.6.3.16.\r\n\r\n     (exactly these 4 raw bytes after the version)
Chunk: PROP {                                    (chunk; sizes are implicit, "}" ends it)
  CLASSID: 2131-1-8                              (bits 0-11, 12-23, 24-31 = PROP 0x08001853)
  COLOR: 0.56, 0.69, 0.79, 1
}
INT: -5   SHORT: 3   REAL: 1.5   SET: ACD (bit n = 'A'+n, '-' = 0)   ResID: GTEX (0000 = 0)
STRING: "name" ('-' = none)   VECTOR: x, y, z   MATRIX: 12 values   BUFFER: hex byte tokens
```

Labels are free (anything before `:`); arrays are one value per line. Limits: `FDIR`'s 24-byte names are read raw, the loading-screen sub-archives stay binary (appended, `FDIR` offsets absolute), NaN/Inf can't be expressed. The bytes of a binary GDW don't say which reader reads which value, so conversion uses a load trace from the mod (`scripts/gdw_to_text.py`). Size about 2.3× the binary, load about 20 s for a 105 MB level. Judged not practical for editing (user); kept as a curiosity. Engine side: `docs/exe_analysis.md` "GDED text format".

### Block format date stamps (found 2026-10-21)

Data blocks carry a format-version number that is a literal **YYYYMMDD date**, and `Jaws.exe`'s loaders compare against it (every exe hit is a `cmp [esp+x], imm` or `cmp eax, imm`). Found by scanning all 20 GDWs, the PS2 `.GDE`s and the exe for date-shaped uint32s and keeping those that sit in block headers:

| Block | Stamp | Date | Note |
|---|---|---|---|
| `WDIM` | 19980304 | 4 Mar 1998 | |
| `GNRL` | 19980331 | 31 Mar 1998 | |
| `GMAT` | 19980409 | 9 Apr 1998 | after the empty `OBPR` (`0x0130E079`) |
| `GMOV` | 19991005 | 5 Oct 1999 | |
| `GSMP` | 20001201 | 1 Dec 2000 | `0x013131B1` |
| `SKEL` | **20020410** | **10 Apr 2002** | all 752 skeletons; the loader also checks `> 20001009` (morph-frame count) and `≥ 20020410` (running-position track) |
| `GTEX` | 20050515 | 15 May 2005 | the "stamp `0x0131F253`" in the texture header |
| `GMDL` | 20051205 | 5 Dec 2005 | all 11,948 meshes |
| `RSRC` | 20051208 | 8 Dec 2005 | |
| (PS2 only) | 20060316 | 16 Mar 2006 | 360 blocks in the `.GDE`s, also checked by `Jaws.exe`; block not identified |

The exe also compares against stamps not seen in the data (1998–2006, e.g. 19980902 in several loaders, 20030218, 20050707), probably formats with no blocks in the shipped files or older revisions still accepted. **The only 2001–2002 date anywhere is the `SKEL` stamp (April 2002)**, i.e. the skeleton format's last revision falls between *Ecco: Defender* and *Sole Predator*. Values 20011008–20011013 that a raw scan finds are chance byte patterns in pixel data, not headers. The 1998 stamps predate GWB's early-1999 start, so the oldest formats may come from earlier Novotrade/Appaloosa tools (inference). Other dates in the exe: PE timestamp and `__DATE__` 14 Sep 2006, `(c) 2004 Majesco Entertainment`, libpng 1.0.5 (Oct 1999), IJG JPEG (1996).

**Development history and engine lineage:**

The engine predates Jaws Unleashed by several years. Appaloosa Interactive built the same underwater engine for *Ecco the Dolphin: Defender of the Future* (2000). The game was then developed under the working title *Sole Predator* and demonstrated as a tech demo in 2004 while Appaloosa searched for a publisher. A publisher subsequently acquired the Jaws license and the game shipped in 2006 as *Jaws Unleashed*.

**Correction (2026-10-21):** this used to say the engine was frozen in June 2003. That date (`20030626`) is only the container format's version; the block format stamps (see "Block format date stamps") show the skeleton format revised in April 2002 and the texture, mesh and resource formats in May–December 2005, so the engine kept changing during Jaws development. Several things visible in the files show old code carried forward:

- `SharkWorld` sits alongside `GDWorld` in the class registry — shark-specific code was layered on top of the generic engine rather than integrated into it
- The water system has multiple versioned classes (`NAWaterGrid2000`, `NAWater2003`, `NAWater2004`, `NASlideWater2004`) — these represent evolution layers carried forward from Ecco through Sole Predator
- `PS2ExportSettings` is baked into the class registry — the PS2 port was planned from the start, not added late in development
- The engine feels more sophisticated than typical 2006 AA titles because it had been in active development since at least 2000

GDW files are **chunk-based binary containers** using little-endian byte order. The top-level structure is:

```
[4-byte FOURCC tag][uint32 size][payload]
```

Chunks may contain nested subchunks using the same pattern. Multiple full `GDED` headers have been observed inside single GDW files, suggesting nested serialization containers or streaming sub-documents.

**CORRECTED/RESOLVED (2026-07-17):** this is now fully explained. Every GDW's declared `ENDF` is not the true end of the file — a second, complete, independent `GDED BINARY FORMAT...` archive (own `VERS/EXBY/GNRL/WDIM/RSPR/CLAS/RSRC/BRTR` chain, but no `FSIZ`/`SCRT`/`SKIP`/`FDIR`/`ENDF` of its own) is concatenated immediately after. `FDIR`'s single entry stores this second archive's exact `[offset, size]`. Confirmed on `OPEN_S.GDW` to be **bundled loading-screen scenes** for level transitions (not nested/streaming sub-documents in a general sense) — bounded story levels carry one small embedded archive, open zones carry several (one per destination they connect to). See CLAUDE.md's `FDIR` note for the full mechanics.

### Known Top-Level Chunks

| Chunk | Confidence | Description |
|---|---|---|
| `FSIZ` | CONFIRMED | ~~File size metadata~~ **CORRECTED (2026-07-17):** payload is NOT total file size — it's the exact byte offset where `SKIP` begins (equivalently, where `SCRT` ends). |
| `VERS` | CONFIRMED | Container version date string `20030626` (same in every file). Never read by the game. |
| `ENDF` | CONFIRMED | ~~Archive terminator~~ **CORRECTED (2026-07-17):** terminates only the FIRST of two concatenated embedded archives in the file — not the true physical EOF. See `FDIR` row and the note above. |
| `FDIR` | **CONFIRMED (2026-07-17, was HIGH)** | Real offset+size index, not just names: 8-byte header (magic/build-date + entry_count), then per-entry `[uint32 offset][uint32 size][24-byte name]`. Points at the second embedded archive described above. Any edit growing a chunk before this offset must patch this field by the same delta. |
| `CLAS` | VERY HIGH | Class/reflection database |
| `BRCM` | LIKELY | Appears immediately after CLAS in all files — likely class/brick registry map |
| `RSRC` | HIGH | Packed resource payloads — does NOT follow recursive chunk structure internally |
| `BRTR` | HIGH | ~~Resource tree / index (maps resource IDs to names or offsets)~~ **CORRECTED — this description is wrong.** CLAUDE.md confirms: `BRTR` is the pre-built **scene graph** — all placed object instances with world-space transforms, mesh references, vertex colours, and AABBs (2,782 `CHBR` nodes in `FISH.GDW`, 1,161 with mesh refs). Not a resource-ID lookup table. |
| `GNRL` | LIKELY | General archive data — decodes to two uint32s; first looks like a `19980331`-style build/format date, second (`35210` in FISH.GDW) is close to but not exactly the max real `BRTR` node ID — inconclusive, not confirmed to mean anything at runtime. |
| `WDIM` | LIKELY | World dimension bounds — observed floats ~5000×2000×5000, likely streaming/level extents |
| `SCRT` | **RESOLVED (2026-07-08), was SUSPECTED "Scripting system"** | Not scripting, not obfuscated. A small top-level `PRPS`/`CHBR`/`PROP` tree (same format as `BRTR`) holding named screen-space overlay objects (`GDScreen`, water reflection/transparency layers, motion blur). The offset originally suspected for this was a false-positive tag match inside `RSRC`; the real `SCRT` is a top-level chunk, sibling of `BRTR`. |
| `SKIP` | **RESOLVED (2026-07-08), missing from this table** | Pure `0xFF`-filled sector-alignment padding, sized so `FDIR` lands on a 512-byte file-offset boundary. Sits between `SCRT` and `FDIR`. |
| `RSPR` | UNKNOWN | Unknown subsystem — always empty (0 bytes) in `FISH.GDW` |
| `EXBY` | **CONFIRMED (2026-11-26)** | "Exported by": `uint32` length + the exporter's login name (`jts`, `gyozo`, `martens` on PC). Never read by the game. See §3 and §7 of `docs/gwb_lineage.md`. |

### High-Frequency Object Chunks (seen across all level files)

| Chunk | Count (approx) | Description |
|---|---|---|
| `PROP` | 88K–225K per file | Property block — core serialization unit |
| `PRPS` | 2K–8K | Property set container |
| `CHBR` | 1K–5K | Child brick reference |
| `GMDL` | 1K–3K | Geometry model container |
| `GMAT` | 1K–4K | Geometry material |
| `VERT` | ~12K total | Vertex data |
| `VIND` | ~12K total | Vertex index buffer |
| `TSET` | ~12K total | Triangle set (submesh ranges; corrected 2026-10-01, not textures) |
| `TANG` | ~12K total | Tangent data |
| `MATR` | ~12K total | Material |
| `POSI` | ~12K total | Position data |
| `TRAN` | ~26K total | Transform |
| `ROTS` | ~16K total | Rotation |
| `TMTX` | ~39K total | Transform matrix — prominent in ARMADA, DOCKS, DEEPSEA2, KATATAMA, WRACK |
| `ACTN` | ~21K total | Action / animation action |
| `GTEX` | ~21K total | Geometry texture reference (distinct from 5-byte `GTEXT` texture blocks). **Corrected 2026-10-03:** every texture is a `GTEX` chunk; "GTEXT" is `GTEX` + a size field whose low byte is `0x54` (`'T'`). See `CLAUDE.md` texture section. |
| `MSHH` | ~1.4K total | Mesh header — contains named model references (e.g. `Shark2Reference`) |
| `CHLD` | ~12K total | Child relationship |
| `APRO` / `BPRO` / `CPRO` / `OBPR` | various | Property block variants |
| `TCAM` | ~12K total | Texture camera — prominent in DOCKS |
| `LUDL` / `LVDL` / `DLUD` / `MTOB` | ~12–14K each | Unknown — likely LOD or render-distance data |

### WDIM Chunk

Size: `0x28` bytes. Contains float-like values interpreted as world extents (~5000, ~2000, ~5000). Likely defines level streaming bounds or world-space dimensions.

---

## Texture System

### GTEXT Structure

> **Correction (2026-10-03):** "GTEXT" is not a separate tag. Walking `RSRC` as a chunk chain shows every texture is a `GTEX` chunk; the "T" is the low byte (`0x54`) of the size field that follows the tag. The real split is plain payload (258/321 FISH textures; the layout below) vs. payload carrying an `OBPR` block (63/321). New textures can be written byte-exactly: `scripts/gdw_textures.py`, see `docs/brtr_editing.md` "Custom textures".

Textures are stored as `GTEXT` blocks. The header layout is fully confirmed:

| Offset | Field | Notes |
|---|---|---|
| `+0x00` | `GTEXT` signature | 5-byte ASCII marker |
| `+0x04` | block size | uint32, includes header + payload |
| `+0x08` | texture ID | uint32 |
| `+0x18` | width | uint32, pixels |
| `+0x1C` | height | uint32, pixels |
| `+0x20` | bits-per-pixel | uint32 — `32` or `24` for known formats |
| `+0x24` | `TGAN0` marker | also contains `TRUEVISION-XFILE` string |
| `+0x54` | ~~pixel payload start~~ **wrong, see correction below** | |

> **Correction (2026-07-29):** pixel data actually starts at `+0x42`, immediately after an 18-byte standard TGA 1.0 header that begins at `+0x30` — not `+0x54`. The `+0x54` figure conflated that real header with a *trailing* TGA 2.0 footer (`"TRUEVISION-XFILE.\0"` + 8 offset bytes) that sits after the pixel data, not before it. Reading from `+0x54` skipped the first 18 bytes of real pixel data and read footer garbage instead — a non-integer-pixel shift that produced diagonally-sheared/wrapped images. `payload_size = block_size - 0x54` is still correct (it already yields the right total pixel byte count); only the **read start offset** was wrong. See `CLAUDE.md`'s "Texture System (GTEXT)" section for full detail. `scripts/rip_textures.py` is fixed.

**Payload size formula (still correct):**
```
payload_size = block_size - 0x54
```

### Pixel Formats

| BPP | Format | Handling |
|---|---|---|
| `32` | ~~RGBA32, read directly~~ **wrong — see correction** | |
| `24` | RGB24 | Stored as BGR — swap to RGB on read |
| Other | Unknown | Dump as `.raw` for manual inspection |

> **Correction (2026-07-29):** 32bpp is **not** straight RGBA. Like GTEX (see `rendering_system.md`), it's native little-endian `D3DFMT_A8R8G8B8`, byte order **B, G, R, A** — same BGR-family convention as the 24bpp row above, just with an alpha byte appended. The old "read directly as RGBA" assumption produced a systematic R/B channel swap (subtle blue tint on naturally warm-toned textures, e.g. a kelp texture rendering blue-teal instead of green/brown). This was hard to notice while the `+0x54` offset bug above was also active, since the resulting image was already visibly corrupted by the shift. `scripts/rip_textures.py` now reads 32bpp with PIL raw mode `'BGRA'`.

Textures are stored with the origin at bottom-left (standard DX/OpenGL convention) and must be vertically flipped on export. `rip_textures.py` handles this with `FLIP_VERTICAL = True`.

### Texture Types Observed

- Particle effect masks (monochromatic, runtime-tinted)
- Texture atlases (multi-object sprite sheets)
- UI textures
- Environmental textures
- Character/creature textures

### Palette / CLUT Textures

Some textures use indexed colour with a CLUT (Color Look-Up Table). Colour ramp patterns like:
```
69 69 69
64 64 64
5F 5F 5F
```
and RGBA markers like `FF 00 FF FF` indicate palette structures. These textures extract incorrectly with the current pipeline (wrong colours, scrambled appearance). This is the primary remaining unsolved texture problem.

> **Note (2026-07-29):** re-evaluate this claim before investigating a real CLUT/palette format — "wrong colours, scrambled appearance" is exactly the symptom of the `+0x54` offset bug and the RGBA/ARGB byte-order bugs corrected above and in `CLAUDE.md`, both of which were active when this section was written. Confirm textures still look wrong under the fixed `scripts/rip_textures.py` before assuming a genuine indexed-color format is involved.
>
> **Separately, a genuine 8bpp indexed/CLUT format was decoded (2026-07-29)** — distinct from the above, and not the explanation for it. `rip_textures.py` was dumping unsupported-BPP blocks as `.raw`; of ~59 such dumps across all 20 GDWs, only 2 were real textures (both 64×64 8bpp, `TITLE.GDW` and `GAUNTLET.GDW`, the same shared UI icon — the other 57 are false-positive `GTEXT` string matches inside unrelated binary data, detectable by nonsensical multi-billion-pixel declared dimensions). Format: `[768-byte palette: 256 × 3-byte RGB entries][width×height index bytes]` — file size is exactly `768 + width*height`. Both confirmed palettes are an identical linear inverted grayscale ramp (`palette[i] = (255-i,255-i,255-i)`). `rip_textures.py` now decodes this via palette lookup (`idx8.png` output). See `CLAUDE.md`'s "Texture System (GTEXT)" section.

### Extraction Pipeline

```
GTEXT block
  → read header (width, height, BPP)
  → calculate payload_offset = GTEXT_offset + 0x42   # corrected 2026-07-29, was +0x54
  → calculate payload_size = block_size - 0x54
  → extract raw bytes
  → convert to PIL image (32bpp: BGRA→RGBA, 24bpp: BGR→RGB)   # 32bpp swap corrected 2026-07-29, was read directly
  → flip vertical
  → export PNG
```

**Primary script:** `scripts/rip_textures.py` — set the `name` variable to the GDW stem (e.g. `'FISH'`). Outputs go to `textures/<NAME>/`.

---

## Reflection / Class System

### CLAS Chunk

The `CLAS` chunk contains a serialized class and property reflection database. This was a major discovery — the engine preserves full runtime type information inside the GDW files, including class names, property names, and component definitions.

The serialization pattern is length-prefixed strings:
```
[uint32 length][class or property name string]
```

This means the engine effectively self-documents. Readable strings can be located with:
```bash
strings -td FISH.GDW | grep -i <term>
grep -oba "ClassName" FISH.GDW
```

### Class Namespace Conventions

| Prefix | Domain |
|---|---|
| `GD` | Generic engine / rendering |
| `NA` | Gameplay / shark systems |
| `MB` | Mission / boat systems |
| `MS` | Menu / spawn / scenario |
| `ML` | Lighting / effects |
| `AN` | AI zones and area volumes |
| `JT` | Gameplay interaction objects |
| `mc` | Mesh collections |
| `X` | Skeleton / bone / animation |

### Confirmed Engine Classes

**Rendering / Models:**

| Class | Purpose |
|---|---|
| `GDModel` | 3D model component |
| `GDStripModel` | Triangle strip geometry model |
| `GDMovingModel` | Animated/moving model |
| `GDSkeletonModel` | Skeletal mesh model |
| `XSkeletonModel` | Extended skeleton model |
| `XExtendedSkeletonModel` | Further extended skeleton model |
| `NALODSkeleton` | LOD skeleton system |
| `MLEnvSkeletonModel` | Environment skeleton model |
| `NAPredatorModel` | Shark-specific model |
| `NAMorphModel` | Morph animation model |
| `NAVirtualModel` | Virtual / proxy model |
| `NAShadowModel` | Shadow mesh |
| `NAStencilVolume` | Stencil shadow volume |
| `mcMeshCollection` | Mesh resource container |
| `GDBrick` | Base engine object |
| `GDFixedBrick` | Static world object |
| `GDLibBrick` | Library/prefab object |

**Lighting / FX:**

| Class | Purpose |
|---|---|
| `GDLight` | Dynamic lighting |
| `GDExtendedLight` | Extended light properties |
| `GDFog` | Fog system |
| `NAParticle2004` | Particle system |
| `GDParticleTest` | Particle test component |
| `NAMotionBlur` | Motion blur |

**Water / Terrain:**

| Class | Purpose |
|---|---|
| `NAWater2004` | Primary water system (used in OPEN_ files) |
| `NAWater2003` | Earlier water system version |
| `NAWaterGrid2000` | Original water grid |
| `NASlideWater2004` | Sliding/shallow water |
| `NATextureGeneratorGrid` | Procedural water texture generation |
| `NATerrain` | Terrain system |
| `NAGrid` | Grid system |

**UI / Sprites:**

| Class | Purpose |
|---|---|
| `GDSprite` | Sprite object |
| `GDRotSprite` / `GDRotSpriteEX` | Rotating sprite |
| `GDFont` / `GDPptFont` | Font rendering |
| `GDTextSprite` / `GDPptTextSprite` | Text sprite |
| `GDShowSprite` | Display sprite |
| `GDScreen` / `GDViewport` | Screen and viewport |
| `GDTileMap` / `GDTile` | Tile-based map (likely UI or minimap) |

**Camera / Rendering:**

| Class | Purpose |
|---|---|
| `GDCamera` | Camera |
| `MBSharkCamera` | Shark-follow camera |
| `GDWorld` / `SharkWorld` | World root object |
| `GDGraph` | Render graph |
| `GDNewMat` | Material |

**Gameplay / Shark Systems:**

| Class | Purpose |
|---|---|
| `NAPredator` | Shark/predator AI |
| `NABiteTarget` | Bite interaction component |
| `NAChewingToy` | Physics-enabled prey/bait |
| `NAWayPoint` | AI navigation node |
| `NAMessenger` | Event/trigger messaging |
| `NATimeControl` | Time dilation / motion blur |
| `NAWhirl2000` | Whirlpool system |
| `JTMineWhirl` | Mine whirlpool interaction |

**Animation:**

| Class | Purpose |
|---|---|
| `XBone` | Skeleton bone |
| `XAnimation` | Animation clip |
| `XAnimationNames` | Animation name table |
| `XAnimationSet` | Animation set container |

**Mission / AI Areas:**

| Class | Purpose |
|---|---|
| `MBMissionBrick` | Mission system object |
| `MBAramlat` | Mission brick variant |
| `ANLaw` | AI law/rule zone |
| `ANBlock` | AI blocking volume |
| `ANPolyArea` | AI polygon area |
| `ANPolyArena` | AI arena zone |
| `ANUnitRef` / `ANHeliRef` / `ANSeekerRef` | AI unit references |
| `ANPosition` | AI position marker |

**Audio:**

| Class | Purpose |
|---|---|
| `GDSound` | Sound object |
| `GDSoundEvent2D` / `GDSoundEvent3D` | 2D/3D sound events |
| `GDSoundEventScope` / `GDSoundEvent3DB` | Sound event variants |
| `GDPlaySound` / `GDStopSound` | Sound control |
| `SoundManager` | Audio manager |

**Engine / Export:**

| Class | Purpose |
|---|---|
| `GDPath` / `GDGoPath` | Spline/path movement |
| `GDSpline` | Spline object |
| `GDEtalon` | Engine utility |
| `GDFolder` | Object grouping/folder |
| `GDPlayMovie` | Cutscene/movie playback |
| `GDPhysicDef` | Physics |
| `GDTestBrick` | Debug/test object |
| `PS2ExportSettings` | PS2 export configuration — confirms `.GDE` files are PS2 exports |

### Selected Property Reflection

**NABiteTarget:**
- `m_hp`, `m_damagemultiplier`, `m_nutrition`, `m_radius`, `m_eattype`
- `m_creature`, `m_dragfactor`, `m_shakefactor`
- `m_bitetargetmodel`, `m_bitetargetmaterialindex`
- `m_dependentlimbs`, `m_rubberskeletonid`

Implies: dismemberment system, material swapping, skeletal replacement, component-based bite interactions.

**NAChewingToy:**
- `m_velocity`, `m_angularvelocity`, `m_gravity`
- `m_attackgroups`, `m_sensorgroups`, `m_target`

**NAWayPoint:**
- `m_links`, `m_waypointgroups`, `m_autolink`, `m_autolinkrange`, `m_dependencytype`

Implies: graph-based AI navigation with automatic path linking.

**NAMessenger:**
- `m_onactivatemessagetargets`, `m_ondeactivatemessagetargets`, `m_onactivatemessagetype`

Implies: event-driven trigger/scripting system.

**NATimeControl:**
- `m_timespeed`, `m_motionblurport`, `m_motionalpha`

Implies: time dilation and motion blur control (cinematic slow-motion).

**Anatomy / Dismemberment:**
- `m_head`, `m_body`, `m_leftarm`, `m_rightarm`, `m_leftleg`, `m_rightleg`
- `m_lefthand`, `m_righthand`, `m_leftfoot`, `m_rightfoot`
- `m_dependentlimbs`, `m_rubberskeleton`, `m_dismembermaterialindex`

Implies: componentized anatomy with limb-specific interactions and dismemberment.

---

## Object Serialization

### PROP Blocks

Runtime gameplay objects are serialized using `PROP` blocks:

```
[PROP][uint32 size][uint32 prop_id][payload]
```

### Known Property IDs

| ID | Meaning | Payload |
|---|---|---|
| `0x080017D8` | Object name | uint32 length + null-terminated string |
| `0x080017DA` | Transform | up to 12 × float32 (local-space rotation matrix + position) |
| `0x080017DF` | AABB bounds | 6 × float32: min XYZ, max XYZ |
| `0x080018CB` | Child link ID | uint32 — used to group objects into hierarchies |

### Hierarchy Reconstruction

Objects are grouped by shared `ChildLink` ID. Within a group, the root is typically a `SkeletonModel` and children are body-part components (head, body, tail, bite targets etc.).

Successfully reconstructed example:
```
Hammerhead SkeletonModel
├── Hammerhead Head Fixed Brick
├── Hammerhead Body Fixed Brick
└── Hammerhead Tail Fixed Brick
```

Transform values represent local-space rotation matrices and positions. Bounds are axis-aligned bounding boxes. Spatial layouts match expected anatomy when visualized.

**Pipeline (archived scripts, now in `scripts/archive/`):** `scripts/object_parser.py` → `dumps/object_parser/objects.txt` → `scripts/hierarchy_rebuilder.py` → `dumps/hierarchy_rebuilder/scene_hierarchy.txt`

**SUPERSEDED (2026-07-16):** this `ChildLink`-ID cross-referencing approach was an early attempt before the real mechanism was found. CLAUDE.md now confirms `BRTR` parent-child nesting is **physical, not ID-based**: a child `CHBR` node sits directly inside its parent's `PRPS` payload, and nested transforms are LOCAL to the parent (not world-space) — world position requires composing the full ancestor chain (`world = parent_world ∘ local`) starting from the root "World" `PRPS` node. Current extractor: `scripts/resolve_brtr_hierarchy.py` → `scenes/<NAME>_resolved_hierarchy.json`. Validated: resolved node count (2,782) exactly matches the flat-scan `CHBR` tag count in `FISH.GDW`.

**Known bug, found 2026-07-30, not yet patched into either script:** both `rip_brtr_scene.py` and `resolve_brtr_hierarchy.py` locate `BRTR` with a naive `data.find(b'BRTR')`, which on some GDWs lands on a false-positive 4-byte match inside `RSRC` instead of the real top-level chunk (same class of bug as the `SCRT` false-positive elsewhere in this doc) — symptom is a nonsense declared size and, in the hierarchy resolver, an `AssertionError: expected root PRPS at start of BRTR`. Confirmed affected: `KATATAMA`, `BEACH`, `BEACHPST`, `START` (not yet swept across the rest). Fix: scan every match, keep only ones where the bytes at `+8`/`+12`/`+16` decode to `magic==0x01025024`, `root_count==1`, next tag `PRPS`, then take the largest such match (small embedded loading-screen sub-archives also pass this check but are far smaller). See CLAUDE.md's note under `scripts/rip_brtr_scene.py` for the exact fix snippet and verified real offsets.

### Important Note

~~The PROP regions currently decoded contain class/property **schema definitions** and **archetype metadata**, not necessarily fully instantiated world-space scene objects. Actual scene object instances with world-space transforms may exist in a separate region later in the file.~~

**RESOLVED — this uncertainty no longer applies.** `BRTR`'s `CHBR` nodes ARE the fully-instantiated world-space scene: 2,782 nodes in `FISH.GDW`, 1,161 with resolvable mesh references, full world transforms, AABBs, and (908 of them) baked per-vertex lighting colour. This has been extracted (`scripts/rip_brtr_scene.py`), hand-edited and reloaded live in-game successfully (see CLAUDE.md's "Live BRTR Editing" section), and even had new content injected into it — see CLAUDE.md's "Custom map feasibility" note.

### Surrounding PROP Structure

```
PRIM
  └── PRPS
        └── PROP
              └── CHBR
```

`PRIM` is a render node / render graph descriptor, not a raw geometry container. It references geometry indirectly rather than storing vertex data directly.

**DECODED (2026-10-03): `PRIM` is a node's collision link.** A `CHBR` node may carry a `PRIM` sub-chunk after its `PRPS`: class `0x20003002`, a zero ID, and its own `PRPS` with `PROP 0x080018D8` = `['MREG'][region_id]`, pointing the node at its `MREG` collision region (598 in FISH). A copied or generated `PRIM` gives an inserted object working collision (user-confirmed). See `CLAUDE.md` (Mesh reference clarification / BVH layout) and `docs/brtr_editing.md`.

**CORRECTED (2026-07-17):** this nesting order is wrong for `BRTR`/`SCRT` scene objects — CLAUDE.md's fully-decoded, byte-verified structure is `CHBR[size]` → `magic(0x0107402F)` + `node_id` → `PRPS[size]` → a flat list of `PROP` entries (mesh ref, name, transform, AABB, flags, etc.), i.e. `CHBR` is the OUTER container and `PROP` entries are direct children of `PRPS`, not the reverse. `PRIM` was not encountered decoding a real node this way — may apply to a different sub-system, or may be a mistaken early read. Individual `PROP` entries are each independently padded to a 4-byte boundary before the next tag (a general alignment rule that also applies at the top chunk level — missing this causes a full parse desync when decoding a property list by hand).

---

## Geometry Pipeline

### Confirmed GMDL Chunk Hierarchy

Fully confirmed by the working `rip_meshes.py` extractor. **11,948 `.obj` files extracted across all 20 GDWs.**

```
GMDL  [variable size]
  [12-byte sub-header: mesh_resource_id, count, hash]
  MATR  [52]        material colour properties
  MATS  [20]        material set
  GMAT              material definitions (GMAT1, GMAT2 sub-entries)
  TSET  [variable]  triangle sets / submeshes, one per MATS material (corrected 2026-10-01)
  TANG  [variable]  triangle data container
    VIND            uint16 triangle LIST index buffer (groups of 3 per triangle)
    TNOR            per-triangle normals
    TFLG            per-triangle flags
  VERT  [variable]  vertex data container
    POSI            float32 XYZ positions  (12 bytes/vertex)
    NORM            float32 XYZ normals    (12 bytes/vertex)
    UVUV            float32 UV coords      (8 bytes/vertex — one pair per vertex)
  VCOL              vertex colours         (16 bytes/vertex — RGBA float32, baked lighting)
```

Key implementation notes:
- `TANG` and `VERT` are **container chunks** — sub-chunks appear inside their payloads, not at the GMDL level
- Index buffer is a **triangle list**, not a strip (groups of 3 uint16 indices per triangle)
- `max(VIND)` must be `< POSI count` — use this to validate meshes and skip false positives
- V coordinate flip (`1.0 - v`) required for standard UV convention in OBJ output
- GMDL blocks with no POSI/VIND, or where max index ≥ vert count, are skipped
- **Triangle winding must be reversed on export (found + fixed 2026-08-17):** raw `VIND` order is DirectX clockwise-front; swap the last two indices per triangle (`a c b`) for OBJ/OpenGL's counter-clockwise-front convention. Verified via cross-product-vs-stored-`NORM` check: 0/1,422 sampled triangles agreed unswapped, 1,422/1,422 agreed swapped. This is what was causing meshes/levels to look "flipped or mirrored" — `BRTR` world positions and rotation matrices were independently checked and are NOT mirrored (positions validated against the real Amity Island map texture, rotation determinants are positive/proper for 1,153/1,161 FISH.GDW objects). All 20 GDWs re-extracted with the fix (2026-08-17); placed-object/mesh counts matched pre-fix totals exactly, confirming no regression. See CLAUDE.md's GMDL Chunk Hierarchy section for full detail.

### Model Types

| Class | Purpose |
|---|---|
| `GDModel` | General model — references geometry via `m_3dModelID` |
| `GDStripModel` | Triangle strip model class (name from class registry; PC format uses triangle lists in VIND) |
| `mcMeshCollection` | Mesh resource container |

### MSHH — Mesh Header

`MSHH` chunks contain named model references. In `TITLE0.GDW` these are immediately followed by names like `Shark2Reference`, `MSDolphinReference`, `MLHalRaj3Reference`. This links a named mesh resource to its geometry data in the RSRC chunk.

### Geometry Linkage (confirmed)

```
BRTR CHBR node
  → PROP 0x08001873: [GMDL tag][mesh_resource_id]
    → linear scan of RSRC for GMDL block whose 12-byte sub-header[0] == mesh_resource_id
      → TANG→VIND (triangle list) + VERT→POSI/NORM/UVUV (vertex data)
```

`rip_brtr_scene.py` builds the `resource_id → mesh_idx` mapping at runtime by scanning GMDL blocks in order.

### Dead End — `0x6FB887C` in `FISH.GDW`

This region was investigated extensively as a potential geometry source. It was **conclusively ruled out** by `scripts/vertex_stride_tester.py`.

At every tested stride (12, 16, 20, 24, 28, 32 bytes), all extracted "vertices" collapsed to the same degenerate value (`~0.0003, 0.0003, 0.0003`). This is characteristic of palette/CLUT colour ramp data being misread as float32 — not a vertex buffer. Do not revisit this region as a geometry source.

### PC vs PS2

This project targets the **PC version** of Jaws Unleashed, which uses **DirectX 8** (`d3d8.dll`). Older notes referencing DirectX 9 or PS2 VIF/GIF DMA packet decoding as the geometry barrier are incorrect for this platform. The PC geometry format uses standard DX8 vertex buffers — float32 XYZ positions, normals, and UVs — as confirmed by the working `rip_meshes.py` extractor. **Mesh extraction is complete: 11,948 `.obj` files extracted across all 20 GDWs.**

---

## Audio System

**Audio extraction is complete.** Two chunk types are fully parsed and exported. All outputs go to `audio/`. Scripts: `scripts/rip_smpb.py` (and `rip_smpc.py`); the original `rip_gsmp.py` was never in the repo, see `docs/audio_format.md`.

### GSMP (raw PCM sample blocks)

Header (24 bytes after the 8-byte chunk header): `[uint32 sample_id][uint32 flags][uint32 hash][uint32 category][uint32 sample_rate][uint32 byte_count]`

Audio data is signed 16-bit PCM mono immediately following the header.

| flags value | meaning |
|---|---|
| `0x01` or `0x81` | standard raw PCM block |
| base \| `0x20` | SMPB-type block (see below) |
| `0x44` | GSFX property block (no audio — contains volume float + GSMP ID reference) |

Category values: `2` = SFX, `3` = music (long loops, 2–3.5 min at 22050 Hz), `6` = ambient.

**Extracted: ~2,873 files across all 20 GDWs.**

### GSMP+SMPB (embedded voice lines)

A variant identified by `data[pos+16:pos+20] == b'OBPR'`. Contains an OBPR sub-chunk replacing the hash/category fields, then a 16-byte secondary header at `pos+16+8+obpr_size` (`[magic][field][sample_rate][byte_count]`), the PCM, and the usual 8 loop bytes (corrected 2026-11-23; read as 20 bytes before, which skipped 2 samples).

These appear to be unused/cut NPC voice lines present in the GDW files but not triggered in the shipped game.

**Extracted: 1,128 files across all GDWs.**

### WMV Cutscenes

Pre-rendered cutscenes in Windows Media Video format live in `movie/` in the game install directory. Audio extracted via ffmpeg to `audio/wmv/`. All WMA2 stereo 48000 Hz. Notable: `INTRO.WMV` (43s), `SHARK.WMV` (79s), `OUTSCENE.WMV` (53s), `PSYCHO.WMV` (157s), `JAWSC4–11.WMV` (unlockable 1975 film clips).

### Unlocated: in-game cutscene voice acting

Voice acting heard during in-engine cutscenes (driven by `NACutScene` / `MPGPlay` / `StreamPlay`) has **not been located**. The 20 GDW files and WMV movies appear to be the complete audio data. Possible remaining locations: unknown RSRC sub-chunks, obfuscated SCRT data, or BRTR audio-source nodes (1,621 non-mesh CHBR nodes include `Audio`-prefixed objects).

### Reflection metadata (engine audio classes)

- `GDSoundEvent2D`, `GDSoundEvent3D`, `GDSoundEventScope`, `GDSoundEvent3DB`
- `GDPlaySound`, `GDStopSound`
- `SoundManager`
- `m_SoundBankList`, `m_soundevent`, `m_sounddelay`

---

## Key Investigation Commands

```bash
# Find all GTEXT texture blocks
grep -oba "GTEXT" GAME_GDWs/FISH.GDW

# Find class/property metadata
grep -oba "NABiteTarget" GAME_GDWs/FISH.GDW
strings -td GAME_GDWs/FISH.GDW | grep -i sound

# Find DDS texture headers (alternate format)
grep -oba "DDS" GAME_GDWs/FISH.GDW

# Find specific PROP property IDs (binary search)
grep -oba $'\xd8\x17\x00\x08' GAME_GDWs/FISH.GDW | head

# Hex inspection at offset
xxd -s 0x06FB5000 -l 4096 GAME_GDWs/FISH.GDW
xxd -s 0x06F7B4A0 -l 256 GAME_GDWs/FISH.GDW
```

### Important Known Offsets (FISH.GDW)

| Offset | Contents |
|---|---|
| `0x06F7B4A0` | CLAS chunk — class registry metadata |
| `0x06F7B7C0` | Skeleton system — GDModel, GDSkeletonModel, XBone |
| `0x06FB5000` | Large reflection metadata region |

---

## Current Status

### Complete / Working

| System | Status | Output |
|---|---|---|
| Top-level chunk parsing | COMPLETE | — |
| GTEXT texture extraction (RGB24, RGBA32, 8bpp indexed) | COMPLETE | 4,923 PNGs across 20 GDWs (updated 2026-07-29, see `CLAUDE.md`) |
| GTEX texture extraction | COMPLETE | 2,787 PNGs across 20 GDWs (updated 2026-07-29, see `CLAUDE.md`) |
| Global texture ID database | COMPLETE | `textures/texture_db.json` — 1,049 unique IDs, 7,710 entries |
| Reflection metadata (CLAS) | CONFIRMED | class names, property names extracted |
| GMDL mesh extraction | COMPLETE | 11,948 `.obj` files across 20 GDWs |
| BRTR scene graph decoding | COMPLETE | 2,782 CHBR nodes in FISH.GDW; 1,161 with mesh refs |
| World-space scene reconstruction | COMPLETE (fixed 2026-10-01) | `scripts/brtr_scene_graph.py` + `rip_brtr_scene.py`, all 20 GDWs: nested composition, absolute-transform flag (`m_nFlags` `0x20000000`), reference instancing (`PROP 0x080017F0`), SC17 whale relocation. Earlier output placed nested meshes with raw local transforms and omitted every reference copy. See CLAUDE.md "Reference Instancing…" |
| Blender scene import | COMPLETE | `scenes/import_fish_blender.py` |
| Audio extraction — GSMP | COMPLETE | ~2,873 WAV files |
| Audio extraction — SMPB | COMPLETE | 1,128 WAV files (NPC barks, GSFX-triggered, **not** cut; corrected 2026-07-29, see CLAUDE.md) |
| WMV cutscene audio | COMPLETE | `audio/wmv/` via ffmpeg |
| d3d8 proxy mod | WORKING | freecam (F2), screenshot (F3), fog (F4), sim pause (F5), foliage hide (F6); **2026-10-01:** real shark XYZ + heading overlay, F8 teleport box + hand-editable bookmarks file, F11 invincibility + infinite hunger (replaces the old god mode removed 2026-08-12). See `mod/README.md` and `docs/exe_analysis.md` |
| `Jaws.exe` static analysis | STARTED (2026-10-01) | Ghidra project + player shark controller, brick memory layout, death paths, reflection field table, see `docs/exe_analysis.md` |

### Open Problems

| System | Status | Notes |
|---|---|---|
| Static environment geometry | **RESOLVED (2025-06-29)** | All terrain tiles, rocks, water planes, and dock structures ARE in BRTR as named mesh instances with full world transforms — no separate BSP/heightmap. |
| Skeletal animation | **RESOLVED (2026-07-17)** | `SKEL`/`BONE`/`WGHT`/`ROTS`/`BROT`/`MTOB`/`CHLD`/`ANIM` fully decoded — bind mesh, per-vertex weights, recursive bone hierarchy, per-bone quaternion keyframes sliced by named clips. Extractor `scripts/rip_skeletons.py` verified on all 30 of FISH.GDW's skeletons. Blender armature/animation import still not written. See CLAUDE.md's Skeletal Animation System section. |
| SCRT scripting chunk | **RESOLVED (2026-07-08)** | Not obfuscated, not scripting — a plain named screen-overlay object tree (same PRPS/CHBR/PROP format as BRTR). |
| In-game cutscene voice acting | NOT FOUND | Present in neither GSMP, SMPB, nor WMV files. |
| Parent-child hierarchy transforms | **RESOLVED (2026-07-16)** | Physical nesting, not ID-based; local transforms compose through the full ancestor chain to world space. See `scripts/resolve_brtr_hierarchy.py`. |
| Texture–mesh material assignment | **RESOLVED (2026-10-01)** | TSET submesh ↔ MATS → GMAT → TEXP, same-GDW textures only (`scripts/gdw_materials.py`). Per-submesh `usemtl` in mesh + scene OBJs, per-face materials in `scenes/import_fish_blender.py`. All 20 GDWs regenerated. The 2026-08-17 heuristic misread TSET counts as texture IDs. See CLAUDE.md "TSET Format" |
| Palette / indexed textures | UNSOLVED (unverified this session) | Some small textures decode incorrectly — likely CLUT/indexed format. Not re-checked in this pass; the PS2 side's palette/PSMT8 format IS fully decoded (see CLAUDE.md's PS2 Version Data section) but that's a separate format from whatever's wrong here on PC. |
| New: brand-new BRTR node insertion | **SOLVED (2026-10-03)** | Was "unsolved" since 2026-07-17. Inserting new nodes works (`scripts/insert_brtr_node.py`, `build_scene.py`); the July attempts all cloned node 302, a hidden render-layer companion. Custom meshes, collision, textures, transparency, Blender scene export and a stripped blank base level all work now. See `docs/brtr_editing.md`. |

---

## Engine Architecture — Confirmed Layout

```
GDW (little-endian, chunk-based)
├── [44-byte text preamble]  "GDED BINARY FORMAT, VERSION 2.6.3.16.\r\n\r\n\x00\x00\x00"
├── FSIZ   [4 bytes]         payload = byte offset where SKIP begins (NOT total file size)
├── VERS   [13 bytes]        version string
├── EXBY   [10 bytes]        exporter's login name ("gyozo" in FISH)
├── GNRL   [8 bytes]         general archive data
├── WDIM   [40 bytes]        world dimension bounds (~5000×2000×5000)
├── RSPR   [0 bytes]         unknown, always empty
├── CLAS   [~250 KB]         class/reflection database — length-prefixed class+property strings
├── RSRC   [~111 MB]         packed resource payloads
│    ├── GMDL blocks         geometry models (VIND/POSI/NORM/UVUV/TSET etc.)
│    ├── GTEXT blocks        textures (TGA-wrapped RGB24/RGBA32)
│    ├── GTEX blocks         sprite/overlay textures
│    └── GSMP blocks         PCM audio samples
├── BRTR   [~5.4 MB]         pre-built scene graph — all placed object instances
│    └── CHBR nodes          one per placed object (name, transform, mesh ref, AABB, vcol)
├── SCRT   [~12 KB]          top-level (NOT inside RSRC), screen-overlay object tree — resolved, not obfuscated scripting
├── SKIP   [variable]        0xFF-filled padding so FDIR lands on a 512-byte boundary
├── FDIR   [40 bytes]        real offset+size index — points at a second, complete, embedded GDED archive
├── ENDF   [0 bytes]         terminates the FIRST embedded archive only — NOT the true EOF
└── [second embedded GDED archive] own VERS/EXBY/GNRL/WDIM/RSPR/CLAS/RSRC/BRTR chain, no FSIZ/SCRT/SKIP/FDIR/ENDF —
      confirmed (on OPEN_S.GDW) to be a bundled loading-screen scene for level transitions
```

**Corrected (2026-07-17):** the original version of this diagram put `SCRT` inside `RSRC` and called it obfuscated scripting, and omitted `RSPR`/`SKIP` and the second embedded archive entirely. See the corrected chunk table above and CLAUDE.md for full details.

The engine is **component-driven and editor-authored**. Runtime gameplay objects are assembled from serialized components with reflected properties. The format preserves a remarkable amount of internal metadata — class names, property names, and object names are all stored as readable strings, making many systems self-documenting. The container version date `20030626` (June 2003) is not an engine freeze: block formats were still revised in 2005 (see "Block format date stamps").

---

## Moved from CLAUDE.md (2026-11-25)

The text below was moved word for word from the root `CLAUDE.md`. It is newer than earlier sections of this file where they disagree.

## GDW Archive Format

`.GDW` files are chunk-based binary containers (little-endian).

**Engine lineage (confirmed 2026-10-11, the user's claim; Claude was hesitant until it was checked):** the format is Appaloosa's **Game World Builder (GWB)** output, the same tool suite as *Ecco the Dolphin: Defender of the Future*. Defender's PS2 `.GDE` levels start `GDED BINARY FORMAT, VERSION 2.1.12.1` (Jaws: 2.6.3.16) and use the same chunks (`GNRL` `WDIM` `RSPR` `CLAS`/`BRCM`/`ACCM` `RSRC` `BRTR` `SCRT`, `CHBR`/`PRPS`/`PROP`, `ACTN`, `GMDL`, `GTEX`, `MREG`, `STRP`) and `GD` classes, packed without 4-byte padding. Appaloosa's 2001 press kit (`docs/sources/Appaloosa_PS2_press_information_2001-09.pdf`) describes GWB as built from "bricks, actions and resources". Details: `docs/gwb_lineage.md`.

**Editor vs. engine (user information, 2026-11-24):** Game World Builder is Appaloosa's in-house **editor** for building the world environments; the runtime **engine** is a separate in-house custom engine called **Diesel Power**. Source: the PAL Dreamcast *Ecco: Defender* back cover (2000, MK-51033-50): "GameWorld Builder™ Software Technology & Diesel Power™ Game Engine are the property of Appaloosa Interactive Corp" (user's scan, `docs/sources/Ecco_Defender_Dreamcast_PAL_back_cover.png`). That Jaws still uses Diesel Power is inferred from the shared Ecco codebase; the name isn't in `Jaws.exe`, the PS2 exe, any GDW or the 2001 press kit. Not to be confused with GRIN's unrelated "Diesel" engine.

**Format date stamps (2026-10-21):** block format versions are literal **YYYYMMDD dates** that `Jaws.exe`'s loaders `cmp` against: `WDIM` 19980304, `GNRL` 19980331, `GMAT` 19980409, `GMOV` 19991005, `GSMP` 20001201, **`SKEL` 20020410** (all 752 skeletons), `GTEX` 20050515 (the texture "stamp `0x0131F253`"), `GMDL` 20051205, `RSRC` 20051208, PS2-only 20060316. The `VERS` string `20030626` is the container version date, **not an engine freeze** (older docs said so; corrected). The only 2001–2002 date anywhere in the files or exe is the April 2002 skeleton revision; raw-scan hits like 20011008–13 are pixel-data noise. Exe: PE timestamp 14 Sep 2006, `(c) 2004 Majesco`, libpng 1.0.5 (1999). Table: `docs/GDW_FORMAT.md` "Block format date stamps".

**File header:** A 44-byte plain-text preamble before the first chunk:
```
GDED BINARY FORMAT, VERSION 2.6.3.16.\r\n\r\n\x00\x00\x00
```
Chunks start at byte offset 44 (0x2C).

**Chunk structure:**
```
[4-byte FOURCC tag][uint32 size][payload]
```

Chunks may contain nested subchunks. Known top-level chunks (in order as they appear):

| Chunk | Offset (FISH.GDW) | Size | Description |
|---|---|---|---|
| `FSIZ` | 0x2C | 4 | File size metadata |
| `VERS` | 0x38 | 13 | Version string |
| `EXBY` | 0x50 | 10 | Unknown — small header block |
| `GNRL` | 0x64 | 8 | General archive data (8-byte placeholder in FISH.GDW) |
| `WDIM` | 0x74 | 40 | World dimension bounds (~5000×2000×5000) |
| `RSPR` | 0xA4 | 0 | Unknown — always empty in FISH.GDW |
| `CLAS` | 0xAC | ~250 KB | Class/reflection database |
| `RSRC` | 0x3D43C | ~111 MB | Packed resource payloads (contains GMDL, GTEXT, GTEX, GSMP, etc.) |
| `BRTR` | 0x6A42B40 | ~5.4 MB | **Scene graph / resource tree** — see Scene System section |
| `SCRT` | 0x6F77FC8 | 12,576 | **Screen/overlay object tree** — see note below. Not scripting, not obfuscated. |
| `SKIP` | 0x6F7B0F0 | 264 | **Sector-alignment padding** — payload is all `0xFF` bytes, sized so the following `FDIR` starts on a 512-byte file-offset boundary. See note below. |
| `FDIR` | 0x6F7B200 | 40 | File directory footer |
| `ENDF` | 0x6F7B230 | 0 | Archive terminator |

Each chunk (including nested ones) is padded to a 4-byte boundary before the next tag begins — account for this when walking the chain, or offsets will drift.

**FDIR chunk structure** (32-byte entries, 8-byte header) — corrected 2026-07-17, FDIR is a real offset index, not just names:
```
Header: [uint32 magic/build-date][uint32 entry_count]
Entry:  [uint32 offset][uint32 size][24 bytes name, null-padded]
```
FDIR names are sub-archive identifiers, not individual asset names (e.g. `FISH00`, `TITLE00`–`TITLE0F`, `AQUARI00`). Each entry's `offset`/`size` point at a second, complete, independently-embedded `GDED BINARY FORMAT...` archive concatenated after the primary archive's `ENDF` (see note below) — verified on `FISH.GDW`: entry `FISH00` decodes to `offset=0x6F7B400, size=14415320`, which exactly matches that archive's real start and satisfies `offset+size == EOF`. **Any edit that grows a chunk before this offset (e.g. appending to `RSRC` or `BRTR`) must patch this field by the same delta**, or the game will seek to the wrong place for the second archive. Individual textures/meshes have no stored names in FDIR; they are identified by their numeric resource ID.

**Note on the second embedded archive (found 2026-07-15, mechanics decoded 2026-07-17):** every GDW's declared `ENDF` is not the true end of the file — a second, complete, independent `GDED BINARY FORMAT...` archive (own preamble, own `VERS/EXBY/GNRL/WDIM/RSPR/CLAS/RSRC/BRTR` chain) is concatenated immediately after, padded to reach it with `0xFF` bytes just like `SKIP`. This second archive has **no `FSIZ`, `SCRT`, `SKIP`, `FDIR`, or `ENDF` of its own** — it just ends at true EOF right after its own `BRTR`. Confirmed on `OPEN_S.GDW` (11 such embedded sub-archives) to be **bundled loading-screen scenes** for level transitions (e.g. one named `OPEN_S00`/`LevelLoaderKAT`, holding progress-bar/hint-text UI objects for transitioning to `KATATAMA.GDW`) — not terrain, not cut content. Bounded story levels carry one small (~14MB) embedded archive (mostly a shared/duplicate stub); open zones carry many more, proportional to how many destinations they connect to. `FISH.GDW`'s own second archive has a ~14MB `RSRC` and a tiny (~6KB) `BRTR` (a handful of `CHBR` nodes), consistent with a small loading-screen scene but not independently re-verified by node name.

**Note on PROP-level alignment (found 2026-07-17):** the "padded to a 4-byte boundary before the next tag" rule (see below) also applies **inside** `PRPS` payloads, i.e. individual `PROP` entries are each individually 4-byte-aligned, not just top-level GDW chunks. Missing this causes a full parse desync when decoding a `CHBR` node's property list by hand — probably a general rule for all nested tag sequences in this format (TSET/TANG/VERT sub-chunks not re-verified against it, but suspected to hold there too).

**Note on `SCRT` (corrected 2026-07-08 — do not trust earlier "obfuscated scripting chunk" claim):** There are two `SCRT`-tagged byte sequences in `FISH.GDW`. The one previously documented at offset `0x1105ECC` **inside** `RSRC` is a **false-positive tag match** — its "size" field decodes to over 1 billion, which is impossible, meaning it is not a real chunk header at all, just a coincidental 4-byte pattern inside unrelated binary/compressed data (the printable-ASCII-but-noise bytes seen there are not obfuscated script code, they're just whatever data happens to sit next to the coincidental match). The **real** `SCRT` chunk is a normal **top-level** chunk (sibling of `BRTR`/`FDIR`, not nested in `RSRC`) at `0x6F77FC8`, and it is **not obfuscated** — it uses the same plain `PRPS`/`CHBR`/`PROP` tree format as `BRTR` (see Scene / Object System section). Its root node is named `"Screen"` and its 20 `CHBR` children are named render/overlay targets: `Whale, GDScreen 3-7, CrowdScreenek, WaterSurface, TransparencyAbove/Below/Blur, ReflectionAbove/Below/Blur, ScreenWater/Above/Below, MotionBlur, ZZZ, XXX`. This is a small **screen-space post-processing overlay tree** (water surface reflection/refraction targets, transparency layers, motion blur, crowd billboard, a "Whale" screen effect) tied to the `GDScreen`/`GDOverlay`/`GDForceOverlay` engine classes seen in `CLAS` — not a scripting/gameplay-logic chunk. It reuses the same object-name property (`0x080017D8`) as `BRTR` CHBR nodes, plus a second, still-undocumented property range (`0x08001980`–`0x08001993`) specific to these screen objects. The PS2 `_FISH.GDE` file has the equivalent chunk (also top-level, 8,772 bytes, 14 `CHBR` children) but its nodes use a different but parallel ID range (`0x08001957`–`0x0800196A`) and have no name property set — see PS2 Version Data section.

**Note on `SKIP` (decoded 2026-07-08):** `SKIP` is sector-alignment padding, nothing more. Its payload is entirely `0xFF` bytes, and its size is always exactly what's needed so the byte offset immediately after it (where `FDIR` begins) lands on a multiple of 512. Confirmed across FISH, TOWN, START, AQUARIUM, TITLE0 (PC) and `_FISH.GDE` (PS2) — sizes vary per file (20–428 bytes) because `SCRT` ends at a different arbitrary offset each time, but the post-`SKIP` offset is always `% 512 == 0` in every case checked. No further structure to parse.

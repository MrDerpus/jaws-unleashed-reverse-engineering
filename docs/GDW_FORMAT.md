# GDW file format

**In short:** a `.GDW` file is one *Jaws Unleashed* level. It is a little-endian binary file made of tagged chunks. Each chunk has a 4-letter tag, a size and its content. The file holds:
- the level's class and field names (`CLAS`);
- all its resources: meshes, textures, sounds, collision, skeletons (`RSRC`);
- the placed objects (`BRTR`);
- a screen-overlay tree (`SCRT`);
- one or more small loading-screen levels, stored after the end.

The format is the output of Appaloosa's **Game World Builder** editor. Its history is in `docs/gwb_lineage.md`.

This doc was rewritten for readability on 2026-11-27. The previous version, with its dated corrections, is in `docs/archive/GDW_FORMAT_old_2026-11-27.md`.

---

## Contents

1. [The level files](#1-the-level-files)
2. [File layout](#2-file-layout)
3. [The top-level chunks](#3-the-top-level-chunks)
4. [Loading-screen levels after the end](#4-loading-screen-levels-after-the-end)
5. [Rules for editing](#5-rules-for-editing)
6. [Format date stamps](#6-format-date-stamps)
7. [The text version of the format](#7-the-text-version-of-the-format)
8. [Resources at a glance](#8-resources-at-a-glance)
9. [Classes](#9-classes)
10. [Dead ends and old mistakes](#10-dead-ends-and-old-mistakes)
11. [Handy commands](#11-handy-commands)

---

## 1. The level files

There are 20 `.GDW` files, one per level, in `GAME_GDWs/`. Which story stage each holds is in `CLAUDE.md` ("Game Content") and `docs/mission_system.md`.

**Special files:**
- **`TITLE0.GDW`** has no meshes. Its field table differs from the other 19 levels (see §3, `CLAS`).
- **`OPEN_S`, `OPEN_NE`, `OPEN_NW`** are the open-ocean zones. They are much bigger: 337–432 MB, against ~120–150 MB for other levels.
- **`_FISH.GDE`** is from the PS2 release, not a PC dev build. All PS2 files are in `GAME_GDWs/ps2/`. See `docs/ps2_asset_extraction.md`.

**Every level carries a shared pool of assets.** An asset being in a file doesn't mean it's used. It is only used if a `BRTR` node points to it.

---

## 2. File layout

### The first line

Every file starts with a 44-byte text line:

```
GDED BINARY FORMAT, VERSION 2.6.3.16.\r\n\r\n\x00\x00\x00
```

The first chunk starts right after it, at byte `0x2C`.

### A chunk

```
[4-byte tag][uint32 size][content]
```

- The size counts only the content, not the 8-byte header.
- **Every chunk is padded to a 4-byte boundary** before the next tag.
- This also holds inside chunks, down to each single `PROP` entry inside a `PRPS`. Forgetting it throws the reading off.
- Some chunks hold more chunks inside them, using the same pattern.

### Top-level chunks, in order

Offsets are from `FISH.GDW`.

| Chunk | Offset | Size | What it is |
|---|---|---|---|
| `FSIZ` | `0x2C` | 4 | Where `SKIP` begins |
| `VERS` | `0x38` | 13 | Container date `20030626` |
| `EXBY` | `0x50` | 10 | Who exported the file (`gyozo` here) |
| `GNRL` | `0x64` | 8 | General data |
| `WDIM` | `0x74` | 40 | World size |
| `RSPR` | `0xA4` | 0 | Always empty |
| `CLAS` | `0xAC` | ~250 KB | Class names and field table |
| `RSRC` | `0x3D43C` | ~111 MB | All resources |
| `BRTR` | `0x6A42B40` | ~5.4 MB | The placed objects (scene graph) |
| `SCRT` | `0x6F77FC8` | 12,576 | Screen-overlay tree |
| `SKIP` | `0x6F7B0F0` | 264 | `0xFF` padding |
| `FDIR` | `0x6F7B200` | 40 | Directory of loading-screen levels |
| `ENDF` | `0x6F7B230` | 0 | End of the main level |
| *(loading-screen level)* | `0x6F7B400` | ~14 MB | See §4 |

PS2 files also have a `BNCH` chunk, a shared name table. See `docs/ps2_asset_extraction.md`.

---

## 3. The top-level chunks

### `FSIZ`

- One `uint32`: the byte offset where `SKIP` begins. That is also where `SCRT` ends.
- It is **not** the total file size.
- The game passes it to a loading-progress function that is empty in the retail build.

### `VERS`

- The text `20030626`, the same in every file.
- It is the container format's date, **not** the date the engine was frozen. Block formats kept changing until December 2005 (§6).
- Never read by the game.

### `EXBY`

- "Exported by": a length, then the login name of whoever exported the file.
- PC logins: `jts`, `gyozo`, `martens`. Who they are: `docs/gwb_lineage.md` §7.
- Never read by the game.

### `GNRL`

- Two `uint32`s.
- The first is a format stamp, `19980331`.
- The second (35,210 in FISH) is close to, but not exactly, the highest node ID. Its meaning isn't confirmed.

### `WDIM`

- 40 bytes: the stamp `19980304`, then floats of about 5000 × 2000 × 5000.
- Probably the world's size or bounds.

### `RSPR`

- Always empty. Purpose unknown.

### `CLAS`: class names and the field table

- Holds the names of every class the level uses, as length-prefixed strings:
  - `BRCM`: brick classes, for the `0x01…` nodes.
  - `ACCM`: action classes, for the `0x02…` actions.
  - Then primitive and property class lists.
- A node's class ID uses its low 12 bits as an index into these lists.
- **The last part, `PRIM`, is the field table.** It lists every (field name, class name) pair.
- **A `PROP` ID is `0x08000000` plus an index into this table.** Example: `0x080017D8` = `GDBrick.m_Name`.
- 19 of the 20 levels have the same table, 6,662 entries. `TITLE0` differs from entry 979 on, so fixed `PROP` IDs don't work there.
- `scripts/gded_lineage.py prop LEVEL ID` names any ID. The full list of common IDs is in `docs/scene_graph.md`.
- This `PRIM` is not the same as the per-node collision `PRIM` in `BRTR`.

### `RSRC`: resources

- Every mesh, texture, sound, collision region, skeleton and material, one after another.
- It starts with a header: a stamp `20051208` and a mode. Each resource then has an ID and flags, followed by its block.
- **Resource IDs share one number space per level.** A new resource takes the next free ID.
- Summaries of each resource type: §8.

### `BRTR`: the placed objects

- The scene graph: every placed object with its transform, mesh, bounding box, flags and baked lighting.
- Layout: `[0x01025024][1]`, then the root `PRPS` ("World"), then `CHBR` nodes.
- Each node: `[class ID][node ID] PRPS{PROP…}`, sometimes followed by a `PRIM` collision link.
- Child nodes sit **inside** their parent. Their transforms are relative to the parent.
- FISH has 2,782 nodes; 1,161 of them have a mesh.
- Full details: `docs/scene_graph.md`. Editing: `docs/brtr_editing.md`.

**Finding `BRTR` safely:** searching for the bytes `BRTR` also hits false matches inside `RSRC` in 8 levels. Keep only matches whose content starts `0x01025024`, root count 1, then `PRPS`, and take the largest. `gdw_grow.find_brtr` does this.

### `SCRT`: the screen-overlay tree

- Same tree format as `BRTR`. It is **not** scripting, and not obfuscated.
- The root is named "Screen". Its 20 children in FISH are screen effects:
  - `WaterSurface`, and water reflection and transparency layers (`ReflectionAbove`, `TransparencyBelow`, …);
  - `MotionBlur`, `CrowdScreenek`, `GDScreen 3`–`7`, `Whale`, `ZZZ`, `XXX`.
- Its own fields are `0x08001980`–`0x08001993`. On PS2 they are `0x08001957`–`0x0800196A`, and the nodes have no names.

### `SKIP`

- Only `0xFF` bytes. Its size makes `FDIR` start on a 512-byte boundary.
- Sizes vary from 20 to 428 bytes.

### `FDIR`

- A directory of the loading-screen levels stored after `ENDF`.
- Header: `[uint32 stamp 20050707][uint32 count]`, then one 32-byte entry per level: `[offset][size][24-byte name]`.
- Names look like `FISH00`, `TITLE00`–`TITLE0F`, `OPEN_S00`.
- Example: FISH's `FISH00` = offset `0x6F7B400`, size 14,415,320, ending exactly at the end of the file.

### `ENDF`

- Empty. It ends the main level, **not** the file.

---

## 4. Loading-screen levels after the end

- After `ENDF` come one or more complete, separate GWB files, padded with `0xFF` to reach them.
- Each has its own first line and its own `VERS EXBY GNRL WDIM RSPR CLAS RSRC BRTR`. They have no `FSIZ`, `SCRT`, `SKIP`, `FDIR` or `ENDF`.
- **They are loading screens** for moving between levels. Example: in `OPEN_S`, `OPEN_S00` / `LevelLoaderKAT` holds the progress bar and hint text for going to `KATATAMA`.
- Story levels carry one, about 14 MB, mostly shared. Open-ocean zones carry several, one per destination: `OPEN_S` has 11.
- They are not terrain and not cut content.

---

## 5. Rules for editing

- **If you grow a chunk before the loading-screen levels**, patch three things by the same amount: `FSIZ`, `SKIP` and the `FDIR` offsets. `scripts/gdw_grow.py` does this.
- **Never trust a tag found by searching bytes** without checking its size. `GTEXT`, `SCRT` and `BRTR` all have false matches inside data.
- New node IDs must be below `0x100000`; the game's runtime IDs start there.
- Full editing rules: `docs/brtr_editing.md` and `docs/custom_level_tutorial.md`.

---

## 6. Format date stamps

Each block type carries a version number that is a plain **YYYYMMDD date**. `Jaws.exe`'s loaders compare against it.

| Block | Stamp | Note |
|---|---|---|
| `WDIM` | 1998-03-04 | |
| `GNRL` | 1998-03-31 | |
| `GMAT` | 1998-04-09 | after the empty `OBPR` |
| `GMOV` | 1999-10-05 | |
| `GSMP` | 2000-12-01 | |
| `SKEL` | **2002-04-10** | all 752 skeletons |
| `GTEX` | 2005-05-15 | the `0x0131F253` in every texture header |
| `GMDL` | 2005-12-05 | all 11,948 meshes |
| `RSRC` | 2005-12-08 | |
| (PS2 only) | 2006-03-16 | 360 blocks; block type not identified |

**Notes:**
- The `SKEL` loader also checks for `> 20001009` (morph frame count) and `≥ 20020410` (a running-position track).
- The game also checks stamps that no shipped block has, such as 1998-09-02, 2003-02-18 and 2005-07-07 (`FDIR`). These are probably older versions it still accepts.
- **The only 2001–2002 date anywhere is the `SKEL` stamp** (April 2002).
- Values like 20011008–13 found by a raw byte search are chance patterns in pixel data, not stamps.
- The 1998 stamps come before GWB's start in early 1999. The oldest block formats may come from older Novotrade/Appaloosa tools. This is an inference.

**Other dates in `Jaws.exe`:** built 14 Sep 2006; "(c) 2004 Majesco Entertainment"; libpng 1.0.5 (Oct 1999); IJG JPEG (1996).

What these stamps tell us about the engine's history: `docs/gwb_lineage.md` §3.

---

## 7. The text version of the format

The same format exists as text: `GDED TEXT FORMAT`. That is what the editor could save.

- Jaws can't write it; the writer code is dead.
- But Jaws still **reads** it. A full level converted to text loaded and played. A hand-edited fog colour took effect (user-confirmed).
- It's about 2.3× the size of the binary file and takes about 20 s to load a 105 MB level.
- Judged not practical for editing (user). Kept as a curiosity.

**Syntax:**

```
GDED TEXT FORMAT, VERSION 2.6.3.16.\r\n\r\n     (then exactly 4 raw bytes)
Chunk: PROP {                                    (no sizes; "}" ends a chunk)
  CLASSID: 2131-1-8                              (bits 0-11, 12-23, 24-31 = PROP 0x08001853)
  COLOR: 0.56, 0.69, 0.79, 1
}
INT: -5   SHORT: 3   REAL: 1.5   SET: ACD (bit n = 'A'+n, '-' = 0)   ResID: GTEX (0000 = 0)
STRING: "name" ('-' = none)   VECTOR: x, y, z   MATRIX: 12 values   BUFFER: hex byte tokens
```

- Labels can be anything before the `:`. Arrays have one value per line.
- `FDIR`'s 24-byte names are read raw. The loading-screen levels stay binary.
- NaN and infinity can't be written.

**How to convert:** the bytes of a binary file don't say which reader reads which value. So converting needs a load trace from the mod: `scripts/gdw_to_text.py LEVEL.GDW TRACE.bin OUT.GDW`. Game-side details: `docs/exe_analysis.md` "GDED text format".

---

## 8. Resources at a glance

All of these live in `RSRC`. Each line points to the doc with the full layout.

| Type | What | Doc |
|---|---|---|
| `GTEX` | Textures | `docs/texture_format.md` |
| `GMDL` | Meshes | `docs/rsrc_formats.md` |
| `GMAT` | Materials | `docs/rsrc_formats.md` |
| `MREG` | Collision | `docs/rsrc_formats.md` |
| `SKEL` | Skeletons and animation | `docs/animation_system.md` |
| `GSMP` | Sound samples, voice lines, cutscene dialogue | `docs/audio_format.md` |
| `GSFX` | Sound triggers | `docs/audio_format.md` |
| `GMOA`, `GSQD` | Other resource types | `docs/rsrc_formats.md` |

### Textures (`GTEX`)

- Every texture is a `GTEX` chunk. "GTEXT" is **not** a tag: it's `GTEX` followed by a size whose first byte is `0x54` ("T").
- Two kinds: plain, and with an `OBPR` block.
- Plain header: `[id][flags 1][stamp 0x0131F253][0][width][height][bpp]`, then `TGAN` with a TGA image inside.
- **Pixels start right after the 18-byte TGA header:** block `+0x42` for plain textures.
- Pixel formats:
  - 24-bit = **BGR**;
  - 32-bit = **BGRA**;
  - 8-bit = a 768-byte RGB palette, then indices.
- Images are stored bottom-up, so flip them on export.
- Cyan `#00FFFF` is the see-through colour.
- **Texture IDs repeat across levels with different images.** Look a texture up in the same level only.
- Extractors: `scripts/rip_textures.py`, `scripts/rip_gtex.py`.

### Meshes (`GMDL`)

```
GMDL
  [12-byte header: mesh ID, count, hash]
  MATR            material colours
  MATS            material set
  TSET            submeshes, one per material
  TANG            triangle data (starts with a uint32 count)
    VIND          uint16 triangle list (3 per triangle; not strips)
    TNOR          per-triangle normals
    TFLG          per-triangle flags
  VERT            vertex data (starts with a uint32 count)
    POSI          float32 XYZ positions
    NORM          float32 XYZ normals
    UVUV          float32 UVs
```

- **Linking a node to its mesh:** `PROP 0x08001873` holds `['GMDL'][mesh ID]`. Find the `GMDL` whose header starts with that ID.
- **Linking a mesh to its textures:** `TSET[i]` uses `MATS[i]` → `GMAT` → `TEXP` → `GTEX` IDs. The first is the base texture.
- **Handedness:** the game is left-handed (DirectX). Exports write `(x, y, −z)` and keep the original triangle order.
- A mesh is valid only if its highest index is below its vertex count. Skip the rest.
- 11,948 meshes extracted: `scripts/rip_meshes.py` → `models/`.

### Sounds (`GSMP`)

- Header: `[sample ID][flags][hash][category][sample rate][byte count]`, then 16-bit mono PCM, then the loop start and end.
- Categories: 2 = sound effects, 3 = music, 6 = ambience.
- **Variants:**
  - `SMPB`: voice barks, all triggered by `GSFX`, so not cut content.
  - `SMPC`: cutscene dialogue with captions.
- Movies (`movie/*.WMV`) are separate files in the game folder.

---

## 9. Classes

**The class lists in `CLAS` name every system in the game.** The engine stores class, field and object names as readable text, so much of it documents itself.

### Name prefixes

| Prefix | Area |
|---|---|
| `GD` | Generic engine and rendering |
| `NA` | Gameplay and shark systems |
| `MB` | Missions and boats |
| `MS` | Menus, spawns, scenarios |
| `ML` | Lighting, effects; also Ecco-era AI such as `MLHalRaj` fish schools |
| `AN` | AI areas and scripted behaviours |
| `BG` | Saved mission state |
| `JT` | Interaction objects |
| `mc` | Mesh collections |
| `X` | Skeletons and animation |

### Classes by area

| Area | Classes |
|---|---|
| Models | `GDModel`, `GDStripModel`, `GDMovingModel`, `GDSkeletonModel`, `XSkeletonModel`, `XExtendedSkeletonModel`, `NALODSkeleton`, `MLEnvSkeletonModel`, `NAPredatorModel`, `NAMorphModel`, `NAVirtualModel`, `NAShadowModel`, `NAStencilVolume`, `mcMeshCollection` |
| Base objects | `GDBrick`, `GDFixedBrick`, `GDLibBrick`, `GDFolder`, `GDTestBrick` |
| Lights and effects | `GDLight`, `GDExtendedLight`, `GDFog`, `NAParticle2004`, `GDParticleTest`, `NAMotionBlur` |
| Water and terrain | `NAWater2004` (main), `NAWater2003`, `NAWaterGrid2000`, `NASlideWater2004`, `NATextureGeneratorGrid`, `NATerrain`, `NAGrid` |
| Screen and text | `GDSprite`, `GDRotSprite`, `GDFont`, `GDPptFont`, `GDTextSprite`, `GDScreen`, `GDViewport`, `GDTileMap` |
| Camera and world | `GDCamera`, `MBSharkCamera`, `GDWorld`, `SharkWorld`, `GDGraph`, `GDNewMat` |
| Gameplay | `NABiteTarget`, `NAChewingToy`, `NAWayPoint`, `NAMessenger`, `NATimeControl`, `NAWhirl2000`, `JTMineWhirl` |
| Animation | `XBone`, `XAnimation`, `XAnimationNames`, `XAnimationSet` |
| Missions and AI areas | `MBMissionBrick`, `MBAramlat`, `ANLaw`, `ANBlock`, `ANPolyArea`, `ANPolyArena`, `ANUnitRef`, `ANHeliRef`, `ANSeekerRef`, `ANPosition` |
| Sound | `GDSound`, `GDSoundEvent2D`, `GDSoundEvent3D`, `GDSoundEventScope`, `GDSoundEvent3DB`, `GDPlaySound`, `GDStopSound`, `SoundManager` |
| Movement and misc. | `GDPath`, `GDGoPath`, `GDSpline`, `GDEtalon`, `GDPlayMovie`, `GDPhysicDef`, `GDControl` (level scripting), `PS2ExportSettings` |

**Watch out for these:**
- `NAPredator` is the predator-vision screen effect, not the shark.
- The shark is `MLSharkCtrl` + `SharkConfig`.
- Several water classes exist side by side (`NAWaterGrid2000`, `NAWater2003`, `NAWater2004`). They are layers carried forward from Ecco. More in `docs/water_system.md`.
- `PS2ExportSettings` is in the registry, so the PS2 version was planned from the start.

### Notable field sets

**`NABiteTarget`** (more in `docs/bite_system.md`):
- `m_hp`, `m_damagemultiplier`, `m_nutrition`, `m_radius`, `m_eattype`;
- `m_creature`, `m_dragfactor`, `m_shakefactor`;
- `m_bitetargetmodel`, `m_bitetargetmaterialindex`, `m_dependentlimbs`, `m_rubberskeletonid`.

These point to limbs coming off, materials swapping on a bite, and skeletons being replaced.

**Body parts:**
- `m_head`, `m_body`, the left and right arms, hands, legs and feet;
- `m_dependentlimbs`, `m_rubberskeleton`, `m_dismembermaterialindex`.

**`NAWayPoint`:** `m_links`, `m_waypointgroups`, `m_autolink`, `m_autolinkrange`. AI paths that link up automatically.

**`NAMessenger`:** `m_onactivatemessagetargets`, `m_ondeactivatemessagetargets`, `m_onactivatemessagetype`. Messages sent when something switches on or off.

**`NATimeControl`:** `m_timespeed`, `m_motionblurport`, `m_motionalpha`. Slow motion with motion blur.

**`NAChewingToy`:** `m_velocity`, `m_angularvelocity`, `m_gravity`, `m_attackgroups`, `m_sensorgroups`, `m_target`.

---

## 10. Dead ends and old mistakes

Earlier notes got these wrong. They're listed here so nobody repeats them.

| Old idea | What's true |
|---|---|
| "GTEXT" is a texture tag | It's `GTEX` + a size byte `0x54` |
| Texture pixels start at `+0x54` | They start at `+0x42`; `+0x54` read 18 bytes too late and sheared the images |
| 32-bit textures are RGBA | They're BGRA |
| Some textures use a broken palette format | That was the two bugs above. Real 8-bit textures are rare: 2 copies of one UI icon, with a grey ramp palette. |
| `SCRT` is obfuscated scripting inside `RSRC` | That was a false match. The real `SCRT` is a plain top-level overlay tree. |
| `BRTR` is a resource index | It's the scene graph |
| Objects are grouped by a shared "child link" ID (`0x080018CB`) | Children sit physically inside their parent's node. The old scripts are in `scripts/archive/`. |
| `FSIZ` is the file size | It's where `SKIP` begins |
| `ENDF` is the end of the file | Loading-screen levels follow it |
| `FDIR` is a list of names | It's an offset and size index |
| `VERS` 2003-06-26 is when the engine froze | Block formats changed until Dec 2005 |
| `SMPB` voice lines are unused | All are triggered by `GSFX` |
| Cutscene voice acting can't be found | It's in `SMPC` sounds |
| PC meshes need PS2 VIF/GIF decoding | The PC uses plain DirectX 8 vertex buffers |
| FISH offset `0x6FB887C` holds geometry | Ruled out: every stride gives the same degenerate values. It's colour-ramp data. |

**Still unchecked:** an old note says the open-ocean files have extra repeating tags (`HHHH`, `TTDT`, `DTTD`, `XXHX`) holding terrain or water grids. Later work found all terrain as normal `BRTR` meshes. Whether those tags are real chunks, perhaps a separate streaming or level-of-detail system, hasn't been checked. `docs/water_system.md` still lists them.

**Unidentified high-count tags:** `TMTX` (common in ARMADA, DOCKS, DEEPSEA2, KATATAMA, WRACK), `TCAM` (common in DOCKS), `LUDL`, `LVDL`, `DLUD`. Their purpose isn't known. `TRAN`, `ROTS`, `MTOB` and `CHLD` are skeleton parts (`docs/animation_system.md`).

---

## 11. Handy commands

```bash
# Where a class or field name appears
grep -oba "NABiteTarget" GAME_GDWs/FISH.GDW
strings -td GAME_GDWs/FISH.GDW | grep -i sound

# A PROP ID in the bytes (0x080017D8 = object name)
grep -oba $'\xd8\x17\x00\x08' GAME_GDWs/FISH.GDW | head

# Look at bytes at an offset
xxd -s 0x6F77FC8 -l 256 GAME_GDWs/FISH.GDW      # start of SCRT

# Name a PROP ID
python3 -I scripts/gded_lineage.py prop GAME_GDWs/FISH.GDW 0x08001873
```

Remember the warning in §5: a tag found this way may be a false match.

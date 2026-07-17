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
| `MINEMSHA.GDW` | Menemsha |
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

## Archive Structure

**Engine version:** All 20 GDW files share the identical header `GDED BINARY FORMAT, VERSION 2.6.3.16` with an internal date of `20030626` (June 26, 2003) — three years before the 2006 release. The engine was frozen well before ship.

**Development history and engine lineage:**

The engine predates Jaws Unleashed by several years. Appaloosa Interactive built the same underwater engine for *Ecco the Dolphin: Defender of the Future* (2000). The game was then developed under the working title *Sole Predator* and demonstrated as a tech demo in 2004 while Appaloosa searched for a publisher. A publisher subsequently acquired the Jaws license and the game shipped in 2006 as *Jaws Unleashed*.

The engine freeze date of June 2003 means the core technology was already mature before Sole Predator was even publicly shown. When the Jaws license was acquired, the engine was not meaningfully changed — content and gameplay were extended on top of a frozen build. This explains several things visible in the files:

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
| `VERS` | CONFIRMED | Version information |
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
| `EXBY` | UNKNOWN | Unknown archive metadata |

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
| `TSET` | ~12K total | Texture set |
| `TANG` | ~12K total | Tangent data |
| `MATR` | ~12K total | Material |
| `POSI` | ~12K total | Position data |
| `TRAN` | ~26K total | Transform |
| `ROTS` | ~16K total | Rotation |
| `TMTX` | ~39K total | Transform matrix — prominent in ARMADA, DOCKS, DEEPSEA2, KATATAMA, WRACK |
| `ACTN` | ~21K total | Action / animation action |
| `GTEX` | ~21K total | Geometry texture reference (distinct from 5-byte `GTEXT` texture blocks) |
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
| `+0x54` | pixel payload start | |

**Payload size formula:**
```
payload_size = block_size - 0x54
```

### Pixel Formats

| BPP | Format | Handling |
|---|---|---|
| `32` | RGBA32 | Read directly as RGBA bytes |
| `24` | RGB24 | Stored as BGR — swap to RGB on read |
| Other | Unknown | Dump as `.raw` for manual inspection |

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

### Extraction Pipeline

```
GTEXT block
  → read header (width, height, BPP)
  → calculate payload_offset = GTEXT_offset + 0x54
  → calculate payload_size = block_size - 0x54
  → extract raw bytes
  → convert to PIL image (swap BGR→RGB for 24bpp)
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

**Pipeline:** `scripts/object_parser.py` → `dumps/object_parser/objects.txt` → `scripts/hierarchy_rebuilder.py` → `dumps/hierarchy_rebuilder/scene_hierarchy.txt`

**SUPERSEDED (2026-07-16):** this `ChildLink`-ID cross-referencing approach was an early attempt before the real mechanism was found. CLAUDE.md now confirms `BRTR` parent-child nesting is **physical, not ID-based**: a child `CHBR` node sits directly inside its parent's `PRPS` payload, and nested transforms are LOCAL to the parent (not world-space) — world position requires composing the full ancestor chain (`world = parent_world ∘ local`) starting from the root "World" `PRPS` node. Current extractor: `scripts/resolve_brtr_hierarchy.py` → `scenes/<NAME>_resolved_hierarchy.json`. Validated: resolved node count (2,782) exactly matches the flat-scan `CHBR` tag count in `FISH.GDW`.

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
  TSET  [variable]  texture channel assignments (see TSET section)
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

**Audio extraction is complete.** Two chunk types are fully parsed and exported. All outputs go to `audio/`. Scripts: `scripts/rip_gsmp.py` and `scripts/rip_smpb.py`.

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

A variant identified by `data[pos+16:pos+20] == b'OBPR'`. Contains an OBPR sub-chunk replacing the hash/category fields, then a secondary header at `pos+16+8+obpr_size` with sample rate and byte count.

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
| GTEXT texture extraction (RGB24, RGBA32) | COMPLETE | 4,673 PNGs across 20 GDWs |
| GTEX texture extraction | COMPLETE | ~1,660 PNGs across 20 GDWs |
| Global texture ID database | COMPLETE | `textures/texture_db.json` — 1,049 unique IDs |
| Reflection metadata (CLAS) | CONFIRMED | class names, property names extracted |
| GMDL mesh extraction | COMPLETE | 11,948 `.obj` files across 20 GDWs |
| BRTR scene graph decoding | COMPLETE | 2,782 CHBR nodes in FISH.GDW; 1,161 with mesh refs |
| World-space scene reconstruction | COMPLETE | `scenes/FISH_brtr.obj` (15 MB), `FISH_brtr.json` |
| Blender scene import | COMPLETE | `scenes/import_fish_blender.py` |
| Audio extraction — GSMP | COMPLETE | ~2,873 WAV files |
| Audio extraction — SMPB | COMPLETE | 1,128 WAV files (cut voice lines) |
| WMV cutscene audio | COMPLETE | `audio/wmv/` via ffmpeg |
| d3d8 proxy mod | WORKING | freecam, XYZ overlay, god-mode toggle |

### Open Problems

| System | Status | Notes |
|---|---|---|
| Static environment geometry | **RESOLVED (2025-06-29)** | All terrain tiles, rocks, water planes, and dock structures ARE in BRTR as named mesh instances with full world transforms — no separate BSP/heightmap. |
| Skeletal animation | UNSOLVED (partial) | `SKEL`/`BONE`/`WGHT`/`ROTS`/`BROT`/`MTOB`/`CHLD`/`ANIM` blocks confirmed and structure partially decoded in RSRC; extractor + Blender armature import not yet written. |
| SCRT scripting chunk | **RESOLVED (2026-07-08)** | Not obfuscated, not scripting — a plain named screen-overlay object tree (same PRPS/CHBR/PROP format as BRTR). |
| In-game cutscene voice acting | NOT FOUND | Present in neither GSMP, SMPB, nor WMV files. |
| Parent-child hierarchy transforms | **RESOLVED (2026-07-16)** | Physical nesting, not ID-based; local transforms compose through the full ancestor chain to world space. See `scripts/resolve_brtr_hierarchy.py`. |
| Texture–mesh material assignment | PARTIAL | TSET IDs resolvable via texture_db.json; UV mapping in Blender not yet implemented |
| Palette / indexed textures | UNSOLVED (unverified this session) | Some small textures decode incorrectly — likely CLUT/indexed format. Not re-checked in this pass; the PS2 side's palette/PSMT8 format IS fully decoded (see CLAUDE.md's PS2 Version Data section) but that's a separate format from whatever's wrong here on PC. |
| New: brand-new BRTR node insertion | **UNSOLVED (found 2026-07-17)** | Injecting a new resource into RSRC and repointing/relocating existing BRTR nodes both work in-game; appending an entirely new CHBR sibling node does not render, cause unknown. See CLAUDE.md's "Custom map feasibility" note. |

---

## Engine Architecture — Confirmed Layout

```
GDW (little-endian, chunk-based)
├── [44-byte text preamble]  "GDED BINARY FORMAT, VERSION 2.6.3.16.\r\n\r\n\x00\x00\x00"
├── FSIZ   [4 bytes]         payload = byte offset where SKIP begins (NOT total file size)
├── VERS   [13 bytes]        version string
├── EXBY   [10 bytes]        unknown archive metadata
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

The engine is **component-driven and editor-authored**. Runtime gameplay objects are assembled from serialized components with reflected properties. The format preserves a remarkable amount of internal metadata — class names, property names, and object names are all stored as readable strings, making many systems self-documenting. The engine freeze date of `20030626` (June 2003) predates the 2006 ship by three years; the core was finalized before the Jaws license was even acquired.

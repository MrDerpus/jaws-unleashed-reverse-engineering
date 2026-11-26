# RSRC resource formats: meshes, materials, collision, AI zones

**In short:** a level's `RSRC` chunk holds all its resources. This doc covers four of them:
- **`GMDL`** meshes: vertices, triangles, and submeshes that each use one material;
- **`GMAT`** materials: which textures a submesh uses, plus colour, shine, two-sidedness and so on;
- **`MREG`** collision regions: a box tree over a mesh's triangles;
- **`GMOA`/`GSQD`** AI zones: named behaviour areas tied to collision regions.

Textures are in `docs/texture_format.md`, skeletons in `docs/animation_system.md`, sounds in `docs/audio_format.md`.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/rsrc_formats_old_2026-11-27.md`.

---

## Contents

1. [What's in `RSRC`](#1-whats-in-rsrc)
2. [Meshes (`GMDL`)](#2-meshes-gmdl)
3. [Submeshes (`TSET`) and texture binding](#3-submeshes-tset-and-texture-binding)
4. [Materials (`GMAT`)](#4-materials-gmat)
5. [Handedness](#5-handedness)
6. [Collision (`MREG` / `BREG` / `STRI`)](#6-collision-mreg--breg--stri)
7. [AI zones (`GMOA` / `GSQD`)](#7-ai-zones-gmoa--gsqd)
8. [Old mistakes](#8-old-mistakes)

---

## 1. What's in `RSRC`

- `RSRC` starts with a header (stamp `20051208` and a mode; `docs/GDW_FORMAT.md`). Then each resource follows as an ID, flags and its block.
- **Resource IDs share one number space per level.** New resources take the next free ID.
- Search for block types by byte pattern rather than hopping by sizes from the start.

**Rough order of blocks in FISH:**

1. `GTEX` textures
2. `GSMP` / `SMPB` audio samples
3. `GSFX` sound triggers
4. `GMAT` materials
5. `SKEL` skeletons (with `BONE`, `ROTS`, `ANIM` inside)
6. `GMDL` meshes
7. `MREG` collision regions (from file offset `0x69CBB80`)
8. `GMOA` / `GSQD` AI zones (from `0x6A329F4`)

**Tags found in FISH's `RSRC`** (a sliding-window scan, 2025-06-29):

| Tag | Count | What |
|---|---|---|
| `GMDL` | 459 | Mesh (§2) |
| `MREG` | 123 | Collision region (§6) |
| `GMOA` / `GSQD` | 485 / 485 | AI zones (§7) |
| `SKEL` / `BONE` / `WGHT` | 30 each | Skeleton, root bone, vertex weights |
| `CHLD` | 548 | Child bone |
| `BROT` | 140 | Sibling bone |
| `MTOB` / `ROTS` | 718 each | Inverse rest matrix (4×3 floats) / per-frame rotations |
| `ANIM` | 10 | Named animation clips |
| `TRAN` | 1,152 | A 4-byte sub-chunk; inside `GMAT` it's transparency, in bones a translation |
| `GTEX`, `GSMP`, `GSFX`, `GMAT` | ~15k, ~10k, ~20k, ~41k | Raw tag matches, mostly coincidences inside data. Real counts: FISH has 321 textures and 434 materials. |

Skeleton tags are explained in `docs/animation_system.md`. `GSFX` is a sound trigger pointing at a sample, not audio (`docs/audio_format.md`).

---

## 2. Meshes (`GMDL`)

**Extraction:** `scripts/rip_meshes.py` works on all 20 levels: **11,948 `.obj` files** in `models/<NAME>/`.

| Level | Meshes | Level | Meshes |
|---|---|---|---|
| AQUARIUM | 1,161 | OPEN_NE | 1,100 |
| START | 1,115 | KATATAMA | 923 |
| OPEN_S | 1,009 | OPEN_NW | 798 |
| BEACH | 765 | TOWN | 696 |
| ARMADA | 666 | DEEPSEA2 | 660 |
| DOCKS | 465 | BEACHPST | 460 |
| MINEMSHA | 386 | FISH | 384 |
| DEEPSEA | 366 | WRACK | 344 |
| GAUNTLET | 261 | CHASE | 244 |
| TITLE | 145 | TITLE0 | 0 |

### Layout

```
GMDL
  [12-byte header: mesh_id, count, hash]
  MATR  [52]    material colour properties
  MATS          [uint32 n] + n × ['GMAT'][gmat_id]   one per submesh
  GMAT          material definitions
  TSET          submeshes (§3)
  TANG          [uint32 triangle count], then:
    VIND        uint16 triangle list
    TNOR        per-triangle normals
    TFLG        per-triangle flags
  VERT          [uint32 vertex count], then:
    POSI        float XYZ positions (12 bytes per vertex)
    NORM        float XYZ normals (12 bytes per vertex)
    UVUV        float UV (8 bytes per vertex, one pair)
  VCOL          vertex colours (16 bytes per vertex, RGBA floats)
```

### Reading it

- **`TANG` and `VERT` are containers.** Each starts with a uint32 count; skip those 4 bytes, then walk the sub-chunks inside.
- `VIND` is a plain triangle list: 3 indices per triangle.
- **Validate:** the largest `VIND` index must be below the `POSI` count. Skip blocks without `POSI`/`VIND` or failing this check; they're false matches.
- Flip V (`1 − v`) when writing OBJ.
- The mesh ID (first header word) is what nodes reference with `PROP 0x08001873` and what `MREG` points at.

---

## 3. Submeshes (`TSET`) and texture binding

**`TSET` lists submeshes.** Each one is a range of triangles drawn with one material.

```
TSET  [size = (1 + 5N) × 4]
  [uint32 N]                                   number of submeshes
  N × [index][first_vert][vert_count][first_tri][tri_count]
```

- Record *i* covers triangles `first_tri` … `first_tri + tri_count − 1` of `VIND`, and the vertices from `first_vert`.
- **Record *i* is drawn with material `MATS[i]`.** N equals the `MATS` count on 383 of 384 FISH meshes.
- The starts are running sums. Example: `(0,0,204,0,186)`, `(1,204,24,186,16)`, `(2,228,46,202,36)`.
- The `tri_count`s add up to the mesh's triangle total on all 384 FISH meshes.

### From submesh to texture

1. `GMDL.TSET[i]` ↔ `GMDL.MATS[i]`, which names a `GMAT` resource.
2. That `GMAT` block (`['GMAT'][size][id][flags]['OBPR']…`, elsewhere in `RSRC`) has a `TEXP` sub-chunk.
3. `TEXP` = `[uint32 n]` + n × `['GTEX'][texture_id]`. **The first entry is the base texture**; more entries are extra layers (e.g. FISH material 692 has two).

Code: `scripts/gdw_materials.py`.

**Look textures up only in the same level.** Texture IDs collide across levels.

**Coverage** (share of triangles that get a texture, same level):

| Level | Textured |
|---|---|
| FISH | 93 % |
| OPEN_S | 96 % |
| TOWN | 95 % |

The rest are materials with no `TEXP` (3–5 %), flat render targets (under 0.5 %), and 74 OPEN_S triangles whose texture isn't stored in that level.

**Checked by rendering in Blender** (2026-10-01):
- the great white: 5 submeshes → textures 72–77, the shark skin atlas;
- the whale carcass: bloody blue-whale hide;
- the FISH pier area: grassy seafloor, wooden piers, a painted fishing boat.

---

## 4. Materials (`GMAT`)

Each `GMAT` is a list of small named sub-chunks, each `[tag][uint32 size][payload]`. FISH has 434 materials, and each sub-chunk below appears once per material.

| Tag | Size | Contents | Probable meaning |
|---|---|---|---|
| `TEXP` | 8n+4 | `[n]` + n × `['GTEX'][id]` | **Textures** (first = base; §3) |
| `COLS` | 48 | 12 floats (4 × RGBA) | Colour slots |
| `SHIN` | 8 | 2 floats | Specular power, intensity |
| `REFL` | 8 | 2 floats | Reflection |
| `BUMP` | 8 | 2 floats | Bump map |
| `SILL` | 4 | float | Silhouette/rim |
| `BIAS` | 4 | float | Polygon offset |
| `TIAS` | 4 | float | Texture alpha scale |
| `TRAN` | 4 | uint32 | Transparency (0 = opaque) |
| `TWOS` | 4 | uint32 | **Two-sided** (confirmed; used by the level tools) |
| `CHRO` | 4 | uint32 | Chroma key |
| `CLAM` | 4 | uint32 | Texture clamping |
| `SMOO` | 4 | uint32 | Smoothing |
| `STAF` | 4 | uint32 | Shadow/stencil flag |
| `SLIF` | 4 | uint32 | Slice/clip flag |
| `COLT` | 4 | uint32 | Colour tint flag |
| `FLAG` | 4 | uint32 | Material flags |
| `MTOP` | 4 | uint32 | Opacity flag |
| `TXAN` | 8 | 2 uint32 | Texture animation |

Only `TEXP` and `TWOS` are confirmed by use. The other meanings are guesses from the tag names. Extra `TEXP` layers and the unused parameters are open (`docs/open_problems.md`).

---

## 5. Handedness

**The game is DirectX left-handed:** X right, Y up, Z forward. OBJ and Blender are right-handed.

**How the exports handle it** (2026-10-01; user-confirmed correct in Blender):
- `rip_meshes.py` and `rip_brtr_scene.py` write positions and normals as **(x, y, −z)**.
- Faces keep the **original `VIND` order**.
- `scenes/import_fish_blender.py` uses `CONV` = (X=x, Y=z, Z=y), determinant −1, plus `FLIP_Z` on the local side: `matrix_world = CONV @ game_world @ FLIP_Z`.
- Scene OBJs import correctly with Blender's **default** OBJ settings (forward −Z, up Y).
- Manifest `xf`/`pos` values stay in raw game coordinates.
- All 20 levels' `models/` and `scenes/` were regenerated this way.

**Why left-handed:** the shark's right fin (`Jobb…`, Hungarian "right") sits at local +X, the dorsal fin at +Y, the head at +Z. That's only "right" in a left-handed system.

**Why it mattered:** writing raw coordinates into a right-handed format *mirrors* everything, and no rotation can undo a mirror. That was the long-standing "levels look mirrored" bug. The old `CONV` (X=x, Y=−z, Z=y) and Blender's OBJ importer are both rotations (determinant +1).

**Evidence:** on 2,363 FISH triangles in Z-mirrored space, the original order's cross-product normals agree with the stored `NORM` data 2,307 times. The old swapped order agrees 8 times.

---

## 6. Collision (`MREG` / `BREG` / `STRI`)

**In short:** each `MREG` pairs a mesh with a box tree over its triangles. Fully decoded 2026-10-03 on all 123 FISH regions. Collision generated by our tools works in-game (user-confirmed 2026-10-03; `obj_to_gmdl.py --collision`, `docs/brtr_editing.md` §6).

FISH has **123 `MREG` blocks**: region IDs `0x943`–`0x9EB` (2371–2539), file offsets `0x69CBB80`–`0x6A329EC`.

### `MREG`

```
MREG [size]
  [uint32 region_id]
  [uint32 1]
  ['GMDL']                 type tag (not a chunk)
  [uint32 mesh_id]         the paired mesh
  [uint32 0xFFFFFFFF]      "has data"
  PERF [4]                 float, 0.25 in all FISH regions
  BREG                     box tree
  STRI                     triangle order
```

A node uses a region through a `PRIM` chunk (`PROP 0x080018D8` = `['MREG'][id]`).

### `BREG`: the box tree

```
BREG [size]
  [uint32 node_count]                 139–199 in FISH
  node_count × [minX minY minZ maxX maxY maxZ]   floats, 24 bytes each
```

- **Heap order:** node 0 is the root; node k's children are 2k+1 and 2k+2.
- `node_count = 2L − 1`, with **L = max(1, ⌊triangles ÷ 4⌋) leaves**.
- Leaf boxes are the exact bounds of their triangles. Internal boxes are the exact union of their children.
- Boxes are in **mesh-local** space, so the node's transform carries them.
- The root box matches the mesh's vertex bounds exactly.

### `STRI`: triangle order

```
STRI [size]
  [uint32 m]           = the mesh's triangle count
  m × uint32           a permutation of the mesh's triangle indices
```

**Leaves own runs of `STRI`:**
- Leaves are taken in **in-order traversal** (left subtree, then right).
- Each leaf owns the next **4 triangles**.
- When the count isn't a multiple of 4, the 1–3 leftover triangles go into one leaf. Which leaf can't be told from the data, so `obj_to_gmdl.py` pads meshes to a multiple of 4.

### Per-triangle data on collision meshes

122 of 123 collision meshes carry:
- **`TNOR`** = −normalize((B − A) × (C − A)), in raw game coordinates (matches all 46,153 shipped triangles);
- **`TFLG`**, 8 bytes per triangle: `[uint32 1][uint16 flags][uint16 n]`. The low 3 flag bits look like per-edge flags; `0x47` (all set) is what our generator writes. Not fully decoded.

### In the engine

- Loader `0x6E3CB0` (`GDMeshRegions::Load`). It reads `PERF`/`BREG`/`STRI` only when the header field is negative (`0xFFFFFFFF`).
- `MREG` class vtable `0x7F79A0`. Fields: `+0x20` `PERF`, `+0x24`/`+0x30` box count/array, `+0x28`/`+0x2C` `STRI` count/array.
- No leaf ranges are stored; the query code recomputes them.

### Regions vs placed objects (FISH)

- **118 regions** pair with meshes that are also placed visibly in `BRTR`: rocks (`szikla`), sandy shore tiles (`Homokos`), foundations and so on.
- **5 regions** have no visible placement: collision-only geometry.
- The paired meshes span roughly mesh index 23–262.

---

## 7. AI zones (`GMOA` / `GSQD`)

At the end of `RSRC` (FISH: from `0x6A329F4`). 485 of each in FISH.

```
GMOA [size]
  [uint32 gmoa_id]
  [uint32 count]
  [uint32 magic]
  SQDR [8]                 points at one GSQD by ID
  GSQD
    [uint32 zone_id]
    [uint32 count]
    [uint32 magic]
    GSEQ                   a named behaviour, e.g. "repul"
    ['MREG'][region_id]    the area it applies to
  MOIL                     not decoded (~66 KB table of numbers)
```

- A `GSQD` ties a behaviour to an area by pointing at an `MREG` region.
- `repul` (FISH) is probably a repulsion zone: creatures kept out of an area. Unconfirmed.
- The names `GMOA` = "Game Model Object Animation" and `GSQD` = "Game Sequence Data" are guesses from the tags.
- **Open:** `MOIL` (`docs/open_problems.md`).

---

## 8. Old mistakes

| Old claim | Now |
|---|---|
| `TSET` holds texture IDs per layer | It lists submeshes: vertex and triangle ranges (2026-10-01). The "IDs" were counts that happened to match texture IDs. |
| The 2026-08-17 textured scene export (a rock using a black render target, a caustic texture *and* a grass decal); "65 render-target IDs" | Built on that misreading; replaced by the `MATS` → `GMAT` → `TEXP` binding |
| Swap triangle winding (b↔c) when exporting | Keep the original order and negate Z (§5). The swap was only right for un-mirrored data. |
| `RSRC` starts with an unknown 12-byte header | A stamp and a mode, then `[id][flags]` per resource (`docs/GDW_FORMAT.md`) |
| `GTEXT` is a second texture block type | `GTEX` followed by a size byte `0x54` (`docs/texture_format.md`) |
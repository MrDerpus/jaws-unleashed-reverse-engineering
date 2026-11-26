# RSRC resource formats: geometry, materials, collision, AI blocks

Moved word for word from the root `CLAUDE.md` on 2026-11-25 to keep that file short. Where this disagrees with older docs, this text is the newer one.

## Geometry Pipeline — `scripts/rip_meshes.py`

Mesh extraction is **working** across all 20 GDWs. **11,948 total `.obj` files** extracted to `models/<NAME>/`.

| GDW | Meshes | GDW | Meshes |
|---|---|---|---|
| AQUARIUM | 1,161 | OPEN_NE | 1,100 |
| START | 1,115 | KATATAMA | 923 |
| OPEN_S | 1,009 | OPEN_NW | 798 |
| BEACH | 765 | TOWN | 696 |
| ARMADA | 666 | DEEPSEA2 | 660 |
| DOCKS | 465 | BEACHPST | 460 |
| MINEMSHA | 386 | FISH | 384 |
| WRACK | 344 | DEEPSEA | 366 |
| CHASE | 244 | GAUNTLET | 261 |
| TITLE | 145 | TITLE0 | 0 |

### GMDL Chunk Hierarchy

```
GMDL  [variable size]
  [12-byte sub-header: mesh_id, count, hash]
  MATR  [52]       material colour properties
  MATS  [variable] material list: [uint32 n] + n × ['GMAT' tag][uint32 gmat_resource_id], one per TSET submesh
  GMAT              material definitions (GMAT1, GMAT2 sub-entries)
  TSET  [variable] triangle sets (submeshes): vertex/triangle ranges, one per MATS entry — see format below
  TANG  [variable] triangle data container
    VIND            uint16 triangle list index buffer
    TNOR            per-triangle normals
    TFLG            per-triangle flags
  VERT  [variable] vertex data container
    POSI            float32 XYZ positions  (12 bytes/vert)
    NORM            float32 XYZ normals    (12 bytes/vert)
    UVUV            float32 UV coords      (8 bytes/vert — one UV pair per vertex)
  VCOL              vertex colours         (16 bytes/vert — RGBA float32)
```

**Key layout notes:**
- TANG and VERT are **container chunks** — they each begin with a **uint32 count header** (triangle count or vertex count), followed immediately by their sub-chunks. Do not try to parse sub-chunks at the GMDL level; descend into the TANG/VERT payload first, skip 4 bytes, then scan for VIND/POSI/etc.
- Index buffer is a **triangle list** (groups of 3 uint16 indices per triangle, alternating winding for quads)
- `max(VIND indices)` must be `< POSI count` — use this to validate meshes and skip false positives
- V coordinate should be flipped (`1.0 - v`) when writing OBJ for standard UV convention
- GMDL blocks with no POSI/VIND, or where max index ≥ vert count, are skipped
- **Handedness: the game is DirectX LEFT-handed; OBJ/Blender are right-handed. Exports negate Z and keep the original `VIND` order (2026-10-01; this supersedes the 2026-08-17 winding-swap entry below).** The game's axes are X right, Y up, Z forward. Proof from the data: the shark model's right fin (`Jobb…` = Hungarian "right") sits at local +X, the dorsal fin at +Y, and the head at +Z, which is only "right" in a left-handed system. Writing raw coordinates into a right-handed format **mirrors** everything, and no rotation can undo a mirror. That was the long-parked "levels look flipped/mirrored" bug: the old Blender `CONV` (X=x, Y=−z, Z=y) and Blender's OBJ importer are both rotations (determinant +1). Fix: `rip_meshes.py` and `rip_brtr_scene.py` write `(x, y, −z)` for positions and normals, and faces in **original** `VIND` order. Verified numerically on 2,363 FISH triangles: in Z-mirrored space the original order's cross-product normals agree with the stored `NORM` data 2,307/2,363, and the old b↔c swap agrees 8/2,363 (the 2026-08-17 swap was only right for raw, un-mirrored data). `scenes/import_fish_blender.py` now uses `CONV` = (X=x, Y=z, Z=y), determinant −1, plus a `FLIP_Z` on the local side: `matrix_world = CONV @ game_world @ FLIP_Z`. The scene OBJs import correctly with Blender's **default** OBJ settings (forward −Z, up Y). Manifest `xf`/`pos` values stay in raw game coordinates. All 20 GDWs' `models/` and `scenes/` were regenerated with this. **User-confirmed correct in Blender (2026-10-01).**

### TSET Format — triangle sets, not textures (corrected 2026-10-01)

```
TSET [uint32 payload_size]          payload_size == (1 + N*5) * 4
  [uint32 N]                         number of submeshes (== MATS count on 383/384 FISH meshes)
  N × [set_idx][first_vert][vert_count][first_tri][tri_count]
```
Record `i` covers triangles `first_tri … first_tri+tri_count−1` of the `VIND` list (and vertices `first_vert…`), and is drawn with material `MATS[i]`. The starts are running sums of the counts (e.g. `(0,0,204,0,186)`, `(1,204,24,186,16)`, `(2,228,46,202,36)`), and the `tri_count`s add up to the mesh's triangle total on all 384 FISH meshes.

**Correction:** this section previously described TSET as texture-layer assignments ("val_A–val_D contain texture IDs"). That was wrong: those values are vertex/triangle counts and offsets. Everything built on that reading was based on coincidental ID collisions, including the 2026-08-17 textured scene export (the rock "referencing a black render target, a caustic texture AND a grass decal" was just vertex counts landing on unrelated texture IDs) and the "65 render-target IDs" claim.

**Texture binding (decoded 2026-10-01):** `GMDL.TSET[i]` ↔ `GMDL.MATS[i]` → GMAT resource block (`['GMAT'][size][uint32 id][uint32 flags]['OBPR']…`, elsewhere in RSRC) → its `TEXP` sub-chunk `[uint32 n] + n × ['GTEX' tag][uint32 texture_id]`. The first entry is the base texture; extra entries are further layers (e.g. FISH material 692 has two). Implemented in `scripts/gdw_materials.py`. **Look textures up only in the same GDW**, since IDs collide across GDWs. Same-GDW coverage: FISH 93% of triangles textured, OPEN_S 96%, TOWN 95%. The rest are materials with no TEXP (3–5%), flat render targets (<0.5%), or 74 OPEN_S triangles whose texture isn't stored in that GDW. Verified visually by rendering in Blender: the great white (5 submeshes → textures 72–77, the shark skin atlas), the whale carcass (bloody blue-whale hide), and the FISH pier area (grassy seafloor, wooden piers, painted fishing boat).

### GMAT Material Sub-Chunks

Each `GMAT` block contains a full material definition as a sequence of small named sub-chunks (all confirmed via sliding-window scan of RSRC). Every sub-chunk follows the standard `[4-byte tag][uint32 size][payload]` format:

| Tag | Size | Description |
|---|---|---|
| `TEXP` | 8n+4 | Texture binding — `[uint32 n]` + n × `['GTEX' 4-byte tag][uint32 texture_id]`; first entry = base texture (corrected 2026-10-01, see TSET Format) |
| `REFL` | 8 | Reflection map — 2 floats (intensity, falloff) |
| `BUMP` | 8 | Bump map — 2 floats |
| `COLS` | 48 | Diffuse colour — 12 floats (4 × RGBA for multiple colour slots) |
| `SHIN` | 8 | Shininess — 2 floats (specular power, specular intensity) |
| `SILL` | 4 | Silhouette/rim intensity — 1 float |
| `TRAN` | 4 | Transparency — 1 uint32 (0 = opaque) |
| `BIAS` | 4 | Polygon offset bias — 1 float |
| `TIAS` | 4 | Texture image alpha scale — 1 float |
| `STAF` | 4 | Shadow/stencil flag — 1 uint32 |
| `SLIF` | 4 | Slice/clip flag — 1 uint32 |
| `CHRO` | 4 | Chroma key flag — 1 uint32 |
| `SMOO` | 4 | Smoothing — 1 uint32 |
| `TWOS` | 4 | Two-sided rendering — 1 uint32 |
| `CLAM` | 4 | Texture clamping mode — 1 uint32 |
| `COLT` | 4 | Colour tint flag — 1 uint32 |
| `FLAG` | 4 | Material flags — 1 uint32 |
| `TXAN` | 8 | Texture animation — 2 uint32s |
| `MTOP` | 4 | Material opacity flag — 1 uint32 |

These appear as 434 instances each (one per GMAT block in FISH.GDW). The `TEXP` sub-chunk is the key link to textures — it maps a material layer to a GTEX texture block by ID, providing the visual appearance of the mesh surface.

## RSRC Internal Layout

The `RSRC` chunk payload does **not** start immediately with a chunk tag. It begins with a **12-byte binary sub-header** (content unknown), then the first resource block. Resource blocks are not a flat `[tag][size]` chain at the top level — they use a mix of 4-byte and 5-byte marker strings depending on type. Use marker-search (byte-pattern `find`) rather than size-hopping to locate specific block types.

**RSRC payload structure:**
```
[12 bytes sub-header]
[GTEX blocks]          ← texture resources (GTEX format, 4-byte tag)
[GTEXT blocks]         ← texture resources (GTEXT format, 5-char marker)
[GSMP / SMPB blocks]   ← audio samples
[GSFX blocks]          ← sound effect property blocks
[GMAT / material sub-chunk blocks]  ← full material database
[SKEL / BONE / ROTS / ANIM blocks]  ← skeletal animation data
[GMDL blocks]          ← mesh geometry (res IDs 0x745–0xFFFFFFFF)
[MREG blocks]          ← collision/BVH regions (0x69CBB80 onward)
[GMOA / GSQD blocks]   ← AI behavior sequences
```

**Complete list of discovered RSRC chunk tags** (confirmed by sliding-window scan of FISH.GDW RSRC, 2025-06-29):

| Tag | Count (FISH) | Description |
|---|---|---|
| `GMDL` | 459 total | Mesh geometry (see Geometry Pipeline section) |
| `GSFX` | ~20,000 | Sound effect property blocks — `flags=0x44` variant of GSMP; contains volume float + GSMP sample ID reference. NOT audio PCM. |
| `GMAT` | ~41,000 | Material definition blocks |
| `GTEX` | ~15,000 | Texture blocks (GTEX format) |
| `GSMP` | ~10,000 | Audio sample blocks |
| `SKEL` | 30 | **Skeletal animation data, fully decoded** — see Skeletal Animation section |
| `TRAN` | 1,152 | Transform property sub-chunk (4-byte, transparency/transform value) |
| `MREG` | 123 | **Collision mesh region** — see Collision / BVH System section |
| `MTOB` | 718 | 4×3 float32 transform matrix (48 bytes, `[col0 col1 col2 translation]`) |
| `ROTS` | 718 | Rotation keyframe array — float32 quaternion/matrix data for animation |
| `CHLD` | 548 | Child node container — holds MTOB + ROTS sub-chunks |
| `GSQD` | 485 | Game Sequence Data — AI behavior zone definition; see AI System section |
| `GMOA` | 485 | Game Model Object Animation — top-level AI/behavior container |
| `BROT` | 140 | Bone rotation track — contains MTOB |
| `BONE` | 30 | Individual bone definition — contains MTOB (rest pose transform) |
| `WGHT` | 30 | **Vertex weights** for skeletal skinning |
| `ANIM` | 10 | Animation name dictionary — maps animation IDs to string names |

## Collision / BVH System — MREG / BREG / STRI

Each `MREG` block pairs a visual GMDL mesh with a **Bounding Volume Hierarchy (BVH)** for physics/collision. There are **123 MREG blocks** in FISH.GDW (region IDs 0x943–0x9EB, file offsets 0x69CBB80–0x6A329EC within RSRC).

### MREG Block Layout

```
MREG [uint32 size]
  [uint32 region_id]       ← unique region ID (2371–2539 in FISH.GDW)
  [uint32 unknown = 1]
  [uint32 "GMDL" type tag] ← ASCII 0x4C444D47, type discriminator (not a chunk)
  [uint32 mesh_res_id]     ← resource ID of the paired GMDL mesh
  [uint32 flags = 0xFFFFFFFF]
  PERF [4]                 ← float32 LOD/performance hint (always 0.25 in FISH.GDW)
  BREG [variable]          ← BVH node array
  STRI [variable]          ← BVH traversal index list
```

### BREG — BVH Node Array

```
BREG [uint32 size]
  [uint32 node_count]           ← number of BVH nodes (139–199 in FISH.GDW)
  [node_count × 24 bytes]       ← one AABB per node
    [float32 minX minY minZ]    ← bounding box minimum corner
    [float32 maxX maxY maxZ]    ← bounding box maximum corner
```

Node 0 is always the root AABB (enclosing the entire mesh). Subsequent nodes subdivide the space recursively. The vertex extents of the paired GMDL mesh match the root BREG AABB exactly (verified for multiple MREGs).

### STRI — triangle order (decoded 2026-10-03)

```
STRI [uint32 size]
  [uint32 m]               ← = the mesh's triangle count
  [m × uint32]             ← a permutation of the mesh's triangle indices (VIND order)
```

### BVH layout — fully decoded (2026-10-03, all 123 FISH MREGs)

- `BREG` is a binary tree in **heap order**: node 0 is the root, node k's children are 2k+1 and 2k+2. It has `n = 2L − 1` nodes, where **L = max(1, ⌊triangles ÷ 4⌋) leaves**.
- Leaves are taken in **in-order traversal** (left subtree, then right), and each owns the next run of `STRI`: **4 triangles per leaf**, with the 1–3 leftover triangles (when the count isn't a multiple of 4) going into a single leaf. Where that leaf sits isn't determinable from the data. `obj_to_gmdl.py` avoids the question by padding meshes to a multiple of 4 triangles.
- Every leaf box is the exact AABB of its triangles; every internal box is the exact union of its children. Boxes are in **mesh-local** space, so a node's transform carries them.
- Header flags `0xFFFFFFFF` = "has data" (the loader `FUN_006e3cb0` reads `PERF`/`BREG`/`STRI` only when that field is negative). `PERF` = 0.25 in all FISH MREGs.
- Engine loader: `FUN_006e3cb0` (MREG class vtable `0x7F79A0`; `+0x20` PERF, `+0x24`/`+0x30` box count/array, `+0x28`/`+0x2C` STRI count/array). It stores no leaf ranges, so the query code recomputes them.
- Collision meshes (122/123) also carry per-triangle `TNOR` = **−normalize((B−A) × (C−A))** in raw game coordinates (46,153/46,153 shipped triangles) and `TFLG` (8 bytes per triangle: `[uint32 1][uint16 flags][uint16 n]`; the low 3 flag bits look like per-edge flags, and `0x47` = all set is what the generator writes).
- **Generated collision works in-game** (user-confirmed 2026-10-03): `obj_to_gmdl.py --collision` + a node with a `PRIM` pointing at the new region. See `docs/brtr_editing.md`.

### MREG ↔ BRTR Relationship

Of the 123 MREG blocks in FISH.GDW:
- **118 mesh_res_ids** match GMDL meshes that are **also placed as visual instances in BRTR** — rocks (`szikla`), sandy shore tiles (`Homokos`), foundation meshes, etc. each have both a visual BRTR placement AND a collision MREG.
- **5 mesh_res_ids** have MREG collision data but **no BRTR visual instance** — collision-only geometry not rendered.

The `mesh_res_id` in MREG matches the **first uint32 of the 12-byte GMDL sub-header** (same linkage as PROP `0x08001873` in BRTR). GMDL mesh indices for the MREG-referenced meshes in FISH.GDW span approximately idx 23–262.

## AI / Behavior Sequence System — GMOA / GSQD

The AI zone and behavior sequence system occupies the tail of RSRC (0x6A329F4 onward in FISH.GDW).

```
GMOA [uint32 size]     ← Game Model Object Animation — top-level container
  [uint32 gmoa_id]
  [uint32 count]
  [uint32 magic]
  SQDR [8]             ← Sequence Director — contains reference to one GSQD by ID
  GSQD [variable]      ← Game Sequence Data — one AI behavior zone
    [uint32 zone_id]
    [uint32 count]
    [uint32 magic]
    GSEQ [variable]    ← Game Sequence — named behavior (e.g. "repul" = repulsion zone)
    [uint32 MREG-type tag]
    [uint32 mreg_region_id]  ← references an MREG spatial region
  MOIL [variable]      ← unknown — large integer/float table (~66 KB)
```

`GSQD` zones define where AI behaviors (attraction, repulsion, patrol) apply spatially by referencing an `MREG` region. The "repul" name seen in FISH.GDW designates zones where certain creatures are repelled. `MOIL` content is not yet decoded.

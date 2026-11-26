# Serialization Format — Jaws Unleashed Engine

> **Note (2026-07-17):** this doc dates from June 2025; `/CLAUDE.md` at the project root is the actively-maintained, current source of truth. This file's core claims held up well — only a few gaps have been patched in below (nested-node transform semantics, PROP-level alignment).

The engine uses a property-based serialization system throughout the BRTR chunk (scene graph) and CLAS chunk (reflection database). Understanding the format is required to parse placed objects and their properties.

---

## CLAS Chunk — Reflection Database

The `CLAS` chunk is a flat stream of length-prefixed strings:

```
[uint32 length][string bytes, no null terminator]
[uint32 length][string bytes]
...
```

These strings are class names, property names, and component schema definitions. They represent the engine's runtime type system baked into the binary — no decompilation needed to read the high-level architecture.

Example readable sequence:
```
NABiteTarget
m_hp
m_damagemultiplier
m_nutrition
m_radius
m_eattype
```

---

## BRTR Chunk — Scene Graph

The BRTR chunk is the pre-built level scene graph. It contains all placed object instances with world-space transforms, mesh references, baked vertex colour data, and AABBs.

### Top-Level Structure

```
BRTR [uint32 size]
  [4-byte magic: 0x01025024][uint32 root_count=1]
  PRPS [root "World" node]       ← pos=(0,0,0), name="World"
  CHBR [uint32 size]             ← one per placed object
    [uint32 magic: 0x0107402F]
    [uint32 node_id]             ← sequential; 66–35137 in FISH.GDW
    PRPS [uint32 size]
      PROP ...                   ← all object properties
      CHBR ...                   ← CAN nest here: child objects physically inside the parent's PRPS payload
  CHBR ...
```

**Important addition (2026-07-16):** `CHBR` nodes can nest — a child sits physically inside its parent's `PRPS` payload (not merely cross-referenced by ID). Only 1,074 of `FISH.GDW`'s 2,782 total `CHBR` nodes are found by a flat top-level scan; the rest are nested children. See the transform note below — this matters a lot for interpreting `0x080017DA`.

FISH.GDW BRTR stats:
- **2,782 CHBR nodes** total (only 1,074 at the top level — see nesting note above)
- **1,161 nodes** have resolvable mesh references
- **908 nodes** have baked vertex colour (lighting)
- **1,621 nodes** are non-mesh: waypoints, audio sources, triggers, AI markers

---

## PROP Block Format

```
[4-byte tag "PROP"][uint32 payload_size][uint32 prop_id][payload bytes]
```

The prop_id determines how to interpret the payload.

**Alignment rule (found 2026-07-17):** each `PROP` entry (and this appears to be a general rule for nested tag sequences in this format, not just top-level GDW chunks) is individually padded to a 4-byte boundary before the next tag begins. `payload_size` covers only `prop_id` + value, NOT the entry's own trailing pad — missing this causes a full parse desync partway through a property list when decoding by hand.

---

## Known PROP IDs

| ID | Meaning | Payload |
|---|---|---|
| `0x080017D8` | Object name | `uint32 length` + UTF-8 string |
| `0x080017D9` | Object flags | `uint32` |
| `0x080017DA` | Transform | 12 × `float32` — column-major 4×3 matrix (see below). **World-space only for top-level (depth 0) nodes** — for a nested `CHBR` (see nesting note above), this is LOCAL to the immediate parent; world position requires composing the full ancestor chain. See `scripts/resolve_brtr_hierarchy.py`. |
| `0x080017DB` | Unknown flag | `uint32` |
| `0x080017DC` | Unknown flag | `uint32` |
| `0x080017DD` | Unknown flag | `uint32` |
| `0x080017DE` | Unknown flag | `uint32` |
| `0x080017DF` | AABB bounds | 6 × `float32`: minX minY minZ maxX maxY maxZ. **Always world-space, regardless of nesting depth** (confirmed 2026-07-17 by cross-checking a nested node's AABB against its resolved world position) — unlike `0x080017DA`, this one does NOT need ancestor-chain composition. Also acts as a broad-phase spatial gate for both rendering culling and collision queries — must be kept in sync with the transform after any edit, or the object goes stale (disappears/loses collision) at its new position. |
| `0x080017E3` | Unknown | `uint32` |
| `0x080017E4` | Unknown | `uint32` |
| `0x08001873` | Mesh reference | 8 bytes: `[uint32 "GMDL" tag = 0x4C444D47][uint32 mesh_resource_id]` |
| `0x08001874` | Unknown | `uint32` |
| `0x08001875` | Object type flags | `uint32` (e.g. `0x1000009`) |
| `0x08001876` | Unknown flags | `uint32` |
| `0x08001877` | Unknown | `uint32` |
| `0x08001878` | Unknown | `uint32` |
| `0x08001879` | Colour scale | 4 × `float32` (RGBA multiplier, usually 1.0) |
| `0x0800187A` | Per-vertex colour | `uint32 vert_count` + `vert_count` × 16 bytes (RGBA float32 per vertex) — baked lighting |
| `0x0800187B` | Unknown | `uint32` |
| `0x080003C7` | Child node ID list | `uint32 count` + `count` × `uint32` node_ids |

---

## Transform Format (PROP `0x080017DA`)

Stored as **12 float32s in column-major 4×3 layout**:

```
xf[0..2]  = X-basis vector (column 0)
xf[3..5]  = Y-basis vector (column 1)
xf[6..8]  = Z-basis vector (column 2)
xf[9..11] = Translation (TX, TY, TZ)
```

To transform a local vertex `(x, y, z)` to world space:
```python
wx = xf[0]*x + xf[3]*y + xf[6]*z + xf[9]
wy = xf[1]*x + xf[4]*y + xf[7]*z + xf[10]
wz = xf[2]*x + xf[5]*y + xf[8]*z + xf[11]
```

Column vector lengths encode scale. Verified: computed world AABBs match stored PROP `0x080017DF` values to within floating-point precision (error = 0.0).

---

## Mesh Reference (PROP `0x08001873`)

Two uint32s:
1. The ASCII tag `GMDL` stored as a 32-bit integer (`0x4C444D47`) — type discriminator
2. The mesh resource ID — matches the **first uint32 of the 12-byte GMDL sub-header** inside the RSRC chunk

The sequential OBJ file index (e.g. `FISH_mesh_0042.obj`) corresponds to the order GMDL blocks are encountered during a linear scan of the GDW — not the resource ID directly. `rip_brtr_scene.py` builds the `resource_id → mesh_idx` mapping at runtime.

---

## Coordinate System

The engine uses **DirectX Y-up (left-handed)**. Y is height.

**Game → Blender conversion:**
```
Blender X =  game X
Blender Y = -game Z
Blender Z =  game Y
```

As a matrix:
```python
CONV = Matrix([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]])
# Apply as: CONV @ game_matrix @ CONV_INV
```

---

## GMDL Chunk Hierarchy (geometry serialization)

```
GMDL  [variable size]
  [12-byte sub-header: mesh_resource_id, count, hash]
  MATR  [52]        material colour properties
  MATS  [20]        material set
  GMAT              material definitions
  TSET  [variable]  triangle sets / submeshes (corrected 2026-10-01; see TSET Format)
  TANG  [variable]  triangle data container
    VIND            uint16 triangle list index buffer
    TNOR            per-triangle normals
    TFLG            per-triangle flags
  VERT  [variable]  vertex data container
    POSI            float32 XYZ positions (12 bytes/vertex)
    NORM            float32 XYZ normals (12 bytes/vertex)
    UVUV            float32 UV coordinates (8 bytes/vertex)
  VCOL              vertex colours (16 bytes/vertex — RGBA float32)
```

### TSET Format

> **Corrected 2026-10-01:** TSET holds **triangle sets (submeshes), not texture IDs**. Each record is `[set_idx][first_vert][vert_count][first_tri][tri_count]`, and record i uses material `MATS[i]` → GMAT → `TEXP ['GTEX' id]`. See CLAUDE.md "TSET Format" and `scripts/gdw_materials.py`. The description below is the old, wrong reading.

```
TSET [uint32 payload_size]
  [uint32 N]               ← number of texture layers
  [N × 20-byte records]
```

Each layer record (5 × uint32): `[layer_idx][val_A][val_B][val_C][val_D]`

- `val_A`–`val_D` contain texture IDs from the global ID space
- For `layer_idx=0`: val_B and val_D are the primary texture IDs
- For `layer_idx>0`: all four values may reference textures
- IDs resolved via `textures/texture_db.json`

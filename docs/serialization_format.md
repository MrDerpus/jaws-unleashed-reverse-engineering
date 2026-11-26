# How objects are stored: `CLAS`, `PRPS` and `PROP`

**In short:** levels store objects as lists of properties.
- Each placed object is a `CHBR` node holding a `PRPS` list of `PROP` entries.
- Each `PROP` has a numeric ID that indexes the level's own field table in `CLAS`.
- Children sit inside their parent's `PRPS`.

This page is the short overview. The full details live elsewhere:

| Topic | Doc |
|---|---|
| Container and chunk list | `docs/GDW_FORMAT.md` |
| Scene graph, property IDs, transforms | `docs/scene_graph.md` |
| Meshes and materials | `docs/rsrc_formats.md` |

Rewritten for readability on 2026-11-27. Old version: `docs/archive/serialization_format_old_2026-11-27.md`.

---

## Contents

1. [`CLAS`: names and the field table](#1-clas-names-and-the-field-table)
2. [`BRTR`: nodes](#2-brtr-nodes)
3. [`PROP` entries](#3-prop-entries)
4. [The most-used properties](#4-the-most-used-properties)
5. [Transforms and bounding boxes](#5-transforms-and-bounding-boxes)
6. [Mesh links](#6-mesh-links)
7. [Old mistakes](#7-old-mistakes)

---

## 1. `CLAS`: names and the field table

- Class and field names as length-prefixed strings: `[uint32 length][bytes]`, no NUL.
- Lists: `BRCM` (brick classes, `0x01…` nodes), `ACCM` (action classes, `0x02…` actions), then primitive and property classes.
- **A class ID's low 12 bits index these lists.**
- **The last part, `PRIM`, is the field table:** every (field, class) pair. **`PROP` ID = `0x08000000` + index into it.**
- 19 levels share one table; `TITLE0` differs.
- `scripts/gded_lineage.py prop LEVEL ID` names any ID.

Example of readable names in sequence: `NABiteTarget`, `m_hp`, `m_damagemultiplier`, `m_nutrition`, `m_radius`, `m_eattype`.

---

## 2. `BRTR`: nodes

```
BRTR [size]
  [0x01025024][root count = 1]
  PRPS                     the root, "World"
  CHBR [size]              one per placed object
    [uint32 class ID]      e.g. 0x0107402F = a plain model node
    [uint32 node ID]
    PRPS [size]
      PROP …
      CHBR …               children sit INSIDE the parent's PRPS
    [PRIM]                 optional collision link
  CHBR …
```

**Children nest.** In FISH only 1,074 of the 2,782 `CHBR` nodes are at the top level; the rest are inside a parent.

**FISH in numbers:**

| What | Count |
|---|---|
| `CHBR` nodes | 2,782 |
| With a mesh | 1,161 |
| With baked vertex colours | 908 |
| Without a mesh (waypoints, sounds, triggers, AI markers) | 1,621 |

Actions (`ACTN`) have the same shape, with their own class and ID. More: `docs/scene_graph.md` §1.

---

## 3. `PROP` entries

```
PROP [uint32 size][uint32 prop_id][value]
```

- `size` covers the ID and the value.
- **Each `PROP` is padded to 4 bytes before the next tag, and `size` doesn't include that padding.** Missing this desyncs the parse partway through a list. The same rule holds for every nested chunk.
- The ID decides how to read the value (§1).

---

## 4. The most-used properties

| ID | Field | Value |
|---|---|---|
| `0x080017D8` | Name | `uint32 length` + string |
| `0x080017D9` | `m_nFlags` | `uint32` (meanings: `docs/scene_graph.md` §2) |
| `0x080017DA` | Transform | 12 floats (§5) |
| `0x080017DD` | `m_Viewport` | `uint32`: `1` above water only, `0x20003` above and below |
| `0x080017DF` | World bounding box | 6 floats: min X Y Z, max X Y Z |
| `0x080017F0` | Reference target | Node ID: this node places a copy of that node's subtree |
| `0x08001873` | Mesh | `['GMDL'][mesh_id]` (§6) |
| `0x08001875` / `76` | `m_StaticLights` / `m_RenderSetting` | `uint32` |
| `0x08001879` | Colour scale | 4 floats (RGBA multiplier, usually 1) |
| `0x0800187A` | Baked vertex colours | `uint32 count` + count × 4 floats |
| `0x080018FF` | Skeleton | `['SKEL'][id]` |
| `0x080003C7` | `SharkWorld.m_teleportlist` | `uint32 count` + IDs: shark start and teleport points |

Every other ID has an exact name through the field table. The full list of common IDs: `docs/scene_graph.md` §2.

---

## 5. Transforms and bounding boxes

### Transform (`0x080017DA`)

12 floats, a column-major 4×3 matrix:

```
xf[0..2]   X basis (column 0)
xf[3..5]   Y basis (column 1)
xf[6..8]   Z basis (column 2)
xf[9..11]  translation
```

```python
wx = xf[0]*x + xf[3]*y + xf[6]*z + xf[9]
wy = xf[1]*x + xf[4]*y + xf[7]*z + xf[10]
wz = xf[2]*x + xf[5]*y + xf[8]*z + xf[11]
```

- Column lengths are the scale.
- **Top-level nodes:** world space.
- **Nested nodes:** relative to the parent, so compose the ancestor chain. Exception: flag `0x20000000` means the transform is absolute.
- Placement rules: `docs/scene_graph.md` §3–4.

### Bounding box (`0x080017DF`)

- **Always world space**, at any depth.
- Computed boxes match the stored ones exactly (error 0.0).
- **Used for culling and collision broad-phase.** After moving an object, update the box too, or the object vanishes or loses collision at its new place.

### Coordinates

The game is DirectX left-handed, Y up. For Blender: `docs/rsrc_formats.md` §5.

---

## 6. Mesh links

`0x08001873` = two uint32s:
1. the ASCII tag `GMDL` (`0x4C444D47`) as a type marker;
2. the **mesh resource ID**, the first word of the `GMDL` header in `RSRC`.

The OBJ file number (e.g. `FISH_mesh_0042.obj`) is the order meshes appear in the file, not the resource ID. `rip_brtr_scene.py` builds the ID → file mapping.

Mesh and `TSET` layout: `docs/rsrc_formats.md`.

---

## 7. Old mistakes

| Old claim | Now |
|---|---|
| `CLAS` is a flat stream of names | Name lists plus the `PRIM` field table, which `PROP` IDs index (§1) |
| `0x0107402F` is a magic number on every `CHBR` | It's a class ID (a plain model node); other nodes have other classes |
| `0x080003C7` is a child node list | `SharkWorld.m_teleportlist` |
| `0x080017DB`–`DE`, `0x080017E3`/`E4`, `0x08001874`, `0x08001877`/`78`, `0x0800187B` are unknown flags | All named through the field table (`docs/scene_graph.md` §2) |
| `0x08001875` = object type flags | `m_StaticLights` |
| `TSET` holds texture IDs | It lists submeshes (`docs/rsrc_formats.md` §3) |
| Blender: X = x, Y = −z, Z = y | That mirrored the levels; now Y = z, determinant −1 (`docs/rsrc_formats.md` §5) |

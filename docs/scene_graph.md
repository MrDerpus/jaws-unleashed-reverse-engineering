# Scene graph (BRTR)

**In short:** a level's `BRTR` chunk is the finished scene: every placed object, with its name, transform, mesh, baked lighting and bounding box. Terrain is placed the same way; there is no separate terrain format. Objects can nest, copy other objects by reference, or carry an absolute world transform. `scripts/rip_brtr_scene.py` extracts any level to an OBJ plus a JSON manifest, and `scenes/import_fish_blender.py` loads it into Blender.

Related docs: `docs/brtr_editing.md` (changing levels), `docs/rsrc_formats.md` (meshes and collision), `docs/GDW_FORMAT.md` (the container).

Rewritten for readability on 2026-11-27. Old version: `docs/archive/scene_graph_old_2026-11-27.md`.

---

## Contents

1. [Layout](#1-layout)
2. [Property IDs](#2-property-ids)
3. [Transforms](#3-transforms)
4. [Placement rules: references, absolute transforms, mission relocation](#4-placement-rules)
5. [Collision link (`PRIM`) and mesh link](#5-collision-link-prim-and-mesh-link)
6. [Area triggers and creature generators](#6-area-triggers-and-creature-generators)
7. [Collectible fields](#7-collectible-fields)
8. [FISH as an example](#8-fish-as-an-example)
9. [Hungarian object names](#9-hungarian-object-names)
10. [Extracting scenes](#10-extracting-scenes)
11. [Blender import](#11-blender-import)
12. [Old mistakes](#12-old-mistakes)

---

## 1. Layout

```
BRTR [uint32 size]
  [uint32 magic 0x01025024][uint32 root_count = 1]
  PRPS                     ← the root node, "World", at (0, 0, 0)
  CHBR [uint32 size]       ← one per placed node; nodes nest
    [uint32 class ID]
    [uint32 node_id]
    PRPS [uint32 size]
      PROP …               ← the node's properties (§2)
    PRIM …                 ← optional collision link (§5)
  CHBR …
```

**Class ID:**
- Not a constant. Examples: `0x0107402F` = plain model (rocks, props), `0x0106F06E` = flora.
- The low 12 bits index the level's `CLAS` name lists: `BRCM` for `0x01…` nodes, `ACCM` for `0x02…` actions.
- So `0x02F` = `GDModel`, `0x06E` = `NAGarden`.

**Node ID:** sequential. FISH uses 66–35137.

**FISH has 2,782 nodes:**
- 1,161 with a mesh;
- 908 with baked vertex colours;
- 1,621 without a mesh: waypoints, AI markers, particles, sounds, triggers.

**Finding the chunk:** a plain `data.find(b'BRTR')` hits a false match inside `RSRC` in 8 levels (BEACH, BEACHPST, KATATAMA, OPEN_S, START, TITLE, TITLE0, WRACK). Keep only candidates with the magic, root count 1 and `PRPS`, then take the **largest**; the loading-screen sub-archives have smaller `BRTR`s of their own.

```python
candidates = []
pos = 0
while True:
    idx = data.find(b'BRTR', pos)
    if idx == -1: break
    sz = u32(data, idx+4)
    if idx+16 <= len(data) and u32(data, idx+8) == 0x01025024 and u32(data, idx+12) == 1 and data[idx+16:idx+20] == b'PRPS':
        candidates.append((sz, idx))
    pos = idx + 4
brtr_sz, brtr_pos = max(candidates)
```

The library version is `gdw_grow.find_brtr`.

---

## 2. Property IDs

**Every `PROP` ID names itself.** A level's `CLAS` chunk ends in a field table (`PRIM`: a count, then (field, class) string pairs). A `PROP` ID is `0x08000000 | index` into that table.

- Look one up: `python3 -I scripts/gded_lineage.py prop LEVEL.GDW 0x080017E3`.
- The table is the same in 19 levels. **`TITLE0` has its own**; it matches only up to index 979.
- PS2 levels have their own table too. PS2 FISH's `SCRT` IDs `0x08001957`–`6A` are the same 20 `GDViewport` fields, shifted by `0x29`.

### Common IDs

| ID | Field | Payload / meaning |
|---|---|---|
| `0x080017D8` | name | uint32 length + string |
| `0x080017D9` | `m_nFlags` | uint32; bits below |
| `0x080017DA` | transform | 12 floats (§3) |
| `0x080017DB` | `m_ExecFilter` | uint32 |
| `0x080017DC` | `m_CameraFilter` | uint32 |
| `0x080017DD` | `m_Viewport` | Render-pass mask: `1` = above water only, `0x20003` = above + underwater (both user-confirmed) |
| `0x080017DE` | `m_CreatorDistance` | uint32 |
| `0x080017DF` | `m_GenMapBound` | World box: 6 floats, min XYZ then max XYZ |
| `0x080017E0` | `m_MapBound` | |
| `0x080017E3` | `m_RoomMask` | uint32 |
| `0x080017E4` | `m_Comment` | uint32 |
| `0x080017F0` | reference target | Node ID to copy (§4) |
| `0x08001873` | mesh | `['GMDL'][mesh_id]` |
| `0x08001874` | `m_DynamicLights` | uint32 |
| `0x08001875` | `m_StaticLights` | e.g. `0x1000009`; `0` on hidden companion nodes |
| `0x08001876` | `m_RenderSetting` | Values below |
| `0x08001877` | `m_ExtRenderSetting` | uint32 |
| `0x08001878` | `m_ChannelSetting` | uint32 |
| `0x08001879` | `m_ModelColor` | 4 floats, RGBA multiplier, usually 1.0 |
| `0x0800187A` | baked vertex colours | uint32 count + count × 4 floats (RGBA) |
| `0x0800187B` | `m_PhysicDef` | uint32 |
| `0x080003C7` | `SharkWorld.m_teleportlist` | uint32 count + node IDs: shark start/teleport spots, e.g. FISH `SharkPosReal`, `SM18`, `800`, `fisherman 1` |

The full `GDBrick` range `0x080017DB`–`E4` is: `m_ExecFilter`, `m_CameraFilter`, `m_Viewport`, `m_CreatorDistance`, `m_GenMapBound`, `m_MapBound`, `m_Filter`, `m_ExportFilter`, `m_RoomMask`, `m_Comment`.

**Node flags (`m_nFlags`):**

| Bit | Meaning |
|---|---|
| `0x1` | Killed at runtime |
| `0x2` | Enabled |
| `0x10`, `0x40` | In the world. Clearing them at runtime removes both visibility and collision. |
| `0x100` | Not rendered (invisible blockers) |
| `0x20000` | Suspended |
| `0x20000000` | Transform is absolute, in world space (§4) |

**`m_RenderSetting` values seen:**

| Value | Used on |
|---|---|
| `0x40000800` | Walls |
| `0x820` | Sand |
| `0x40000400`, `0x40002400` | The hidden companion layer |
| `0x80000920` | Seaweed (alpha cut-out) |
| `0x200820` | Blended sand overlays |

### Camera and fog

| IDs | Class | Fields |
|---|---|---|
| `0x080017FD`–`0x08001802` | `GDCamera` | `m_nFOV` (radians, e.g. 0.873), `m_nRatio`, `m_NearPlane`, **`m_FarPlane`** (`SharkCamera`: 600), `m_FogSensor`, `m_CameraFlags` |
| `0x08001848`–`0x08001850` | `GDFog` | `m_FogFlags`, `m_Range`, `m_ConstRange`, `m_Condens`, `m_FogDensity`, **`m_FogStart`** (`…184D`), **`m_FogEnd`** (`…184E`), `m_FogType`, … |
| `0x08001853` | `GDFog` | **Fog colour**: r, g, b, a in 0–1. FISH's `FogAbove` = 0.561, 0.694, 0.788. |

### Viewports

`0x08001980`–`93` are `GDViewport`: `m_Width`, `m_Height`, `m_PositionX/Y`, `m_OriginX/Y`, `m_Aspect`, `m_ActualCamera`, `m_Color`, `m_ViewportSetting`, `m_ClearColor`, `m_ClearZ`, `m_CopyOtherBuffer`, `m_ClearOnly`, `m_MotionBlur`, `m_JoinBGControl`, `m_JoinBGFactor`, `m_TargetTexture`, `m_DependsOn`, `m_RenderList`.

**Still open:** what most values' bits mean (`docs/open_problems.md` §5).

---

## 3. Transforms

`PROP 0x080017DA` holds 12 floats, a column-major 4×3 matrix:

```
xf[0..2]  = X basis (column 0)
xf[3..5]  = Y basis (column 1)
xf[6..8]  = Z basis (column 2)
xf[9..11] = translation
```

Local to world:

```python
wx = xf[0]*x + xf[3]*y + xf[6]*z + xf[9]
wy = xf[1]*x + xf[4]*y + xf[7]*z + xf[10]
wz = xf[2]*x + xf[5]*y + xf[8]*z + xf[11]
```

- Column lengths give the scale (uniform or not).
- **Checked:** world boxes computed this way match the stored `0x080017DF` exactly.
- Nested nodes compose with their parents, unless flagged absolute (§4).
- The game is DirectX left-handed: X right, Y up, Z forward.

---

## 4. Placement rules

Three rules beyond plain nesting, all in `scripts/brtr_scene_graph.py` (shared by `rip_brtr_scene.py` and `resolve_brtr_hierarchy.py`).

### Rule 1: reference instancing

**`PROP 0x080017F0` = a target node ID** (0 = none). Every node has the field. A reference node places **a copy of the target's whole subtree**.

- **"Replace" semantics:** the copy's root takes the reference node's world transform. The target's own transform is ignored; its children compose under the copy as usual.
- References can nest: templates that contain references, like KATATAMA's `TRef*` grid of `ope*` seafloor clusters.
- **Scale:** FISH has 130 reference nodes → 1,591 copied nodes; OPEN_S 539 → 37,082.
- The most-copied template is the ~140-node `Civilian` rig, 21–94 times per level.

**Evidence:**
- OPEN_S `Starfish01` is authored at y −27.6, with 10 references. "Replace" puts every copy on the seafloor (y −28 to −33); composing would bury them at y −55 to −61. Each reference has its own random rotation.
- FISH's pier `molo` (authored at y 3.59) and its 12 references sit at y 3.4–4.3.

**Templates still exist at their authored spot**, usually the origin.
- In-game, *some* render there: OPEN_S's starfish at (0, 0, 0.14), a piece of wood at FISH's origin (probably `debris1` under `Floater1_Brown`). The user saw both by teleporting to `0 0 0` (2026-10-01).
- Most don't: FISH's buoy template (referenced 72 times), civilians, fish.
- So it's per object, not a rule. Exports keep templates, flagged `is_template`. More: `docs/terrain_and_water_bounds.md`.

### Rule 2: absolute transforms

**`m_nFlags` bit `0x20000000`** = the transform is already in world space; the parent is ignored.

- This matches the engine's world-matrix update (`Jaws.exe` `0x696EA0`), which skips the parent when the flag is set.
- Example: FISH's `fenyo` pines and their `Box0N` foliage cards (flags `0x2000005A`). Composing them through the parent sent them ~7,400 units away.
- FISH has 738 such nodes, 92 of them nested.

### Rule 3: mission relocation

**`MSMineAllMineMission.m_WhaleID` (`PROP 0x08000AE5`)** on `MineAllMine Mission Root` (FISH, at (2021, 0, −3827)) moves the whale node `WhaleCarcass MorePrim` **relative to the mission root**.

- "Compose" semantics: whale world = root world ∘ whale local. The whale is moved, not copied.
- **Checked in-game:** predicted (2081, −20, −3722). The user teleported there and landed against the carcass.
- Other fields of the mission:

  | ID | Field | Value |
  |---|---|---|
  | `0x08000AE6` | `m_SharksID` | 5 shark node IDs |
  | `0x08000AE7`–`9` | `m_Easy/Medium/HardSharkNum` | 5 / 7 / 10 |
  | `0x08000AEA`–`C` | `m_Easy/Medium/HardWhaleDeadHurt` | 14.0 / 10.0 / 6.0 |

- This is the only mission relocation handled. Other mission classes may move objects the same way.

### Known limits

- **OPEN_NE's `LeisureOverlay`** (referenced once, by `LeisureOverlayRef 1`) has crew references ~6,000 units from its origin. Its copy lands off the map: 150 placements beyond ±12,000. Probably a group attached at runtime, e.g. a crew on a moving boat. Not resolved.
- **Multi-variant templates** like `Civilian` hold every body type and LOD mesh. A copy exports all of them overlapping, where the game shows one.

---

## 5. Collision link (`PRIM`) and mesh link

### `PRIM`: collision

- A node may carry a `PRIM` chunk after its `PRPS`.
- It has class `0x20003002` and its own `PRPS`, with `PROP 0x080018D8` = `['MREG'][region_id]`.
- FISH has 598.
- `MREG` collision is mesh-local, so a copied `PRIM` follows its node.
- **Tested (user-confirmed 2026-10-03):** an inserted wall carrying its template's `PRIM` blocks the shark at its new spot. Without a `PRIM`, you swim through it.

### Mesh link

- `PROP 0x08001873` = `['GMDL'][mesh_id]`. The first word is the ASCII tag `GMDL` (`0x4C444D47`), a type marker.
- `mesh_id` matches the first word of the `GMDL` block's 12-byte sub-header.
- The extracted OBJ files (`FISH_mesh_XXXX.obj`) are numbered in file order, not by ID. `rip_brtr_scene.py` maps ID → index at runtime.

---

## 6. Area triggers and creature generators

### Area triggers: entrances and exits

**Node class `0x01134132`.** 17 of them in 6 levels.

| ID | Field | Meaning |
|---|---|---|
| `0x0800028D` | `m_type` | 1 = vertical column; 2 = uses `m_top`/`m_bottom` |
| `0x0800028E` | `m_target` | The shark node (`SHARRRK`) |
| `0x0800028F` | `m_radius` | float |
| `0x08000290` / `91` | `m_enter_act` / `m_leave_act` | `[count, action IDs…]` |
| `0x08000292`–`96` | `m_rate`, `m_top`, `m_bottom`, two debug colours | |

**Examples:**
- **FISH's exit** `OPEN_S` (1551, centre (2005, −4004)) fires on **leave**, at radius 795. Its 72 `BolyaReference` children are just the buoy ring.
- **The open-ocean entrances** (OPEN_S `FISHERMAN`, `WRACK`, …) fire on **enter**.

**The action chain:**
1. `OssLoadChecker` (`0x0217B17A`: `m_type`, `m_stage`, `m_toact`, `m_toactcancel`) shows the prompt (message slot 598).
2. A `GDControl` adds the loading effect.
3. It starts a `GDLoad` action (`0x02038036`/`0x02038037`), with the stage name in `PROP 0x08001839`.

**Tools:**
- `build_scene.py` turns Blender objects with `jaws_exit` into enter-type zones.
- `scripts/redirect_stage.py` rewrites a `GDLoad` stage name. OPEN_S's Fisherman's Isle loader sits in an embedded sub-archive.

Details: `docs/brtr_editing.md` "Area triggers and level exits".

### Creature generators: ambient wildlife

- `ACTN` class `0x02129128`, on `Parent<X>Gen` group nodes.
- `PROP 0x08000A78` = creature template, `0x08000A79` = count, `0x08000A82` = area box.

---

## 7. Collectible fields

Gameplay classes have their own `PROP` ranges. `BSCollectibleGameObject`, the placed collectible:

| ID | Field | Meaning |
|---|---|---|
| `0x080004A1` | `m_Template` | Node ID of its template (`"NN - ItemName"`) |
| `0x080004A2` | `m_AutoYPlacement` | bool: snap to the ground |
| `0x080004A3` | `m_AutoY_Offset` | float: height on top of the snap |
| `0x080004A4` | `m_myid` | Per-level number, shared by all categories. In WRACK: licence plates 1–5, tin cans 6–9, the necklace 10. |

**The template class**, `BSCollectibleGameObjectTemplate`, has `m_DisplayName`, `m_TypeIndex`, `m_AllCount`, `m_RareItem`, `m_RegenerationMode` and `m_AddOn`. Their IDs aren't mapped one by one. Probable meanings:
- `m_TypeIndex` = the `NN` catalogue number in the template's name.
- `m_AllCount` = the total in the game, as in "45 license plates hidden throughout the story locations".
- `m_RareItem` = one-off finds (necklace, trident, pirate ship, body bag, mermaid, nautilus, mask) vs counted sets (licence plates, tin cans). The two kinds use different reward texts.

The category list: `docs/mission_system.md` §6.

---

## 8. FISH as an example

**One area**, around (1600–2900, −3600 to −4900). It holds:
- the pier and dock;
- rocks (`szikla`), wrecks (`wrack`, `torzs`), a skull (`koponya`);
- alpha overlays (`interalph`), two underwater mansions (`mansionC`), a cadillac;
- the whale carcass at (2081, −20, −3722).

**Extents of real placements:** X −240 to 2917, Y −226 to 3457 (the top is the `NEW_SKY_OPEN` sky dome), Z −4879 to 193.

**Other placed objects:** `GWside` (great white model), `WhaleCarcass Body`, `MartinWalker` (NPC), `CorkScrewEffect`, `PredatorEffectNONPS2`.

### Terrain is in `BRTR`

All terrain and environment geometry is placed as ordinary mesh nodes. There is no BSP, heightmap or hidden terrain container.

| Name pattern | World Z | What |
|---|---|---|
| `Homokos_PartSzakasz_B03..B23` | −3908 to −4331 | Sandy shore tiles, the main seafloor |
| `Homokos_Alpha_Szakasz_…` | ~−4100 | Shore tiles with alpha |
| `szikla elem`, `szikla a`, `szikla a04/a05` | −3760 to −4534 | Rocks, ~908 triangles each |
| `Plane01` (×7), `Plane02` | −4004 to −4429 | Flat water/seafloor planes |
| `plane16` (×6) | ~−4100 | Small floor tiles |
| `alap01`, `alapkieg` | ~−3904 | Terrain base layer |
| `Kotelszakito_szikla` | ~−4534 | "Rope-breaking rock", named after the cut Aurora rope fight (`docs/cut_content.md` §3). Whether FISH's copy had a purpose is unchecked. |
| `molo04`, `molo05`, `molo_also`, `molo_felso` | template | Dock sections |
| `kis_halaszhajo` | template | Small fishing boat |
| `seascooter-optimalized` | template | Sea scooter |
| `HammerHead Headpart/Tailpart` | ~−4050 | Hammerhead |

---

## 9. Hungarian object names

Appaloosa (formerly Novotrade) was in Budapest, so object names are Hungarian.

| Hungarian | English |
|---|---|
| `szikla` | rock |
| `deska` | plank |
| `oszlop` | pillar |
| `koponya` | skull |
| `wrack` | wreck (loanword) |
| `Torheto_pozna` | breakable post |
| `pierstores` | pier structures |
| `fa` | tree |
| `fenyo` | pine |
| `feny` | light |
| `torzs` | trunk |
| `molo` | pier |
| `molo_also` / `molo_felso` | lower / upper dock |
| `csonak` | boat |
| `korlat` | railing |
| `csolezaro` | boat barrier (DEEPSEA) |
| `homokos` | sandy |
| `PartSzakasz` | shore section |
| `alap` | base |
| `alapkieg` | base extension |
| `Kotelszakito` | rope-breaking |
| `kis_halaszhajo` | small fishing boat |

---

## 10. Extracting scenes

### `scripts/rip_brtr_scene.py`

Run from the project root. Set `NAME = 'FISH'` at the top to choose a level.

```bash
python3 scripts/rip_brtr_scene.py
```

**Output in `scenes/`:**
- `<NAME>_brtr.obj`: all geometry in world space, one group per placed object.
- `<NAME>_brtr.mtl`: materials, per submesh, from `MATS` → `GMAT` → `TEXP` with same-level textures.
- `<NAME>_brtr.json`: one entry per placement:
  - `node_id`, `name`, `mesh_id`, `mesh_idx` (into `models/<NAME>/`);
  - world `xf` and `pos`, `tris`, `vcols`;
  - `depth`, `via_ref` (the reference node that placed this copy), `is_template`, `relocated_by`.
- OBJ object names get `@ref<id>` for copies and a `TEMPLATE__` prefix for template spots.
- `<NAME>_resolved_hierarchy.json` (from `resolve_brtr_hierarchy.py`) has `absolute_xf`, `ref_target`, `is_template` and `relocated_world_pos`.

**All levels:**

```bash
for name in AQUARIUM ARMADA BEACH BEACHPST CHASE DEEPSEA2 DEEPSEA DOCKS FISH GAUNTLET KATATAMA MINEMSHA OPEN_NE OPEN_NW OPEN_S START TITLE0 TITLE TOWN WRACK; do
    python3 -c "
import re; from pathlib import Path
script = Path('scripts/rip_brtr_scene.py').read_text()
script = re.sub(r\"^NAME\s*=.*\$\", \"NAME = '$name'\", script, flags=re.MULTILINE)
exec(compile(script, 'rip_brtr_scene.py', 'exec'))
"
done
```

### Mesh placements per level

Last full run 2026-10-01, with all the rules in §4. No bad geometry. `scenes/` is 3.3 GB.

| Level | Placements | Level | Placements |
|---|---|---|---|
| AQUARIUM | 6,119 | MINEMSHA | 3,765 |
| ARMADA | 4,429 | OPEN_NE | 9,940 |
| BEACH | 3,442 | OPEN_NW | 11,251 |
| BEACHPST | 1,841 | OPEN_S | 16,234 |
| CHASE | 730 | START | 6,273 |
| DEEPSEA | 3,917 | TITLE | 226 |
| DEEPSEA2 | 3,940 | TITLE0 | 0 (an 8-node menu stub) |
| DOCKS | 3,877 | TOWN | 7,789 |
| FISH | 1,610 | WRACK | 2,256 |
| GAUNTLET | 1,201 | | |
| KATATAMA | 6,152 | | |

The three open-ocean zones are by far the largest.

---

## 11. Blender import

**`scenes/import_fish_blender.py`:** paste into Blender's Scripting workspace and run. Set `NAME` at the top for another level.

- Each unique mesh is loaded once from `models/<NAME>/` and shared.
- Objects are sorted into collections: Player, Characters, Buildings, Rocks, Flora, Dock, Terrain, Collision, …
- It reads our OBJ files directly (`mesh.from_pydata`), so Blender's OBJ importer doesn't change any axes.

**Coordinates** (user-confirmed 2026-10-01):
- `matrix_world = CONV @ game_world @ FLIP_Z`.
- `CONV`: Blender X = game X, Y = game Z, Z = game Y. Determinant −1, because the game is left-handed.

**Viewport settings after import:**
- Clip End: 20,000. A level spans ~4,600 units.
- Unit scale: 0.01.

---

## 12. Old mistakes

| Old claim | Now |
|---|---|
| FISH has two clusters, with a pier/dock cluster at the origin | The origin "cluster" is reference templates (pier, posts, boat, buoys, civilians, fish, weapons) and the mission-local whale and sharks. FISH is one area (§8). The 12 real pier copies are at (1810–2006, −4010 to −4110). |
| The origin starfish is a deliberate marker | It's a reference template that also renders at its own spot (§4) |
| `0x080003C7` is a child-node list | `SharkWorld.m_teleportlist` (2026-11-25) |
| `CHBR`'s first word is a constant magic | A class ID (2026-10-03) |
| PROP IDs are read off the exe's field registration order, with a drift | Superseded 2026-11-25 by the exact `CLAS` table (§2). The old method is in `docs/brtr_editing.md`. |
| KATATAMA's `BRTR` size is corrupt | It was the false-match problem in §1 |

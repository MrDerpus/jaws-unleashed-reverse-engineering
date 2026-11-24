# Scene graph (BRTR): structure, PROP IDs, transforms, instancing, extraction

Moved word for word from the root `CLAUDE.md` on 2026-11-25 to keep that file short. Where this disagrees with older docs, this text is the newer one.

## Scene / Object System — BRTR Chunk

**The `BRTR` chunk IS the pre-built scene graph.** It contains all placed object instances with full world-space transforms, mesh references, vertex colour data, and AABBs — the complete level layout as authored by the developers.

### BRTR Internal Structure

```
BRTR [uint32 size]
  [4-byte magic: 0x01025024][uint32 root_count=1]
  PRPS [root "World" object]     ← root scene node, pos=(0,0,0), name="World"
  CHBR [uint32 size]             ← child branch node (one per placed object)
    [uint32 class ID]           ← e.g. 0x0107402F = plain model brick (rocks, props), 0x0106F06E = flora; not a constant magic (2026-10-03, see "Blank base level" in docs/brtr_editing.md). Low 12 bits = index into the level's CLAS name lists (BRCM for 0x01… nodes, ACCM for 0x02… actions): 0x02F = GDModel, 0x06E = NAGarden (2026-10-04)
    [uint32 node_id]             ← sequential ID, range 66–35137 in FISH.GDW
    PRPS [uint32 size]
      PROP ...                   ← all object properties (see below)
  CHBR ...
```

FISH.GDW BRTR stats:
- **2782 CHBR nodes** — all have names and world transforms
- **1161 nodes** have resolvable mesh references → geometry placed in the level
- **908 nodes** have baked vertex colour data (baked lighting)
- **1621 nodes** are non-mesh objects: waypoints, AI markers, particle systems, audio sources, triggers

### Known PROP IDs (BRTR / PRPS context)

| ID | Meaning | Payload |
|---|---|---|
| `0x080017D8` | Object name | uint32 length + UTF-8 string |
| `0x080017D9` | Object flags (`m_nFlags`) — `0x2` enabled, `0x100` **not rendered** (invisible blockers), `0x10`/`0x40` "active in world" (clearing at runtime removes visibility and collision), `0x20000` suspended, `0x20000000` absolute transform; `0x1` = killed at runtime (see GDControl below) | uint32 |
| `0x080017DA` | World transform | 12 float32s — column-major 4×3 (see below) |
| `0x080017DB` | `m_ExecFilter` (name from reflection table, see note below) | uint32 |
| `0x080017DC` | `m_CameraFilter` | uint32 |
| `0x080017DD` | `m_Viewport` — render-pass mask; `1` = above-water only, `0x20003` = above + underwater (both user-confirmed) | uint32 |
| `0x080017DE` | Unknown flag | uint32 |
| `0x080017DF` | AABB bounds | 6 float32s: minX minY minZ maxX maxY maxZ — **world space** |
| `0x080017E3` | `GDBrick.m_RoomMask` | uint32 |
| `0x080017E4` | `GDBrick.m_Comment` | uint32 |
| `0x080017FD`–`0x08001802` | `GDCamera`: `m_nFOV` (radians, e.g. 0.873), `m_nRatio`, `m_NearPlane`, **`m_FarPlane`** (`SharkCamera`: 600), `m_FogSensor`, `m_CameraFlags` (2026-10-17) | float / uint32 |
| `0x08001848`–`0x08001850` | `GDFog`: `m_FogFlags`, `m_Range`, `m_ConstRange`, `m_Condens`, `m_FogDensity`, **`m_FogStart`** (`…184D`), **`m_FogEnd`** (`…184E`), `m_FogType`, `m_Color` (2026-10-17) | float / uint32 |
| `0x08001873` | Mesh reference | 8 bytes: `[uint32 "GMDL" tag][uint32 mesh_resource_id]` |
| `0x08001874` | `m_DynamicLights` | uint32 |
| `0x08001875` | `m_StaticLights` (e.g. `0x1000009`; `0` on hidden render-layer companions) | uint32 |
| `0x08001876` | `m_RenderSetting` (`0x40000800` walls, `0x820` sand; `0x40000400`/`0x40002400` = hidden companion layer; `0x80000920` = seaweed alpha cut-out, `0x200820` = blended sand overlays) | uint32 |
| `0x08001877` | `m_ExtRenderSetting` | uint32 |
| `0x08001878` | `m_ChannelSetting` | uint32 |
| `0x08001879` | `m_ModelColor` — colour scale | 4 float32s (RGBA multiplier, usually 1.0) |
| `0x0800187A` | Per-vertex colour data | uint32 vert_count + vert_count × 16 bytes (RGBA float32 per vert) — **baked lighting** |
| `0x0800187B` | `GDModel.m_PhysicDef` | uint32 |
| `0x080003C7` | **`SharkWorld.m_teleportlist`** (corrected 2026-11-25; was "child node ID list"): shark start/teleport positions, e.g. FISH `SharkPosReal`, `SM18`, `800`, `fisherman 1` | uint32 count + count × uint32 node_ids |

**Field names, exact (2026-11-25):** a level's `CLAS` chunk ends in a field table (`PRIM`: count + (field, class) string pairs), and a `PROP` ID is `0x08000000 | index` into it, so every ID can be named exactly from the file itself: `python3 -I scripts/gded_lineage.py prop LEVEL.GDW 0x080017E3`. Identical in 19 levels; **`TITLE0` has its own table** (matches only up to index 979). Remaining unknown IDs named this way: `0x080017DB`–`E4` = `GDBrick` `m_ExecFilter`, `m_CameraFilter`, `m_Viewport`, `m_CreatorDistance`, `m_GenMapBound`, `m_MapBound`, `m_Filter`, `m_ExportFilter`, `m_RoomMask`, `m_Comment`; `0x08001874`–`7B` = `GDModel` `m_DynamicLights` … `m_PhysicDef`; `0x08001980`–`93` = `GDViewport` `m_Width`, `m_Height`, `m_PositionX/Y`, `m_OriginX/Y`, `m_Aspect`, `m_ActualCamera`, `m_Color`, `m_ViewportSetting`, `m_ClearColor`, `m_ClearZ`, `m_CopyOtherBuffer`, `m_ClearOnly`, `m_MotionBlur`, `m_JoinBGControl`, `m_JoinBGFactor`, `m_TargetTexture`, `m_DependsOn`, `m_RenderList`. Note `0x080017DF` is `m_GenMapBound` (generated bound) and `0x080017E0` `m_MapBound`. PS2 levels have their own table: PS2 FISH's `SCRT` IDs `0x08001957`–`6A` are the same 20 `GDViewport` fields (`m_Width` … `m_RenderList`), shifted by 0x29.

**Field names (2026-10-03, superseded by the above):** PROP IDs' low bits are each field's global registration index in `Jaws.exe`'s reflection table (`scripts/dump_class_fields.py`), plus a small offset that drifts because the dump misses a few registrations, so names can be read off by neighbourhood. Details in `docs/brtr_editing.md`.

**`PRIM` sub-chunk = collision link (2026-10-03):** a `CHBR` node may carry a `PRIM` chunk after its `PRPS` (class `0x20003002`, its own `PRPS` with `PROP 0x080018D8` = `['MREG' tag][uint32 region_id]`), linking it to its `MREG` collision region. 598 in FISH. `MREG` is mesh-local, so a copied `PRIM` follows the node: an inserted wall carrying its template's `PRIM` blocks the shark at its new position, and one without a `PRIM` can be swum through (both user-confirmed 2026-10-03).

**Mesh reference clarification:** PROP `0x08001873` first uint32 is literally the ASCII tag `GMDL` (= `0x4C444D47`) stored as a type discriminator, not an "unknown" field. Second uint32 = mesh resource ID matching the first uint32 of the GMDL 12-byte sub-header.

**Area triggers = level entrances and exits (decoded 2026-10-04):** node class **`0x01134132`**, fields `m_type` (`0x0800028D`: 1 = vertical column, 2 = with `m_top`/`m_bottom`), `m_target` (`0x0800028E`, the shark node `SHARRRK`), `m_radius` (`0x0800028F`, float), `m_enter_act` / `m_leave_act` (`0x08000290`/`0x08000291`, `[count, action ids…]`), `m_rate`, `m_top`, `m_bottom`, two debug colours (`…0292`–`…0296`). 17 in 6 GDWs. FISH's exit `OPEN_S` (1551, centre (2005, −4004)) fires on **leave** at radius 795; its 72 `BolyaReference` children are only the buoy ring. The open-ocean entrances (OPEN_S `FISHERMAN`, `WRACK`, …) fire on **enter**. Action chain: `OssLoadChecker` (`0x0217B17A`: `m_type`, `m_stage`, `m_toact`, `m_toactcancel`) shows the prompt (message slot 598, below), then a `GDControl` adds the loading effect and starts a `GDLoad` action (`0x02038036`/`0x02038037`, stage name `PROP 0x08001839`). `build_scene.py` turns Blender objects with `jaws_exit` into enter-type zones; `scripts/redirect_stage.py` rewrites a `GDLoad` stage name (OPEN_S's Fisherman's Isle loader sits in an embedded sub-archive). **Ambient wildlife** comes from creature generators: `ACTN` class `0x02129128` on `Parent<X>Gen` group nodes, `PROP 0x08000A78` = creature template, `0x08000A79` = count, `0x08000A82` = area box. Details: `docs/brtr_editing.md` "Area triggers and level exits".

**Class-specific PROP IDs (decoded 2026-08-13, `BSCollectibleGameObject`):** in addition to the generic `0x080017Dx`/`0x08001873` engine-wide fields above, individual gameplay classes have their own PROP ID ranges for class-specific fields, found by matching the class's field-name list in `Jaws.exe`'s reflection strings (`BSCollectibleGameObject.m_Template..m_AutoYPlacement....m_AutoY_Offset..m_myid`) against a live node's raw PROP IDs, in declaration order:

| ID | Field | Meaning |
|---|---|---|
| `0x080004A1` | `m_Template` | uint32 — BRTR node ID of this instance's `BSCollectibleGameObjectTemplate` (the shared `"NN - ItemName"` reference/template node — see Collectible System note below) |
| `0x080004A2` | `m_AutoYPlacement` | uint32 (bool) — auto-snap to ground height flag |
| `0x080004A3` | `m_AutoY_Offset` | float32 — vertical offset applied on top of auto-placement |
| `0x080004A4` | `m_myid` | uint32 — per-level sequential instance ID (shared across all collectible categories in that GDW, not per-category — e.g. in `WRACK.GDW`, License Plates use IDs 1–5, Tin Cans 6–9, the Diamond Necklace is 10) |

The sibling class `BSCollectibleGameObjectTemplate` has its own fields (`m_DisplayName`, `m_TypeIndex`, `m_AllCount`, `m_RareItem`, `m_RegenerationMode`, `m_AddOn` — PROP IDs not yet individually mapped) — `m_TypeIndex` is almost certainly the `"NN"` catalog number seen in every template node's name (`"06 - Diamond Necklace"`, `"10 - Trident"`, etc.), `m_AllCount` the total-instances-in-game figure quoted in reward text (e.g. `"45 license plates hidden throughout the story locations"`), and `m_RareItem` a bool distinguishing single one-off finds (Diamond Necklace, Trident, Pirate Ship, Body Bag, Mermaid, Nautilus, Mask — generic `"YOU HAVE FOUND A %s"` reward text) from per-level counted sets (License Plate, Tin Can — dedicated `"...THERE IS %d MORE..."` reward text). See `docs/cut_content.md` ("Cut collectible category — Trident only") for the full category catalog and cut-content finding, and `docs/mission_system.md` for complete detail.

### Transform Format (PROP `0x080017DA`)

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

Column vector lengths encode uniform or non-uniform scale. Verified correct: computed world AABBs match stored PROP `0x080017DF` values to within floating-point precision (error = 0.0).

**Objects at the world origin (found 2026-10-01, user-observed in-game via F8 teleport to `0 0 0`):** `OPEN_S.GDW` has a starfish (`Starfish02`, at `(0, 0, 0.14)`) and `FISH.GDW` has a small piece of floating wood (best match: `debris1` under `Floater1_Brown`). The starfish was first read as a deliberate origin marker, but it's a **reference template** (6 placed starfish point at it via `PROP 0x080017F0`, see "Reference instancing" below) that also renders at its authored position. Most origin-authored templates (FISH's 72×-referenced buoy template, civilians, fish, weapon models) do *not* appear at the origin in-game, so whether a template renders at its own position is per-object, not a rule. Details in `docs/terrain_and_water_bounds.md`.

### Reference Instancing, Absolute Transforms, and Mission Relocation (decoded 2026-10-01)

Three placement rules beyond plain nesting. All three are implemented in **`scripts/brtr_scene_graph.py`**, which `rip_brtr_scene.py` and `resolve_brtr_hierarchy.py` now share:

1. **Reference instancing: `PROP 0x080017F0` = target node ID** (a base-brick field present on every node, 0 = none). The reference node places a **copy of the target's whole subtree**, with **"replace" semantics**: the copy's root takes the reference node's own world transform, the target's own transform is ignored, and the target's descendants compose beneath it as usual. Evidence: OPEN_S `Starfish01` (authored at y −27.6) and its 10 references. Replace puts every copy at seafloor depth (y −28 to −33), compose would bury them at y −55 to −61, and each reference carries its own random rotation. FISH's pier `molo` (authored at dock height y 3.59) and its 12 references at y 3.4–4.3 agree. References nest (templates containing references, like KATATAMA's `TRef*` grid of `ope*` seafloor clusters). Scale: FISH 130 reference nodes → 1,591 copied nodes; OPEN_S 539 → 37,082. The most-copied template everywhere is the ~140-node `Civilian` NPC rig (21–94× per level).
   - **Templates still exist at their authored spot** (usually the origin). In-game, *some* render there (OPEN_S's origin starfish, a piece of wood at FISH's origin) but most don't (FISH's 72×-referenced buoy template, civilians, fish), so it's per-object. Exports keep them, flagged `is_template`.
2. **Absolute transforms: node flags (`PROP 0x080017D9`, `m_nFlags`) bit `0x20000000`** means the node's transform is **already world space**, and the parent is ignored. This matches the engine's world-matrix updater (`Jaws.exe` `0x696EA0`), which skips parent composition when brick flag `0x20000000` is set. Example: FISH's `fenyo` pine trees and their `Box0N` foliage-card children (flags `0x2000005A`). Composing those through the parent sent them ~7,400 units away. FISH has 738 nodes with the flag (92 of them nested).
3. **Mission relocation: `MSMineAllMineMission.m_WhaleID` (`PROP 0x08000AE5`)** on `MineAllMine Mission Root` (FISH, at (2021, 0, −3827)) positions the whale's top-level node `WhaleCarcass MorePrim` **relative to the mission root** ("compose" semantics: whale world = root world ∘ whale authored local). The whale is moved, not copied. Verified in-game: predicted (2081, −20, −3722), and the user teleported there and landed against the carcass. Sibling fields: `m_SharksID` (`0x08000AE6`, a list of 5 shark node IDs), `m_Easy/Medium/HardSharkNum` (`0x08000AE7–9`, 5/7/10), `m_Easy/Medium/HardWhaleDeadHurt` (`0x08000AEA–C`, 14.0/10.0/6.0). This is the only mission relocation implemented. Other mission classes may link objects the same way and aren't handled yet.

**Known limitation:** OPEN_NE's `LeisureOverlay` template (referenced once, by `LeisureOverlayRef 1`) has crew references authored ~6,000 units from the template origin, so its copy lands off-map (150 placements beyond ±12,000). It's probably a runtime-attached group (e.g. a crew on a moving boat). Not resolved. Copies of multi-variant templates (e.g. `Civilian`, which contains every tourist body type and its LOD meshes) also emit every variant overlapping, where the engine shows one.

### Mesh–Object Linkage

PROP `0x08001873` second uint32 = mesh resource ID. This matches the **first uint32 of the 12-byte GMDL sub-header** (the mesh's resource ID). Use this to link a CHBR scene object to its GMDL geometry.

The sequential OBJ file index (`FISH_mesh_XXXX.obj`) corresponds to the order GMDL blocks are encountered during a linear scan of the GDW — not the resource ID directly. `rip_brtr_scene.py` builds the `resource_id → mesh_idx` mapping at runtime.

### Scene Layout — FISH.GDW

Coordinate system is DirectX Y-up (Y = height). World extents of real (non-template) mesh placements after the 2026-10-01 instancing/composition fix: X −240 to 2917, Y −226 to 3457 (the top is the `NEW_SKY_OPEN` sky dome), Z −4879 to 193.

**Correction (2026-10-01):** this section used to describe "two spatial clusters", with a **pier/dock cluster at the world origin**. That was wrong. The origin "cluster" is **reference templates**: the pier `molo`, breakable posts `Torheto_pozna`, the small fishing boat `Kis_Halaszhajo`, buoys `BolyaDefOpen`, the civilian rig, fish and weapon models, plus the SC17 mission's whale/sharks authored in mission-local coordinates. They're placed in the real play area by reference nodes or the mission root (see "Reference Instancing" below). For example, the 12 real pier copies sit at y 3.4–4.3 around (1810–2006, −4010 to −4110). FISH is essentially **one area**, around (1600–2900, −3600 to −4900), containing the pier/dock, the rocks (`szikla`), wrecks (`wrack`, `torzs`), the skull (`koponya`), alpha overlays (`interalph`), mansions (`mansionC`), the cadillac, and the whale carcass at (2081, −20, −3722).

Notable placed objects in FISH.GDW: `GWside` (great white shark model), `WhaleCarcass Body`, `MartinWalker` (NPC), `mansionC` (×2 underwater buildings), `CorkScrewEffect`, `PredatorEffectNONPS2`.

**Static terrain is IN BRTR** — confirmed 2025-06-29. All terrain and environment geometry is placed as regular BRTR mesh instances with full world transforms. There is no separate BSP, heightmap, or hidden terrain container.

| BRTR Object Name Pattern | World Z range | Description |
|---|---|---|
| `Homokos_PartSzakasz_B03..B23` | −3908 to −4331 | Sandy shore tiles — main seafloor in tutorial area |
| `Homokos_Alpha_Szakasz_…` | ~−4100 | Shore tiles with alpha transparency |
| `szikla elem`, `szikla a`, `szikla a04/a05` | −3760 to −4534 | Rock formations (~908 tris each) |
| `Plane01` (×7), `Plane02` | −4004 to −4429 | Water surface / seafloor flat planes |
| `plane16` (×6) | ~−4100 | Small path/floor tile sections |
| `alap01`, `alapkieg` | ~−3904 | Terrain foundation / base layer mesh |
| `Kotelszakito_szikla` | ~−4534 | "Rope-breaking rock": named after the cut Aurora rope mechanic (see Cut Content), whose rocks sit in START; whether the FISH copy had a purpose is unchecked |
| `molo04`, `molo05`, `molo_also`, `molo_felso` | ~0 | Main dock structure (lower/upper sections) |
| `kis_halaszhajo` | ~0 | Small fishing boat prop near pier |
| `seascooter-optimalized` | ~0 | Seascooter vehicle prop near pier |
| `HammerHead Headpart/Tailpart` | ~−4050 | Hammerhead shark mesh (creature) |

### Object Naming Convention — Hungarian

Content was authored at Appaloosa Interactive (formerly Novotrade, Budapest). Object names are in Hungarian:

| Hungarian | English |
|---|---|
| `szikla` | rock |
| `deska` | plank/board |
| `oszlop` | column/pillar |
| `koponya` | skull |
| `wrack` | wreck (English loanword) |
| `Torheto_pozna` | breakable post |
| `pierstores` | pier structure container |
| `fa` | tree |
| `fenyo` | pine tree |
| `feny` | light |
| `torzs` | trunk |
| `molo` | pier/dock |
| `molo_also` | lower dock section |
| `molo_felso` | upper dock section |
| `csonak` | boat |
| `korlat` | railing |
| `csolezaro` | boat barrier/blocker (seen in DEEPSEA.GDW) |
| `homokos` | sandy (terrain tile type) |
| `PartSzakasz` | shore/beach section |
| `alap` | base/foundation |
| `alapkieg` | foundation extension/supplement |
| `Kotelszakito` | rope-breaking (named gameplay obstacle) |
| `kis_halaszhajo` | small fishing boat |

## Scene Extraction Pipeline

### `scripts/rip_brtr_scene.py` — primary scene extractor

Run from the project root:
```bash
python3 scripts/rip_brtr_scene.py
```

Outputs to `scenes/`:
- `FISH_brtr.obj` — merged world-space geometry (15 MB), one OBJ group per placed object
- `FISH_brtr.json` — manifest of all 1161 instances, each with:
  - `node_id`, `name`, `mesh_id`, `mesh_idx` (index into `models/FISH/FISH_mesh_XXXX.obj`)
  - `xf` — full 12-float transform matrix
  - `pos` — world-space translation
  - `tris`, `vcols` (vertex colour count)

To change target GDW, edit `NAME = 'FISH'` at the top of the script.

**Textures:** scene OBJs use per-submesh `usemtl` from MATS → GMAT → TEXP with same-GDW textures (see TSET Format), with materials in `scenes/<NAME>_brtr.mtl`.

**Re-extracted 2026-10-01 with the scene-graph fix** (nested composition + absolute-transform flag + reference instancing + whale relocation; see "Reference Instancing…" in the Scene / Object System section). Mesh placements per GDW: AQUARIUM 6,119 · ARMADA 4,429 · BEACH 3,442 · BEACHPST 1,841 · CHASE 730 · DEEPSEA2 3,940 · DEEPSEA 3,917 · DOCKS 3,877 · FISH 1,610 · GAUNTLET 1,201 · KATATAMA 6,152 · MINEMSHA 3,765 · OPEN_NE 9,940 · OPEN_NW 11,251 · OPEN_S 16,234 · START 6,273 · TITLE0 0 · TITLE 226 · TOWN 7,789 · WRACK 2,256. Zero bad-geometry skips. `scenes/` grew from 632 MB to 3.3 GB. Manifest (`<NAME>_brtr.json`) entries now carry a **world** `xf`/`pos` plus `depth`, `via_ref` (reference node that placed this copy, or null), `is_template`, and `relocated_by`. OBJ object names get `@ref<id>` for copies and a `TEMPLATE__` prefix for template spots. `<NAME>_resolved_hierarchy.json` entries gained `absolute_xf`, `ref_target`, `is_template`, and `relocated_world_pos`.

`OPEN_S`/`OPEN_NE`/`OPEN_NW` are the three largest scenes by a wide margin, consistent with being the big free-roam Open Ocean zones; `TITLE0` remains an 8-node menu stub with zero placed mesh instances, matching its already-documented 0-mesh status elsewhere in this file.

Re-extraction command (same loop pattern as the `rip_gtex.py`/`rip_textures.py` all-GDW loops earlier in this file, run from project root):
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

**Locating `BRTR`:** a naive `data.find(b'BRTR')` lands on a coincidental match inside `RSRC` in 8 GDWs (`BEACH`, `BEACHPST`, `KATATAMA`, `OPEN_S`, `START`, `TITLE`, `TITLE0`, `WRACK`). Both scene scripts use this instead: keep candidates with the right magic, root count and `PRPS`, then take the **largest** (embedded loading-screen sub-archives have their own, smaller `BRTR`).
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

### `scenes/import_fish_blender.py` — Blender import script

Paste into Blender's Scripting workspace and run. Imports each unique mesh from `models/FISH/` once (shared mesh data), then places 1161 instances with proper Blender object transforms. Objects are sorted into named collections (Player, Characters, Buildings, Rocks, Flora, Dock, Terrain, Collision, etc.).

**Coordinate conversion** (current, user-confirmed 2026-10-01): `matrix_world = CONV @ game_world @ FLIP_Z`, with `CONV` = (Blender X = game X, Y = game Z, Z = game Y), determinant −1, because the game is left-handed. See the handedness entry under GMDL Chunk Hierarchy. The script parses our OBJ files directly (`mesh.from_pydata`), not through Blender's OBJ importer, so no importer axis conversion is involved. Set `NAME` at the top to import any GDW.

**Viewport settings to apply after import:**
- Clip End: 20,000 (level spans ~4600 units)
- Scale: scene unit scale = 0.01 (game units are centimetre-scale)

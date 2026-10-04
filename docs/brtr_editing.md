# Live BRTR Editing and Custom Map Feasibility

> Moved here from `CLAUDE.md` on 2026-10-02 to keep that file under its size limit. Text is verbatim.

> **Building a level yourself?** Start with the step-by-step tutorial, [`custom_level_tutorial.md`](custom_level_tutorial.md). This file is the technical background.

**Level-editing tool index (2026-10-04, all in `scripts/`, run from there unless noted):**

| Script | Does |
|---|---|
| `blender_export_scene.py` | runs **in Blender**: exports collection `JAWS` (meshes, transforms, images, material blend/culling settings) to `blender_export/` + `manifest.json` |
| `build_scene.py BASE OUT EXPORT_DIR [--deploy NAME] [--show-exits] [--tile N]` | one-command build: textures + materials + meshes (large ones tiled) + collision + nodes + exit zones, verified, optionally deployed (then F10 in-game) |
| `strip_level.py IN OUT [--minimal] [--keep-class/--keep-name/--keep-id]` | blank base: removes scenery, keeps gameplay layer, protects referenced nodes; `--minimal` also removes NPCs, animals, the SC17 mission and collectibles |
| `make_level_kit.py [--force] [--kit DIR]` | (project root) creates the custom-level kit `levels/custom_fish/`: minimal base + starter `.blend` |
| `redirect_stage.py IN OUT FROM TO` | make a level entrance load another `.GDW` (OPEN_S `FISH` → `TEST`) |
| `../levels/custom_fish/build.sh` | the kit's one-command export + build + install (`--show-exits`, `--no-deploy`) |
| `obj_to_gmdl.py IN OUT model.obj [ID] [--gmat --scale --collision]` | single OBJ → `GMDL` (+ generated `MREG`) appended to `RSRC`; library for `build_scene.py` |
| `insert_brtr_node.py IN OUT` | append node clones (edit `SPECS`); `build_node` is the library used by `build_scene.py` |
| `gdw_textures.py` | library: `build_gtex` (new texture blocks), `clone_gmat` (new materials), `find_block` |
| `gdw_grow.py` | library: `replace_chunk_payload` / `append_to_chunk` (resize `RSRC`/`BRTR`, fix `FSIZ`/`SKIP`/`FDIR`), `find_brtr`, `top_chunks` |
| `patch_texture.py` | in-place texture swap (same size), matched by pixel content |

## Live BRTR Editing — confirmed working (2026-07-16/17)

Beyond static extraction, `BRTR` can be **hand-edited and reloaded** by the actual game with predictable results — validated through a live edit-and-test loop against a running Proton install (backup-and-swap into the Steam install's `data/` directory; game re-reads a level's `.GDW` from disk on stage re-entry, no full process restart needed between edits).

**To cleanly relocate a placed static (non-physics) object**, patch two `PROP`s together, shifted by the same delta:
- `0x080017DA` (world transform) — the object's new position/orientation.
- `0x080017DF` (AABB) — **must** be updated to match, or the object's own AABB goes stale relative to its new transform. A stale AABB causes intermittent disappearing/culling *and* missing collision at the new location (both rendering and collision queries appear to use this AABB as a broad-phase spatial gate). With both fields kept in sync, relocation is clean: renders correctly, has correct collision, no fall/pop-in artifact. No `MREG` edit needed for objects without their own dedicated collision region.
- Editing the transform alone (leaving the AABB stale) is the most common mistake and produces exactly this failure mode — confirmed by direct A/B test on a large static mesh (`torzs`, a ship hull).

**Physics-eligible objects behave differently and this is correct, not a bug.** A physics/buoyant object (confirmed on `WhaleCarcass Body`, a boss-encounter rig) will visibly "drop" and resettle after an edit, *even for a pure horizontal move that doesn't touch Y*. This isn't an artifact of the edit pipeline — the shipped `Y` value in `BRTR` is simply the exact resting height the original level designers hand-placed for that specific `(X,Z)`; any edit that changes the effective location without also recomputing the true resting `Y` for the new spot leaves real gravity/buoyancy to visibly correct it. Static (non-physics) objects showed zero fall/drop when moved, confirming this is object-type-specific, not a general side effect of BRTR edits.

**Parent-child transform composition (see PROP `0x080017DA` note above) matters for reasoning about "where things are"**, not just for editing — a nested node's raw local-transform reading is frequently a red herring (e.g. reads near `(0,0,0)` regardless of true location) unless composed through the full ancestor chain via `scripts/resolve_brtr_hierarchy.py`. Learned the hard way while trying to locate objects by raw position during this experiment.

**Scaling a runtime spawn marker's transform works, and the scale carries through to whatever gets spawned there (confirmed 2026-08-13).** All prior live-edit tests above were on nodes with a directly-attached mesh (`PROP 0x08001873`). Collectible pickups (see the `BSCollectibleGameObject` PROP ID note above) are different — the marker node itself has no mesh, and the actual pickup mesh is presumably instanced by game code at runtime via the marker's `m_Template` reference. Scaled `WRACK.GDW`'s `CGO_Necklace` marker transform 10x (3×3 basis only, translation unchanged) plus its AABB proportionally (see the AABB-sync rule above — same failure mode applies), deployed to the live install, and confirmed in-game: the spawned necklace pickup rendered at 10x size. This proves the runtime spawner reads the marker's full transform, including scale, not just its position — useful for any future "make X easier to find/verify" experiment on this class of object.

Full narrative (including several dead-end fixes tried and ruled out, and the discovery that `FISH.GDW`'s BRTR content is actually the SC17 "Mine All Mine" side-challenge instance) is preserved in memory; see also `mod/README.md`'s "XYZ Overlay Accuracy" section for a related but distinct investigation into reading live player position for this same purpose — **solved 2026-10-01 by decompiling `Jaws.exe`: see the "Executable Analysis — `Jaws.exe` (Ghidra) and the Mod" section below.**

## Custom map feasibility (2026-07-17, insertion solved 2026-10-03) — resource injection and brand-new node insertion both work

Explored growing the archive itself (not just in-place editing) toward the goal of importing custom content. Two techniques are **confirmed working in-game**:

1. **Injecting a new resource.** Duplicate an existing `GMDL` block verbatim, patch only its mesh-ID field, append it to the end of `RSRC`'s payload (right before `BRTR`), and fix up `RSRC`'s size field, `FSIZ`, `SKIP` (recompute so `FDIR` stays 512-aligned — see `SKIP` note above), and the `FDIR` archive-2 offset entry (see FDIR note above) by the same inserted-byte delta. Repointing an existing `BRTR` node's `PROP 0x08001873` to the new resource ID renders it correctly — the game's resource loader does discover data appended into `RSRC` after original build time.
2. **Repointing/relocating existing nodes**, including **nested** ones. For a nested node, relocating to an arbitrary world position requires composing through the parent's transform (`new_local = parent_M⁻¹ @ (target_world − parent_translation)`, i.e. invert the parent's 3×3 rotation+scale basis), not just adding a translation delta — a plain delta only works for depth-0 (unparented) nodes. AABB shifts by the plain **world-space** delta regardless of nesting depth.

**Superseded 2026-10-03 (see next section).** Original 2026-07-17 finding: appending a brand-new `CHBR` sibling node to `BRTR` itself (same size-field-cascade technique as above, applied to `BRTR` instead of `RSRC`) does not render in-game — tried 3 ways (out-of-range node_id, in-range node_id, and a verbatim byte-clone of a real working node with only mesh-ref/transform/AABB patched), all failing identically with no crash and no render, despite every build independently re-verified as structurally sound. Leading theory: some precomputed spatial/streaming index or node membership list, built at level-authoring time and not touched by these edits, gates which nodes the engine even considers loading — but this isn't confirmed, and a weak counter-signal (new node was placed well inside an already-densely-populated, currently-streaming cluster) argues against simple region-based gating. Static analysis is exhausted here; next step would be runtime instrumentation of the game via the `mod/` d3d8 proxy to directly observe `BRTR` node processing during level load. Full narrative in memory (`project_custom_map_feasibility`).

## Brand-new node insertion — solved (2026-10-03)

**Inserting a brand-new `CHBR` node works.** Tool: `scripts/insert_brtr_node.py IN.GDW OUT.GDW` (edit `SPECS` at the top). Each spec copies an existing top-level node, gives it the next free node ID (max + 1), a new world translation, an optional mesh swap and optional uint32 PROP overrides, and recomputes the world AABB from the mesh's real vertices. It then appends the node at the end of the primary `BRTR` and fixes the size cascade: `BRTR` size, `FSIZ` (= `SKIP` offset), `SKIP` (`FDIR` stays 512-aligned) and every `FDIR` sub-archive offset, asserting each still lands on a `GDED` preamble.

**Why the July attempts failed:** all three used node 302 (`Homokos_PartSzakasz_F03 1`) as the template, and node 302 is a hidden render layer. Every rock and sand tile in `FISH.GDW` has a `" 1"`-suffixed companion (nodes 264–302) at the same position. The companions are ~400-byte nodes with a tiny low-poly mesh (node 302's mesh `0x80E` has 12 vertices and 10 triangles; its visible twin, node 349, uses `0x80B` with 280 triangles), no baked vertex colours, and these render fields:

| Field (PROP) | Visible node (e.g. 79 `szikla elem34`) | Hidden companion (e.g. 302) |
|---|---|---|
| `m_StaticLights` (`0x08001875`) | `0x1000009` | `0` |
| `m_RenderSetting` (`0x08001876`) | `0x40000800` (walls) / `0x820` (sand) | `0x40000400` / `0x40002400` |
| vertex colours (`0x0800187A`) | present | count 0 |

Controlled test in a copy of FISH (`TEST.GDW`, user-confirmed in-game): node 35138, a clone of node 79 at (2160, −5, −3650), **renders**. Node 35139, a clone of node 302 with the same wall mesh and a correct mesh-derived AABB at (2400, −5, −3650), **stays hidden**. With the AABB ruled out, the inherited render fields are what hide it. Which one of them is decisive hasn't been isolated.

**Viewport mask:** with `m_Viewport` (`0x080017DD`) = `1` (as on node 79), the clone renders only while the camera is **above** the water and disappears underwater. Most visible walls use `0x20003` (some `0xE0003` / `0x60001`), and the `SCRT` overlay tree has separate above-/below-water targets, so the mask most likely selects those passes. **Confirmed 2026-10-03:** setting the inserted wall's `m_Viewport` to `0x20003` makes it render both above and below the water (user-confirmed in-game).

**What the exe does (Ghidra):** `FUN_00693180` walks the archive's top-level chunks and hands `BRTR`/`SCRT` to the node reader `FUN_00699360`. That reader takes a class ID (`0x0107402F` = plain model brick) and node ID, reads `PRPS` (`FUN_00692cd0`, which aborts with "Missing properties" if `PRPS` isn't first), then loops over sub-chunks: `PRIM` → `FUN_006e1240`, linked at node `+0xD8`; `ACTN` → `FUN_0068ed80`, at `+0x2C`; `CHBR` → recursive child, at `+0x28`. There's no node count, index or membership list. `FUN_00692c10` registers node IDs in a map and gives an ID a fresh runtime number when it can't be registered, so duplicate IDs aren't fatal.

**`PRIM` = collision link.** `PRIM` (598 in FISH, on ordinary mesh nodes) holds a class ID `0x20003002`, a zero ID and a `PRPS` whose `PROP 0x080018D8` is `['MREG' tag][uint32 region_id]`: the node's `MREG` collision region. The `MREG` is stored in **mesh-local space** (`MREG 0x943`'s root `BREG` box equals mesh `0x891`'s local vertex extents exactly), so it follows the node's transform. **User-confirmed in-game 2026-10-03:** inserted wall A (clone of node 79, no `PRIM`) can be swum through. Inserted wall C (clone of node 77 `szikla elem43`, same mesh, carrying its `PRIM` → `MREG 0x943`, moved to (2300, −5, −3520)) **blocks the shark** at its new position. A copied `PRIM` whose `MREG` matches the node's mesh therefore gives a new object working collision, with no edits to `MREG` itself.

**PROP IDs ≈ reflection field index.** A PROP ID's low bits match the field's global registration index from `scripts/dump_class_fields.py`, plus a small offset that drifts because the dump misses a few registrations (+0x15 near `BSCollectibleGameObject`, +0x23 near `m_WhaleID`, about +0x59 for the brick base and +0x89 for `GDModel`). That's good enough to name fields by neighbourhood: `0x080017D8` `m_Name`, `0x17D9` `m_nFlags`, `0x17DA` `mtx`, `0x17DB` `m_ExecFilter`, `0x17DC` `m_CameraFilter`, `0x17DD` `m_Viewport`; `GDModel`: `0x1873` `m_3dModelID`, `0x1874` `m_DynamicLights`, `0x1875` `m_StaticLights`, `0x1876` `m_RenderSetting`, `0x1877` `m_ExtRenderSetting`, `0x1878` `m_ChannelSetting`, `0x1879` `m_ModelColor`.

**Template rule for new objects:** copy a node that is actually visible in-game, i.e. one with static lighting and vertex colours, not a `" 1"` companion. Set `m_Viewport` to a value used by visible geometry, and give it a `PRIM` if it should be solid.

## Custom meshes from OBJ — working (2026-10-03)

`scripts/obj_to_gmdl.py IN.GDW OUT.GDW model.obj [MESH_ID] [--gmat ID] [--scale S]` converts an OBJ (Blender default export, or our own extracted OBJs) into a `GMDL` and appends it to `RSRC`; `scripts/insert_brtr_node.py` then places a node that uses it (SPECS mesh field). **User-confirmed in-game:** a generated upright ring (833 verts, 1,536 tris, GMAT 1073) renders textured at (2160, 10, −3650) in `TEST.GDW`. No collision yet (no `PRIM`/`MREG`), as expected.

- **Layout written:** the minimal one used by 42 shipped FISH meshes: `GMDL [id][1][0x0131F505]` → `MATR` ([1] + identity 4×3) → `MATS` → `TSET` → `TANG([tri_count] VIND)` → `VERT([vert_count] POSI NORM UVUV)`. `TNOR`/`TFLG`/`VCOL` are optional in shipped meshes and left out. `0x0131F505` = 20051205, an export date stamp on every shipped GMDL (RSRC's sub-header is `0x0131F508` = 20051208).
- **Padding rule (found by byte-comparison):** nested chunks are 4-byte padded between siblings, but a container's size field **excludes** the padding after its last child. With that, rebuilding every minimal-layout mesh from its decoded data is byte-identical: 42/42 FISH, 90/90 OPEN_S.
- **Submeshes:** `VIND` indices are absolute; each `TSET` submesh owns a contiguous vertex block used by no other submesh.
- **OBJ conventions:** z and normal z negated, v flipped, face order kept (inverse of `rip_meshes.py`). Round-tripping mesh `0x891` through its extracted OBJ returns the identical 280 triangles in the same order and winding. Polygons are fan-triangulated; missing normals get face normals.
- **Materials by `usemtl` name:** `gmat_<id>` = that GMAT; `mat_<texture id>` = first GMAT whose base texture matches (several GMATs can share a texture, e.g. 837/1070/1073 all use texture 193, so `gmat_` is safer); otherwise `--gmat`.
- **Resource IDs must stay in range.** `RSRC` is a clean chain of resource blocks with unique IDs in **one shared ID space** (FISH: 1,718 blocks, IDs 1–2832: GTEX 1–2726, GSMP 81–601, GSFX 637–1735, GMAT 661–2832, SKEL 1766–1858, GMDL 1861–2370, MREG 2371–2539…). A mesh injected as `0x7000` was silently ignored; the same mesh as 2833 (next free) rendered. The converter defaults to the next free ID. Exact limit unknown (the node reader masks class IDs with `& 0xFFF`; a similar 4096 cap on resource IDs would fit).
- **Baked vertex colours** (`0x0800187A`) hold exactly one RGBA float4 per mesh vertex (node 79: 176 = mesh `0x891`'s vertex count). When a node's mesh is swapped, `insert_brtr_node.py` regenerates the list at the new vertex count, filled with the source node's average colour.
- **Shared growth code:** `scripts/gdw_grow.py` (`append_to_chunk`) grows `RSRC` or `BRTR` and fixes `FSIZ`/`SKIP`/`FDIR`; both tools use it (refactor verified byte-identical against the previous build).

## Workflow: Blender model → in-game object (2026-10-03)

Step by step, as used for the first user-made model (`something.obj`, see below). Run from `scripts/` (both tools import `gdw_grow.py` / `gdw_materials.py` from there).

1. **Model in Blender** and export with **File → Export → Wavefront (.obj)** at default settings (forward −Z, up Y; normals and UVs on). Several objects in one file are merged into one game mesh.
2. **Materials are optional.** Each Blender material becomes one submesh, chosen by name: `gmat_<id>` (a game GMAT ID) or `mat_<texture id>` (the names our extracted OBJs use). With no materials, or other names, pass `--gmat <id>` (FISH rock-wall material: `1073`).
3. **UV-unwrap if the texture should show.** Without UVs every vertex gets UV (0, 0) and the object is one flat colour from the texture's corner.
4. **Scale:** Blender's default 1-unit objects are tiny in-game (game units are roughly centimetres; the FISH wall mesh is about 70 across). `--scale 20` turned a 2.5 × 3.2 model into a 50 × 64 object.
5. **Shading:** a flat-shaded export splits vertices per face (`something.obj`: 651 OBJ vertices → 2,672 game vertices). That's harmless below the 65,535-vertex-per-mesh `uint16` limit. Use Shade Smooth for fewer vertices and smooth lighting.
6. **Convert and inject:**
   ```bash
   python3 obj_to_gmdl.py IN.GDW STEP1.GDW model.obj --gmat 1073 --scale 20
   ```
   Prints the mesh ID it used (next free resource ID, e.g. `0xb11`).
7. **Place it:** add a `SPECS` entry in `insert_brtr_node.py`: `(79, (x, y, z), <mesh id>, {0x080017DD: 0x20003})`. Node 79 is a visible top-level wall used as the template; the `m_Viewport` override makes it render underwater as well. The translation is where the model's origin goes, so the OBJ's y = 0 lands at `y`. Then:
   ```bash
   python3 insert_brtr_node.py STEP1.GDW OUT.GDW
   ```
8. **Deploy** `OUT.GDW` to the live `data/` folder (back up first) and re-enter the level.

Always build from a clean base (here `TEST.GDW.pre_insert`) instead of stacking runs: re-running on an already-edited file would add a second copy of everything and pick a different next free ID.

**Collision:** add `--collision` to the convert step and place the object with **template node 77** (it has a `PRIM`) plus `{'prim_region': <MREG id printed by the converter>}`, e.g. `(77, (x, y, z), 0xB11, {'prim_region': 0xB12})`. Node 77 already uses `m_Viewport` `0x20003`.

**Blank base:** see "Blank base level" below (`strip_level.py`).

### Live test state (2026-10-03, early; superseded, see "Current live state" at the end)

Live `TEST.GDW` (Fisherman's Isle copy, reached through the renamed `OPEN_S` transition; rocks tinted magenta, sand cyan) is `TEST.GDW.pre_insert` plus:

| Node | Template | Position (X Y Z) | Mesh | Notes |
|---|---|---|---|---|
| 35138 | 79 `szikla elem34` | 2160, −25, −3650 | `0xB11` = user's `something.obj` (cone + torus + icosphere), ×20, GMAT 1073 | `m_Viewport` 0x20003, no collision. **User-confirmed: renders, textured with GMAT 1073's (tinted) rock texture, at the expected large size.** First user-made Blender model in-game. Next build: same model unscaled (×1). |
| 35139 | 77 `szikla elem43` | 2300, −5, −3520 | `0x891` (wall) | keeps `PRIM` → `MREG 0x943`; renders and blocks the shark (confirmed) |

Earlier builds tested at the 35138 slot: the generated test ring (mesh `0x7000`: invisible; same mesh as `0xB11`: renders, confirmed) and plain wall clones (A/B/C viewport and collision tests above).

## Collision for custom meshes — working (2026-10-03)

**User-confirmed in-game:** the user's model (`something.obj`, ×15) with a generated collision region blocks the shark. Built with `obj_to_gmdl.py ... --gmat 1073 --scale 15 --collision` → mesh `0xB11` + `MREG 0xB12`, placed by `(77, (2160, -25, -3650), 0xB11, {'prim_region': 0xB12})`.

**MREG format (verified against all 123 FISH MREGs):** `[region_id][1]['GMDL'][mesh_id][0xFFFFFFFF]`, then `PERF` (0.25), then `BREG`: `n = 2L − 1` boxes in heap order, `L = max(1, ⌊tris ÷ 4⌋)` leaves, leaves in in-order traversal each owning 4 consecutive `STRI` entries, internal boxes = union of children, all mesh-local. Then `STRI`, a permutation of the mesh's triangle indices. Leftover triangles (count not a multiple of 4) go into one leaf whose position the data can't pin down, so the generator pads the mesh to a multiple of 4 by repeating its last triangles (they draw on top of themselves).

**Mesh side:** 122/123 collision meshes carry `TNOR` and `TFLG`, so `--collision` writes both: `TNOR` = −normalize((B−A) × (C−A)) in game space (matches all 46,153 shipped triangles; generated values for mesh `0x891` match the stored ones within 1.2×10⁻⁷), `TFLG` = `[1][0x47][0]` (all edge bits set).

**Generator validation:** rebuilding mesh `0x891` and its region gives an `MREG` of the same size (4,512 bytes) with an identical header to the shipped `MREG 0x943`. The tree passes every rule (permutation, 70/70 leaf boxes, 69/69 unions) and is ~26% tighter (total leaf volume) thanks to a median split on the longest centroid axis.

**Engine side:** the loader `FUN_006e3cb0` (vtable `0x7F79A0`) only copies `PERF`/`BREG`/`STRI` into memory when the header's flags field is negative. It stores no leaf ranges, so the query code must derive them with the same 4-per-leaf rule. Query code not yet located.

## Blender scene export → level, one command (2026-10-03)

**User-confirmed in-game:** a test scene built entirely in Blender (a cube scaled 1×1×2 and rotated, a linked duplicate, a tilted Suzanne with collision off) appears with correct positions and rotation. Both cubes are solid, and Suzanne can be swum through. Rotation was re-checked with a 30°/60° tilt next to an upright copy.

### How to use it

1. In Blender, put the objects to export in a collection named **`JAWS`** (if there is none, the selected objects are exported). The Blender origin maps to `GAME_ORIGIN` (default (2160, −25, −3650), next to the whale in FISH/TEST), and 1 Blender unit = `GAME_SCALE` (default 15) game units. Blender Z (up) becomes game Y.
2. Optional per-object custom properties: `jaws_collision` = 0 for a non-solid object (default solid), `jaws_gmat` = game material ID for faces whose Blender material isn't named `gmat_<id>` / `mat_<texture id>` (default 1073, the FISH rock wall).
3. Open `scripts/blender_export_scene.py` in Blender's Text Editor and Run Script (or `blender -b file.blend --python scripts/blender_export_scene.py`). It writes `manifest.json` plus one OBJ per unique mesh to `EXPORT_DIR` (default: a `blender_export/` folder next to the saved `.blend`; `~/blender_export` if it's unsaved).
4. From `scripts/`:
   ```bash
   python3 build_scene.py "<live data>/TEST.GDW.pre_insert" /tmp/out.GDW <path to blender_export> --deploy TEST
   ```
5. Press **F10** in the level.

### What each side does

- **`scripts/blender_export_scene.py`** (Blender 4.0+): exports evaluated meshes (modifiers applied), triangulated with `loop_triangles`, per-corner normals and the active UV map, one `usemtl` group per material slot. Each object's scale × `GAME_SCALE` is **baked into its mesh** (normals use the inverse-transpose), so the node carries only rotation + translation and collision is built at final size. Linked duplicates without modifiers and with equal scale share one mesh. Transform: game = C·blender with C = swap Y/Z (same as `scenes/import_fish_blender.py`); node basis = C·R·C (game column j = C(R column C(j))), translation = origin + scale·C·location. OBJ output uses the OBJ/Blender-export convention (x, z, −y), so `obj_to_gmdl.py`'s existing conversion applies unchanged. Blender 4.0 quirk: `mesh.corner_normals` exists but stays empty, so the script falls back to `calc_normals_split()`.
- **`scripts/build_scene.py`**: converts every unique mesh (`obj_to_gmdl.load_parts` + `build_gmdl`, with `build_mreg` if any object using it is solid), assigns consecutive next-free resource IDs, appends everything to `RSRC` in one go, then appends one `BRTR` node per object. Solid objects clone **node 77** (has a `PRIM`, viewport `0x20003`) with the `PRIM` pointed at the mesh's `MREG`; non-solid ones clone **node 79** with viewport set to `0x20003`. Full 12-float transform, AABB from the mesh, vertex colours resized. Then it verifies the `RSRC`/`BRTR` chains, `FSIZ`/`SKIP`/`FDIR`, and with `--deploy NAME` copies to the live `data/NAME.GDW` (first-time backup `NAME.GDW.pre_build`).
- **Verification (headless Blender 4.0.2):** each placed node's world AABB equals Blender's world-space vertex bounds mapped to game space, within 0.0001. Triangle winding agrees with vertex normals on 12/12 (cube) and 968/968 (Suzanne) triangles.

### Large objects fade out (found 2026-10-04, user-confirmed)

A single 1,500×1,500-unit floor object (the `custom_fish` starter seafloor, one node at its centre, correct world AABB) **slowly faded out whenever the shark looked away from it and faded back in when it looked at it**. Cutting the same floor into 8×8 tiles (~190 units each, origin at each tile's centre) removed the fading completely (user-confirmed). So the engine runs a per-object, time-smoothed visibility fade whose test misjudges very large objects; the AABB was correct, so it isn't the stale-AABB culling. Shipped terrain is tiled the same way (FISH `Homokos_PartSzakasz_*`). The exact test (pivot point vs. bounding sphere vs. distance) isn't traced in `Jaws.exe`. **`build_scene.py` now tiles automatically:** any mesh wider than 300 game units on an axis is cut (by triangle centroid, mesh-local) into cells of at most 200 units, each its own `GMDL`/`MREG`/node with re-centred vertices and the node translation moved through the object's basis (`--tile 0` = off). Verified: the 64 auto-tiles' AABBs union to exactly the one-piece floor's AABB, also for a 30°-rotated copy. It also lifts the 65,535-vertex limit for big terrain.

### Limits

- Mirrored objects (negative scale) aren't handled specially.
- One mesh holds at most 65,535 vertices (`uint16` indices). Split large terrain into several objects.
- Collision follows rotation: the 30°/60° tilted cube blocks the shark along its slanted faces (user-confirmed 2026-10-03).
- Textures: images on Blender materials are converted (see "Custom textures" below); material properties (shininess, transparency) always come from GMAT 1073. For an empty level, strip the base first (see "Blank base level").

### Live state (superseded, see "Current live state" at the end)

`TEST.GDW` = `TEST.GDW.pre_insert` + the 3-object test scene (export in the session scratchpad, not kept). The previous build with the user's `something.obj` and wall C is saved as `TEST.GDW.pre_build`.

## Custom textures — working (2026-10-03)

**User-confirmed in-game:** two images on Blender materials appear correctly on the test scene: one packed into the `.blend` (256×256 coloured quadrants with "JAWS", on both cubes) and one linked from disk (300×200 rainbow gradient resized to 256×256, on Suzanne). Both are test images generated with PIL, not game assets.

### Texture block format (`GTEX`, plain variant)

"GTEXT" was never a tag: every texture in `RSRC` is a `GTEX` chunk, and the "T" is the low byte (`0x54`) of the following size field. Two payload variants exist: plain (258/321 in FISH) and one with an `OBPR` block holding a `TEXB`/`TEXH`/`TEXD` tag (63/321). New textures use the plain variant:

```
GTEX [size]
  [tex_id][flags = 1][stamp = 0x0131F253][0][width][height][bpp = 24 | 32]
  TGAN [tgan_size]
    [tgan_size - 4]
    18-byte TGA header: idlen 0, cmap 0, type 2, cmap spec 0, origin 0,0, width, height, bpp, descriptor (0 for 24-bit, 8 for 32-bit)
    pixels: bottom-up rows, BGR (24) or BGRA (32)
    26-byte TGA 2.0 footer: 8 zero bytes + "TRUEVISION-XFILE.\0"
```

Survey of the 258 plain FISH textures: stamp and flags constant; 134 × 24-bit (descriptor 0) and 124 × 32-bit (descriptor 8); 246 have the standard footer inside `TGAN` (a handful have none or odd trailing bytes); `TGAN`'s second field is always size − 4; the block has no slack after `TGAN`. Not all dimensions are powers of two, but nearly all are, so the generator resizes to the nearest power of two (max 1024).

**Validation:** `build_gtex` rebuilds texture 193 (512×512, 24-bit) and texture 1 (128×128, 32-bit) from their extracted PNGs byte-identically, and 240/241 plain FISH textures with the standard footer.

### Material (`GMAT`)

```
GMAT [size] [gmat_id][flags 0x21] OBPR [0] [stamp] TEXP [n]['GTEX'][tex_id]... REFL BUMP COLS SHIN ...
```
New materials are a byte copy of GMAT 1073 (FISH rock wall: opaque, renders above and below water) with only the ID and the first `TEXP` entry changed (`clone_gmat`). So every custom texture currently shares 1073's lighting, shininess and transparency settings.

### Pipeline

- `scripts/blender_export_scene.py` finds each material's image (the Image Texture node feeding Principled Base Color, else any image node). On-disk images are copied as-is; packed or generated images are saved as PNG (the `.blend`'s own image path is restored afterwards). Each textured material gets a `usemtl` token `bmat_NNN` (so names with spaces work) and a `materials` entry in the manifest. Materials named `gmat_<id>` / `mat_<texture id>` still pick game materials, and materials without an image fall back to `jaws_gmat`. Exported test images were pixel-identical to the originals (packed one included).
- `scripts/build_scene.py` creates one `GTEX` per unique image and one `GMAT` per textured material (consecutive next-free resource IDs, appended before the meshes), then converts meshes with the token → GMAT mapping.
- Test build IDs: GTEX `0xB11`/`0xB13`, GMAT `0xB12`/`0xB14`, GMDL `0xB15` (+ MREG `0xB16`) / `0xB17`.

### Limits

Transparency: see "Transparency" below. Only the base texture is set; extra `TEXP` layers aren't. Max texture side 1024.

## Transparency — working (2026-10-03)

**User-confirmed in-game** with four labelled planes built from Blender materials through the normal pipeline (1 Alpha Blend, 2 Alpha Clip, 3 Alpha Blend + Backface Culling, 4 Alpha Clip + Backface Culling): 1 and 3 fade smoothly, 2 and 4 cut hard; 1 and 2 show from behind, 3 and 4 don't.

### What controls what

| Effect | Controlled by | Values |
|---|---|---|
| See-through pixels | **32-bit texture alpha** alone | works on any node/material, even the opaque rock material 1073 |
| Smooth blend vs. hard cut-out | **node render settings** | normal (template 77/79, `m_RenderSetting` `0x40000800`) = alpha **blend**; FISH seaweed values `m_RenderSetting` (`0x08001876`) `0x80000920` + `m_StaticLights` (`0x08001875`) `0x81000021` = alpha **test / cut-out** |
| Back faces | **material `TWOS`** only | GMAT 668 (FISH seaweed material, `TWOS` 1) shows them; 1073 (`TWOS` 0) culls them |

Where these came from: FISH seaweed/plants (`NA hinar`, `NA kisnad`, 73 nodes, nested in "Tile" groups, viewport `0x2`) use 32-bit textures, GMATs 668/727 (same sub-chunks as 1073 apart from colours/shininess, but `TWOS` 1) and the render settings above. The sand-blend overlays (`interalph`, `Homokos_Alpha`) are different again: 24-bit textures, `m_RenderSetting` `0x200820`, `m_StaticLights` `0x81000001`, `TIAS` 50000 / `BIAS` 1.0 in the material; their fade presumably comes from vertex-colour alpha (not used here).

**Lesson from the tests:** a first reading suggested the cut-out node setting also toggled back-face culling (and cancelled a two-sided material). It came from numbering the panels left-to-right while looking at them **from behind**, where the order is reversed. Labelled test images (number + mode text, mirrored when seen from the back) removed the ambiguity.

### Mapping in the pipeline

`blender_export_scene.py` records each textured material's Blend Mode (`blend_method`; Blender 4.2+ `surface_render_method`) and `use_backface_culling`. `build_scene.py` then does:

| Blender material | Texture | GMAT clone | Node |
|---|---|---|---|
| Opaque | 24-bit (alpha dropped) | 1073 (one-sided; Blender's culling-off default is ignored for opaque) | normal |
| Alpha Blend | 32-bit | 668 if Backface Culling off, else 1073 | normal |
| Alpha Clip / Hashed | 32-bit | 668 if Backface Culling off, else 1073 | + `0x08001876` = `0x80000920`, `0x08001875` = `0x81000021` |

The cut-out node settings apply per object: if any material on the object's mesh is Clip, the whole node gets them.

### Caveats

- Blended (Alpha Blend) surfaces aren't sorted by us; overlapping blended objects may draw in the wrong order, as with any alpha blending.
- A material's lighting/colour sub-chunks come from the template (668 or 1073), so transparent and opaque versions of an image can look slightly different in brightness.

## Blank base level — working (2026-10-03)

**User-confirmed in-game:** stripped `TEST.GDW` (Fisherman's Isle copy) has no scenery left, while the level still loads normally. Left: shark + HUD, NPCs and animals, the SC17 Mine All Mine setup (whale carcass, challenge buoy, sharks), water, sky, sun, and the exit back to Open Ocean South (all checked).

### Tool and workflow

```bash
cd scripts
python3 strip_level.py "<live data>/TEST.GDW.pre_insert" /tmp/blank.GDW
python3 build_scene.py /tmp/blank.GDW /tmp/out.GDW <path to blender_export> --deploy TEST
```
`build_scene.py` now copies its template nodes (77 solid / 79 non-solid) from stock `GAME_GDWs/FISH.GDW` (`--templates` to override), because the stripped base no longer contains them. `gdw_grow.replace_chunk_payload` resizes a chunk in either direction (`append_to_chunk` is built on it; refactor checked byte-identical).

### What gets removed (FISH)

809 top-level nodes, 1,297 including children; `BRTR` 5.46 MB → 1.81 MB:
- **classes** `0x0107402F` (plain model brick: rocks, sand, piers, houses, props; 648 top-level), `0x0106F06E` (flora: 143), `0x01072071` (2);
- **the `Tiles` group** (kept class `0x010AA0A4`, but 173 seafloor/flora meshes: `ope` seafloor clusters, plants, corals, `feny` light shafts);
- **scenery reference templates** `molo` (pier), `Torheto_pozna 1` (breakable posts), `Kis_Halaszhajo` (fishing boat), and every top-level reference node (`0x080017F0`) copying them (12 + 7 + 3).

Survey of FISH's 1,074 top-level nodes by class: apart from those two scenery classes, the rest (~283) is gameplay/engine: cameras (`0x01023020`), lights (`0x0101F01D`), fog (`0x0102001F`), water (`0x01042040`), sounds (`0x0100D00C`), HUD, weapons (`0x010B80B7`), AI waypoints, missions, effects, creature/NPC templates, the `OPEN_S` exit object (`0x01134132`). All kept. `RSRC` is untouched (unused meshes/textures stay in the file).

### What must be kept, and why

- **`NEW_SKY_OPEN`** (sky dome, a plain model): kept by name.
- **`Sun` (3569, a plain model):** `NAWater2004 Hiwave`'s property **`0x08001376` points at it**. With it removed, the water surface stopped rendering above and below (the shark could still swim and breach). Found by bisection: keeping all plain models brought the water back, then the render-settings survey showed `Sun` as the odd one out (`m_RenderSetting` `0x82842`, flags `0x12`). The strip tool now protects anything a kept node points at through `ID_PROPS` (`0x080017F0` reference, `0x08000AE5`/`AE6` whale/shark mission links, `0x080004A1` collectible template, `0x080003C7` child list, `0x08001376` water sun) and keeps such nodes unchanged.
- ~~**8 nodes named inside top-level `ACTN` blocks**~~ **(corrected 2026-10-04: false positives).** `Kotelszakito_szikla_vf16` (72), `szikla elem52` (84), `Plane01 1` (128), `fishbone 1`, `szikla elem41 1` (272), `szikla elem64 1` (288), `Box185 2` (500), `Box216 2` (516) were kept and moved 50,000 units down because their IDs appeared in top-level `ACTN` blocks (`Stage0Quest`, `StreamPlay 1`, `MBMovieJelzo 1`). The scan read every uint32 of the block, and those IDs are the blocks' own chunk/PROP **size fields** (e.g. `Stage0Quest`'s `ACTN` size is 516, a PROP size 84). `strip_level.py` now only looks at PROP values, and they're removed.

### Minimal mode (2026-10-04, untested in-game at time of writing)

`strip_level.py --minimal` also removes the visible gameplay layer: NPCs (`0x01085081`), waypoints (`0x010C80C7`), the bird flock (`0x01096095`), fish schools (`0x01078077`), the SC17 mission root and sharks (`0x01104103`, `0x01094092`), the collectible `07 - Treasure Chest` (`0x0112B12A`), the beach sound area (`0x0101B019`), and by name `WhaleCarcass MorePrim`, `CrowdAllo`, `CollectableObjects`, `CollectibleAddOn`. **Ambient wildlife comes from creature generators**, not the creature templates: `ACTN` class `0x02129128` (`SeaOtterGenAct`, `BarracudaGenAct`, `MarlinGenAct`, `SwordfishGen`, `MantarayGen`), each on a group node `Parent<X>Gen` (FISH 1795–1803). `PROP 0x08000A78` = creature template node (e.g. `Marlin Root` 22836), `0x08000A79` = count, `0x08000A82` = 6 floats (area box). The first minimal build kept them and marlins and rays still spawned (user, 2026-10-04); `--minimal` now removes any top-level node carrying that action. FISH: 842 top-level nodes removed (1,400 incl. children), 232 left. Kept: water, sun, sky, cameras, fog, lights, HUD, effects, sound definitions, weapons, creature templates, `GameState`/`Stage Completed Save`, the `OPEN_S` exit.

### Blank mode, recentred, no exit (2026-10-04, user-confirmed)

`strip_level.py --blank` (implies `--minimal`) is the kit's base (`levels/custom_fish/FISH_blank_base.GDW`, from `make_level_kit.py`):
- **Removes the leftovers:** the 8 rocks/planes above, `tores`, `horgaszszek` (fishing chair), `Floater1_Brown`/`Floater2_Brown` (the floating wood seen at FISH's origin), the buoy template `BolyaDefOpen`, the exit's 72-buoy ring, and ~30 ship/boat effect nodes (any name containing `ship`, plus `hajo_csavar_bubu`, `ANXploGen 1_dc`, `boat_crash`, `cuttergun_shot`). A leftover stays if a kept node or action has a PROP value equal to an ID in its subtree, ignoring IDs below 1000 (sizes and counts collide with them): `SplashEffectDown_ship`, `Debris_metal_ships`, `ship_hit_blood` stay (used by `Grenade 4_cut`). FISH: 885 top-level nodes removed (1,523 incl. children), 189 left.
- **Recentres on the world origin:** `SHARRRK` (the shark, spawn) moves to x = z = 0, y −6.5, and `SharkPosReal`, `NEW_SKY_OPEN`, `Sun` (water's sun), `Sun(Y)`, `OceanMap1` (minimap anchor) move by the same (−1998.3, 0, +3628.0). Water, cameras, fog and lights sit at the origin and follow the shark.
- **Disables the stock exit:** the leave-type trigger's action list moves to enter, radius 0, parked at x = z = 100,000. Teleporting anywhere gives no prompt (user-tested). `build_scene.py` finds an area trigger with either list set and reuses its actions for Blender exit zones.
- **Spawn from Blender:** `jaws_spawn` = 1 on an object → manifest `spawn` → `build_scene.set_spawn` rewrites `SHARRRK`'s and `SharkPosReal`'s transforms (yaw only; the shark faces its local +Z, basis X = (fz, 0, −fx)) and shifts their subtrees' AABBs and absolute-flag descendants. User-tested: spawn at (75, −10, 75) facing +X.
- The exporter's `GAME_ORIGIN` is now **(0, −25, 0)** (was FISH's (2160, −25, −3650)); existing `.blend`s keep their layout.

**Unused resources (`prune_level.py`, `build_scene.py --prune`, used by `build.sh`):** keeps every `RSRC` block reachable from typed references (`['GMDL'][id]`, `['GTEX'][id]`, `['GSFX'][id]`, …) in the primary `BRTR`/`SCRT`, then transitively inside kept blocks (mesh → `MATS` → `GMAT` → `TEXP` → `GTEX`, `GSFX` → `GSMP`, …), drops the rest, and checks every reference still resolves. `RSRC`'s 12-byte header is a constant stamp (`0x0131F508, 1, 0` in every level), no count. Blank base 127.4 → 105.6 MB; the user's level 130.8 → 109.9 MB; both user-tested. What's left is mostly needed: level music `SndMusic` 41 MB, pause menu artwork 18.5 MB, fonts/HUD ~5 MB, civilian rig 4 MB, shark 4 MB. The 14 MB loading-screen sub-archive (`FISH00`) is separate and untouched.

### Class IDs name their class (2026-10-04)

A node or action class ID's **low 12 bits index the level's `CLAS` name lists**: `CLAS` holds sections `BRCM` (brick classes: 311 names in FISH, `[uint32 count]` then `[uint32 len][name, 4-aligned]`) and `ACCM` (action classes, next section). Nodes (`0x01…`) index `BRCM`, actions (`0x02…`) index `ACCM`. Checked: `0x0107402F` → `GDModel`, `0x0106F06E` → `NAGarden` (flora), `0x01134132` → `ANSphereCheck` (area trigger), `0x0203B039` → `GDControl`, `0x02038036` → `GDLoad`, `0x0217B17A` → `MBLoadChecker`, `0x02129128` → `MSHHSharkGen` (creature generator), `0x02092091` → `Stage0Quest`, `0x02173172` → `StreamPlay`, `0x0218F18E` → `MBMovieJelzo`.

### False lead

`PROP 0x08001051` looked like a node reference (`NAWater2004`'s value 93 = rock `szikla elem24`), but it's set on 301 particle/effect nodes with values like 2141 that aren't nodes. It's a texture/material resource ID that happens to collide with rock node IDs (both are small numbers). Lesson: small-number "references" between node IDs and resource IDs are often coincidences; confirm with a test.

### Limits

- `SCENERY_GROUPS` / `SCENERY_TEMPLATES` / `KEEP_NAMES` are FISH names; other levels will need their own lists (the class-based rule and the reference protection are generic).
- The ocean floor is gone, so the shark can swim down to wherever the engine limits depth. Build a floor in Blender if needed.

## Area triggers and level exits (2026-10-04)

A level's exit and the Open Ocean level entrances are **area triggers**, node class **`0x01134132`**. Fields (reflection class `?@0x8cc320`, PROP IDs consecutive from `0x0800028D`):

| PROP | Field | FISH exit `OPEN_S` (1551) |
|---|---|---|
| `0x0800028D` | `m_type` | 1 = vertical column (2 = with `m_top`/`m_bottom`, DEEPSEA rooms) |
| `0x0800028E` | `m_target` | 26116 `SHARRRK` (the shark) |
| `0x0800028F` | `m_radius` | 795.0 |
| `0x08000290` | `m_enter_act` | empty (`[0]`) |
| `0x08000291` | `m_leave_act` | `[1, 1552]` |
| `0x08000292` | `m_rate` | 10 |
| `0x08000293`/`94` | `m_top`/`m_bottom` | 0 / 0 |
| `0x08000295`/`96` | `m_color1`/`m_color2` | 1 / 9 |

Lists are `[count, ids…]`. FISH's exit fires when the shark **leaves** the circle; its 72 `BolyaReference` children are just the buoy ring marking it. Action 1552 `OssLoadChecker` (class `0x0217B17A`, fields `m_type`, `m_stage`, `m_toact` = 1553, `m_toactcancel`) starts the `Accept` control 1553 (adds `LoadingPredatorEffect`, then after 90 ticks starts 1554, a `GDLoad` action with stage name `FISH00`, `PROP 0x08001839`). The open-ocean entrances use **enter** instead: OPEN_S `FISHERMAN` r 615, `WRACK` r 115, OPEN_NW `GAUNTLET` r 415 and so on; GAUNTLET's own exit is a leave-type one (r 820). 17 area triggers in 6 GDWs.

**Models from other levels (2026-10-04):** `mat_<n>` resolves against the base level's own texture numbers (FISH), which collide with other levels' (WRACK 205 = ship hull, FISH 205 = shop front: an imported WRACK wreck got FISH's shop front). `blender_export_scene.py` now treats a `mat_<n>` material whose image path is `textures/<LEVEL>/…` with LEVEL ≠ `BASE_LEVEL` ('FISH') as an image material, so the image is embedded as a new `GTEX`/`GMAT` (verified: byte-identical WRACK image, palette `mat_272`/`mat_209` still map to FISH GMATs 838/830).

**Exit zones from Blender:** an object in `JAWS` with custom property `jaws_exit` = 1 (Empty: radius = display size × largest X/Y scale; mesh: half its largest X/Y size) becomes an exit zone instead of geometry. `build_scene.py` rebuilds the base's leave-type exit as the first zone (buoys dropped, moved, radius set, action list moved from leave to enter) and copies its `PRPS` for further zones (new IDs, same enter list, no `ACTN`s). User-confirmed in-game 2026-10-04 (both test zones exit). `build_scene.py --show-exits` adds a see-through, non-solid marker column per zone (user-confirmed) in the exit object's material colour (exporter `colour`: Principled Base Color/Alpha, else Viewport Display; default pink).

## Level scripting (`GDControl`)

A level's scripted events (cutscene steps, effects spawning, objects being killed, hidden or shown, barriers opening, checkpoint clean-up) are `GDControl` actions: `ACTN` blocks attached to nodes, each a timeline of up to 8 steps that act on lists of node or action IDs. Format, opcode and scope tables: `docs/exe_analysis.md` "`GDControl`". Read any level's scripting with `python3 scripts/dump_gdcontrol.py GAME_GDWs/<NAME>.GDW [REGEX]`.

- **Hiding without moving:** `m_nFlags` (`PROP 0x080017D9`) bit `0x100` = not rendered (that's how the invisible `Kizaro_Lap_Kozepes` blockers work). Untested as a static BRTR edit; the "move 50,000 down" method is what's been verified.
- **Removing a node that scripts point at** is safe: the interpreter skips IDs that don't resolve, and shipped levels already contain 9 to 72 such dangling IDs each.

## Scripted triggers — working (2026-10-03, user-confirmed)

**Breaking a chosen object makes other objects disappear (visibility and collision).** Tool: **`scripts/add_trigger.py BASE.GDW OUT.GDW`**, configured in its `CONFIG` block. Verified in-game: biting the pink trigger post leaves the target alone; breaking it removes the target and its collision.

### What it builds

1. **Trigger:** a copy of a breakable subtree (default FISH's pier post `Torheto_pozna 1`, node 130: a group root with a destructible `MBRombolhato` `ACTN` and three mesh parts with bite targets), with fresh IDs for every node/action and the internal references remapped (`PROP 0x080018CB` mesh → destructible, `0x08000D05` bite target → mesh). It's placed **directly** (root transform set, every AABB mapped along); with `replace_ref` it takes an existing reference copy's spot and parks that reference 50,000 units below. Optional scale and tint (`m_ModelColor` on every mesh, which does show in-game).
2. **Targets:** new nodes (template with a `PRIM` + mesh + collision region + position + tint, same machinery as `insert_brtr_node.py`) and/or existing node IDs.
3. **Control:** a `GDControl` copied from START's `SeaSeekerQuestEventControl` with, by default, one step, **suspend** `0x4B000400`, on the targets, at delay −1. Steps can be limited to specific targets. Tested one step per target (user-confirmed): suspend, hide `0x8F000100` and clearing `0x10`/`0x40` (`0x4F000040`) each make a target invisible and non-solid; kill `0x0F000008` alone makes it invisible but leaves it solid. The first working builds used all four together. It's attached to the **trigger's root node** (after its own `ACTN`, before its children), and the destructible's hook points at it: `m_robbcontrol` (`PROP 0x08000673`, when destroyed) and/or `m_megutcontrol` (`0x0800067C`, on every hit).

### Rules (each one found by a failed test)

- **The control must live on a group-type node** (classes `0x010B10AA` / `0x010AA0A4`). A destructible's hook doesn't start the control definition; the lookup (`0x6C3010`) returns the control's *live instance* (registered object `+0x24`). Plain model nodes (`0x0107402F`, e.g. a rock or our monkey) never get one, so a control placed there is never started (verified by the F12 dump). All 132 shipped hook targets live on group-type nodes.
- **New IDs must be unused and below `0x100000`.** The engine's runtime counter starts there, and file IDs at or above it collide with runtime objects (the object vanishes). The tool allocates from `0xF000`. (`max file ID + 1` also failed at first, but that build had the control on a plain model node, so the low IDs weren't proven bad.)
- **Steps at delay −1 when the trigger deletes itself.** Posts have `m_killparent` = 1: breaking one deletes its root, and the control on it, in the same frame. A control runs delay −1 steps in its start pass and delay 0 on the next tick, which never comes.
- **Hit vs destroyed:** `m_megutcontrol` fires on the first bite; `m_robbcontrol` fires when the post breaks (its durability is `m_maxhitpoint`, 15 for posts; bites break posts in a few hits).

### Target mesh used in the test

The red monkey is Blender's Suzanne: exported as OBJ (triangulated, smart-UV), `obj_to_gmdl.py BASE OUT suzanne.obj --gmat 0xB12 --scale 10 --collision` (→ `GMDL 0xB13`, `MREG 0xB14`), with a plain white texture added first as `GTEX 0xB11` + `GMAT 0xB12` (`gdw_textures.build_gtex` + `clone_gmat(d, 1073, 0xB12, 0xB11)`, appended to `RSRC`), tinted red per node. Any mesh with collision works; set `TARGETS` accordingly.

### How it was debugged (for the record)

About 15 in-game iterations. Visual probes (hide + collision-off steps, delays, an ID test row of differently coloured monkeys) separated "control never starts" from "steps don't work", and **the mod's F12 dump** (`mod/README.md`) settled it by showing the registry: the control was registered with correct data but had no live instance (`+0x24` = 0), while the destructible's runtime held the right hook value. Wrong turns worth not repeating: the "max file ID + 1" collision theory (partly right, not the cause), IDs at `0x100000` (break objects), `m_nFlags` = 2 as "auto-start" (it isn't), and pointing a hook at a shipped plain-node control (`LoadingEffectControl`), which has no live instance either.

## Current live state (2026-10-04)

The custom level is now a reproducible kit (`levels/custom_fish/`, `scripts/make_level_kit.py`, user tutorial `docs/custom_level_tutorial.md`); since 2026-10-04 afternoon `build.sh` installs it as `custom_levels/CUSTOM_FISH.GDW` next to `Jaws.exe`, loaded by the mod's F9 picker (file-open redirect, `mod/src/levels.{h,cpp}`; user-confirmed). No stock file is edited for it any more.

Game install `data/` folder (`~/.steam/debian-installation/steamapps/compatdata/2342933845/pfx/drive_c/Program Files (x86)/Jaws Unleashed/data/`):

| File | Contents |
|---|---|
| `../custom_levels/CUSTOM_FISH.GDW` (+ `.pre_blank`) | **live:** the user's custom level (F9 in-game), built on `FISH_blank_base.GDW` and pruned; `.pre_blank` = the earlier build on the minimal base |
| `../custom_levels/MUSIC_TONES.GDW`, `MUSIC_NONE.GDW`, `MUSIC_FISH.GDW` | 2026-10-04 music tests: user's level with the four test tones (all four tracks user-confirmed; suspense/action needed loud harsh tones to be heard over the calm layer) / silence; stock FISH with the test tones (to try suspense/action) |
| `../custom_levels/BLANK.GDW`, `BLANK_PRUNED.GDW`, `SPAWN_TEST.GDW` | 2026-10-04 tests: blank base, blank base pruned, user's level with a `jaws_spawn` at (75, −10, 75) facing +X (all user-confirmed) |
| `TEST.GDW` | before 2026-10-04 afternoon: the user's custom level (no entrance points at it any more), built by `levels/custom_fish/build.sh` from `custom_fish.blend` on `FISH_minimal_base.GDW` (`strip_level.py --minimal` of stock FISH) |
| `TEST.GDW.trigger_test` | end of 2026-10-03: scripted-trigger test, `add_trigger.py` defaults on `TEST.GDW.pre_insert` + white texture and Suzanne: pink trigger post (×1.3) at (2036, 1.5, −3971), red monkey at (2110, 12, −3960) |
| `TEST.GDW.pre_trigger` | `strip_level.py`(`TEST.GDW.pre_insert`) + the 7-object Blender test scene (2 rock cubes, Suzanne, 4 transparency planes) |
| `TEST.GDW.pre_insert` | copy of FISH with the construction-worker face, rocks tinted magenta, sand cyan (don't use as a base for real levels: its textures are tinted) |
| `TEST.GDW.pre_build` | earlier build: the user's `something.obj` sculpture (×15, generated collision) + wall C |
| `OPEN_S.GDW` (+ `.orig`, `.test_redirect`) | **stock** again (2026-10-04); the old redirected copy (Fisherman's Isle entrance → `TEST`) is `.test_redirect` |
| `FISH.GDW` (+ `.orig`), `DOCKS.GDW` (+ `.orig`) | construction-worker face texture swap only |
| `../d3d8.dll` (+ `.pre_levels`, `.pre_messages`, `.pre_reload`, `.pre_iddump`) | mod with F9 custom level loader, F10 reload, F12 ID dump and message overrides |
| `../../../jaws_messages.txt` (= `C:\jaws_messages.txt`) | message overrides: `CUSTOM_FISH 598` exit prompt (copy kept in `levels/custom_fish/`) |
| `BEACH.GDW`, `BEACHPST.GDW` (+ `.orig`) | stock (restored 2026-10-03); no-boulder versions kept in the project root as `*.open_barrier.GDW` |

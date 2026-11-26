# Level editing

**In short:** levels can be edited and grown:
- moving objects;
- adding new nodes;
- custom meshes, collision, textures and transparency;
- a whole scene from Blender in one command;
- blank base levels, exits and spawn points;
- scripted triggers and longer draw distance.

All of it is user-confirmed in-game. The game re-reads a level file every time you enter the stage, and the mod's F10 reloads it in place.

**Building a level yourself?** Start with the step-by-step tutorial, [`custom_level_tutorial.md`](custom_level_tutorial.md). This file is the technical background.

Related docs: `docs/scene_graph.md` (the node format), `docs/rsrc_formats.md` (meshes, collision), `docs/exe_analysis.md` (engine side).

Rewritten for readability on 2026-11-27. Old version: `docs/archive/brtr_editing_old_2026-11-27.md`.

---

## Contents

1. [Rules at a glance](#1-rules-at-a-glance)
2. [Tools](#2-tools)
3. [Moving existing objects](#3-moving-existing-objects)
4. [New resources and new nodes](#4-new-resources-and-new-nodes)
5. [Custom meshes from OBJ](#5-custom-meshes-from-obj)
6. [Collision for custom meshes](#6-collision-for-custom-meshes)
7. [Blender scene export](#7-blender-scene-export)
8. [Custom textures](#8-custom-textures)
9. [Transparency](#9-transparency)
10. [Blank base level](#10-blank-base-level)
11. [Area triggers and level exits](#11-area-triggers-and-level-exits)
12. [Level scripting and scripted triggers](#12-level-scripting-and-scripted-triggers)
13. [Boat markers (`ANPosition`)](#13-boat-markers-anposition)
14. [Draw distance in a level file](#14-draw-distance-in-a-level-file)
15. [Where things live now](#15-where-things-live-now)
16. [Old mistakes](#16-old-mistakes)

---

## 1. Rules at a glance

| Rule | Why |
|---|---|
| Move an object by patching its transform `0x080017DA` **and** its box `0x080017DF` by the same amount | A stale box causes flickering culling and missing collision |
| Nested nodes: `new_local = parent_M⁻¹ @ (target_world − parent_translation)` | A plain delta only works for top-level nodes. The box still shifts by the plain world delta. |
| New resource IDs = **the next free ID** | One shared ID space per level; `0x7000` was silently ignored |
| New node IDs must be **below `0x100000`** | The engine's runtime IDs start there; higher file IDs make objects vanish |
| Clone a **visibly rendered** node, never a `" 1"` companion | The companions are a hidden render layer |
| New visible nodes: `m_Viewport` `0x20003` | `1` renders only above water |
| Swapping a node's mesh means resizing its baked vertex colours | One float4 per vertex (`0x0800187A`) |
| New group nodes holding actions, or used as markers: `m_nFlags` `0x12` | Without `0x10` the node gets no live object |
| A `GDControl` started by a destructible must sit on a **group-type node** (`0x010B10AA`/`0x010AA0A4`) | Plain model nodes never get a live control |
| To remove an object at runtime: suspend, hide, or clear `0x10`/`0x40` | "Kill" alone leaves it solid |
| Tile anything wider than ~300 units | Very large objects fade out |
| Any edit that grows a chunk must fix `FSIZ`, `SKIP` and the `FDIR` offsets | `scripts/gdw_grow.py` does it |
| Physics objects (e.g. `WhaleCarcass Body`) drop and resettle after any move | Expected: the shipped Y is their hand-placed resting height |

---

## 2. Tools

All in `scripts/`, run from there unless noted.

| Script | Does |
|---|---|
| `../levels/custom_fish/build.sh` | **The custom-level kit:** `.blend` → export → build on `FISH_blank_base.GDW` → prune → install as `custom_levels/<NAME>.GDW` (mod F9). Options `--show-exits`, `--no-deploy`. |
| `blender_export_scene.py` | Runs **in Blender**: exports collection `JAWS` (meshes, transforms, images, blend/culling settings) to `blender_export/` + `manifest.json` |
| `build_scene.py BASE OUT EXPORT_DIR [--deploy NAME] [--show-exits] [--tile N] [--prune] [--music]` | One-command build: textures, materials, meshes (tiled), collision, nodes, exit zones, spawn. Verified. Deploys to `custom_levels/NAME.GDW`. |
| `strip_level.py IN OUT [--minimal\|--blank]` | Blank base level (§10) |
| `prune_level.py IN OUT` | Drop `RSRC` blocks nothing references |
| `make_level_kit.py [--force] [--kit DIR]` | (project root) Creates `levels/custom_fish/`: blank base + starter `.blend` with a material palette and a `jaws_spawn` cone |
| `redirect_stage.py IN OUT FROM TO` | Rewrite a `GDLoad` stage name (same length). Not needed for custom levels since the F9 loader. |
| `gdw_music.py IN OUT none\|DIR` | Replace level music: silence, or four files via ffmpeg (also `build_scene.py --music`, `build.sh MUSIC=`) |
| `dump_messages.py [OUT]` | The exe's 1,000 on-screen messages → `docs/game_messages.txt` |
| `obj_to_gmdl.py IN OUT model.obj [ID] [--gmat --scale --collision]` | One OBJ → `GMDL` (+ `MREG`) in `RSRC` |
| `insert_brtr_node.py IN OUT` | Append node clones (edit `SPECS`) |
| `gdw_textures.py` | Library: `build_gtex`, `clone_gmat`, `find_block` |
| `gdw_grow.py` | Library: `replace_chunk_payload`, `append_to_chunk`, `find_brtr`, `top_chunks` |
| `patch_texture.py` | Same-size texture swap in place |
| `add_trigger.py BASE OUT` | A breakable that removes targets via `GDControl` (§12) |
| `dump_gdcontrol.py LEVEL.GDW [REGEX]` | Print a level's scripting |
| `import_skeleton_blender.py` | In Blender: a skinned, animated model |
| `build_pursuit_test.py [OUT] [--deploy NAME] [--stock-jetski]` | Playable cut *Hot Pursuit* in a copy of MINEMSHA (`docs/cut_content.md` §2) |
| `build_fishball_test.py [OUT] [--deploy NAME]` | Ecco `MLHalRaj` fish schools (`FISHBALL`) |
| `build_ecco_dolphin.py [OUT] [--deploy NAME] [--size S]` | Ecco's dolphin as the player (`DOLPHIN`; `docs/ecco_dolphin_controller.md`) |
| `stage_ecco_sonar.py [--sound WAV]` | Stage sonar assets for the mod's Ecco mode |

---

## 3. Moving existing objects

**Static objects:** patch two properties by the same delta:
- `0x080017DA`, the transform;
- `0x080017DF`, the world box.

With both in sync, the object renders and collides correctly. No `MREG` edit is needed.

**Forgetting the box is the most common mistake.** A stale box causes on-and-off culling *and* missing collision at the new spot, because rendering and collision both use it as a first filter. Shown by an A/B test on a ship hull (`torzs`).

**Physics objects** visibly drop and resettle after an edit, even a purely sideways one. The shipped Y is the exact resting height the designers placed for that spot; gravity or buoyancy corrects anything else. Seen on `WhaleCarcass Body`. Static objects don't drop.

**Nested nodes:** a raw local transform often reads near (0, 0, 0) wherever the node really is. Compose through the parents with `scripts/resolve_brtr_hierarchy.py`. To place a nested node at a world point, invert the parent's 3×3 basis (rule in §1).

**Spawn markers scale what they spawn.** Collectible markers have no mesh; the game spawns the pickup there. Scaling WRACK's `CGO_Necklace` marker 10× (basis only, plus its box) made the necklace 10× larger in-game (2026-08-13). So the spawner reads the full transform, scale included.

---

## 4. New resources and new nodes

### Adding a resource

1. Copy an existing `GMDL` block and patch its mesh ID.
2. Append it to the end of `RSRC`'s payload, just before `BRTR`.
3. Fix `RSRC`'s size, `FSIZ`, `SKIP` (so `FDIR` stays 512-aligned) and the `FDIR` offsets, all by the same delta.
4. Point a node's `PROP 0x08001873` at the new ID. It renders.

**Use the next free ID.** `RSRC` has one shared ID space (FISH: 1,718 blocks, IDs 1–2832). A mesh added as `0x7000` was silently ignored; the same mesh as 2833 rendered. The exact limit isn't known. The node reader masks class IDs with `& 0xFFF`, so a 4,096 cap would fit.

### Adding a node

**Tool:** `scripts/insert_brtr_node.py IN.GDW OUT.GDW` (edit `SPECS` at the top). Each spec:
- copies an existing top-level node;
- gives it the next free node ID;
- sets a new translation, an optional mesh and optional uint32 property overrides;
- recomputes the world box from the mesh's real vertices.

It then appends the node to the main `BRTR` and fixes `BRTR`'s size, `FSIZ`, `SKIP` and every `FDIR` offset, checking each still lands on a `GDED` header.

**Hidden companions.** Every FISH rock and sand tile has a `" 1"` twin (nodes 264–302) at the same spot: a small low-poly mesh with no lighting. Cloning one gives an invisible node.

| Field | Visible node (e.g. 79 `szikla elem34`) | Hidden companion (e.g. 302) |
|---|---|---|
| `m_StaticLights` (`0x08001875`) | `0x1000009` | `0` |
| `m_RenderSetting` (`0x08001876`) | `0x40000800` (walls) / `0x820` (sand) | `0x40000400` / `0x40002400` |
| Vertex colours (`0x0800187A`) | Present | Count 0 |

Node 302's mesh `0x80E` has 12 vertices and 10 triangles; its visible twin (349) uses `0x80B` with 280 triangles.

**The test (TEST.GDW, user-confirmed):**
- A clone of node 79 at (2160, −5, −3650) **renders**.
- A clone of node 302, with the same wall mesh and a correct box, at (2400, −5, −3650), **stays hidden**.
- So the inherited render fields hide it. Which one decides isn't isolated.

**Viewport:**
- With `m_Viewport` = `1` (as on node 79), the clone shows only while the camera is above water.
- Most visible walls use `0x20003` (some `0xE0003` / `0x60001`).
- **`0x20003` renders above and below the water** (user-confirmed 2026-10-03).

**Template rule:** copy a node that's actually visible in-game (static lighting and vertex colours), set `m_Viewport` `0x20003`, and give it a `PRIM` if it should be solid.

### What the exe does

- `0x693180` (`GDLoadGame`) walks the top-level chunks and passes `BRTR`/`SCRT` to the node reader `0x699360`.
- The reader takes a class ID and node ID, reads `PRPS` (`0x692CD0`; aborts with "Missing properties" if `PRPS` isn't first), then loops over sub-chunks:

  | Sub-chunk | Handler | Linked at |
  |---|---|---|
  | `PRIM` | `0x6E1240` | node `+0xD8` |
  | `ACTN` | `0x68ED80` | `+0x2C` |
  | `CHBR` | recursive child | `+0x28` |

- **There's no node count, index or membership list.**
- `0x692C10` registers node IDs in a map. An ID that can't be registered gets a fresh runtime number, so duplicates aren't fatal.

### Collision link (`PRIM`)

- `PRIM` holds class `0x20003002`, a zero ID and a `PRPS` with `PROP 0x080018D8` = `['MREG'][region_id]`.
- 598 in FISH, on ordinary mesh nodes.
- `MREG` is mesh-local: `MREG 0x943`'s root box equals mesh `0x891`'s local extents exactly. So it follows the node.
- **Tested:** an inserted wall without `PRIM` can be swum through. A clone of node 77 (`szikla elem43`), keeping its `PRIM` → `MREG 0x943`, moved to (2300, −5, −3520), **blocks the shark**.

---

## 5. Custom meshes from OBJ

**Tool:** `scripts/obj_to_gmdl.py IN.GDW OUT.GDW model.obj [MESH_ID] [--gmat ID] [--scale S] [--collision]`. It turns an OBJ (a default Blender export, or our extracted OBJs) into a `GMDL` and appends it to `RSRC`. Then place it with `insert_brtr_node.py`.

**First test (user-confirmed):** a generated ring (833 vertices, 1,536 triangles, GMAT 1073) rendered textured at (2160, 10, −3650).

### The format written

The minimal layout used by 42 shipped FISH meshes:

```
GMDL [id][1][0x0131F505]
  MATR  [1] + identity 4×3
  MATS
  TSET
  TANG  [tri_count] VIND
  VERT  [vert_count] POSI NORM UVUV
```

- `TNOR`, `TFLG` and `VCOL` are optional and left out (except for collision, §6).
- `0x0131F505` = 20051205, a date stamp on every shipped `GMDL`. `RSRC`'s is `0x0131F508` (20051208).
- **Padding rule:** nested chunks are 4-byte padded between siblings, but a container's size **excludes** the padding after its last child. With that, rebuilding every minimal-layout mesh gives identical bytes: 42/42 FISH, 90/90 OPEN_S.

### Conventions

- **Submeshes:** `VIND` indices are absolute. Each `TSET` submesh owns its own contiguous vertex block.
- **OBJ:** z and normal z negated, v flipped, face order kept (the inverse of `rip_meshes.py`). Round-tripping mesh `0x891` returns the same 280 triangles in the same order and winding.
- Polygons are fan-triangulated. Missing normals get face normals.
- **Materials by `usemtl` name:**
  - `gmat_<id>` = that GMAT;
  - `mat_<texture id>` = the first GMAT whose base texture matches. Several can share a texture (837/1070/1073 all use 193), so `gmat_` is safer;
  - otherwise `--gmat`.
- **Baked vertex colours** hold one RGBA float4 per mesh vertex (node 79: 176 = mesh `0x891`'s count). On a mesh swap, `insert_brtr_node.py` regenerates them at the new count, using the source node's average colour.

### Step by step: Blender model → in-game object

Run from `scripts/`.

1. **Model in Blender.** Export with File → Export → Wavefront (.obj) at default settings (forward −Z, up Y; normals and UVs on). Several objects in one file merge into one game mesh.
2. **Materials are optional.** Each material becomes one submesh, chosen by name (`gmat_<id>` or `mat_<texture id>`). Otherwise pass `--gmat <id>` (FISH rock wall: `1073`).
3. **UV-unwrap** if the texture should show. Without UVs, the object is one flat colour.
4. **Scale:** Blender's 1-unit objects are tiny in-game (the FISH wall mesh is ~70 across). `--scale 20` turned a 2.5 × 3.2 model into 50 × 64.
5. **Shading:** flat shading splits vertices per face (651 OBJ vertices → 2,672). Harmless below the 65,535-vertex limit. Shade Smooth gives fewer vertices.
6. **Convert:**
   ```bash
   python3 obj_to_gmdl.py IN.GDW STEP1.GDW model.obj --gmat 1073 --scale 20
   ```
   It prints the mesh ID used, e.g. `0xb11`.
7. **Place:** add to `SPECS` in `insert_brtr_node.py`: `(79, (x, y, z), <mesh id>, {0x080017DD: 0x20003})`. The OBJ's origin lands at (x, y, z).
   ```bash
   python3 insert_brtr_node.py STEP1.GDW OUT.GDW
   ```
8. **Deploy** and re-enter the level.

**Always build from a clean base.** Re-running on an edited file adds a second copy and picks a different free ID.

**For collision:** add `--collision` and place with template node 77: `(77, (x, y, z), 0xB11, {'prim_region': 0xB12})`.

---

## 6. Collision for custom meshes

**User-confirmed in-game:** the user's model, ×15, with a generated collision region blocks the shark. Built with `obj_to_gmdl.py ... --gmat 1073 --scale 15 --collision` → mesh `0xB11` + `MREG 0xB12`.

### `MREG` layout

Checked against all 123 FISH `MREG`s:

```
[region_id][1]['GMDL'][mesh_id][0xFFFFFFFF]
PERF  0.25
BREG  n = 2L − 1 boxes, heap order
STRI  a permutation of the mesh's triangle indices
```

- `L = max(1, ⌊tris ÷ 4⌋)` leaves.
- Leaves, in in-order traversal, each own 4 consecutive `STRI` entries.
- Internal boxes = union of their children. All boxes mesh-local.
- **Leftover triangles** (count not a multiple of 4) go into one leaf whose position can't be pinned down. So the generator pads the mesh to a multiple of 4 by repeating its last triangles; they draw on top of themselves.

### Mesh side

- 122 of 123 collision meshes carry `TNOR` and `TFLG`, so `--collision` writes both.
- `TNOR` = −normalize((B−A) × (C−A)) in game space. Matches all 46,153 shipped triangles.
- `TFLG` = `[1][0x47][0]`: all edge bits set.

### Checks

- Rebuilding mesh `0x891` and its region gives an `MREG` of the same size (4,512 bytes) and identical header to the shipped `0x943`.
- The tree passes every rule (permutation, 70/70 leaf boxes, 69/69 unions).
- It's ~26 % tighter in total leaf volume, thanks to a median split on the longest axis.

### Engine side

- The loader `0x6E3CB0` (vtable `0x7F79A0`) copies `PERF`/`BREG`/`STRI` into memory only when the header's flags field is negative.
- It stores no leaf ranges, so the query code must use the same 4-per-leaf rule. The query code isn't located.

---

## 7. Blender scene export

**In short:** put objects in a Blender collection named `JAWS`, run the exporter in Blender, then `build_scene.py`. Positions, rotations and collision come out right.

**User-confirmed:** a test scene (a rotated 1×1×2 cube, a linked duplicate, a tilted Suzanne with collision off) appeared correctly. Both cubes were solid; Suzanne could be swum through. Rotation was re-checked with a 30°/60° tilt, and the tilted cube blocks along its slanted faces.

### How to use it

1. **Collection:** put the objects in `JAWS` (if there is none, the selected objects are exported).
   - Blender's origin maps to `GAME_ORIGIN`, now (0, −25, 0). It used to be FISH's (2160, −25, −3650); old `.blend`s keep their layout.
   - 1 Blender unit = `GAME_SCALE` (15) game units.
   - Blender Z (up) becomes game Y.
2. **Custom properties** (optional, per object):

   | Property | Meaning |
   |---|---|
   | `jaws_collision` = 0 | Not solid (default: solid) |
   | `jaws_gmat` | Game material for faces whose material isn't `gmat_<id>`/`mat_<id>` (default 1073) |
   | `jaws_exit` = 1 | An exit zone, not geometry (§11) |
   | `jaws_spawn` = 1 | The shark's spawn point (§10) |

3. **Export:** open `scripts/blender_export_scene.py` in Blender's Text Editor and Run Script, or `blender -b file.blend --python scripts/blender_export_scene.py`. Output goes to `blender_export/` next to the `.blend` (`~/blender_export` if unsaved).
4. **Build** from `scripts/`:
   ```bash
   python3 build_scene.py <base>.GDW /tmp/out.GDW <path to blender_export> --deploy NAME
   ```
5. **In-game:** F9 (custom level) or F10 (reload).

### The exporter (`blender_export_scene.py`, Blender 4.0+)

- Exports meshes with modifiers applied, triangulated (`loop_triangles`), with per-corner normals and the active UV map. One `usemtl` group per material slot.
- **Scale is baked into the mesh** (normals use the inverse-transpose), so the node carries only rotation and translation, and collision is built at final size.
- Linked duplicates without modifiers and with equal scale share one mesh.
- **Transform:** game = C · blender, with C = swap Y/Z (as in `scenes/import_fish_blender.py`).
  - Node basis = C·R·C.
  - Translation = origin + scale · C · location.
- OBJ output uses (x, z, −y), so `obj_to_gmdl.py`'s conversion applies unchanged.
- Blender 4.0 quirk: `mesh.corner_normals` exists but stays empty, so it falls back to `calc_normals_split()`.

### The builder (`build_scene.py`)

1. Converts every unique mesh, plus an `MREG` if any object using it is solid.
2. Assigns consecutive next-free IDs and appends everything to `RSRC` at once.
3. Appends one `BRTR` node per object:
   - solid → clone of **node 77** (has a `PRIM`, viewport `0x20003`), with the `PRIM` pointed at the new `MREG`;
   - not solid → clone of **node 79**, viewport set to `0x20003`.
   - Templates are taken from stock `GAME_GDWs/FISH.GDW` (`--templates` to override), so a stripped base works.
4. Sets the full transform, the box from the mesh, and resized vertex colours.
5. Verifies the `RSRC`/`BRTR` chains and `FSIZ`/`SKIP`/`FDIR`. `--deploy NAME` installs it.

**Checks (headless Blender 4.0.2):** each node's world box equals Blender's world vertex bounds mapped to game space, within 0.0001. Winding agrees with vertex normals on 12/12 (cube) and 968/968 (Suzanne) triangles.

### Large objects fade out; the build tiles them

- **Seen (2026-10-04):** a single 1,500 × 1,500 floor slowly faded out when the shark looked away and faded back when it looked at it. Its box was correct, so this isn't stale-box culling.
- **Fix:** cut into 8×8 tiles (~190 units each, origin at each tile's centre), the fading stopped (user-confirmed).
- Shipped terrain is tiled the same way (FISH `Homokos_PartSzakasz_*`).
- The engine's exact test (pivot, bounding sphere or distance) isn't traced.
- **`build_scene.py` tiles automatically:** any mesh wider than 300 units on an axis is cut, by triangle centroid, into cells of at most 200. Each cell is its own `GMDL`/`MREG`/node, re-centred. `--tile 0` = off.
- Checked: the 64 tiles' boxes add up exactly to the one-piece floor's box, also when rotated 30°.
- It also lifts the 65,535-vertex limit for big terrain.

### Models from other levels

- `mat_<n>` resolves against the base level's own texture IDs (FISH), which collide with other levels'. WRACK 205 is a ship hull, FISH 205 a shop front, so an imported wreck got a shop front.
- **Fix:** a `mat_<n>` whose image path is `textures/<LEVEL>/…` with LEVEL ≠ FISH is embedded as a new texture instead.
- Materials named `mat_<id>.001` (Blender duplicates) map to `mat_<id>`.

### Limits

- Mirrored objects (negative scale) aren't handled specially.
- One mesh holds at most 65,535 vertices (tiling helps).

---

## 8. Custom textures

**In short:** images on Blender materials become new `GTEX` blocks plus a new `GMAT` cloned from FISH's rock material.

**User-confirmed:** two test images (made with PIL, not game assets) showed correctly: one packed into the `.blend`, one linked from disk and resized to 256×256.

### Texture block (`GTEX`, plain variant)

Every texture is a `GTEX` chunk ("GTEXT" is `GTEX` + the size byte `0x54`). Two variants exist: plain (258 of 321 in FISH) and one with an `OBPR` block (63). New textures use plain:

```
GTEX [size]
  [tex_id][flags = 1][stamp = 0x0131F253][0][width][height][bpp = 24 | 32]
  TGAN [tgan_size]
    [tgan_size − 4]
    18-byte TGA header: idlen 0, cmap 0, type 2, cmap spec 0, origin 0,0, width, height, bpp, descriptor (0 for 24-bit, 8 for 32-bit)
    pixels: bottom-up rows, BGR (24) or BGRA (32)
    26-byte TGA 2.0 footer: 8 zero bytes + "TRUEVISION-XFILE.\0"
```

**Survey of the 258 plain FISH textures:**
- Stamp and flags constant.
- 134 are 24-bit, 124 are 32-bit.
- 246 have the standard footer.
- `TGAN`'s second field is always size − 4; nothing follows `TGAN`.
- Nearly all sizes are powers of two, so the generator resizes to the nearest one (max 1024).

**Check:** `build_gtex` rebuilds textures 193 (512×512, 24-bit) and 1 (128×128, 32-bit) byte-identically from their PNGs, and 240 of 241 footer-carrying FISH textures.

### Material (`GMAT`)

```
GMAT [size] [gmat_id][flags 0x21] OBPR [0] [stamp] TEXP [n]['GTEX'][tex_id]... REFL BUMP COLS SHIN ...
```

New materials are a byte copy of GMAT 1073 (FISH rock wall: opaque, renders above and below water) with the ID and first `TEXP` entry changed (`clone_gmat`). So custom textures share 1073's lighting, shininess and transparency.

### The pipeline

- **The exporter** finds each material's image (the Image Texture node feeding Base Color, else any image node).
  - Images on disk are copied as they are. Packed or generated ones are saved as PNG.
  - Each textured material gets a `usemtl` token `bmat_NNN` (so names with spaces work) and a manifest entry.
  - Exported test images were pixel-identical to the originals.
- **The builder** creates one `GTEX` per unique image and one `GMAT` per textured material, before the meshes.

**Limits:** only the base texture is set (no extra `TEXP` layers). Max side 1024.

---

## 9. Transparency

**In short:** 32-bit texture alpha makes pixels see-through. The node's render settings choose smooth blend or hard cut-out. The material's `TWOS` alone decides whether back faces show.

**User-confirmed** with four labelled planes: 1 Alpha Blend, 2 Alpha Clip, 3 Blend + Backface Culling, 4 Clip + Backface Culling. 1 and 3 fade smoothly, 2 and 4 cut hard; 1 and 2 show from behind, 3 and 4 don't.

### What controls what

| Effect | Controlled by | Values |
|---|---|---|
| See-through pixels | **32-bit texture alpha** alone | Works on any node or material, even opaque 1073 |
| Smooth blend vs hard cut-out | **Node render settings** | Normal (`m_RenderSetting` `0x40000800`) = blend. FISH seaweed's `m_RenderSetting` `0x80000920` + `m_StaticLights` `0x81000021` = cut-out. |
| Back faces | **Material `TWOS`** only | GMAT 668 (seaweed, `TWOS` 1) shows them; 1073 (`TWOS` 0) culls them |

**Where these came from:**
- FISH's seaweed and plants (`NA hinar`, `NA kisnad`, 73 nodes, in "Tile" groups, viewport `0x2`) use 32-bit textures, GMATs 668/727 and the settings above.
- The sand-blend overlays (`interalph`, `Homokos_Alpha`) are different: 24-bit textures, `m_RenderSetting` `0x200820`, `m_StaticLights` `0x81000001`, `TIAS` 50000 / `BIAS` 1.0. Their fade probably comes from vertex-colour alpha.

### Mapping in the pipeline

The exporter records each material's Blend Mode (`blend_method`; Blender 4.2+ `surface_render_method`) and `use_backface_culling`.

| Blender material | Texture | GMAT clone | Node |
|---|---|---|---|
| Opaque | 24-bit (alpha dropped) | 1073 (one-sided; Blender's culling-off default is ignored) | Normal |
| Alpha Blend | 32-bit | 668 if culling off, else 1073 | Normal |
| Alpha Clip / Hashed | 32-bit | 668 if culling off, else 1073 | + `0x08001876` = `0x80000920`, `0x08001875` = `0x81000021` |

The cut-out setting is per node: if any material on the object is Clip, the whole node gets it.

### Caveats

- Blended surfaces aren't sorted. Overlapping blended objects may draw in the wrong order.
- Lighting and colour come from the template material (668 or 1073), so transparent and opaque versions of one image can differ slightly in brightness.

---

## 10. Blank base level

**In short:** `strip_level.py` removes a level's scenery and keeps the gameplay layer. `--blank` makes the kit's base: no leftovers, centred on the origin, no exit.

**Usage:**

```bash
cd scripts
python3 strip_level.py <FISH>.GDW /tmp/blank.GDW [--minimal | --blank]
python3 build_scene.py /tmp/blank.GDW /tmp/out.GDW <path to blender_export> --deploy NAME
```

### Default mode (user-confirmed 2026-10-03)

The level loads normally with no scenery. Left: shark and HUD, NPCs and animals, the SC17 setup (whale, buoy, sharks), water, sky, sun, and the exit.

**Removed in FISH** (809 top-level nodes, 1,297 with children; `BRTR` 5.46 → 1.81 MB):
- classes `0x0107402F` (plain models: rocks, sand, piers, houses, props; 648), `0x0106F06E` (flora: 143) and `0x01072071` (2);
- the `Tiles` group: 173 seafloor and flora meshes (`ope` clusters, plants, corals, `feny` light shafts);
- the scenery templates `molo`, `Torheto_pozna 1`, `Kis_Halaszhajo`, and every reference copying them (12 + 7 + 3).

**Kept:** the other ~283 top-level nodes are gameplay or engine: cameras (`0x01023020`), lights (`0x0101F01D`), fog (`0x0102001F`), water (`0x01042040`), sounds (`0x0100D00C`), HUD, weapons (`0x010B80B7`), AI waypoints, missions, effects, creature and NPC templates, the exit (`0x01134132`). `RSRC` is untouched.

**Must be kept, and why:**
- **`NEW_SKY_OPEN`** (sky dome): kept by name.
- **`Sun`** (3569): **`NAWater2004 Hiwave`'s `PROP 0x08001376` points at it.** Without it the water surface stops rendering (the shark can still swim and breach). Found by bisection.
- So the tool protects anything a kept node points at through `ID_PROPS`:
  - `0x080017F0` reference;
  - `0x08000AE5`/`AE6` whale and shark links;
  - `0x080004A1` collectible template;
  - `0x080003C7` `SharkWorld.m_teleportlist`;
  - `0x08001376` water sun.

### `--minimal`

Also removes the visible gameplay layer:
- NPCs (`0x01085081`), waypoints (`0x010C80C7`), the bird flock (`0x01096095`), fish schools (`0x01078077`);
- the SC17 mission root and sharks (`0x01104103`, `0x01094092`);
- the collectible `07 - Treasure Chest` (`0x0112B12A`), the beach sound area (`0x0101B019`);
- by name: `WhaleCarcass MorePrim`, `CrowdAllo`, `CollectableObjects`, `CollectibleAddOn`;
- **creature generators.** Ambient wildlife comes from these, not from the templates: `ACTN` class `0x02129128` (`SeaOtterGenAct`, `BarracudaGenAct`, `MarlinGenAct`, `SwordfishGen`, `MantarayGen`), each on a group node `Parent<X>Gen` (FISH 1795–1803).
  - `PROP 0x08000A78` = creature template (e.g. `Marlin Root` 22836);
  - `0x08000A79` = count;
  - `0x08000A82` = area box (6 floats).
  - The first minimal build kept them, and marlins and rays still spawned.

FISH: 842 top-level nodes removed (1,400 with children), 232 left. Kept: water, sun, sky, cameras, fog, lights, HUD, effects, sound definitions, weapons, creature templates, `GameState`/`Stage Completed Save`, the exit.

### `--blank` (user-confirmed 2026-10-04)

Implies `--minimal`. It's the kit's base, `levels/custom_fish/FISH_blank_base.GDW`.

- **Removes leftovers:**
  - `tores`, `horgaszszek` (fishing chair);
  - `Floater1_Brown`/`Floater2_Brown` (the wood seen at FISH's origin);
  - the buoy template `BolyaDefOpen` and the exit's 72-buoy ring;
  - ~30 ship/boat effect nodes (names containing `ship`, plus `hajo_csavar_bubu`, `ANXploGen 1_dc`, `boat_crash`, `cuttergun_shot`).
  - A leftover stays if a kept node or action points into its subtree (ignoring IDs below 1000, which collide with sizes and counts). So `SplashEffectDown_ship`, `Debris_metal_ships` and `ship_hit_blood` stay; `Grenade 4_cut` uses them.
  - FISH: 885 top-level nodes removed (1,523 with children), 189 left.
- **Recentres on the origin:** `SHARRRK` (the shark) moves to (0, −6.5, 0). `SharkPosReal`, `NEW_SKY_OPEN`, `Sun`, `Sun(Y)` and `OceanMap1` (minimap anchor) move by the same (−1998.3, 0, +3628.0). Water, cameras, fog and lights follow the shark.
- **Disables the stock exit:** the leave-list moves to enter, radius 0, parked at x = z = 100,000. Teleporting anywhere gives no prompt (user-tested).
- **Spawn from Blender:** `jaws_spawn` = 1 on an object → `build_scene.set_spawn` rewrites `SHARRRK`'s and `SharkPosReal`'s transforms.
  - Yaw only. The shark faces its local +Z; basis X = (fz, 0, −fx).
  - Their subtrees' boxes and absolute-flag children move along.
  - User-tested: spawn at (75, −10, 75) facing +X.

### Pruning unused resources

**`prune_level.py`** (also `build_scene.py --prune`, used by `build.sh`):
1. Keeps every `RSRC` block reachable from typed references (`['GMDL'][id]`, `['GTEX'][id]`, `['GSFX'][id]`, …) in the main `BRTR`/`SCRT`.
2. Follows references inside kept blocks: mesh → `MATS` → `GMAT` → `TEXP` → `GTEX`, `GSFX` → `GSMP`, …
3. Drops the rest and checks every reference still resolves.

- `RSRC`'s 12-byte header is a constant stamp (`0x0131F508, 1, 0`), with no count.
- **Sizes:** blank base 127.4 → 105.6 MB; the user's level 130.8 → 109.9 MB. Both user-tested.
- **What's left** is mostly needed: level music `SndMusic` 41 MB, pause menu art 18.5 MB, fonts/HUD ~5 MB, civilian rig 4 MB, shark 4 MB.
- The 14 MB loading-screen sub-archive (`FISH00`) is separate and untouched.

### Class IDs name their class

A node or action class ID's **low 12 bits index the level's `CLAS` name lists**: `BRCM` for nodes (`0x01…`; 311 names in FISH), `ACCM` for actions (`0x02…`). Each list is `[uint32 count]` then `[uint32 len][name, 4-aligned]`.

| Class ID | Name |
|---|---|
| `0x0107402F` | `GDModel` |
| `0x0106F06E` | `NAGarden` (flora) |
| `0x01134132` | `ANSphereCheck` (area trigger) |
| `0x0203B039` | `GDControl` |
| `0x02038036` | `GDLoad` |
| `0x0217B17A` | `MBLoadChecker` |
| `0x02129128` | `MSHHSharkGen` (creature generator) |
| `0x02092091` | `Stage0Quest` |
| `0x02173172` | `StreamPlay` |
| `0x0218F18E` | `MBMovieJelzo` |

### Limits

- `SCENERY_GROUPS`, `SCENERY_TEMPLATES` and `KEEP_NAMES` are FISH names. Other levels need their own lists (the class rule and reference protection are generic).
- The ocean floor is gone, so the shark can dive to the engine's depth limit. Build a floor in Blender.

---

## 11. Area triggers and level exits

**In short:** a level's exit and the open-ocean entrances are area triggers (class `0x01134132`). They start a prompt, then a loading effect, then a `GDLoad` action that names the stage file.

**Fields** (consecutive from `0x0800028D`), with FISH's exit `OPEN_S` (1551) as the example:

| PROP | Field | FISH exit |
|---|---|---|
| `0x0800028D` | `m_type` | 1 = vertical column (2 = uses `m_top`/`m_bottom`, DEEPSEA rooms) |
| `0x0800028E` | `m_target` | 26116 `SHARRRK` (the shark) |
| `0x0800028F` | `m_radius` | 795.0 |
| `0x08000290` | `m_enter_act` | empty (`[0]`) |
| `0x08000291` | `m_leave_act` | `[1, 1552]` |
| `0x08000292` | `m_rate` | 10 |
| `0x08000293`/`94` | `m_top`/`m_bottom` | 0 / 0 |
| `0x08000295`/`96` | `m_color1`/`m_color2` | 1 / 9 |

**FISH's exit fires on leaving the circle.** Its 72 `BolyaReference` children are just the buoy ring.

**The chain:**
1. Action 1552, `OssLoadChecker` (class `0x0217B17A`: `m_type`, `m_stage`, `m_toact` = 1553, `m_toactcancel`), shows the prompt.
2. On accept, control 1553 adds `LoadingPredatorEffect`, then after 90 ticks starts 1554.
3. 1554 is a `GDLoad` action with the stage name `FISH00` (`PROP 0x08001839`).

**The open-ocean entrances fire on enter:** OPEN_S `FISHERMAN` r 615, `WRACK` r 115, OPEN_NW `GAUNTLET` r 415, and so on. GAUNTLET's own exit is leave-type (r 820). 17 area triggers in 6 levels.

### Exit zones from Blender (user-confirmed 2026-10-04)

- An object in `JAWS` with `jaws_exit` = 1 becomes an exit zone:
  - an Empty: radius = display size × largest X/Y scale;
  - a mesh: half its largest X/Y size.
- `build_scene.py` rebuilds the base's leave-type exit as the first zone (buoys dropped, moved, radius set, action list moved from leave to enter). Further zones copy its `PRPS` with new IDs.
- Without any, the base's exit stays (disabled on the blank base, so no exit).
- **`--show-exits`** adds a see-through, non-solid marker column per zone, in the exit object's material colour (default pink).

---

## 12. Level scripting and scripted triggers

### Level scripting (`GDControl`)

A level's scripted events (cutscene steps, effects, objects killed, hidden or shown, barriers opening, checkpoint clean-up) are `GDControl` actions: `ACTN` blocks on nodes, each a timeline of up to 8 steps acting on lists of IDs.

- Format, ops and scope bits: `docs/exe_analysis.md` "`GDControl`".
- Read any level's scripting: `python3 scripts/dump_gdcontrol.py GAME_GDWs/<NAME>.GDW [REGEX]`.
- **Removing a node that scripts point at is safe:** the interpreter skips IDs that don't resolve. Shipped levels already have 9 to 72 such dangling IDs each.
- **Hiding without moving:** `m_nFlags` bit `0x100` = not rendered (how the invisible `Kizaro_Lap_Kozepes` blockers work). Untested as a static edit; moving 50,000 units down is the verified method.

### Scripted triggers (user-confirmed 2026-10-03)

**In short:** breaking a chosen object makes other objects disappear, visibility and collision both. Tool: **`scripts/add_trigger.py BASE.GDW OUT.GDW`**, configured in its `CONFIG` block. In-game: biting the pink trigger post leaves the target alone; breaking it removes the target.

**What it builds:**
1. **A trigger:** a copy of a breakable subtree. Default: FISH's pier post `Torheto_pozna 1` (node 130), a group root with a destructible `MBRombolhato` action and three mesh parts with bite targets.
   - Fresh IDs for every node and action, with internal references remapped (`PROP 0x080018CB` mesh → destructible, `0x08000D05` bite target → mesh).
   - Placed directly, with every box mapped along. With `replace_ref` it takes an existing reference copy's spot and parks that reference 50,000 units below.
   - Optional scale and tint (`m_ModelColor` on every mesh; it shows in-game).
2. **Targets:** new nodes (template with a `PRIM`, mesh, collision, position, tint) and/or existing node IDs.
3. **A control:** a `GDControl` copied from START's `SeaSeekerQuestEventControl`.
   - Default: one step, **suspend** `0x4B000400`, on the targets, at delay −1.
   - It's attached to the **trigger's root node** (after its own `ACTN`, before its children).
   - The destructible's hook points at it: `m_robbcontrol` (`PROP 0x08000673`, when destroyed) and/or `m_megutcontrol` (`0x0800067C`, on every hit).

**Step ops tested, one per target (user-confirmed):**

| Op | Value | Result |
|---|---|---|
| Suspend | `0x4B000400` | Invisible and not solid |
| Hide | `0x8F000100` | Invisible and not solid |
| Clear `0x10`/`0x40` | `0x4F000040` | Invisible and not solid |
| Kill | `0x0F000008` | Invisible, **still solid** |

**Rules, each found by a failed test:**
- **The control must sit on a group-type node** (`0x010B10AA` / `0x010AA0A4`). The hook doesn't start the control definition; the lookup (`0x6C3010`) returns its *live instance* (registered object `+0x24`). Plain model nodes never get one (verified with the F12 dump). All 132 shipped hook targets are on group-type nodes.
- **New IDs must be unused and below `0x100000`.** The tool allocates from `0xF000`.
- **Use delay −1 when the trigger deletes itself.** Posts have `m_killparent` = 1: breaking one deletes its root, and the control with it, in the same frame. Delay −1 steps run in the start pass; delay 0 would wait for a next tick that never comes.
- **Hit vs destroyed:** `m_megutcontrol` fires on the first bite; `m_robbcontrol` when the post breaks (`m_maxhitpoint` 15; a few bites).
- **New group nodes holding actions, or used as markers, need `m_nFlags` `0x10`; use `0x12` like `SHARRRK`** (found 2026-10-10 with Hot Pursuit). Without it `0x6C3010` returns null, the node's actions get no live instance, and it has no position. A copy of MINEMSHA's `NorthBrick` (flags `0x2`) failed all three ways. Details: `docs/exe_analysis.md` "Running it in-game".

**The test target:** Blender's Suzanne, exported as OBJ (triangulated, smart UV), converted with `obj_to_gmdl.py BASE OUT suzanne.obj --gmat 0xB12 --scale 10 --collision` (→ `GMDL 0xB13`, `MREG 0xB14`). A plain white texture was added first as `GTEX 0xB11` + `GMAT 0xB12`, then tinted red per node.

**How it was debugged:**
- About 15 in-game rounds. Visual probes (hide and collision-off steps, delays, a row of differently coloured monkeys with test IDs) separated "the control never starts" from "the steps don't work".
- **The mod's F12 dump settled it:** the control was registered with correct data but had no live instance (`+0x24` = 0), while the destructible held the right hook value.
- Wrong turns not to repeat:
  - the "max file ID + 1" theory (partly right, not the cause);
  - IDs at `0x100000` (they break objects);
  - `m_nFlags` = 2 as "auto-start" (it isn't);
  - pointing a hook at a shipped control on a plain node (`LoadingEffectControl`), which has no live instance either.

Engine side: `docs/exe_analysis.md` "Object registry, live actions and destructibles".

---

## 13. Boat markers (`ANPosition`)

Found while getting *Hot Pursuit*'s jet ski to race (2026-10-11).

**In short:** an `ANPosition` node spawns a boat (a copy of the template in `PROP 0x080017F0`) that drives a `GDPath` route. **The boat is removed once it leaves the marker's box**, so a long route needs a box covering it.

**Fields:** `PROP 0x080001EE` + field index (class descriptor `0x8CBB10`, 98 fields).

| PROP | Field | Meaning |
|---|---|---|
| `0x080001EF` / `F0` | fields 1–2 | The route (a `GDPath` node). The canal sailboats set both. |
| `0x080001FB` / `FC` | `m_chase_proc` / `m_chase_area` | Keep the boat roaming inside an area; 0 for a long route |
| `0x08000212` | `m_speed` | |
| `0x08000214` | `m_customcrew` | Rider reference list |
| `0x08000218` / `19` | `m_turnd` / `m_stopd` | Turn and stop distances |

- **`GDPath`:** points in `PROP 0x080018BC` (`[n][xyz…]`, local to its node); `0x080018BD` = closed loop.
- A boat at the end of an open route keeps going straight.
- Quests list boats by their marker; the lookup follows marker `+0xF4` → the spawned copy.
- Working example: `scripts/build_pursuit_test.py`. Details: `docs/exe_analysis.md` "Getting the jet ski to race".

---

## 14. Draw distance in a level file

**In short:** a longer view is a same-size float edit, with no resizing. Underwater, keep the fog end at 400 or less. The mod's `Shift+F4` does the same at runtime in every level.

**Fields** (the same in every level; user-tested on OPEN_S 2026-10-17):

| Node | Field | PROP | OPEN_S stock | Tested good |
|---|---|---|---|---|
| `SharkCamera` | `m_FarPlane` | `0x08001800` | 600 | 3000 |
| `FogAbove` | Fog colour (r, g, b, a, 0–1) | `0x08001853` | FISH 0.561, 0.694, 0.788, 1 | 0.56, 0, 0.29 worked (2026-11-25) |
| `FogAbove` | `m_FogStart` / `m_FogEnd` | `0x0800184D` / `0x0800184E` | 40 / 1100 | 1000 / 2900 |
| `NAWaterYCamera 1` (`ACTN`) | `m_fogbelowstartPC` / `EndPC` | `0x0800133A` / `0x0800133B` | 30 / 170 | 100 / 400 |
| same | PS2 copies (unused on PC) | `0x0800133C` / `0x0800133D` | 30 / 170 | Changed to match |
| same | `m_fogstartbottom` / `endbottom` | `0x0800133E` / `0x0800133F` | 70 / 170 | 100 / 400 |
| `FogBelow` | `m_FogStart` / `m_FogEnd` | `0x0800184D` / `0x0800184E` | 40 / 80 | 100 / 400 (overridden by the row above) |

**Finding `NAWaterYCamera`:** it's an `ACTN` block, not a node, so `brtr_scene_graph.load_nodes` doesn't see it. Find it by its name PROP (`0x080017C3`, after its field PROPs), or by searching for `PROP 0x08001339` = the `FogBelow` node ID.

**Underwater, the fog end is also the camera far plane** (`docs/rendering_system.md` "Draw distance"). So:
- 300–1200 made the shipwreck flicker, barriers show only up close, and NPCs cull more.
- 800–2500 crashed on load.
- **Keep it at 400 or below.**

**Test levels** (OPEN_S copies, made by a one-off script):

| Level | Camera / above fog / underwater fog |
|---|---|
| `FAR_S` | 3000 / 1000–2900 / 300–1200 |
| `FAR_M` | 1500 / 600–1450 / 300–1200 |
| `FAR_C` | Camera and above-water fog only |
| `FAR_U` | Underwater 300–1200 only |
| `FAR_U4` | Underwater 100–400 only |
| **`FAR_X`** | **3000 / 1000–2900 / 100–400: user-confirmed good** |

The `FAR_*` files were deleted from `edited_levels/` on 2026-11-26; Shift+F4 replaces them. For other levels, find the PROPs by ID as above.

---

## 15. Where things live now

As of the install cleanup (2026-10-04, user-approved), with later changes.

- **No stock file is edited.** The custom level is a reproducible kit (`levels/custom_fish/`, `scripts/make_level_kit.py`, tutorial `docs/custom_level_tutorial.md`). `build.sh` installs it as `custom_levels/CUSTOM_FISH.GDW`, loaded by the mod's F9 picker.
- **The game install** (`…/steamapps/compatdata/2342933845/pfx/drive_c/Program Files (x86)/Jaws Unleashed/`):

  | File | Contents |
  |---|---|
  | `data/*.GDW` | The 20 **stock** levels, identical to `GAME_GDWs/` |
  | `custom_levels/` | `CUSTOM_FISH.GDW` (the user's level) and the other custom levels |
  | `d3d8.dll` | The mod |
  | Mod files | Next to `Jaws.exe` since 2026-11-25 (`jaws_messages.txt`, `jaws_bookmarks.txt`, `jaws_config.txt`, …; `mod/README.md`) |

- **`edited_levels/`** (see its `README.txt`):
  - `FISH_face_swap.GDW` / `DOCKS_face_swap.GDW` (construction-worker face);
  - `TEST_trigger_test.GDW`, the trigger demo: a pink post at (2036, 1.5, −3971) removes the red monkey at (2110, 12, −3960);
  - `FISH_edited_2026-10-01.GDW` / `WRACK_edited_2026-10-01.GDW` (early edit tests);
  - `CUSTOM_FISH_pre_blank.GDW` (the user's level on the old minimal base).
- **Deleted 2026-11-26 (user OK):**
  - `install_archive_2026-10-04/`, which held the old `TEST.GDW*` experiments, test levels and old DLL builds. The pre-mod `d3d8.dll.orig` was kept as `game_binary/d3d8.dll.orig_pre_mod`.
  - The no-boulder BEACH/BEACHPST test files.

---

## 16. Old mistakes

| Old claim | Now |
|---|---|
| Brand-new `CHBR` nodes don't render; maybe a hidden spatial index gates them (July 2026) | All three tests cloned node 302, a hidden companion. Clone a visible node (§4). There's no index. |
| PROP IDs are named by their position in the exe's field registration, with a drift (+0x15 … +0x89) | Superseded 2026-11-25: exact names come from the level's `CLAS` table (`docs/scene_graph.md` §2) |
| 8 nodes named inside top-level `ACTN` blocks must be kept | False positives: those "IDs" were the blocks' own size fields. Only PROP values count now (2026-10-04). |
| `PROP 0x08001051` is a node reference | It's a resource ID that happens to match small node IDs. Small-number "references" are often coincidences; test them. |
| The cut-out node setting also toggles back-face culling | The test panels were numbered while viewed from behind, which reverses the order. Label test images with numbers. |
| `0x080003C7` is a child list | `SharkWorld.m_teleportlist` |

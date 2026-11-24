# Animation System — Jaws Unleashed

*Note: `CLAUDE.md` at the project root is the actively-maintained, current source of truth for this project. This file is an early-project snapshot, spot-corrected below where stale.*

Skeletal animation classes are confirmed in the CLAS reflection database but keyframe data extraction is **not yet achieved**. This document records what is known and what remains unresolved.

---

## Known Classes (from CLAS chunk)

### Skeleton

| Class | Purpose |
|---|---|
| `XBone` | Individual skeleton bone |
| `XSkeletonModel` | Skeleton model — primary skeletal mesh class |
| `XExtendedSkeletonModel` | Extended variant with additional features |
| `NALODSkeleton` | Level-of-detail skeleton (reduces bone count at distance) |
| `MLEnvSkeletonModel` | Environment-attached skeleton |
| `GDSkeletonModel` | Engine-level skeletal model |

### Animation

| Class | Purpose |
|---|---|
| `XAnimation` | Animation clip |
| `XAnimationNames` | Name table mapping animation IDs to string names |
| `XAnimationSet` | Container for multiple animation clips |

### Runtime Binding

| Class | Purpose |
|---|---|
| `NAPredatorModel` | Shark-specific model, uses skeletal system |
| `NAMorphModel` | Morph target animation (vertex-level, not bone-level) |
| `GDMorphAnim` | Morph animation controller |
| `GDMatAnim` | Material animation (UV scrolling, texture swapping) |

---

## Dismemberment Skeleton

The bite system (see `bite_system.md`) references `m_rubberskeletonid` — a replacement skeleton ID that is swapped in when a body part is destroyed. This is the ragdoll / "rubber" skeleton used for dismemberment physics, distinct from the animation skeleton.

---

## Current Status: Fully Decoded and Extracting

~~Skeletal animation has **not** been extracted... the actual keyframe data (bone transforms per frame) has not been located in the RSRC chunk.~~ ~~RESOLVED (2025-06-29): the keyframe data location IS now known... Still not extracted.~~ **FULLY DECODED (2026-07-17):** every open question below is now answered. `SKEL` (skeleton container — **30** in FISH.GDW, not 3,030 as earlier notes claimed; that figure was an accidental doubling) holds a bind-pose mesh (`VERT`/`NORM`), per-vertex bone weights (`WGHT`, decoded), and a recursive bone hierarchy (`BONE` root + `CHLD`/`BROT` children, each carrying a bind-pose `MTOB` transform and its own `ROTS` stream of per-frame unit quaternions). `ANIM` — present only on skeletons with named clips — slices each skeleton's shared quaternion pool into named ranges. Extractor: `scripts/rip_skeletons.py` → `skeletons/<NAME>/skel_<id>.json`, verified against all 30 of FISH.GDW's skeletons (zero false positives, 728/729 sampled quaternions unit-length, all clip frame ranges in-bounds). Full byte-level layout in CLAUDE.md's "Skeletal Animation System" section.

**Blender import done, skinning math solved (2026-10-03).** Corrections to the 2026-07-17 decode, from `Jaws.exe` and checked numerically (frame-0 skinning reproduces every FISH skeleton's shipped `GMDL` mesh to ≤ 1.5e-6):
- `BROT` is the **next sibling**, not a child (`CHLD` is the first child).
- `MTOB` is the **inverse rest matrix**; `TRAN` is the **local translation**; `ROTS` holds **local rotations, transposed** (`local = [R(q)ᵀ | TRAN]`). `world = parent · local`, `skin = world · MTOB`.
- Frame 0 is the pose baked into the `GMDL` mesh; the `VERT` mesh is the rest pose `inverse(MTOB)`.
- The pre-`VERT` blob is per-frame root motion (plus a second running-position track and an optional morph-frame count).
- Human bodies borrow their clips from `GlobalSkeletonAnim` (`SKEL 1770`, 75 clips).
- Importer: `scripts/import_skeleton_blender.py` (armature, textured skinned mesh, one action per clip, root motion). Full details in `CLAUDE.md` "Skeletal Animation System".

**What is known:**
- Skeleton class names are in the CLAS reflection database
- `XBone` and `XSkeletonModel` appear in FISH.GDW at offset `0x06F7B7C0` (note: this offset falls inside the file's second embedded archive's own `CLAS` region — see CLAUDE.md's GDW Archive Format section — so it's just that archive's own full class registry, not a special/unique location)
- BRTR places `XSkeletonModel` instances with transforms (**caveat added 2026-07-16**: nested BRTR node transforms are LOCAL to their parent, not automatically world-space — see CLAUDE.md's Parent-child hierarchy note if resolving a skeleton instance's true world placement)
- Mesh extraction is working — static poses are visible in extracted `.obj` files
- `SKEL`/`BONE`/`WGHT`/`ROTS`/`BROT`/`MTOB`/`CHLD`/`ANIM` are all fully decoded (see CLAUDE.md)

**What is not yet known:**
- Cross-referencing `ANIM` clip names / decoded `SKEL` blocks to the `XAnimation`/`XAnimationSet`/`XAnimationNames` CLAS classes listed below, and to specific `XSkeletonModel` instances placed in `BRTR`
- The undecoded pre-`VERT` blob and `TRAN`'s role (see CLAUDE.md's "Still open" list under Skeletal Animation System)

---

## Notes

- The animation system was inherited from *Ecco the Dolphin: Defender of the Future* (2000), but not unchanged: the `SKEL` format stamp is **20020410** (10 April 2002), the date of its last revision, which added the per-frame running-position track; the loader also checks `> 20001009` for the morph-frame count (corrected 2026-10-21; this used to cite a "June 2003 engine freeze", which is only the container version date, see `docs/GDW_FORMAT.md` "Block format date stamps").
- `NALODSkeleton` confirms the engine has LOD-aware skeletal rendering — low-poly skeletons at distance, full skeleton up close.
- `NAMorphModel` / `GDMorphAnim` suggest facial animation or creature deformation is done via morph targets rather than bones in some cases.

---

## Moved from CLAUDE.md (2026-11-25)

The text below was moved word for word from the root `CLAUDE.md`. It is newer than earlier sections of this file where they disagree.

## Skeletal Animation System — SKEL / BONE / WGHT / ROTS / ANIM

**Fully decoded (2026-07-17).** Each `SKEL` block is one complete skeleton (one per skinned character/creature mesh) — bind-pose reference mesh, per-vertex bone weights, a recursive bone hierarchy, and (if the skeleton has named clips) a shared quaternion keyframe pool sliced by an animation dictionary. **Correction:** earlier docs listed `SKEL` count as 3,030 — the real count is **30** (an accidental doubling of the true figure; it now matches the `BONE`/`WGHT` counts below, all of which describe the same 30 skeletons). `ROTS`/`MTOB`/`CHLD`/`BROT` counts below are likewise per-bone-node totals across all 30 skeletons, not top-level RSRC entries.

**Skinning math solved and Blender import working (2026-10-03).** Several of the 2026-07-17 readings below were wrong; corrected from `Jaws.exe` and verified numerically: skinning each skeleton's `VERT` mesh with frame 0 reproduces its shipped `GMDL` mesh to float precision (≤ 1.5e-6) for **all 30 FISH skeletons**. **All 20 GDWs re-extracted (2026-10-03): 752 skeletons** (`python3 scripts/rip_skeletons.py NAME`); 740 of the 741 with a placed mesh verified the same way. The exception, START `SKEL 2424`, is a 3-vertex animation placeholder sharing its mesh with `SKEL 2430` (which matches). The other 11 have no scene user and are all one rig: a 25-bone, 275-vertex **low-detail scuba diver** (AQUARIUM `SKEL 2547` ↔ unplaced `GMDL 3653` / `AQUARIUM_mesh_0821`, frame-0 match 5.6e-7) in 11 levels, sharing 10 of 11 textures with the placed `NewScuba` diver (839 verts). Either an unused LOD or the older diver `NewScuba` replaced; not determinable from the data.
- **`BROT` = next sibling, `CHLD` = first child** (bone loader `FUN_006F4F00`: `CHLD` → `+0x38` with this bone as parent, `BROT` → `+0x3C` with this bone's parent). The old extractor nested `BROT` as a child.
- **`MTOB` = inverse rest matrix** (mesh → bone space); the bone's rest pose is `inverse(MTOB)`, where the `VERT` mesh lives. **`TRAN` = local translation** relative to the parent. **`ROTS` = local rotation per frame, transposed:** `local = [R(q)ᵀ | TRAN]` with `R` the standard `(x,y,z,w)` matrix.
- `world = parent_world · local`; `skin = world · MTOB`; `v' = Σ wᵢ skinᵢ v` (pose `FUN_006F5600`, skinning `FUN_006F63F0`). **Frame 0 is the pose baked into the `GMDL` render mesh.**
- Bone indices (WGHT) follow the engine order: root, then each bone's sibling chain before its child (`FUN_006F46D0`/`FUN_006F5140`).
- **The pre-`VERT` blob is decoded:** `[u32 version][u32 frame_count][u32 morph_frame_count if version > 0x13130F1][frame_count × vec3 root-motion deltas][frame_count × vec3 running position if version ≥ 0x1317CBA]` (the versions are dates: `0x13130F1` = 20001009, `0x1317CBA` = 20020410, the stamp every shipped skeleton has). Optional `MORF` chunk = vertex-animation frames (none in FISH).
- **Model ↔ skeleton link:** the scene node's `PROP 0x080018FF` = `['SKEL'][id]` next to its `0x08001873` mesh (FISH `GWside` → `SKEL 1766` + `GMDL 1890`).
- **Human bodies have no clips of their own:** the 75 human animations live in `GlobalSkeletonAnim` (`SKEL 1770`, a 51-vertex placeholder); all human rigs share its 24-bone layout.
- **Blender:** `blender -b --python scripts/import_skeleton_blender.py -- --name FISH --skel 1766 [--anim-skel 1770] [--clip NAME] [--save out.blend]` (`--clip` = part of a clip name to make active, added 2026-10-12) (or run in Blender's text editor with `CONFIG`). Builds armature + textured skinned mesh + one action per clip, with optional root motion; Blender's deformation matches the engine math to 3e-6 (checked over 6 shark clips). Bones are unnamed in the data (`bone_00`…). `--anim-name LEVEL` takes `--anim-skel` from another GDW.
- **All animations exported (2026-10-20):** `python3 scripts/export_all_animations.py [--jobs 3] [--only NAME] [--force]` → `animations/<Rig>_<LEVEL>_skel<ID>.blend`, one per distinct rig (grouped by bone count + vertex count + clip names): **150 rigs, 754 clips, 871 MB**, 0 failures. `animations/index.txt`/`index.json` list clips, frame counts and every level/skeleton each rig appears in. 19 clip-only rigs (≥ 24 bones, ≤ 114-vertex placeholder: the human clip sets, movie shark/squid/Shaw rigs) are shown on a real body with the identical bone hierarchy (humans: FISH `MartinWalker` SKEL 1858; the body is recorded in the index). Textures are linked from `textures/`, not packed.

Extractor: `scripts/rip_skeletons.py` (run from project root, set `NAME` to the target GDW stem) → `skeletons/<NAME>/skel_<id>.json` (one file per skeleton: bind mesh, weights, full bone tree with per-bone rotation keyframes, named clips) + `_summary.json`. Verified clean on `FISH.GDW`: 30/30 skeletons parsed with zero false positives; spot-checked 729 quaternions across all skeletons — 728 are unit-length to within 1%, all named-clip frame ranges fall within their skeleton's shared frame-pool bounds.

### Known chunk types

| Tag | Count (FISH) | Description |
|---|---|---|
| `SKEL` | 30 | Skeleton container — one per skinned character/creature mesh, 54 KB–1 MB each |
| `BONE` | 30 | Root bone of each skeleton's hierarchy — a recursive container (see below), not a single leaf |
| `WGHT` | 30 | Per-vertex bone skinning weight table, one per skeleton — fully decoded, see below |
| `VERT`/`NORM` | 30 each | Bind-pose reference mesh (positions + normals) embedded in each `SKEL`, sized to match that skeleton's `WGHT` vertex count |
| `ANIM` | ≤30 (optional per-skeleton) | Named animation-clip dictionary — present only on skeletons with authored clips (e.g. shark: 73 clips; many prop/creature skeletons have 0) |
| `MTOB` | 718 total (one per bone node, all skeletons) | **Inverse rest matrix** (mesh → bone space), 4×3 float32 column-major like PROP `0x080017DA` (corrected 2026-10-03; was read as a local transform) |
| `TRAN` | one per bone node | **Local translation** relative to the parent bone (corrected 2026-10-03), typically `(0, length, 0)` |
| `ROTS` | one per bone node | Per-bone stream of unit quaternions (`x,y,z,w`, 16 bytes each), one frame per shared skeleton-wide frame pool — **this is the actual keyframe animation data** |
| `CHLD` / `BROT` | 548 / 140 total | `CHLD` = first child, **`BROT` = next sibling** (shares the current bone's parent). Same payload grammar as `BONE` (corrected 2026-10-03) |

### WGHT — Vertex Skinning Weights (decoded)

No header — straight array of fixed 32-byte records, one per bind-pose mesh vertex (vertex count comes from the sibling `VERT` block):

```
WGHT [uint32 size]     ← size == vertex_count * 32, no leading count/header field
  per vertex (32 bytes):
    [4 × int32 bone_index]   ← -1 marks an unused influence slot
    [4 × float32 weight]     ← only meaningful where the paired bone_index != -1;
                                the weight slot for an unused (-1) index holds
                                leftover/garbage data (often 1.0) and must be
                                masked out, not summed
```
Verified on FISH.GDW's 40-bone shark skeleton (2,384 verts): masked weights sum to 1.0 for all 2,384 vertices; raw (unmasked) sums are wrong for any vertex with fewer than 4 real influences.

### BONE / CHLD / BROT — Recursive Bone Hierarchy (decoded)

`BONE` is not a single bone leaf — it's the **root of the entire skeleton tree**, and its declared size spans everything from the root bone's own data through every nested child, all the way to the end of the `SKEL` payload. `CHLD` and `BROT` are children using the identical node grammar (interchangeable, no semantic split found — a branching bone with two children just uses one of each tag at that level):

```
BONE | CHLD | BROT  [uint32 size]        ← one bone node
  MTOB [48]   ← inverse rest matrix: 3×3 basis (col-major) + translation
  TRAN [12]   ← local translation relative to the parent bone
  ROTS [N×16] ← N unit quaternions (x,y,z,w), one per frame of this skeleton's
                shared pool (every bone in a skeleton has the same N)
  [CHLD = first child, BROT = next sibling (corrected 2026-10-03), same grammar]
```
Verified on the shark skeleton: 40 `MTOB` nodes total (root + 39 nested), tree depth up to 17, every `ROTS` stream exactly 1,516 frames long (matching the `ANIM` dictionary's frame-pool bounds below), all sampled quaternions unit-length.

### ANIM — Animation Name Dictionary + Frame Ranges (decoded)

Present only on skeletons with named clips (e.g. shark: 73 clips; most creature/prop skeletons: 0, animating only via the bind pose / external drivers). All bones in a skeleton share **one contiguous quaternion pool**; `ANIM` slices it into named clips:

```
ANIM [uint32 size]
  [uint32 clip_count]
  [uint32 name_bytes]                       ← Σ name_len (string bytes incl. NULs, no padding); 345/345 shipped ANIM chunks (2026-10-21)
  clip_count × {
    [uint32 name_len]                       ← includes NUL terminator
    [name_len bytes, NUL-terminated ASCII]  ← padded to 4-byte alignment
  }
  clip_count × [uint32 start_frame]         ← index into the shared ROTS pool
  clip_count × [uint32 end_frame]           ← inclusive
```
Frame 0 of the pool is the shared bind/rest frame and falls outside every named clip (shark's clips start at frame 1). Verified: `end_frame` of the last clip equals the shared pool's final frame index (1,515, for a 1,516-frame pool) on the shark skeleton.

**Confirmed animation names from FISH.GDW's shark skeleton (73 total):** `Shark_GW_BodyBomb2`, `Shark_GW_BodySlam_Left/Right`, `Shark_GW_Devour01/02`, `Shark_GW_NyammogA/B/C/D` + `_nagy`/`_kicsi_*` size variants (`nyammog` = munching/biting motion in Hungarian), `Shark_GW_TailWhip_Left/Right_*`, `Shark_GW_Swallow_A/B/Begin/C/End`, `Shark_GW_Landwalk*`, `Shark_GW_DeathSpinCW_Begin/Spin`, `Shark_GW_ThrowLeftDown/Up`, `Shark_GW_ThrowRightDown/Up`, and more (full list in `skeletons/FISH/skel_01766.json`).

**NPC human animations** (the 75 clips of `GlobalSkeletonAnim`, `SKEL 1770`, shared by all 24-bone human rigs; corrected 2026-10-03): `BeingDevouredLegs_A01/02/03`, `FrightenedRun`, `GetOut`, `GrThrow`, `Harpoon`, `icRun`, `Run2x`, `Walk2x`, `FatWalk2x`, `PanicRun`, `SharkAvoid2x`, `StandCheer3x`, `StandClap4x`

### Still open

- Bone names (none stored; the importer uses `bone_00`…).
- How the engine binds a body to `GlobalSkeletonAnim`'s clips at runtime (the importer just takes rotations from the clip skeleton and `TRAN` from the body's), and the engine's playback rate (importer assumes 30 fps).
- The second per-frame track's exact role and `MORF` vertex animation (not seen in FISH). (The `ANIM` header's second word is solved: total name bytes, see above.)

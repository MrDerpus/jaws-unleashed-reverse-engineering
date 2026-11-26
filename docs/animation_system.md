# Skeletons and animation (`SKEL`)

**In short:** each `SKEL` resource is one complete skinned rig: a rest-pose mesh, per-vertex bone weights, a bone tree, and per-bone rotations for every frame. An optional `ANIM` table cuts the frames into named clips. Everything is decoded and verified.
- Skinning frame 0 reproduces the game's own mesh to float precision.
- All 752 skeletons in the 20 levels are extracted.
- Every clip is exported as a Blender file (150 rigs, 754 clips).

Rewritten for readability on 2026-11-27. Old version: `docs/archive/animation_system_old_2026-11-27.md`.

---

## Contents

1. [Tools and results](#1-tools-and-results)
2. [`SKEL` layout](#2-skel-layout)
3. [The bone tree (`BONE` / `CHLD` / `BROT`)](#3-the-bone-tree-bone--chld--brot)
4. [Skinning math](#4-skinning-math)
5. [Weights (`WGHT`)](#5-weights-wght)
6. [Clips (`ANIM`)](#6-clips-anim)
7. [Clip names](#7-clip-names)
8. [Linking a model to its skeleton](#8-linking-a-model-to-its-skeleton)
9. [Classes](#9-classes)
10. [Still open](#10-still-open)
11. [Old mistakes](#11-old-mistakes)

---

## 1. Tools and results

### Extraction: `scripts/rip_skeletons.py`

```bash
python3 scripts/rip_skeletons.py NAME
```

- Output: `skeletons/<NAME>/skel_<id>.json` (rest mesh, weights, bone tree with per-bone rotations, named clips) plus `_summary.json`.
- **All 20 levels: 752 skeletons** (2026-10-03). FISH has 30.

**Verification:**
- 740 of the 741 skeletons with a placed mesh reproduce that mesh at frame 0 (all 30 FISH ones to ≤ 1.5e-6).
- The exception, START `SKEL 2424`, is a 3-vertex animation placeholder sharing its mesh with `SKEL 2430`, which matches.
- FISH: 728 of 729 sampled quaternions are unit length within 1 %; all clip ranges are in bounds.

**The 11 skeletons with no scene user** are all one rig, a **low-detail scuba diver**:
- 25 bones, 275 vertices; AQUARIUM `SKEL 2547` ↔ the unplaced `GMDL 3653` (`AQUARIUM_mesh_0821`), frame-0 match 5.6e-7.
- In 11 levels. Shares 10 of 11 textures with the placed `NewScuba` diver (839 vertices).
- Either an unused low-detail version or an older diver that `NewScuba` replaced. The data can't tell which.

### Blender import: `scripts/import_skeleton_blender.py`

```bash
blender -b --python scripts/import_skeleton_blender.py -- \
    --name FISH --skel 1766 [--anim-skel 1770] [--anim-name LEVEL] [--clip NAME] [--save out.blend]
```

- Builds an armature, a textured skinned mesh, and one action per clip, with optional root motion.
- `--anim-skel` takes the clips from another skeleton (humans: §8); `--anim-name LEVEL` takes it from another level.
- `--clip` = part of a clip name to make active (added 2026-10-12).
- Can also run from Blender's text editor with `CONFIG`.
- Blender's deformation matches the engine math to 3e-6 (checked over 6 shark clips).
- Bones are unnamed in the data, so they're called `bone_00`, `bone_01`, …

### Every clip: `scripts/export_all_animations.py`

```bash
python3 scripts/export_all_animations.py [--jobs 3] [--only NAME] [--force]
```

- Output: `animations/<Rig>_<LEVEL>_skel<ID>.blend`, one per distinct rig (grouped by bone count, vertex count and clip names).
- **150 rigs, 754 clips, 871 MB, 0 failures** (2026-10-20).
- `animations/index.txt` / `index.json` list clips, frame counts, and every level and skeleton each rig appears in.
- **19 clip-only rigs** (≥ 24 bones on a ≤ 114-vertex placeholder: the human clip sets, the movie shark, squid and Shaw rigs) are shown on a real body with the same bone tree. Humans use FISH `MartinWalker` (`SKEL 1858`); the body used is recorded in the index.
- Textures are linked from `textures/`, not packed.

---

## 2. `SKEL` layout

One `SKEL` per skinned character or creature, 54 KB – 1 MB each.

```
SKEL
  [u32 version]                     20020410 on every shipped skeleton
  [u32 frame_count]
  [u32 morph_frame_count]           only if version > 20001009
  frame_count × vec3                root-motion deltas
  frame_count × vec3                running position, only if version ≥ 20020410
  VERT / NORM                       rest-pose mesh (positions, normals)
  WGHT                              per-vertex weights (§5)
  BONE                              the bone tree (§3)
  ANIM                              named clips, optional (§6)
  MORF                              vertex-animation frames, optional (none in FISH)
```

- The versions are format date stamps: `0x13130F1` = 20001009, `0x1317CBA` = 20020410.
- The rest-pose mesh's vertex count matches `WGHT`'s.

**Dating:**
- The animation system came from *Ecco: Defender*, but `SKEL`'s stamp is 2002-04-10, its last revision. That revision added the running-position track.
- The loader checks `> 20001009` for the morph frame count.
- Skeletons date from *Sentinels* (`docs/gwb_lineage.md`).

---

## 3. The bone tree (`BONE` / `CHLD` / `BROT`)

`BONE` is the **root of the whole tree**, not a single bone. Its size covers every nested bone to the end of the `SKEL`.

```
BONE | CHLD | BROT  [size]       one bone
  MTOB [48]    inverse rest matrix: 3×3 basis (column-major) + translation
  TRAN [12]    local translation relative to the parent
  ROTS [N×16]  N quaternions (x, y, z, w), one per frame
  CHLD         first child (same layout)
  BROT         next sibling (same layout)
```

- **`CHLD` = first child; `BROT` = next sibling** (shares this bone's parent).
- Every bone in a skeleton has the same N.
- `TRAN` is typically `(0, length, 0)`.

**Bone loader `0x6F4F00`:** `CHLD` → `+0x38` with this bone as parent; `BROT` → `+0x3C` with this bone's parent.

**Bone order** (used by `WGHT`): the root, then each bone's sibling chain before its child (`0x6F46D0` / `0x6F5140`).

**FISH totals:** `MTOB` / `ROTS` 718 each (one per bone), `CHLD` 548, `BROT` 140.

**Example:** the shark has 40 bones (root + 39), a tree up to 17 deep, and 1,516 frames per `ROTS`.

---

## 4. Skinning math

Solved 2026-10-03 from `Jaws.exe` and checked numerically.

1. **Local** bone matrix at a frame: `local = [R(q)ᵀ | TRAN]`. `R` is the standard (x, y, z, w) rotation matrix; **note the transpose**.
2. **World:** `world = parent_world · local`.
3. **Skin matrix:** `skin = world · MTOB`.
4. **Vertex:** `v' = Σ wᵢ · skinᵢ · v` over the vertex's bones.

- **`MTOB` is the inverse rest matrix** (mesh → bone space). The rest pose `inverse(MTOB)` is where the `VERT` mesh lives.
- **Frame 0 is the pose baked into the `GMDL` render mesh.**
- Engine: pose `0x6F5600`, skinning `0x6F63F0`. Runtime playback: `docs/exe_analysis.md` §6 "Animation runtime".

---

## 5. Weights (`WGHT`)

No header: one 32-byte record per rest-pose vertex. Size = vertex count × 32.

```
per vertex:
  4 × int32  bone index     −1 = unused slot
  4 × float  weight
```

- **Mask out the weights of unused slots.** They hold leftover data (often 1.0).
- **Evidence:** on the FISH shark (2,384 vertices), masked weights sum to 1.0 for every vertex; unmasked sums are wrong wherever a vertex has fewer than 4 bones.
- Some unused slots hold NaN or Inf: 3,293 in the blank FISH base level. That matters for the text format (`docs/exe_analysis.md` §3).

---

## 6. Clips (`ANIM`)

All bones share **one frame pool**. `ANIM` cuts it into named clips. Only skeletons with authored clips have one; many prop and creature skeletons have none.

```
ANIM [size]
  [u32 clip_count]
  [u32 name_bytes]                    total name bytes, NULs included, padding not
  clip_count × { [u32 name_len] [name, NUL-terminated, padded to 4] }
  clip_count × [u32 start_frame]
  clip_count × [u32 end_frame]        inclusive
```

- `name_bytes` matches all 345 shipped `ANIM` chunks (2026-10-21).
- **Frame 0 is the rest frame** and lies outside every clip; the shark's clips start at 1.
- On the shark, the last clip's end equals the pool's last frame (1,515 of 1,516).

---

## 7. Clip names

**Great white** (FISH `SKEL 1766`, 73 clips; full list in `skeletons/FISH/skel_01766.json`). Examples:

| Clip | Note |
|---|---|
| `Shark_GW_BodyBomb2` | |
| `Shark_GW_BodySlam_Left/Right` | |
| `Shark_GW_Devour01/02` | |
| `Shark_GW_NyammogA/B/C/D`, `_nagy`, `_kicsi_*` | *Nyammog* = munching; *nagy* big, *kicsi* small |
| `Shark_GW_TailWhip_Left/Right_*` | |
| `Shark_GW_Swallow_A/B/Begin/C/End` | |
| `Shark_GW_Landwalk*` | |
| `Shark_GW_DeathSpinCW_Begin/Spin` | |
| `Shark_GW_ThrowLeftDown/Up`, `ThrowRightDown/Up` | |
| `Shark_GW_Pitbull04` | The grab-chew-shake bite (`docs/exe_analysis.md` §6 "Bite animation") |

**Humans** (`GlobalSkeletonAnim`, 75 clips). Examples: `BeingDevouredLegs_A01/02/03`, `FrightenedRun`, `GetOut`, `GrThrow`, `Harpoon`, `icRun`, `Run2x`, `Walk2x`, `FatWalk2x`, `PanicRun`, `SharkAvoid2x`, `StandCheer3x`, `StandClap4x`.

---

## 8. Linking a model to its skeleton

- A scene node's **`PROP 0x080018FF`** = `['SKEL'][id]`, next to its mesh `PROP 0x08001873`. Example: FISH `GWside` → `SKEL 1766` + `GMDL 1890`.
- **Humans have no clips of their own.** All 75 human clips live in `GlobalSkeletonAnim` (FISH `SKEL 1770`, a 51-vertex placeholder). All human rigs share its 24-bone layout.
- The importer takes rotations from the clip skeleton and `TRAN` from the body. How the engine binds them at runtime isn't known.
- **Clips are found by name only**: the shark controller plays any rig whose `ANIM` has the `Shark_GW_*` names (`docs/exe_analysis.md` §6 "Animation runtime").

### The dismemberment skeleton

The bite system's `m_rubberskeletonid` (`docs/bite_system.md`) is a replacement skeleton swapped in when a body part is destroyed. It's the "rubber" ragdoll skeleton, separate from the animation skeleton.

---

## 9. Classes

From the `CLAS` reflection database. Which of these the decoded blocks map to wasn't checked.

**Skeletons:**

| Class | Probably |
|---|---|
| `XBone` | One bone |
| `XSkeletonModel` | Skinned model (the main class) |
| `XExtendedSkeletonModel` | Extended variant |
| `NALODSkeleton` | Level-of-detail skeleton (fewer bones at a distance) |
| `MLEnvSkeletonModel` | Skeleton attached to the environment |
| `GDSkeletonModel` | Engine-level skinned model |

**Animation:**

| Class | Probably |
|---|---|
| `XAnimation` | A clip |
| `XAnimationNames` | Clip name table |
| `XAnimationSet` | A set of clips |
| `NAMorphModel`, `GDMorphAnim` | Vertex (morph) animation, e.g. faces or creature deformation |
| `GDMatAnim` | Material animation (UV scrolling, texture swapping) |

`NAPredatorModel` came in with Defender PS2 (`docs/gwb_lineage.md`). Note that `NAPredator` itself is the predator-vision screen effect, not the shark.

---

## 10. Still open

- **Bone names:** none are stored.
- **Runtime clip binding:** how the engine binds a body to `GlobalSkeletonAnim`'s clips.
- **Playback rate:** the importer assumes 30 fps (the game runs at a fixed ~30).
- **The running-position track:** its exact role.
- **`MORF`** vertex animation: not seen in FISH.
- **Classes ↔ data:** mapping `XAnimation` / `XAnimationSet` / `XAnimationNames` to the decoded blocks and to placed `XSkeletonModel` nodes.

---

## 11. Old mistakes

| Old claim | Now |
|---|---|
| Keyframe data not located / not extracted | Fully decoded 2026-07-17, skinning solved 2026-10-03 |
| FISH has 3,030 `SKEL` blocks | 30 (an accidental doubling) |
| `BROT` is a child bone | The next sibling (2026-10-03) |
| `CHLD` and `BROT` are interchangeable | `CHLD` = first child, `BROT` = next sibling |
| `MTOB` is a local transform / rest pose | The inverse rest matrix (2026-10-03) |
| `ROTS` quaternions are used as-is | Transposed: `local = [R(q)ᵀ \| TRAN]` |
| The data before `VERT` is undecoded | Version, frame counts, root motion, running position (2026-10-03) |
| `TRAN`'s role unknown | Local translation |
| Human clips belong to each human rig | They're shared from `GlobalSkeletonAnim` |
| `ANIM`'s second header word unknown | Total name bytes (2026-10-21) |
| The `SKEL` format dates from a "June 2003 engine freeze" | 20030626 is only the container's `VERS` date; `SKEL` is 2002-04-10 (`docs/GDW_FORMAT.md`) |
| `XBone` at FISH `0x06F7B7C0` is a special location | That's inside an embedded loading-screen sub-archive's own `CLAS`, its normal class list |

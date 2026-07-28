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

**Still not done:** Blender armature/animation import (mesh-only import exists in `scenes/import_fish_blender.py`, no skinning wired in). Still open: an undecoded ~tens-of-KB blob preceding `VERT` in each `SKEL` (possible morph/blendshape data, unconfirmed), and the small per-bone `TRAN` field's exact role (near-zero in every sample checked).

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

- The engine freeze date (June 2003) predates the Jaws license acquisition (August 2004). The animation system was inherited from *Ecco the Dolphin: Defender of the Future* (2000) and carried forward through *Sole Predator* development unchanged.
- `NALODSkeleton` confirms the engine has LOD-aware skeletal rendering — low-poly skeletons at distance, full skeleton up close.
- `NAMorphModel` / `GDMorphAnim` suggest facial animation or creature deformation is done via morph targets rather than bones in some cases.

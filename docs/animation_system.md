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

## Current Status: Located, Not Yet Extracted

~~Skeletal animation has **not** been extracted... the actual keyframe data (bone transforms per frame) has not been located in the RSRC chunk.~~ **RESOLVED (2025-06-29):** the keyframe data location IS now known. `SKEL` (skeleton container, ~1MB each, 3,030 in FISH.GDW), `BONE` (individual bone + rest-pose `MTOB` matrix), `WGHT` (per-vertex bone weights), `ROTS` (rotation keyframe stream), `BROT`/`MTOB`/`CHLD` (bone rotation tracks / transform matrices / child node groupings), and `ANIM` (animation name dictionary — confirmed clip names like `Shark_GW_BodySlam_Left`, `FrightenedRun`, `PanicRun`) are all confirmed chunk types inside `RSRC`, not a separate location. See CLAUDE.md's "Skeletal Animation System" section for the full chunk table and partial structure decode. **Still not extracted** — no SKEL hierarchy parser or Blender armature import has been written yet, so the practical status ("not usable yet") is similar to before, but the *location* question below is resolved.

**What is known:**
- Skeleton class names are in the CLAS reflection database
- `XBone` and `XSkeletonModel` appear in FISH.GDW at offset `0x06F7B7C0` (note: this offset falls inside the file's second embedded archive's own `CLAS` region — see CLAUDE.md's GDW Archive Format section — so it's just that archive's own full class registry, not a special/unique location)
- BRTR places `XSkeletonModel` instances with transforms (**caveat added 2026-07-16**: nested BRTR node transforms are LOCAL to their parent, not automatically world-space — see CLAUDE.md's Parent-child hierarchy note if resolving a skeleton instance's true world placement)
- Mesh extraction is working — static poses are visible in extracted `.obj` files
- `SKEL`/`BONE`/`WGHT`/`ROTS`/`BROT`/`MTOB`/`CHLD`/`ANIM` blocks are confirmed present in `RSRC` (see above)

**What is not yet known:**
- The exact binary layout/traversal order within `SKEL` (partial structure only — see CLAUDE.md)
- How `ROTS`+`CHLD` per-frame keyframe data is organized
- How animation clips (named via `ANIM`) are referenced from skeleton instances
- Whether the animation format is keyframed matrices, quaternion+translation, or a different encoding
- `WGHT`'s exact vertex-weight table format and skeleton hierarchy traversal order (flagged as an open problem in CLAUDE.md)

---

## Notes

- The engine freeze date (June 2003) predates the Jaws license acquisition (August 2004). The animation system was inherited from *Ecco the Dolphin: Defender of the Future* (2000) and carried forward through *Sole Predator* development unchanged.
- `NALODSkeleton` confirms the engine has LOD-aware skeletal rendering — low-poly skeletons at distance, full skeleton up close.
- `NAMorphModel` / `GDMorphAnim` suggest facial animation or creature deformation is done via morph targets rather than bones in some cases.

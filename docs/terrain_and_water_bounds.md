# Level edges and the "endless" ocean

**In short:** when you swim past a level's edge, the ocean seems to go on forever. That's a flat fallback plane drawn by the level's water object (`NAWater2004.m_infinitesurface`), not generated terrain: no geometry, no collision, nothing placed out there.
- Most level edges don't block the shark with walls. They push it back with buoys and currents.
- The extra archives after the end of each level file are loading screens, not terrain tiles.

Related: `docs/water_system.md`, `docs/speedrun_glitches.md` §13, `docs/exe_analysis.md` §14.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/terrain_and_water_bounds_old_2026-11-27.md`.

---

## Contents

1. [The endless ocean: `m_infinitesurface`](#1-the-endless-ocean-m_infinitesurface)
2. [Level edges: push barriers, not walls](#2-level-edges-push-barriers-not-walls)
3. [Not the cause: the mission boundary](#3-not-the-cause-the-mission-boundary)
4. [Dead end: the embedded archives are loading screens](#4-dead-end-the-embedded-archives-are-loading-screens)
5. [Objects at the world origin](#5-objects-at-the-world-origin)
6. [Old mistakes](#6-old-mistakes)

---

## 1. The endless ocean: `m_infinitesurface`

**`NAWater2004`** is the water and wave-surface object. Its fields (from the exe and every level's `CLAS`):

```
m_fresnelpow, m_fresnelthresholdpow
m_detaildistanceabove, m_detaildistancebelow      level-of-detail switch distances
m_rtreedim, m_gridsize, m_maxvertex, m_lodconst   the detail grid
m_infinitesurface                                 on/off
m_freq, m_dampening, m_GridDimensionLog
m_WindDirection, m_WindSpeed, m_WaveHeight, …
```

**Every level places exactly one.** Seen by name: FISH `"NAWater2004 Hiwave"`, START and OPEN_S `"NAWater2004"`.

**How it works:**
- Near the camera, a real but finite wave grid, managed by distance (`m_detaildistanceabove`/`below`, `m_rtreedim`, `m_gridsize`).
- Beyond that range, when `m_infinitesurface` is on, a **flat plane** is drawn so the player never sees an edge.
- It's a cheap visual trick: no geometry, no collision, no props or fish out there. **Not** procedural terrain.

---

## 2. Level edges: push barriers, not walls

Found 2026-11-23.
- Most level edges push the shark back instead of blocking it:
  - **buoy lines:** `ANTol` on the buoy template `BolyaDef`;
  - **currents:** `NAWhirl2000` paths.
- Both show "Current's too strong."
- A strong enough swim can beat them (the vanilla Arrival out-of-bounds).
- Strength per level, the uncapped DOCKS/TOWN/ARMADA buoys and DOCKS's zero-push gaps: `docs/speedrun_glitches.md` §13.
- Engine side: `docs/exe_analysis.md` §14 "Push barriers".

---

## 3. Not the cause: the mission boundary

`m_OutOfBoundID` / `m_BoundaryID` (next to the string `"You have left the mission area.\n"` in the exe) are a separate mission-boundary trigger: a warning or penalty when you leave a mission's area. Unrelated to the endless-ocean plane.

---

## 4. Dead end: the embedded archives are loading screens

**The idea:** every level file has complete extra archives after `ENDF`, each with its own first line and `VERS`/`CLAS`/`RSRC`/`BRTR`. Bounded story levels carry one of ~14.4 MB; OPEN_S carries 11. So maybe they were terrain or water tiles for the open zones.

**Disproven.** One of OPEN_S's archives has a tiny `BRTR` (~6 KB against the main 11.5 MB). Its scene is **a loading screen for a destination level**:
- root `"OPEN_S00"`, child `"LevelLoaderKAT"` (a loader for KATATAMA);
- `"PUSH THE ^CONT^ BUTTON!"`, `"Progress Bar"`, `"Progress Bar Border"`, `"LoaderFog"`, `"LoaderCam"`.

OPEN_S has 11 because it's a hub with many destinations. **Don't re-investigate these as terrain.** Format and `FDIR` index: `docs/GDW_FORMAT.md`.

---

## 5. Objects at the world origin

Both found in-game by the user with the mod's F8 teleport to `0 0 0` (2026-10-01).

### OPEN_S: a starfish

- Node **`Starfish02`**: top level, at **(0.0, 0.0, 0.14)**, mesh `2582` (56 triangles).
- **It's a reference template,** not a deliberate origin marker. Six placed starfish (`starfish 3`, `starfish 4`, `starfish 6`, `starfish1 6`, `starfish1 7`, …) point at it through `PROP 0x080017F0` (`docs/scene_graph.md` §4).
- The artist made the template at the origin, and it renders there as well as at every reference.
- Its sibling template `Starfish01` (referenced 10 times) was made on the seafloor at (−61.3, −27.6, −305.3).
- START also has a `Starfish02` template at the origin, referenced 9 times.
- Either way, it reliably marks (0, 0, 0) in OPEN_S: handy for checking coordinate readouts.

**Other origin objects in OPEN_S:** 195 of its 3,122 placed meshes sit at exactly (0, 0, 0). They're spawn templates (`Atlantic Cod`, `Barracuda`, `BlueWhale Model 1`, `BloodyHead`/`BloodyLeftArm`…, `littlestar` boat pieces) and aren't seen there in-game.

### FISH: a small piece of wood

- The user found a small piece of wood floating at the origin.
- Many FISH objects are at exactly (0, 0, 0), so which one isn't pinned down.
- **Best match: `debris1`** (mesh `2218`, under the top-level `Floater1_Brown`, brown floating debris; nothing references it).
- Other origin objects: `gorbecso` ×4 (*görbe cső* = bent pipe, under `above_explosion_ships`), the buoy template `BolyaDefOpen` (referenced 72 times), the `Civilian` NPC rig, fish (`Hammerhead`, `Barracuda`, `Marlin`, `Swordfish`, `Mantaray`), weapons and props (`harpoon`, `GrenadeModel`, `FreeTheSharkModel`, `CameraDigiCamModel`).

### What this means

- Most objects made at the origin are *not* visible there (no buoy, civilians, fish or weapons at FISH's origin). Some are (this wood, OPEN_S's starfish).
- So whether a template renders at its own position is **per object**, probably a class or flag property, not a general rule.
- Scene exports should keep templates but mark them as templates, so they can be hidden.

---

## 6. Old mistakes

| Old claim | Now |
|---|---|
| The ocean floor is generated forever | A flat fallback plane (§1) |
| The embedded archives are terrain or water tiles | Loading screens for destination levels (§4) |
| `Starfish02` is a level designer's origin marker | A reference template that also renders at its own position (§5) |

# Terrain / Water Bounds — Why the Ocean Floor Seems to Generate Forever

*Note: `CLAUDE.md` at the project root is the actively-maintained, current source of truth for this project. This file was already current as of 2026-07-15; one cross-reference below updated 2026-07-17.*

Investigates why swimming out of a level's authored area shows an ocean floor that appears to continue indefinitely, rather than a void or hard edge.

---

## The Mechanism — `NAWater2004.m_infinitesurface`

`NAWater2004` (see `water_system.md` for the class's place in the water-system version history) is the water/wave-surface object. Its field list, read from both `game_binary/Jaws.exe`'s RTTI string table and every GDW's `CLAS` chunk:

```
m_fresnelpow, m_fresnelthresholdpow
m_detaildistanceabove, m_detaildistancebelow   -- LOD switch distances
m_rtreedim, m_gridsize, m_maxvertex, m_lodconst -- spatial-grid LOD system
m_infinitesurface                               -- boolean flag
m_freq, m_dampening, m_GridDimensionLog
m_WindDirection, m_WindSpeed, m_WaveHeight, ...
```

Every level places exactly **one** `NAWater2004` object in its primary `BRTR` scene graph as that level's global water body — confirmed by name in `FISH.GDW` (`"NAWater2004 Hiwave"`), `START.GDW` (`"NAWater2004"`), and `OPEN_S.GDW` (`"NAWater2004"`).

**Conclusion:** the object has a real, finite, distance-based LOD grid for the actual simulated wave/seafloor mesh near the camera (`m_detaildistanceabove/below`, `m_rtreedim`, `m_gridsize`). Beyond that grid's range, the engine falls back to rendering a flat "infinite surface" plane — gated by `m_infinitesurface` — purely so players never see a void or hard edge at the map boundary. It's a cheap visual fallback: no real geometry, no collision, no props or fish out there. It is **not** procedural terrain generation.

---

## Not the Cause: Mission Boundary System

`m_OutOfBoundID` / `m_BoundaryID` (found next to the string `"You have left the mission area.\n"` in `Jaws.exe`) is a **separate, unrelated mission-boundary trigger** — it fires a warning/penalty when a player leaves a mission's playable radius. It has nothing to do with the infinite-surface rendering trick.

---

## Dead End: Embedded Sub-Archives Are Not Terrain Tiles

Every GDW has a second, complete GDED archive appended after the documented `ENDF` terminator (own preamble, `VERS`/`CLAS`/`RSRC`/`BRTR` chunks) — now documented in `CLAUDE.md`'s GDW Archive Format section (as of 2026-07-17, including the `FDIR` offset-index mechanics that point to it). Initial hypothesis: these were tileable terrain/water sectors for the open-world zones, since the trailing data size scales with how "open" a level is (bounded story levels carry a near-identical ~14.4 MB blob; `OPEN_S.GDW` carries 11 of them).

**Disproven by inspection.** Decoded one of `OPEN_S.GDW`'s embedded sub-archives (`BRTR` size only ~6 KB, versus the primary archive's 11.5 MB) and found its scene graph is a **bundled loading-screen scene** for a connected destination level — e.g. root node `"OPEN_S00"`, child `"LevelLoaderKAT"`, UI objects `"PUSH THE ^CONT^ BUTTON!"`, `"Progress Bar"`, `"Progress Bar Border"`, `"LoaderFog"`, `"LoaderCam"` — a loading/transition screen for `KATATAMA.GDW`. `OPEN_S.GDW` has 11 of these because it's a hub connecting to many destinations, not because it holds 11 terrain tiles.

**Do not re-investigate this as a terrain-tiling system** — it's confirmed to be loading-screen bundling.

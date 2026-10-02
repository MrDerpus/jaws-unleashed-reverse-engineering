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

## Objects at the World Origin — `OPEN_S` Starfish and `FISH` Wood (2026-10-01)

Both observed in-game by the user, using the mod's F8 teleport to `0 0 0`.

### `OPEN_S.GDW`: a starfish

BRTR node **`Starfish02`** is top-level, at world **`(0.0, 0.0, 0.14)`**, with mesh resource `2582` (56 tris per the scene manifest).

**Revised interpretation (same day):** it's almost certainly **not** a deliberate origin marker. `Starfish02` is a **reference template**: 6 placed starfish (`starfish 3`, `starfish 4`, `starfish 6`, `starfish1 6`, `starfish1 7`, …) point at it through the generic reference property `PROP 0x080017F0` (see `CLAUDE.md`, "Reference instancing"). The artist authored the template at the origin, and the template itself happens to render at its authored position as well as at every reference. Its sibling template `Starfish01` (referenced 10×) is authored on the seafloor at `(-61.3, -27.6, -305.3)`. `START.GDW` has a `Starfish02` template at the origin too, referenced 9×. Either way, it does reliably mark `(0, 0, 0)` in OPEN_S, which is handy for checking coordinate readouts.

### `FISH.GDW`: a small bit of wood

The user found **a small piece of wood floating at the world origin**. The FISH BRTR has many objects authored at exactly `(0,0,0)`, so which one it is isn't pinned down. The best match is **`debris1`** (mesh `2218`, under top-level `Floater1_Brown`, i.e. brown floating debris, which no reference node points to). Other origin objects include `gorbecso` ×4 ("görbe cső" = bent pipe, under `above_explosion_ships`), the buoy template `BolyaDefOpen` (referenced 72×), the `Civilian` NPC rig, fish models (`Hammerhead`, `Barracuda`, `Marlin`, `Swordfish`, `Mantaray`), and weapon/projectile models (`harpoon`, `GrenadeModel`, `FreeTheSharkModel`, `CameraDigiCamModel`).

**What this tells us:** most objects authored at the origin are *not* visible there in-game (no buoy, civilians, fish or weapons were reported at FISH's origin), but some are (this wood, OPEN_S's starfish). Whether an origin-authored template renders at its own position is **per-object**, probably a class or flag property, not a general rule. Scene exports should therefore keep templates but mark them as templates, so they can be hidden.

## (Superseded) World Origin Marker — `Starfish02` in `OPEN_S.GDW` (found 2026-10-01)

*Superseded by the section above. Kept for history.*

User found in-game (using the mod's F8 teleport to go to `0 0 0`) that a starfish sits at the exact world origin in `OPEN_S.GDW` (Open Ocean: South). Cross-checked against the extracted scene data:

- BRTR node **`Starfish02`**: top-level (depth 0, no parent, so its stored position is already world space), world position **`(0.0, 0.0, 0.14)`**, its own mesh (OPEN_S mesh resource `2582`, 56 triangles per the scene manifest).
- Its sibling **`Starfish01`** (same 56-tri starfish model, mesh resource `2581`) is placed normally on the seafloor at `(-61.3, -27.6, -305.3)`. Several other starfish groups (`starfish 1`–`8`, `starfish1 4`–`11`) sit nested under `ope2`/`ope2B`/`ope4` seafloor clusters around Y −28 to −38, so this mesh is normal level dressing. Only `Starfish02` is parked at the origin, and at Y ≈ 0 (the water surface) instead of on the seafloor.

**Interpretation:** most likely a level designer's world-origin reference marker, as the user suggests. A lone, visible, otherwise-ordinary prop placed at exactly `(0, 0, ~0)` instead of on the seafloor fits that. **Caveat:** this isn't the only object at the origin. 195 of OPEN_S's 3,122 placed meshes sit at exactly `(0, 0, 0)`, but those are clone templates/prototypes (`Atlantic Cod`, `Barracuda`, `BlueWhale Model 1`, `BloodyHead`/`BloodyLeftArm`… dismemberment parts, `littlestar` boat-piece variants, etc.) that spawners copy at runtime. They're presumably hidden or not rendered at their template position. `Starfish02` differs in two ways: it's a top-level static prop with a nonzero Z (`0.14`), not a spawner template, and it's actually visible in-game. Whether the designers *intended* it as an origin marker can't be proven from data alone, but it does reliably mark the origin, which makes it a handy in-game sanity check for coordinate readouts.

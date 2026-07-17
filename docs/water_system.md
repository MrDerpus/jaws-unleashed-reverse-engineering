# Water System — Jaws Unleashed

The water system is one of the most technically significant parts of the engine — it was the original core technology developed for *Ecco the Dolphin: Defender of the Future* (2000) and evolved through multiple versions into Jaws Unleashed. The class registry preserves the full version history.

---

## Water Class Hierarchy

| Class | Era | Purpose |
|---|---|---|
| `NAWaterGrid2000` | Ecco (2000) | Original water grid system |
| `NAWater2003` | Sole Predator era | Intermediate water update |
| `NAWater2004` | Jaws Unleashed | Primary shipping water system |
| `NASlideWater2004` | Jaws Unleashed | Shallow/sliding water (beaches, canals) |
| `NATextureGeneratorGrid` | Jaws Unleashed | Procedural water texture generation |

The version suffixes (2000, 2003, 2004) are literal year markers, giving a clear timeline of engine evolution. All versions are retained in the class registry, suggesting the engine carries forward old code rather than replacing it — water bodies in different levels may use different class versions.

---

## Terrain

| Class | Purpose |
|---|---|
| `NATerrain` | Terrain system (heightmap-based) |
| `NAGrid` | Grid data (shared infrastructure with water) |

---

## OPEN_ Files — Terrain and Water Data

The three open ocean GDW files (`OPEN_S.GDW`, `OPEN_NE.GDW`, `OPEN_NW.GDW`) are significantly larger than regular levels (337–432 MB vs ~120–150 MB for interior levels). This extra size comes from `NATerrain` and `NAWater2004` grid data.

These files contain unusual repeating chunk tags not seen in other GDWs:

| Tag | Likely Meaning |
|---|---|
| `HHHH` | Terrain/water height grid |
| `TTDT` | Terrain tile data |
| `DTTD` | Terrain tile data (variant) |
| `XXHX` | Unknown grid data |

These tags do not conform to the standard GMDL/GTEXT chunk structure and are not parsed by the standard mesh/texture extraction scripts. They are likely binary grid arrays — height values, water surface normals, or terrain material indices stored as packed float or integer arrays.

---

## Static Environment Geometry — Resolved

**Superseded (2025-06-29):** this section previously claimed terrain/coastline/dock/water geometry wasn't present in any GMDL/BRTR node. That's wrong — all static terrain (sandy shore tiles, rocks, water planes, dock structure) **is** placed as regular BRTR mesh instances with full world transforms, same as any other object. See `CLAUDE.md`'s "Scene / Object System — BRTR Chunk" section for the full object-name-pattern table (`Homokos_PartSzakasz_*`, `szikla*`, `Plane01/02`, `molo*`, etc.). There is no separate BSP, heightmap, or hidden terrain container.

Each level's `NAWater2004` object (exactly one per level, placed in `BRTR`) does still drive the *visible water surface* rendering — waves, reflection, and a flat "infinite surface" fallback plane beyond its LOD range. See `terrain_and_water_bounds.md` for the full mechanism (the `m_infinitesurface` flag) and why the ocean floor appears to extend forever near a level's edge.

---

## Rendering Notes

The engine uses heavy underwater fog as a draw-distance mask — a technique carried over from Ecco. This was a deliberate design choice to hide pop-in and limit visible geometry complexity at depth, where the water light model absorbs colour and reduces visibility naturally.

`NATextureGeneratorGrid` suggests the water surface texture (caustics, ripples) is generated procedurally by the engine each frame rather than being stored as a static asset — consistent with the ~1,660 extracted GTEX sprites including caustic pattern layers confirmed in the sprite texture set.

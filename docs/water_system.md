# Water

**In short:** each level has one `NAWater2004` object for the visible water: waves, reflection, and a flat plane beyond its range so the ocean never ends. One `NAWaterYCamera` action switches everything when the camera crosses the surface: viewports, fog, and the camera's far plane. Terrain is ordinary placed meshes; there's no hidden heightmap.

Water code goes back to *Ecco the Dolphin: Defender of the Future* (2000). The class names keep older versions alongside the shipping one.

Related: `docs/rendering_system.md` §5 "Draw distance", `docs/terrain_and_water_bounds.md` (the infinite-ocean plane), `docs/exe_analysis.md` §6 "Water height".

Rewritten for readability on 2026-11-27. Old version: `docs/archive/water_system_old_2026-11-27.md`.

---

## Contents

1. [Water classes](#1-water-classes)
2. [`NAWaterYCamera`: crossing the surface](#2-nawaterycamera-crossing-the-surface)
3. [Water height in the engine](#3-water-height-in-the-engine)
4. [Terrain](#4-terrain)
5. [Open-ocean files](#5-open-ocean-files)
6. [Old mistakes](#6-old-mistakes)

---

## 1. Water classes

| Class | Probably from | Does |
|---|---|---|
| `NAWaterGrid2000` | Ecco (2000) | The original water grid |
| `NAWater2003` | Between Ecco and Jaws | An intermediate version |
| **`NAWater2004`** | Jaws | **The shipping water.** One per level, placed in `BRTR`. |
| `NASlideWater2004` | Jaws | Shallow, sliding water: beaches, canals |
| `NATextureGeneratorGrid` | Jaws | Probably generates caustic and ripple textures each frame |
| **`NAWaterYCamera`** | Jaws | **Switches above/below water** (§2) |

- The suffixes look like years. That's a reading of the names, not proven.
- Old versions stay in the class registry. Whether any shipped level still uses them wasn't checked.

**`NAWater2004`:**
- A finite wave grid managed by level of detail, bounded by `m_detaildistanceabove`/`below` and the level's `WDIM` extents.
- Beyond it, the flag **`m_infinitesurface`** turns on a flat plane so the player never sees an edge. It's a visual trick: no collision, nothing placed out there. Details: `docs/terrain_and_water_bounds.md`.

**Heavy underwater fog** hides the draw distance and pop-in, a technique carried over from Ecco.

---

## 2. `NAWaterYCamera`: crossing the surface

Decoded 2026-10-17. One per level (OPEN_S: action `NAWaterYCamera 1`, ID 28100). Class `0x02071070`.

**Fields** (`PROP 0x08001330` + index):

| Fields | What |
|---|---|
| `m_viewportabove` … `m_viewportsharkview` | 7 viewport node IDs |
| `m_creatorreflection` | Reflection |
| `m_fogabove`, `m_fogbelow` | IDs of the `FogAbove` / `FogBelow` `GDFog` nodes |
| `m_fogbelowstartPC`, `m_fogbelowendPC` | Underwater fog on PC (OPEN_S: 30–170) |
| The same for PS2 | |
| `m_fogstartbottom`, `m_fogendbottom`, `m_fogbottomy` | Deep-water fog (OPEN_S: 70–170 below y = −40) |
| Three fog colours, `m_fogtransparentbelow` | |
| Water textures, transparency and reflection settings | |
| `m_transparencyfarplanefromabove` / `frombelow` | |

**What it does:**
- **Crossing the surface** (`0x62AC40` going up, `0x62AEF0` going down): shows and hides the matching viewports, swaps the fogs, sets the camera's far plane, and sets the music's underwater flag.
- **Every frame underwater** (tick `0x62B430`): writes the PC fog start and end into `FogBelow`, blended toward the bottom values with depth, **and sets the camera's far plane to the fog end.** So the underwater fog end is the underwater draw distance.

**Limits found in testing:** an underwater fog end past ~400 causes flicker and culling bugs; 2500 crashed. See `docs/rendering_system.md` §5.

---

## 3. Water height in the engine

The engine asks for the water height through three function pointers, all `float f(const float* pos)`. They return −2147483648.0 where there's no water.

| Pointer | Gives |
|---|---|
| `0x8B2E94` | The **wave surface** height |
| `0x8B2E98` | Not identified |
| `0x8B2E9C` | The **flat water level** (the water brick's world Y) |

- The shark's jump physics use the wave surface. The camera and the max-depth limit use the flat level.
- The mod's F7 air swim wraps these.
- Every caller is listed in `docs/exe_analysis.md` §6 "Water height".

---

## 4. Terrain

**There's no separate terrain system in the shipped levels.**
- Sandy shores, rocks, water planes and docks are ordinary `BRTR` mesh instances with world transforms. Examples: `Homokos_PartSzakasz_*` (sandy shore), `szikla*` (rock), `Plane01/02` (water planes), `molo*` (pier). Name glossary: `docs/scene_graph.md` §9.
- No BSP, heightmap or hidden terrain container was found.

The classes `NATerrain` (terrain) and `NAGrid` (a grid shared with water) exist in the registry. Whether any level uses them wasn't checked.

---

## 5. Open-ocean files

- `OPEN_S`, `OPEN_NE` and `OPEN_NW` are much larger than the story levels: 353–452 MB against ~130–155 MB.
- **Unchecked:** an early note says they contain repeating tags not seen elsewhere: `HHHH`, `TTDT`, `DTTD`, `XXHX`, guessed to be terrain or water grids.
- Since then, all terrain was found as normal `BRTR` meshes. Whether those tags are real chunks (perhaps a streaming or detail system) or coincidences inside data isn't known. Also listed in `docs/GDW_FORMAT.md`.

---

## 6. Old mistakes

| Old claim | Now |
|---|---|
| Terrain, coastline, docks and water planes aren't in any mesh or node | They're ordinary `BRTR` mesh instances (2025-06-29) |
| `NAWater2004` generates an infinite ocean | A finite wave grid plus a flat fallback plane (2026-07-15) |
| The open-ocean files' extra size comes from `NATerrain` and `NAWater2004` grid data | Not established; see §5 |

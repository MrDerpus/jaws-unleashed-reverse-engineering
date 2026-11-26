# Rendering

**In short:** the PC game draws with DirectX 8 (`d3d8.dll`). It's left-handed and Y-up, and runs at a fixed ~30 fps.
- Each frame has several passes. Some render to textures (water reflection, crowd sprites) before the main view.
- How far you can see is set by level data: the camera's far plane and fog. Underwater, the fog end *is* the far plane.
- The mod is a `d3d8.dll` proxy that sits between the game and the real DirectX 8, which is how the freecam, HUD and sonar are drawn.

Textures: `docs/texture_format.md`. Water: `docs/water_system.md`. Mod internals: `mod/README.md`.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/rendering_system_old_2026-11-27.md`.

---

## Contents

1. [API and runtime](#1-api-and-runtime)
2. [Coordinates](#2-coordinates)
3. [Frame structure](#3-frame-structure)
4. [Cameras](#4-cameras)
5. [Draw distance](#5-draw-distance)
6. [Render states and foliage](#6-render-states-and-foliage)
7. [Textures at runtime](#7-textures-at-runtime)
8. [Shadows, reflections, water and UI](#8-shadows-reflections-water-and-ui)
9. [Rendering classes](#9-rendering-classes)
10. [Open problems](#10-open-problems)
11. [Old mistakes](#11-old-mistakes)

---

## 1. API and runtime

| Property | Value |
|---|---|
| Graphics API | DirectX 8 (`d3d8.dll`, `IDirect3DDevice8`); only `Direct3DCreate8` is imported |
| Main pixel format | `D3DFMT_A8R8G8B8` (bytes in memory: B, G, R, A) |
| Coordinates | Left-handed, Y up |
| Frame rate | Fixed ~30 fps; lag means slow motion, not dropped frames |
| Resolution tested | 1920×1080 |
| On Linux | Proton with DXVK's d3d8. GE-Proton11-9 since 2026-10-16, for the WMV movies (`docs/exe_analysis.md` §13). |

---

## 2. Coordinates

- **Left-handed: X right, Y up (height), Z forward.**
- FISH's extents: X −120 to 2499, Y −229 to 2305, Z −4584 to 32.

**Converting to Blender** (user-confirmed 2026-10-01; `docs/rsrc_formats.md` §5):
- Exports write `(x, y, −z)` and keep the original triangle order.
- The Blender importer uses `CONV` = (X=x, Y=z, Z=y), determinant −1: `matrix_world = CONV @ game_world @ FLIP_Z`.

---

## 3. Frame structure

**Several passes per frame,** each with its own `BeginScene`/`EndScene`:
- render-to-texture passes: water reflection and refraction, crowd sprites;
- the main view: opaque geometry, then water, characters and alpha-blended objects.

**`SetTransform(D3DTS_VIEW)` is called for each pass.**
- The last view and projection set while the back buffer is the target are the main camera (`docs/exe_analysis.md` §6).
- The mod's freecam writes its matrix into every view call. That also moves the reflection passes, which causes some visual glitches in freecam.

**What this means for drawing from the mod:**
- `EndScene` also ends the render-to-texture passes. HUD text drawn there ended up inside the water reflection and on crowd sprites.
- So the HUD is drawn in `Present`, once per frame, on the back buffer only (fixed 2026-11-25, user-confirmed).
- The Ecco sonar is world-space and still draws in `EndScene`, but only when the back buffer is the target (`mod/README.md`).

**The device is recreated constantly:**
- `IDirect3D8::CreateDevice` (a full teardown and recreation, not just `Reset`) fired 366 times in one play session (found 2026-08-16). Each call succeeded.
- Why isn't known.
- **Rule for the mod:** persistent state can't live on `DeviceProxy`. A per-device screenshot counter kept resetting because of this (`mod/README.md` "Screenshots (F3)").

---

## 4. Cameras

### Main camera

**Eye position** from view matrix V:

```
eye.x = −(V._11·V._41 + V._21·V._42 + V._31·V._43)
eye.y = −(V._12·V._41 + V._22·V._42 + V._32·V._43)
eye.z = −(V._13·V._41 + V._23·V._42 + V._33·V._43)
```

**Yaw and pitch** from the forward vector (third column of the rotation):

```
pitch = asin(V._23)
yaw   = atan2(V._13, V._33)
```

### A second camera

- Set about every 5 frames, roughly 345 units above the main camera (Y ≈ +335 against Y ≈ −9).
- Probably a shadow or reflection pass. Not decoded.
- The mod ignores it with a 5-sample rolling median when seeding the freecam from the main camera.

---

## 5. Draw distance

Decoded 2026-10-17. **The visible distance is level data plus one water action; the exe has no fixed limit.**

| What | Where | Stock |
|---|---|---|
| Camera far plane | `SharkCamera` node (`GDCamera`), `m_FarPlane` = `PROP 0x08001800`; runtime `camera+0x11C` (near `+0x114`) | 600 in every level |
| Above-water fog | `FogAbove` (`GDFog`), `m_FogStart`/`m_FogEnd` = `PROP 0x0800184D`/`E`; runtime `+0x12C`/`+0x134` | End 300–1100, per level |
| Underwater fog **and underwater far plane** | `NAWaterYCamera`: `m_fogbelowstartPC`/`EndPC` (`PROP 0x0800133A`/`B`), deep water `m_fogstartbottom`/`endbottom` (`0x0800133E`/`F`) | OPEN_S: 30/170, deep 70/170 |

**How it works:**
- **Underwater,** `NAWaterYCamera`'s tick (`0x62B430`) copies its fog values into `FogBelow` every frame and **sets the camera's far plane to the fog end.** `FogBelow`'s own 40/80 never applies.
- **Above water,** the far plane is set once when crossing the surface (`0x62AC40`).
- The frustum test is `0x69B400` (near, far, four sides).

**In-game tests** (OPEN_S copies, user-tested):

| Setting | Result |
|---|---|
| Far plane 3000, above-water fog 1000–2900 | Distant objects show that stock draws only up close. No side effects. |
| Underwater fog 800–2500 | Crashed on load |
| Underwater fog 300–1200 | The shipwreck flickers or appears only right next to the shark; mission barriers show only very close or at the screen edge; more NPCs culled |
| Underwater fog 100–400 | No problems |

- **The mod's Shift+F4** applies 3000 / 1000–2900 / 100–400 at runtime (`mod/src/farview.{h,cpp}`; user-confirmed 2026-11-25).
- Engine detail: `docs/exe_analysis.md` §12 "Draw distance and fog".
- Editing it in a level file: `docs/brtr_editing.md` §14 "Draw distance in a level file".

---

## 6. Render states and foliage

Seen through the proxy:

| State | Used for |
|---|---|
| `D3DRS_FOGENABLE` | The heavy distance fog |
| `D3DRS_FILLMODE` | Solid normally; the mod can switch to wireframe |
| `D3DRS_ALPHATESTENABLE`, `ALPHAREF`, `ALPHAFUNC` | Cut-out cards (kelp, seaweed, plants) |
| `D3DRS_ALPHABLENDENABLE` | Transparent objects |
| `D3DRS_ZENABLE`, `ZWRITEENABLE` | Depth buffer |
| `D3DRS_CULLMODE` | Back-face culling |
| `D3DRS_LIGHTING` | Fixed-function lighting |
| `D3DRS_COLORVERTEX` | Per-vertex colour (baked lighting) |

**Foliage** is flat cards with cut-out textures (alpha test).
- **To hide it** (the mod's F6): after every `ALPHATESTENABLE = TRUE`, force `ALPHAREF = 255` and `ALPHAFUNC = D3DCMP_GREATER`. No pixel passes, so every alpha-tested draw disappears.

**Transparency in level files:** 32-bit texture alpha, with the node's render setting choosing blend or cut-out (`docs/brtr_editing.md` §9).

---

## 7. Textures at runtime

- 32-bit textures are `D3DFMT_A8R8G8B8`. The name lists bits from most to least significant, so the bytes are B, G, R, A. 24-bit textures are B, G, R.
- Stored bottom-up.
- **Chroma key: cyan `#00FFFF`** (D3D `0xFF00FFFF`, at `0x725427` in the exe).
- A few textures are empty **render targets** the engine fills at runtime. They cover under 0.5 % of textured triangles.

Full format: `docs/texture_format.md`.

---

## 8. Shadows, reflections, water and UI

**Shadows:**
- `NAShadowModel` (a shadow mesh) and `NAStencilVolume` (stencil shadow volumes) exist as classes.
- The second camera (§4) may drive a shadow or reflection pass. The pass structure isn't decoded.

**Water** (`docs/water_system.md`):
- `NAWater2004` draws the ocean surface: a finite, level-of-detail wave grid. Beyond it, a flat plane (`m_infinitesurface`) hides the world's edge; that plane has no collision and nothing on it (`docs/terrain_and_water_bounds.md`).
- `NATextureGeneratorGrid` probably generates caustic and ripple textures each frame.
- `NASlideWater2004` handles beaches and canals.
- Heavy fog hides the draw distance, a technique carried over from Ecco (§5).

**UI:**
- Drawn with `GDSprite`, `GDRotSprite`, `GDFont`, `GDTextSprite`.
- Many of the 2,787 `OBPR`-variant textures are HUD elements, caustic layers and interface pieces, with chroma-key transparency.

---

## 9. Rendering classes

From the `CLAS` reflection database. The purposes are read from the names, unless another doc confirms them.

| Class | Probably |
|---|---|
| `GDModel` | A 3D model |
| `GDStripModel` | Triangle-strip model |
| `GDMovingModel` | Moving model |
| `GDSkeletonModel` | Skinned model (`docs/animation_system.md`) |
| `NAPredatorModel` | Added with Defender PS2 (`docs/gwb_lineage.md`) |
| `NAMorphModel`, `GDMorphAnim` | Vertex (morph) animation |
| `NAShadowModel` | Shadow mesh |
| `NAStencilVolume` | Stencil shadow volume |
| `GDMatAnim` | Material animation (UV scrolling, texture swap) |
| `NAMotionBlur` | Motion blur |
| `NATimeControl` | Slow motion (`m_timespeed`, `m_motionblurport`) |
| `NAParticle2004` | Particles |
| `GDLight`, `GDExtendedLight` | Lights |
| `GDFog` | Fog (confirmed, §5) |

Note: `NAPredator` (without "Model") is the predator-vision screen effect.

---

## 10. Open problems

- **Underwater far plane past ~400:** why it breaks object visibility (flicker, barriers, NPC culling). Probably a per-object visibility or fade test, or a draw budget. The same cause may be behind the large-object fade (`docs/brtr_editing.md`).
- **Shadow and reflection passes:** the full pass structure.
- **Device recreation:** why the device is rebuilt hundreds of times per session.
- **The pier water planes** (`Plane01/02` in FISH): whether they're partly driven at runtime.

---

## 11. Old mistakes

| Old claim | Now |
|---|---|
| Blender: X = x, Y = −z, Z = y (`CONV @ M @ CONV_INV`) | That's a rotation, which mirrors the levels. Now Y = z with determinant −1 (§2). |
| 32-bit textures are RGBA or ARGB; 24-bit `OBPR` textures are R, B, G | All B, G, R(, A) (2026-07-29) |
| 65 texture IDs are runtime render targets (reflections, shadow maps) | Came from misreading `TSET` counts as texture IDs (withdrawn 2026-10-01). Real render targets cover under 0.5 % of triangles. |
| Some small indexed textures decode wrongly | The only two 8-bit textures decode fine (palette + indices; `docs/texture_format.md`) |
| Terrain, coastline and water surface aren't in the level data | They're ordinary `BRTR` mesh instances (2025-06-29) |
| Skeletal animation not decoded | Fully decoded, with a Blender importer (`docs/animation_system.md`) |
| Two passes per frame: opaque, then transparent | More: render-to-texture passes come first (§3) |

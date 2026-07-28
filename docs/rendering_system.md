# Rendering System — Jaws Unleashed (PC)

*Note: `CLAUDE.md` at the project root is the actively-maintained, current source of truth for this project. This file is an early-project snapshot, spot-corrected below where stale.*

The PC version targets **DirectX 8** (`d3d8.dll`, `IDirect3DDevice8`). The game runs under Proton via DXVK's d3d8 implementation. This document covers what is known from binary analysis, class registry inspection, and the d3d8 proxy mod.

---

## API and Hardware

| Property | Value |
|---|---|
| Graphics API | DirectX 8 (`d3d8.dll`) |
| Device interface | `IDirect3DDevice8` |
| Primary pixel format | `D3DFMT_A8R8G8B8` (32bpp; name is MSB→LSB bit order, actual little-endian file/memory byte order is BGRA — see Texture Formats below) |
| Coordinate system | D3D left-handed, Y-up |
| Display resolution (confirmed) | 1920×1080 |
| Runtime | Wine / Proton via DXVK d3d8 wrapper |

---

## Coordinate System

DirectX Y-up, left-handed. Y is height (positive = up). World extents in FISH.GDW: X −120 to 2499, Y −229 to 2305, Z −4584 to 32.

**Game → Blender conversion:**
```
Blender X =  game X
Blender Y = -game Z
Blender Z =  game Y
```
Applied as: `CONV @ game_matrix @ CONV_INV` where:
```python
CONV = Matrix([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]])
```

---

## Frame Structure

The game renders **multiple passes per visible frame** using multiple `BeginScene`/`EndScene` pairs:
1. **Opaque pass** — solid geometry
2. **Transparent/skinned pass** — water, characters, NPCs, alpha-blended objects

`SetTransform(D3DTS_VIEW)` is called for each pass. Our d3d8 proxy injects the freecam matrix into all `SetTransform(VIEW)` calls, which affects all passes simultaneously — this causes some visual artefacts in freecam mode since shadow/reflection passes also get the injected matrix.

---

## Camera System

### Primary camera
Called each frame with the player's view matrix via `SetTransform(D3DTS_VIEW)`.

**Position extraction** from view matrix V:
```
eye.x = −(V._11·V._41 + V._21·V._42 + V._31·V._43)
eye.y = −(V._12·V._41 + V._22·V._42 + V._32·V._43)
eye.z = −(V._13·V._41 + V._23·V._42 + V._33·V._43)
```

**Yaw/pitch** from forward vector (column 3 of rotation):
```
pitch = asin(V._23)
yaw   = atan2(V._13, V._33)
```

### Secondary camera
Called roughly every 5 frames — believed to be shadow map or reflection pass. Positioned ~345 units above the main camera (Y ≈ +335 vs Y ≈ −9). The proxy mod filters this out using a 5-sample rolling median to reliably seed freecam position from the main camera.

---

## Texture Formats

| Format | D3D Equivalent | Byte Order | Used For |
|---|---|---|---|
| GTEXT 32bpp | `D3DFMT_A8R8G8B8` | BGRA (native little-endian) | Environment, character textures |
| GTEXT 24bpp | — | BGR (swap to RGB) | Environment textures |
| GTEX 32bpp | `D3DFMT_A8R8G8B8` | BGRA (native little-endian) | Sprite/overlay layers |
| GTEX 24bpp | — | BGR (swap to RGB) | Sprite layers |

> **Correction (2026-07-29):** the byte orders above were previously documented as GTEXT 32bpp = straight RGBA, GTEX 32bpp = ARGB (`byte[0]=A,1=R,2=G,3=B`), and GTEX 24bpp = R,B,G — all wrong. `D3DFMT_A8R8G8B8`'s name describes bit significance MSB→LSB, not actual little-endian file byte order, which for all three cases above is native **B,G,R(,A)** — the same convention GTEXT 24bpp already had right. The wrong GTEXT 32bpp assumption produced a subtle R/B swap (blue tint on warm-toned textures); the wrong GTEX assumptions produced a visible R/G swap. Both were masked by a separate, now-fixed pixel-offset bug (see `CLAUDE.md`'s "Texture System (GTEXT)"/"(GTEX)" sections) that scrambled positioning badly enough to hide the channel-order error. `scripts/rip_textures.py` and `scripts/rip_gtex.py` are both fixed.

All textures stored bottom-up in GDW files (flip on export).

### Chroma Key
Sprite/overlay textures use cyan `#00FFFF` as chroma key (D3D DWORD `0xFF00FFFF`, confirmed at binary VA `0x725427`). Pixels where R<20, G>235, B>235 are made fully transparent on extract. (Detection must read R/G/B from the corrected BGRA byte positions above, per the 2026-07-29 correction — the old ARGB-based detection in `scripts/rip_gtex.py` was checking the wrong bytes.)

### Runtime Render Targets
65 texture IDs in the global space are **runtime render targets** — reflections, shadow maps — created by the engine at startup. No pixel data is stored in GDW files for these. They appear in TSET references but cannot be extracted.

---

## Render States (from proxy mod intercepts)

| State | Observed Use |
|---|---|
| `D3DRS_FOGENABLE` | Underwater distance fog — heavy, inherited from Ecco lineage |
| `D3DRS_FILLMODE` | `D3DFILL_SOLID` normally; togglable to `D3DFILL_WIREFRAME` |
| `D3DRS_ALPHATESTENABLE` | Alpha-cutout cards for foliage (kelp, seaweed, plants) |
| `D3DRS_ALPHAREF` | Threshold for alpha test |
| `D3DRS_ALPHAFUNC` | Comparison function for alpha test |
| `D3DRS_ALPHABLENDENABLE` | Blending for transparent objects |
| `D3DRS_ZENABLE` / `D3DRS_ZWRITEENABLE` | Depth buffer control |
| `D3DRS_CULLMODE` | Backface culling |
| `D3DRS_LIGHTING` | D3D fixed-function lighting |
| `D3DRS_COLORVERTEX` | Per-vertex colour (baked lighting from `VCOL`) |

### Foliage Rendering
Sea foliage (kelp, seaweed, plants) uses flat billboard cards with alpha-cutout textures via `D3DRS_ALPHATESTENABLE`. To hide foliage, force `D3DRS_ALPHAREF = 255` + `D3DRS_ALPHAFUNC = D3DCMP_GREATER` immediately after any `ALPHATESTENABLE = TRUE` call — a condition no pixel satisfies, discarding all alpha-tested draws.

---

## Shadow and Reflection System

- 65 runtime render targets suggest a shadow map + reflection pipeline
- `NAShadowModel` — shadow mesh class (casts or receives shadows)
- `NAStencilVolume` — stencil shadow volume (shadow projection)
- Secondary `SetTransform(VIEW)` call per frame likely drives shadow map camera

---

## Engine Classes (from CLAS reflection)

| Class | Purpose |
|---|---|
| `GDModel` | General 3D model component |
| `GDStripModel` | Triangle strip geometry model |
| `GDMovingModel` | Animated/moving model |
| `GDSkeletonModel` | Skeletal mesh |
| `NAPredatorModel` | Shark-specific model |
| `NAMorphModel` | Morph target animation |
| `NAShadowModel` | Shadow mesh |
| `NAStencilVolume` | Stencil shadow volume |
| `GDMatAnim` | Material animation (UV scrolling, texture swap) |
| `GDMorphAnim` | Morph animation controller |
| `NAMotionBlur` | Motion blur system |
| `NATimeControl` | Time dilation / slow-motion (`m_timespeed`, `m_motionblurport`) |
| `NAParticle2004` | Particle system |
| `GDLight` | Dynamic light |
| `GDExtendedLight` | Extended light properties |
| `GDFog` | Fog system |

---

## Water Rendering

See `water_system.md` for full detail. Key rendering facts:
- `NAWater2004` drives open ocean surface — procedural, not authored mesh. **Clarified 2026-07-15**: this is a real, finite, LOD-managed wave/seafloor grid (bounded by `m_detaildistanceabove/below` and the level's `WDIM` world extents), not infinite generation. Beyond that grid, a boolean `m_infinitesurface` flag on the same class enables a flat fallback plane so players never see a void/edge at the world boundary — a cheap visual trick, not real geometry (no collision, no props out there). See CLAUDE.md for full writeup.
- `NATextureGeneratorGrid` generates water caustic/ripple textures per-frame
- Heavy fog used as draw-distance mask — inherited from Ecco lineage
- `NASlideWater2004` handles beaches and canals

---

## Overlay / UI

The engine uses `GDSprite`, `GDRotSprite`, `GDFont`, `GDTextSprite` for UI elements. The GTEX sprite system provides composited overlay layers — 2,787 GTEX sprites extracted (updated 2026-07-29, was ~1,660 before the pixel-offset fix — see `CLAUDE.md`), including HUD elements, caustic overlays, and interface textures. Sprites use `D3DFMT_A8R8G8B8` with chroma-key transparency.

---

## Open Problems

| Problem | Status |
|---|---|
| ~~Static environment geometry (terrain, coastline, water surface)~~ | **RESOLVED 2025-06-29**: all terrain tiles, rocks, water planes, and dock structures are present in `BRTR` as regular named mesh instances with full world transforms — no hidden BSP/heightmap, fully extractable. The pier-area water surface (`Plane01/02` instances) may still be partly runtime-driven — soft open question. See CLAUDE.md's Scene Layout table. |
| ~~Skeletal animation keyframe format~~ | **FULLY RESOLVED 2026-07-17**: `SKEL`, `BONE`, `WGHT`, `ROTS`, `BROT`, `MTOB`, `CHLD`, `ANIM` blocks in `RSRC` fully decoded — bind mesh, per-vertex bone weights, recursive bone hierarchy, per-bone quaternion keyframes sliced into named clips. Extractor `scripts/rip_skeletons.py` verified on all 30 of FISH.GDW's skeletons; Blender armature/animation import still not written. See CLAUDE.md's Skeletal Animation System section. |
| Palette / indexed texture decoding | Some small textures decode incorrectly — CLUT format unresolved |
| Shadow map / reflection pipeline detail | Secondary camera confirmed; full pass structure not decoded |

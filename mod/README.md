# Jaws Unleashed — d3d8 Proxy Mod

A reverse-engineering / exploration mod for *Jaws Unleashed* (PC, 2006, Appaloosa Interactive).  
Runs under Proton 10.0 on Linux. Targets DirectX 8 (`d3d8.dll`).

---

## Controls

| Key | Action |
|-----|--------|
| `F1` | *(unbound by the mod — left free for the game's own map screen)* |
| `F2` | Toggle freecam on / off *(moved off F1 2026-08-12 so F1 stays free for the map; god-mode removed the same pass)* |
| `F3` | Screenshot — saves `C:\jaws_screenshot_NNNN.bmp` |
| `F4` | Toggle fog on / off |
| `F5` | Toggle sim pause — slows physics, AI, and cutscene playback to ~25% speed |
| `F6` | Toggle foliage hide — makes alpha-tested geometry (seaweed, kelp, plants) invisible |
| `F7` | Dev tool: two-pass health-address memory scanner (not player-facing) |
| `F9` | Dev tool: three-pass player-position memory scanner (not player-facing, unsolved — see below) |
| `I` / `K` | Freecam: move forward / backward |
| `J` / `L` | Freecam: strafe left / right |
| `U` / `O` | Freecam: move up / down |
| `Alt` | Hold for fast movement (45× speed) |
| Mouse | Freecam look (cursor captured and re-centred each frame) |

The **XYZ overlay** (top-left corner) shows a camera-derived world-space position and all toggle states at all times. **Known accuracy issue:** this is not a reliable player-position readout — see [XYZ Overlay Accuracy](#xyz-overlay-accuracy--known-unsolved-issue) below.

Screenshots land at:
```
~/.steam/steam/steamapps/compatdata/2342933845/pfx/drive_c/jaws_screenshot_0000.bmp
```

---

## Build

**Requirements:** `i686-w64-mingw32-g++` (32-bit MinGW cross-compiler), `make`.

```bash
cd mod/
make              # build d3d8.dll
make clean        # remove build output
```

No external SDK needed — the DX8 interface is hand-rolled in `src/d3d8_iface.h`.

---

## Deploy

1. **Set the Steam launch option** for Jaws Unleashed:
   ```
   WINEDLLOVERRIDES="d3d8=native,builtin" %command%
   ```
   This tells Proton to prefer the game-directory `d3d8.dll` over DXVK's system copy.

2. **Copy the built DLL** into the game directory:
   ```bash
   cp d3d8.dll "/path/to/steamapps/compatdata/2342933845/pfx/drive_c/Program Files (x86)/Jaws Unleashed/"
   ```

3. **Launch the game** via Steam. Check the log at:
   ```
   ~/.steam/steam/steamapps/compatdata/2342933845/pfx/drive_c/jaws_mod.log
   ```
   A successful load shows `[jaws_mod] DeviceProxy created 1920x1080` and `[jaws_mod] time hooks: GTC=ok QPC=ok`.

---

## Source Layout

```
mod/
├── Makefile
└── src/
    ├── d3d8.def            # Forces undecorated Direct3DCreate8 export name
    ├── d3d8_iface.h        # Hand-rolled DX8 COM interface definitions
    ├── d3d8_proxy.cpp      # DllMain, Direct3DCreate8, D3D8Proxy, IAT time hooks
    ├── device_proxy.h      # DeviceProxy class declaration
    ├── device_proxy.cpp    # Freecam, view matrix injection, key toggles, EndScene hook
    ├── overlay.h / .cpp    # GDI → D3D texture HUD renderer
    ├── dinput8_proxy.cpp   # Abandoned injection attempt (not built)
    └── winmm_proxy.cpp     # Abandoned injection attempt (not built)
```

---

## Architecture

```
Direct3DCreate8 (our export, undecorated via d3d8.def)
  ├─ installs IAT time hooks into Jaws.exe (GetTickCount, QueryPerformanceCounter)
  ├─ lazy-loads DXVK d3d8 from system32
  └─ returns D3D8Proxy wrapping the real IDirect3D8
       └─ CreateDevice → returns DeviceProxy wrapping the real IDirect3DDevice8

DeviceProxy intercepts:
  SetTransform(VIEW)  → extracts world-space camera pos/orientation;
                        injects freecam view matrix when F2 active
  SetRenderState      → suppresses D3DRS_FOGENABLE (F4);
                        forces alpha test impossible to hide foliage (F6)
  EndScene            → draws overlay HUD; polls F2–F6 keys; takes screenshots (F3)
  Reset               → releases and re-initialises overlay after device reset
  (everything else)   → forwarded directly to the real DXVK device
```

---

## How the Freecam Works

### View matrix injection

The game calls `SetTransform(D3DTS_VIEW, &viewMatrix)` each frame. We intercept this and, when freecam is active, substitute a matrix built from our own position + yaw/pitch.

### Seeding on activation

The game calls `SetTransform(VIEW)` multiple times per frame for several different camera identities, not just one secondary camera (see [XYZ Overlay Accuracy](#xyz-overlay-accuracy--known-unsolved-issue) below for the full investigation). `ExtractCamPos` filters out the one degenerate case that's cheap and reliable to detect — a secondary camera whose translation is exactly `(0,0,0)` — and maintains a 5-sample rolling median of what's left for freecam seeding. This is good enough for seeding (a one-time snapshot on F1 press, where being off by a bit doesn't matter) but is **not** sufficient for the continuous, precise position readout the XYZ overlay is meant to provide.

### Position extraction

Given the D3D row-vector view matrix V:
```
eye.x = −(V._11·V._41 + V._21·V._42 + V._31·V._43)
eye.y = −(V._12·V._41 + V._22·V._42 + V._32·V._43)
eye.z = −(V._13·V._41 + V._23·V._42 + V._33·V._43)

pitch = asin(V._23)
yaw   = atan2(V._13, V._33)
```

### View matrix construction

Standard D3D left-handed view matrix from position, yaw, and pitch.  
The up vector is `forward × right` — using `right × forward` gives the down vector in a left-handed system and flips the scene upside-down.

---

## Overlay Rendering Bug Fix (2026-07-16)

The XYZ/status overlay never rendered at all — F1 toggled freecam fine, but no HUD ever appeared. Root cause was a wrong D3D FVF (vertex format) constant in `overlay.cpp`:

```cpp
// Wrong — evaluates to D3DFVF_XYZB1 | D3DFVF_TEX1 (position + a blend
// weight, no diffuse color, and NOT pretransformed):
#define D3DFVF_TLVERTEX (0x002 | 0x004 | 0x100)

// Correct — D3DFVF_XYZRHW | D3DFVF_DIFFUSE | D3DFVF_TEX1:
#define D3DFVF_TLVERTEX (0x004 | 0x040 | 0x100)
```

`D3DFVF_XYZ` (`0x002`) and `D3DFVF_XYZRHW` (`0x004`) are alternatives in the FVF's position-type field, not combinable flags. OR-ing them together produced `0x006`, which happens to numerically equal `D3DFVF_XYZB1` (position + one blend weight) combined with `D3DFVF_TEX1` — a completely different vertex layout with no color component, and critically *not* pretransformed/screen-space. The overlay's quad vertices were being run back through the game's real 3D world/view/projection + lighting pipeline instead of being drawn as a fixed screen-space HUD, which is why nothing ever showed up.

Also fixed in the same pass: the overlay's texture was being locked with `D3DLOCK_DISCARD`, which is only valid for `DYNAMIC`-usage resources — this texture is `POOL_MANAGED` with no usage flags, so the flag was invalid and DXVK could fail the lock outright (old native D3D8 drivers tended to just ignore the invalid flag, masking the bug). Changed to a plain lock (`0`).

---

## XYZ Overlay Accuracy — Known Unsolved Issue

The overlay renders correctly (see bug fix above) and shows *a* position, but it is **not a reliable readout of the player's actual position**. This was investigated extensively (2026-07-17) and is documented here so the investigation isn't repeated from scratch.

### The core problem

The game calls `SetTransform(D3DTS_VIEW, ...)` **multiple times per frame** for different camera identities — the real player camera, plus at least one water reflection/refraction camera, and evidence of more (see below). There is no reliable way found so far to tell them apart from data available in the D3D call stream:

- **A camera that's sometimes static, sometimes moving.** Logging near a fixed reflective surface showed the secondary camera sitting almost still (barely drifting over a 20s window). Logging in open water instead showed it actively moving in a pattern that roughly mirrors the real camera's own motion. Any approach that assumes "the secondary camera is the static/degenerate one" only works in the first case.
- **Exact-zero filtering (implemented, partial fix).** One specific secondary camera reliably has translation `(0,0,0)` exactly, and — because it happens to be called last in the frame, right before the overlay reads the position — dominates a naive "latest value" or even a 5-sample-median read every single frame (not by chance: the call order is fixed, so the zero sample is always the freshest). `ExtractCamPos()` filters this exact case out. This is the *only* part of the problem that's actually fixed.
- **Reflection determinant check (tried, failed).** A mirrored/reflected transform should mathematically have a negative determinant on its 3×3 rotation part, vs. positive for an ordinary camera. Logged determinants for both real and mirrored-looking samples: **always exactly `+1.0`**. This engine must implement reflections via a genuinely repositioned/reoriented second camera (still a proper rotation matrix), not a flipped-handedness matrix — so this check has no discriminating power here.
- **Render-target gating (tried, failed).** Reflections normally render to an off-screen texture, so the theory was: only trust the camera set while the primary back buffer is the active render target. Interleaved logging of `SetRenderTarget` + `SetTransform(VIEW)` calls (in true call order, via a shared sequence counter) showed the real camera's `SetTransform(VIEW)` is **never** called while the back buffer is active — this engine renders the whole scene to off-screen textures first and only briefly touches the back buffer for a final composite blit at the end of the frame, with no camera transform set during that moment. There is no "this call is the real one" signal anywhere in the D3D call stream that was found.

### Memory-scan pivot (also unsuccessful so far)

Bypassed the rendering pipeline entirely and tried reading the player's position directly from memory, the same technique used to find the existing god-mode health addresses (`0x8F11A8` etc., found via the `F7` two-pass scanner already in the codebase).

Built `F9`, a three-pass scanner in `device_proxy.cpp`:
1. Snapshot every 4-byte-aligned XYZ float triplet in a plausible coordinate range (magnitude 0.5–6000) across `0x845000`–`0xE70000` (the same range `F7` already reads safely, and where all known god-mode addresses live).
2. After swimming, keep triplets that moved a meaningful amount.
3. After continuing to swim in the *same direction*, keep survivors whose two displacement vectors point in a consistent direction (cosine similarity > 0.5) — added specifically because a simpler 2-pass "did it move" version found a false positive: some oscillating/animation value that happened to differ between two snapshots by chance, without actually tracking real movement.

The best candidate found, `0x008CFC88`, passed the 3-pass test cleanly (cos=0.98 across two independent movement segments) but **failed live verification**. Per-frame logging of the raw value while swimming showed it cycling through several independently, slowly-drifting value clusters (roughly 645.x, 646.x, 666.x, then a jump to -461.x, then zeroed out entirely) rather than one continuously-moving value — consistent with a **shared/reused scratch address written by multiple different entities** (likely several nearby fish/NPCs, or a temp variable reused across position updates each frame), not a dedicated player-position field. Same fundamental class of problem as the D3D approach, just manifesting in memory instead of render calls.

### Recommended next approach (not yet tried)

Scan for the position field **near the already-confirmed player-specific god-mode addresses** (`0x8F11A8`, `0x8FB1B0`, `0x8FB1C0`, `0x9E907C`, `0x9E908C`, `0x9E909C`, `0x9E90AC`, `0x9E90FC`, `0xA14ED4`, `0xA16318`, `0xA59448`) instead of the broad `0x845000`–`0xE70000` range. Those addresses are known-good because toggling god mode reliably keeps *the player* alive, not some other entity — the position field is very likely a small fixed byte offset away in the *same* player object struct, not somewhere else in memory shared with other entities. The `F9` scanner's 3-pass structure is reusable as-is; it just needs its scan range narrowed to a tight window around one of those addresses instead of the whole `.data` range.

**Current state:** the overlay shows the D3D camera-transform reading (`cam_x_/y_/z_`) — imperfect (third-person camera orbits with rotation; occasional pollution from an unfiltered secondary camera identity) but not actively showing data known to be wrong, unlike the memory candidate.

---

## How Sim Pause Works (F5)

The game's simulation (physics, AI, animations, cutscene playback) advances based on a delta-time value derived from `QueryPerformanceCounter` (QPC) and `GetTickCount` (GTC). At startup, `InstallTimeHooks` walks the import address table (IAT) of `Jaws.exe` and replaces the function pointers for both with our hooks.

While sim pause is active, both hooks return fake time advancing at `1 / SIM_DIVISOR` of real speed (`SIM_DIVISOR = 4` → 25% speed). Both must be slowed together: the game uses QPC to gate its own render loop, so slowing only one causes the other to diverge and either stops rendering or causes a time jump on resume.

On unpause, accumulated offsets are adjusted so the game sees no time discontinuity — the fake dt on the first post-resume frame is approximately zero.

**Render rate tradeoff:** slowing both timers reduces the game's effective render rate to roughly `60fps / SIM_DIVISOR` (~15 fps at divisor=4). This causes mild visual choppiness in freecam during pause — unavoidable without a more invasive hook into the game's render loop. The freecam itself moves at a consistent real-time speed regardless of render rate (camera position is scaled by actual wall-clock dt via the saved real QPC pointer).

**Tuning:** `SIM_DIVISOR` in `src/d3d8_proxy.cpp`. Lower = smoother freecam, faster simulation. Higher = more frozen simulation, choppier freecam.

---

## Foliage Hide (F6)

Sea foliage (kelp, seaweed, plants) is rendered as flat billboard cards using `D3DRS_ALPHATESTENABLE` to punch transparent cutouts. When foliage hide is active, any `D3DRS_ALPHATESTENABLE = TRUE` call is intercepted and immediately followed by:
- `D3DRS_ALPHAREF = 255`
- `D3DRS_ALPHAFUNC = D3DCMP_GREATER` — "pass only if alpha > 255"

No pixel can satisfy this condition, so all alpha-tested draws discard every pixel. Solid geometry is unaffected. `alpha_test_enabled_` tracks state so subsequent `ALPHAREF`/`ALPHAFUNC` calls from the game are also overridden while a test pass is active.

---

## Render State Isolation

`Overlay::DrawQuad` saves and restores every device state it touches. D3D8 state blocks (`CreateStateBlock`) are unreliable under DXVK so all save/restore is done manually with explicit `Get`/`Set` calls.

States saved/restored: texture slot 0 (note: `GetTexture` adds a COM ref), texture stage state 0 (ColorOp/Arg1, AlphaOp/Arg1), render states (AlphaBlendEnable, SrcBlend, DestBlend, ZEnable, ZWriteEnable, CullMode, Lighting, ColorVertex), vertex shader/FVF, stream source 0, index buffer.

**Why stream source matters:** `DrawPrimitiveUP` rebinds stream source 0 to a temporary buffer. The game renders multiple `BeginScene`/`EndScene` passes per frame (opaque, then transparent/skinned). Without restoring stream source after the overlay draw, the second pass reads from the wrong buffer, making water, characters, and NPCs invisible.

---

## Known Limitations

- **Frustum culling follows the player.** The game culls geometry before calling `SetTransform`. Freecam only replaces the view matrix — objects outside the player's frustum are not rendered even if the freecam is pointed at them.
- **Multi-pass rendering artefacts.** The view injection fires for every `SetTransform(VIEW)` call, including shadow and reflection passes, causing some visual artefacts in freecam mode.
- **Map screen.** The map's 3D view is affected by freecam. Disable freecam (F2) before opening the map — freecam was moved off F1 specifically so F1 is left free for the game's own map key.
- **Sim pause choppiness.** At `SIM_DIVISOR=4`, the game renders at ~15 fps while paused. Increase the divisor for a stronger freeze at the cost of more choppiness.
- **XYZ overlay is not a reliable position readout.** See [XYZ Overlay Accuracy](#xyz-overlay-accuracy--known-unsolved-issue) — extensively investigated, not yet solved.

---

## Tuning

Speed and sensitivity constants in `src/device_proxy.cpp`:
```cpp
static const float FC_SPEED = 5.0f;    // units per second
static const float FC_SHIFT = 45.5f;   // multiplier when Alt held
static const float FC_SENS  = 0.003f;  // mouse look, radians per pixel
```

Sim pause strength in `src/d3d8_proxy.cpp`:
```cpp
static const DWORD SIM_DIVISOR = 4;    // 4 = 25% sim speed, ~15fps render
```

---

## Injection Approach — History

Getting the DLL to load under Proton required several attempts:

| Approach | Result |
|----------|--------|
| `winmm.dll` proxy in game dir | Never loaded — Wine uses winmm builtin-first |
| `dinput8.dll` proxy | Loaded, but forwarding `DirectInput8Create` hit `EXCEPTION_WINE_STUB (0x80000100)` in Wine's i386 stub PE |
| `d3d8.dll` without launch option | Never loaded — Proton's DXVK override takes priority |
| `d3d8.dll` + `WINEDLLOVERRIDES="d3d8=native,builtin"` | **Works** |

**Export name gotcha:** MinGW exports `__stdcall` functions with stdcall decoration by default (`Direct3DCreate8@4`). Wine's loader looks for the undecorated name `Direct3DCreate8`. Without `src/d3d8.def`, Wine creates a stub and crashes on the first call.

---

## Future Work — BRTR Node-Insertion Mystery (2026-07-17)

A file-level custom-map-import experiment (see CLAUDE.md's "Custom map feasibility" note and memory `project_custom_map_feasibility`) hit a wall this mod could help resolve. Summary:

- Injecting a new resource into `RSRC` and repointing/relocating existing `BRTR` nodes both work reliably in-game.
- Appending an entirely new `CHBR` sibling node to `BRTR` (structurally valid, verified 3 different ways including a byte-for-byte clone of a real working node) **never renders** — no crash, just silently absent.

Static file analysis is exhausted. The natural next step is **runtime instrumentation**: hook whatever code path parses `BRTR` during level load (or a nearby allocation/object-registration call) to observe how many nodes the game actually processes, and whether that count is read from somewhere other than the `BRTR` chunk's own byte content — e.g. a precomputed spatial/streaming index or a node count cached elsewhere in the file/executable. This would need:
- Locating the `BRTR`-parsing or scene-object-instantiation routine in `game_binary/Jaws.exe` (not yet done — no disassembly work has targeted this path specifically).
- A logging hook in `device_proxy.cpp`/`d3d8_proxy.cpp` (or a new hook point) to dump node counts/IDs during a level load, comparable to how the existing freecam/overlay hooks already intercept `SetTransform`/`EndScene`.

Not started — flagged here so a future session doesn't have to rediscover the dead end in static analysis before reaching for this.

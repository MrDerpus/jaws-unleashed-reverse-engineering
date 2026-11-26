# Ecco's dolphin controller in Jaws

**In short:** we decompiled Ecco's player controller (`DolphCtrl`) from *Ecco the Dolphin: Defender of the Future*'s PS2 exe and rebuilt it in C++ in the mod. Then we converted Ecco's model and animations into a Jaws level, and added his sonar (look and sound only). All of it works in-game (user-confirmed 2026-10-21).

**Why it was done (user, 2026-11-27):** mainly as a test of our engine knowledge.
- It checked that what we had worked out about the engine (`BRTR`, resources, skeletons) was right.
- It proved that resources from Ecco: Defender (PS2) can be copied into Jaws (PC) and work: the dolphin model, its animations and the sonar assets.
- A fully playable Ecco was never the main goal.

**How to try it:**
- **Shift+F2** in any level: the shark moves like Ecco.
- **F9 → `DOLPHIN`:** the player is Ecco's model and plays his own clips.
- **F** or the **middle mouse button** underwater: sonar.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/ecco_dolphin_controller_old_2026-11-27.md`.

---

## Contents

1. [The plan](#1-the-plan)
2. [Step 1: decompiling `DolphCtrl`](#2-step-1-decompiling-dolphctrl)
3. [Step 2, Phase A: Ecco movement drives the shark](#3-step-2-phase-a-ecco-movement-drives-the-shark)
4. [Step 2, Phase B1: Ecco's model on the player](#4-step-2-phase-b1-eccos-model-on-the-player)
5. [Step 2, Phase B2: Ecco's own clips](#5-step-2-phase-b2-eccos-own-clips)
6. [Step 3: sonar, decompiled](#6-step-3-sonar-decompiled)
7. [Step 3, sonar in the mod](#7-step-3-sonar-in-the-mod)
8. [Still open](#8-still-open)

---

## 1. The plan

**Port options considered after step 1:**
1. **Model only:** convert `Ecco.gdm` to a Jaws `SKEL` + `GMDL` and place it. No controller.
2. **Ecco movement in the mod:** rebuild the movement states and shared physics, read Jaws input, drive the shark. No sonar, air, HUD or songs.
3. **Full port:** everything, including effects, HUD and sounds. Most of those systems don't exist in Jaws.

**The user chose the middle option:** all 7 movement states plus the idle routines; no sonar, air, songs or HUD at first.
- **A:** Ecco physics drives the shark (§3).
- **B:** convert Ecco's model to a Jaws skeleton and play its clips (§4, §5).
- **C:** a clean handover from the shark to a dolphin. Not done.
- **Then abilities:** sonar first (§6, §7).

---

## 2. Step 1: decompiling `DolphCtrl`

**Sources:**
- PS2 exe `SLUS_203.94`, Ghidra project `~/tools/ghidra_projects/ECCO`.
- Decompiled code in `~/Projects/ECCO/re/dolphctrl/`:

  | File | Contents |
  |---|---|
  | `dolphctrl.c` | All methods |
  | `dolphctrl_annot.c` | With `DolphConfig` reads labelled |
  | `helpers.c` | 30 helper functions |
  | `dolphconfig_offsets.txt` | Config field offsets |
  | `dolphconfig_120NORTH.txt` | One level's config values |

### Findings

- **Decompiling works.** Ghidra's output for the R5900 code is readable. PS2 vector ops appear as `_lqc2`/`_vadd`/`_vmul`/`_vsqrt` intrinsics: plain 4-float maths, easy to translate.
- **None of it is in `Jaws.exe`.** Jaws kept `TRActor` as a 1-field shell; `DolphCtrl` and `DolphConfig` are gone. So a port means rewriting in C++.
- **Size:**
  - `DolphCtrl` = 10 functions, 34 KB.
  - The per-tick function `vf_05C` (`0x19E270`) alone is **28.9 KB: ~4,050 decompiled lines, 150 `goto`s**.
  - With its helpers (`0x19B000`–`0x1B2000`, shared with `TRVolleyCam`, `TRCut`, `TRCoconut`, `DolphConfig`), about 87 KB.
  - It calls **~147 distinct non-virtual engine functions**. None is matched to `Jaws.exe` (`func_pairs.tsv` only pairs virtual methods).
- **The model is the easy half.** Ecco's rig (`Ecco.gdm`, `skeletons/<LEVEL>/Ecco_gdm.json`) is rigid segments: 28 bones, 1,247 vertices, a 319-frame pool. A rigid rig gives Jaws's `WGHT` and `MTOB` directly.

### Where it sits in a level

Ecco's player in 120NORTH:
- **`TRActor`** node 2315, carrying three actions:
  - **`DolphCtrl`** (2322);
  - `TRColGen` (collision);
  - `TREnvirFX` (water effects).
- The dolphin is a `GDSkeletonModel` child (2333, `Ecco.gdm`), with its own `NABubbleSplashAct`.
- **Tuning** comes from a **`DolphConfig`** brick (2 per level, 82 in all), the counterpart of Jaws's `SharkConfig`.
- `DolphCtrl` itself has no reflected fields.
- `DolphCtrl2`/`DolphCtrl3` (~3 KB each; fields `m_EccoModel`, `m_Buble`, `m_MorphEffect`, `m_InitSpeed`, `m_Time`) are small scripted variants.

### `DolphConfig` (119 fields)

- Registered by a separate function (around `0x1AE2C0`), which the generic field dump missed.
- Each field is registered as `GDRegisterField(…, name, …, offA 0, offB)`; the value is at `offB + 4` of the config object that `DolphCtrl+0x34` points to.

| Group | Examples |
|---|---|
| Flags | `m_bSS`, `m_bAutoCtrl`, `m_bVolleyCtrl`, `m_bCollEnv`, `m_bTurnUp` |
| Physics | `m_rGravity` 0.03, `m_rWaterDrag` 0.04, side/vertical/roll turn speeds and bends |
| Swim speed | `m_rS1min` 0.4, `m_rS1max` 5.0, `m_rS1aa`, `m_rS1ar` |
| Other moves | Charge and super charge, push, jumps (`m_rOverridedJump*`), tail-walk (`m_rTW*`), back/brake/strafe, hit reaction |
| Sonar | `m_rSonarAirNeed`; wave, cone and magnet sonar effects |
| Air | `m_AirCapacity` |
| HUD | Meters, icons |
| Sounds | ~15 sets: swim, charge, chirp, fish/turtle/shark/ray songs, air yelps, hurt, death, collisions |
| Effects | Splash, morph, bubbles |

### The tick (`vf_05C`)

Main state at `+0x228`, sub-state at `+0x22C`. States named by the fields and clips they use (probable):

| State | Uses | Probably |
|---|---|---|
| 0 | `m_rBackSpeed`, `m_rBrakeSlowdown`, drag; clips 134–165, 197–213 | Idle / brake / back up |
| 1 | `m_rS1*`, drag; 3 swim cycles; sub-states 0–3, 13 | Swimming |
| 2 | `m_rChargeAccelRatio`, charge bubbles; clips 166–196, 286–318 | Charge (dash) |
| 3 | `m_rOverridedJump*`, vertical bend | Jump / airborne |
| 4 | `m_rTW*`; clip 102–133 | Tail-walk |
| 5 | `m_idsTurn180`; clips 214–249, 250–285 | 180° turn |
| 6 | `m_asra`, `m_rsrg`, button `0x100` held | Circling (radius grows while held) |
| Every tick | Turn/roll physics (`m_rTurnFall`, `m_aTurn180Fall`), `m_rGravity`, hit reaction (`m_aHitMax`), swim sounds, environment collision (`m_bCollEnv`) | Shared |

- **Idle routines:** a second switch (`+0x32C`, 0–5). After 600 idle ticks it randomly starts one involving a global object (`[0x58A9D8]`), probably an ambient or companion event.
- **Fields:** velocity `+0x260`; brick `+0x14` (world matrix `+0x40`, position `+0x70`).
- **Input:** the pad object at `[0x5896A4]+0xD0E8` (buttons `+0xC`, previous `+0x10`).

**Other methods:**

| Method | Address |
|---|---|
| Constructor | `0x19B2A8` |
| Init `vf_06C` | `0x19B5E0` |
| Cleanup `vf_074` (releases effects and HUD) | `0x19C7A0` |
| Checkpoint save `vf_07C` (stores the world matrix) | `0x19E168` |
| `vf_08C` (1.2 KB) | `0x1ADCD8`, not read |

### Animation clips

The clip ranges are in the exe, not the model. `FUN_0019DF80(speed, ctrl, entry, loop_start, loop_end)` plays a range of the frame pool on one of two blend channels (`+0x3F4` selects), cross-fading between the three swim cycles.

| Loop frames | Entry | Probably |
|---|---|---|
| 0–5 | – | Rest (stop) |
| 6–37 | 15 | Slow swim |
| 38–69 | 50 | Medium swim |
| 70–101 | 82 | Fast swim |
| 102–133 | 102 | Tail-walk |
| 134–165 | 152 | Idle / hover |
| 166–196 | 166 | Charge |
| 197–213 | 197 | Brake / back up |
| 214–249 | 214 | 180° turn, part 1 |
| 250–285 | 250 | 180° turn, part 2 |
| 286–318 | 286 | Second charge clip |

They tile `Ecco.gdm`'s 319-frame pool exactly.

---

## 3. Step 2, Phase A: Ecco movement drives the shark

**User-confirmed working in-game, 2026-10-21.** Toggle with **Shift+F2**. Code: `mod/src/ecco.{h,cpp}`.

### What was ported

A structured C++ port of the tick's 3D path:
- **States:**

  | State | Move |
  |---|---|
  | 0 | Idle / brake / back up |
  | 1 | Swim, with speed levels |
  | 2 | Charge / super charge |
  | 3 | Jump |
  | 4 | Tail-walk |
  | 5 | 180° turn (34-entry yaw table at PS2 `0x490208`, summing to π) |
  | 6 | Circling (visual offset + roll) |

- **Physics:** gravity on the part of the body above water, direction-dependent drag, thrust after integration.
- **Steering:** rate smoothing, turn-up auto-level, and the idle look-at-camera routine.
- **Config:** 120NORTH's `DolphConfig` (node 2337).
- **Animation:** clip frames are simulated, because several state changes are timed by them.

**Frames:**
- Ecco basis E0 = −J0, E1 = J1, E2 = −J2. Ecco's nose is −E2; the shark's is +Z.
- Positions are in Ecco units = Jaws units ÷ `scale` (default 4).

### Hooking into Jaws

Engine details: `docs/exe_analysis.md` §6 "Tick, input, water height and the animation runtime".
- **Tick hook:** the shark controller's tick slot `0x7F2944` (`0x7F28FC + 0x48` = `0x667FB0`; thiscall, no args).
- **Each frame, the hook:**
  1. runs the stock tick (unless `skip_shark_tick 1`);
  2. adopts the brick's position, so collision push-out and F8 teleports carry over (a jump of more than 100 units zeroes the velocity);
  3. writes the brick's world matrix and its local matrix (solved through the parent's inverse, keeping the ~2.1 row scale);
  4. sets stale flag `0x20`.
- **Water height:** the function pointer at `0x8B2E9C`, `float f(const float* pos)`. It returns −2147483648.0 where there's no water. The water action points it at `0x633260`/`0x633320`, which return the water brick's world Y (`[0x902EA4]+0xAC`): a flat plane.
- **Stick:** rebuilt from `0x65EAE0`: a `0x1000` deadzone, scaled to ±`0x4000`. (The original prints "Nem Invert" every frame when byte `0x8D1DC1` is 0.)
- **Pad:** `[[0x920E24]+0x88]+8` = buttons, previous buttons, X, Y. Swim = bit `2` or `0x800000`.

### Keys

| Key | Action |
|---|---|
| Game swim button | Swim (each tap adds a speed level) |
| Right mouse button | Charge |
| R | Brake / back up |
| T, Y | 180° turn (Y turns the mirrored way) |
| C | Circle |
| B | Cruise |
| Q, E | Roll |
| U | Turn up |

**Tuning file `jaws_ecco.txt`:** `scale`, `body_length` (3.2), `invert_x`, `invert_y`, `skip_shark_tick`.

### Offline check

The real `ecco.cpp` was run in a scratchpad harness with stubbed Windows calls:
- holding swim stays at level 0.5, about 0.087 Ecco units per frame;
- tapping raises it to 3.9; top speed 0.675 units per frame (expected ≈ 0.66);
- stick turns trace circles; holding the stick pitches into loops;
- with no input it coasts to a stop in state 0 and bobs at the surface when slow;
- a steep, fast breach jumps about 6 Ecco units (24 Jaws units) high on a parabola, then dives back in;
- tail-walk didn't trigger in the scenarios tried (it needs a near-vertical pitch);
- no NaNs.

Then still to check in-game: stick and mouse Y signs, whether the mouse drives pad X/Y, the scale, and how the stock tick and collision interact with the overwritten transform.

---

## 4. Step 2, Phase B1: Ecco's model on the player

**User-confirmed 2026-10-21:** no crash, model and textures fine. Some actions looked janky, because they used mapped shark clips (fixed by §5).

```bash
python3 scripts/build_ecco_dolphin.py [OUT] [--deploy NAME] [--size S]
```

Builds custom level **`DOLPHIN`** on the blank FISH base. In game: F9 → DOLPHIN. The player's model node `GWside` (26124) shows Ecco.

### The conversion

Source: 110L_BAY's `Ecco.gdm`. Ecco's rig is rigid segments: each vertex stored bone-local under one bone.

**Skeleton (`SKEL`):**
- Rest mesh = Ecco's `GMDL` vertices in their original order. Frame 0 rebuilds them to 5e-5.
- `WGHT`: one bone per vertex at weight 1.
- `MTOB` = inverse of the frame-0 world matrix.
- `TRAN`/`ROTS` keep their values: both engines use `local = [R(q)ᵀ | TRAN]`.
- **Check:** a round trip through `rip_skeletons.parse_bones` and Jaws skinning reproduces the `GMDL` to 1e-7.

**Orientation and size:**
- Ecco's nose is local −Z, the shark's +Z, so everything turns 180° about Y: a vector `v` → `diag(−1, 1, −1)·v`, a quaternion `(x, y, z, w)` → `(−x, y, −z, w)`.
- Positions are scaled by 4 / 2.1: Phase A's physics scale divided by `GWside`'s scale. The dolphin comes out at about 77 % of the shark's length.

**Bones:** Ecco's 28 are padded to the shark's 40 with dummy root children, in case code reads bones by index. `WGHT` indices follow the engine's bone order.

**Clips (`ANIM`):**
- The stock controller looks clips up by name, so `ANIM` holds all 73 `Shark_GW_*` names, each mapped to a dolphin range:

  | Shark clips | Dolphin range |
  |---|---|
  | Swims | Swims |
  | Charges | Charge |
  | Turns and slams | 180° turns |
  | Landwalk | Tail-walk |
  | Bites and everything else | Frames 6–69 (two swim cycles), long enough for `Pitbull04`'s +33-frame damage timing |

- The 11 `Ecco_*` ranges are added too.
- The header word after the clip count = Σ(strlen + 1), checked on FISH.
- Root motion is zero.

**Mesh and materials:**
- 3 materials, cloned from the shark's skin `GMAT` 689, with Ecco's textures (body 512², eye, blowhole).
- The forehead star glyphs (`StarText` A–E) keep their vertices but get no triangles.

**Node edit:**
- `GWside` gets `GMDL` 2839 / `SKEL` 2840.
- Its vertex colours are resized to 1,247 and its bounding box recomputed.
- Ancestor `CHBR` sizes are fixed.

---

## 5. Step 2, Phase B2: Ecco's own clips

**User-confirmed working, 2026-10-21.** In Ecco mode, after the shark tick, `PoseDolphin` (`mod/src/ecco.cpp`) poses the model with the clip and frame the simulated `DolphCtrl` is playing.
- Only when the player skeleton has `Ecco.gdm`'s 319-frame pool (the `DOLPHIN` level).
- The stock shark is never touched.

**How** (the animator is described in `docs/exe_analysis.md` §6 "Animation runtime"):
1. Save the first `0x80` bytes of the shark's clip animator (`ctrl+0xBC`).
2. Write the Ecco clip range and frame: speed 0, no cross-fade, weight 1, loop flag. A stopped clip uses the rest frames 0–5.
3. Call `0x4DD250(anim, 0)` so the engine poses the bones.
4. Restore the saved bytes, so the shark logic's own clip timing (and its "clip ended" checks) is unaffected.

---

## 6. Step 3: sonar, decompiled

**In short:** pressing sonar underwater spawns a cone at Ecco's head and a wave that travels forward. Anything the wave touches gets message `0xE`. That message has no receiver in Jaws, so what sonar should *do* there is a design choice.

None of the sonar classes are in `Jaws.exe` (`NASonarAct`, `NASonarConeAct`, `SendSonarAction`, `HasPowerSonarStar`, `DDTractorSonarAct`, `Sonarmap`). The trigger was found with a raw MIPS scan for loads of `DolphConfig`'s sonar offsets.

### The trigger: `FUN_001ABBE8`

Called from `0x1ADAF0`, in `DolphCtrl`'s helper range.
- **Conditions:** sonar button (bit `4`) pressed, and depth (`+0x228` of the second argument) below −2, i.e. underwater.
- **Cooldown:** next allowed tick = now + `m_rSonarFrequency` (1.0 in 120NORTH) × ticks per second (`DAT_00589678`).
- **Sound:** `m_idSonarSnd`, or `m_idPowerSonarSnd` when the sonar type (`+0x188`) is 1 (power sonar, unlocked by `HasPowerSonarStar`).
- **Air cost:** if ability flag `0x2000` is set, it costs `m_rSonarAirNeed` air (2.0) through `FUN_001AD5E0`. That subtracts from air `+0x88`, with a floor of 0 (10 in an easy mode).
- **Spawn:** `FUN_00304920(0x40000000, cone[type], actor, 2, type)`, with `cone[type]` from `m_idConeSonar`'s list.
- **Aiming:** with a target set (`+0x90`/`+0xB4`), the pulse aims at it.

**Holding and double tap:**
- While the button stays down (`+0x190` set), the held-state handler `FUN_00304510` runs and the cooldown keeps being re-armed. So holding never fires again.
- **A new press within 15 ticks** of a pulse (`+0x198` = pulse tick + 15) starts the **magnet sonar** (`m_idMagnetSonarSnd`, then `FUN_00304588` while held).

### The visuals: `NASonarAct` and `NASonarConeAct`

| Class | Vtable | Tick |
|---|---|---|
| `NASonarAct` (wave) | `0x559388` | `0x304220` |
| `NASonarConeAct` (cone) | `0x5592C8` | `0x304E40` |

**Spawner `FUN_00304920`:**
1. shows a hidden template brick (clears `m_nFlags 0x100`) and sets timers of +1 / +0x20 / +0x1E ticks (+0x150 in mode 2);
2. places it at the actor's head bone (bone list `actor+0x1D4`, stride 0x70);
3. clones its child (`FUN_0010A888(…, 0x800)`) as the cone; the cone's action gets the mode, actor, sound handle and flags.

**Cone tick:**
- Keeps the cone on the head bone, oriented from the camera position (`[game+0xB0]+0xE0`) through the head.
- Eases two scale/fade values towards 1 (×0.25 per tick); mode 2 also fades `+0x140`.
- When its timer runs out it hides itself (`0x100`) and stops.

**Wave tick:**
- The wave grows along Z each tick (`FUN_0016E1E8` = a local translate: row 3 += v · rows 0–2).
- While its brick has collision bit `1`, `FUN_0011AC78(game, brick, 1, −1, 0xE)` sends **message `0xE` (sonar)** to everything it touches.
- That's the gameplay effect: receivers react through their own `m_OnSonar` / `m_sonaract` actions (glyphs, creatures, doors). The strings `SONAR MESSAGE`, `MONOLIT SONAR!` and `No sonaract` are those receivers' debug prints.

### The assets

- 120NORTH's dolphin actor (node 2315) carries the hidden cone meshes `sonarkup__Cone01_1/2/3` (*kúp* = cone) and the wave meshes `sonar__OilTank01_*`. Extracted to `~/Projects/ECCO/models/120NORTH/`.
- Their materials have no extracted texture.
- Sounds are in the `ECCOCORE` bank (`audio/sfx/ECCOCORE/`). Sound ID `0x945` (`m_idSonarSnd`) isn't matched to a file.

---

## 7. Step 3, sonar in the mod

**User-confirmed working, 2026-10-21.** Sonar looks and sounds like Ecco's but doesn't affect Jaws objects. The mod's D3D8 proxy draws it, so it needs no level edit and works in any level in Ecco mode (best with the `DOLPHIN` model).

### Using it

- **F** or the **middle mouse button**, underwater only: the head more than 2 Ecco units below the surface, or anywhere if the level reports no water.
- A press fires; holding re-arms the 30-tick cooldown, as in Ecco.
- No magnet or power sonar, no air cost (the port has no air).

**Files:**

```bash
python3 scripts/stage_ecco_sonar.py [--sound WAV]
```

- Writes `jaws_sonar_cone.obj`, `jaws_sonar_wave.obj` (#1 + #2 merged) and `jaws_sonar.wav`.
- The sound defaults to ECCOCORE sample 15, a guess, since the bank has no names. Try `_50_` or `_46_` by ear.
- Read when Ecco mode is switched on. Missing meshes fall back to a generated cone and ring of the same size; a missing WAV plays nothing.

**Tuning in `jaws_ecco.txt`:**

| Setting | Default | Does |
|---|---|---|
| `sonar_head` | 1.3 | Head offset, in Ecco units |
| `sonar_alpha` | 0.6 | Opacity |
| `sonar_ztest` | 1 | 0 draws through walls (in case the depth buffer isn't usable) |

### How it works

**Code:** `mod/src/sonar.{h,cpp}`.
- **`SonarTick`** runs from the Ecco tick hook, after `PoseDolphin`. Head = brick position + nose direction (−E2) × `sonar_head`.
- **`SonarDraw`** runs in `EndScene`, only while the back buffer is the render target (`on_primary_target_`). It uses the last view and projection set there (`DeviceProxy::SetTransform`).
- Additive blend, depth test on, no depth write, colour from `TEXTUREFACTOR`.
- Every render state, texture state, transform, shader, texture, stream and index buffer it touches is restored.
- Sound: winmm `PlaySoundA` from memory, async.

**Behaviour taken from the decompile:**
- The cone stays on the head and points from the camera through it. Scale `+0x34` eases to 1 at 0.25 per tick, `+0x38` follows at 0.25; gone after 32 ticks.
- The wave starts at the head and moves 2.4 Ecco units per tick along its spawn heading. Alpha eases to 1 at 0.2; scale (from 0.2) to 1 at 0.05. Then a 6-tick end phase (scale at 0.25).

**Our own choices:**
- cone alpha = 1 − `+0x38`;
- wave phase 0 = 24 ticks (the spawner doesn't set the clone's timer);
- a linear fade over the end phase (Ecco eases alpha at only 0.02 there, then removes the wave);
- travel along the nose (which way Ecco's spawn frame faces isn't settled);
- the colours.

**Meshes**, from 120NORTH's actor (node 2315):
- cone template `Cone01#1` (node 2435, identity local);
- → mover brick 2443 (collision);
- → wave `OilTank01#1` (node 2445; its local rotation turns mesh Y onto the mover's Z, so the dome's axis is its direction of travel);
- → `OilTank01#2` (node 2454: scale 0.5, offset 0.8 along the axis).
- The `#2`/`#3` cone sets are the other sonar types (`#3`'s wave at scale 2).
- Each `OilTank` mesh is a shallow dome: radius 3.2, height 0.85.

**Offline check:** the tick logic compiled with mingw and run under Wine.
- A pulse fires at the press; a second press during the cooldown is ignored; the next press after it fires.
- The cone is gone in ~0.5 s; the wave travels ~280 Jaws units in 1 s.

---

## 8. Still open

- **Phase C:** a clean handover from the shark to a dolphin.
- **Sonar:** a gameplay effect (Ecco's message `0xE` has no Jaws receiver), magnet and power sonar, air, using the real head bone instead of a fixed offset.
- **Decompile:** `vf_08C`; the sub-states of state 1; which button masks map to which pad buttons; `m_bSS` (read 11 times, the most-used flag).

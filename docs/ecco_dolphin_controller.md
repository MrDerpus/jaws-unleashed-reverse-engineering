# Ecco's player controller (`DolphCtrl`), decompiled for a possible Jaws port

Step 1 of "put Ecco (model + controller) into a Jaws level" (2026-10-21): decompile the controller from
Ecco: Defender of the Future's PS2 executable (`SLUS_203.94`, Ghidra project `~/tools/ghidra_projects/ECCO`),
map what it does and what it depends on, and size a port. **Read-only so far; nothing ported.**
Decompiled sources: `~/Projects/ECCO/re/dolphctrl/` (`dolphctrl.c` all methods, `dolphctrl_annot.c` with
`DolphConfig` reads labelled, `helpers.c` 30 helper functions, `dolphconfig_offsets.txt`,
`dolphconfig_120NORTH.txt` = a level's config values).

## Verdict

- **Decompiling works.** Ghidra's output for the R5900 code is readable; PS2 vector-unit ops show up as
  `_lqc2`/`_vadd`/`_vmul`/`_vsqrt`… intrinsics (plain 4-float vector maths, trivial to translate).
- **It can't run in Jaws as is**, and none of it is in `Jaws.exe` (Jaws kept `TRActor` as a 1-field shell,
  `DolphCtrl`/`DolphConfig` not at all). A port means rewriting it in C++ in the mod (`mod/`).
- **Size:** `DolphCtrl` is 10 functions / 34 KB, of which the per-tick function `vf_05C` (`0x19E270`) is
  **28.9 KB, ~4,050 decompiled lines, 150 `goto`s**; with the helpers around it (`0x19B000`–`0x1B2000`,
  shared with `TRVolleyCam`, `TRCut`, `TRCoconut`, `DolphConfig`) about 87 KB. It calls **~147 distinct
  non-virtual engine functions**; none of them is matched to `Jaws.exe` yet (`func_pairs.tsv` only pairs
  virtual methods).
- **The dolphin model is the easy half:** Ecco's rig (`Ecco.gdm`, `skeletons/<LEVEL>/Ecco_gdm.json`) is
  rigid-segment, 28 bones, 1,247 vertices, a 319-frame pool. Jaws's `SKEL` (decoded) needs `WGHT` and
  `MTOB`, which a rigid rig gives directly (one bone per vertex at weight 1; `MTOB` = inverse rest pose).

## Where it sits in a level

Ecco's player (120NORTH): **`TRActor`** node 2315 carrying three actions, **`DolphCtrl`** (2322),
`TRColGen` (collision), `TREnvirFX` (water effects), with the dolphin as a `GDSkeletonModel` child (2333,
`Ecco.gdm`, its own `NABubbleSplashAct`). Tuning comes from a **`DolphConfig`** brick (2 per level, 82 in
all), the counterpart of Jaws's `SharkConfig`. `DolphCtrl` itself has no reflected fields (everything is
in code or the config). `DolphCtrl2`/`DolphCtrl3` (~3 KB each, fields `m_EccoModel`, `m_Buble`,
`m_MorphEffect`, `m_InitSpeed`, `m_Time`) are small scripted variants.

## `DolphConfig` (119 fields)

Registered by a separate function (`0x1AE2C0` area; the generic field dump missed it), each field as
`GDRegisterField(…, name, …, offA 0, offB)`, value at `offB + 4` of the config object that `DolphCtrl+0x34`
points to. Groups: flags (`m_bSS`, `m_bAutoCtrl`, `m_bVolleyCtrl`, `m_bCollEnv`, `m_bTurnUp`…), physics
(`m_rGravity` 0.03, `m_rWaterDrag` 0.04, side/vertical/roll turn speeds and bends), swim speed
(`m_rS1min` 0.4, `m_rS1max` 5.0, `m_rS1aa`, `m_rS1ar`), charge and super charge, push, sonar
(`m_rSonarAirNeed`, wave/cone/magnet sonar effects), jumps (`m_rOverridedJump*`), tail-walk (`m_rTW*`),
back/brake/strafe, hit reaction, air (`m_AirCapacity`), HUD meters/icons, ~15 sound sets (swim, charge,
chirp, fish/turtle/shark/ray songs, air yelps, hurt, death, collisions), splash/morph/bubble effects.

## The tick (`vf_05C`)

Main state `+0x228`, sub-state `+0x22C`. States named by the config fields and clips they use (probable):

| State | Uses | Probably |
|---|---|---|
| 0 | `m_rBackSpeed`, `m_rBrakeSlowdown`, drag; clips 134–165, 197–213 | idle / brake / back up |
| 1 | `m_rS1*`, drag; 3 swim cycles; sub-states 0–3, 13 | swimming |
| 2 | `m_rChargeAccelRatio`, charge bubbler; clips 166–196, 286–318 | charge (dash) |
| 3 | `m_rOverridedJump*`, vertical bend | jump / airborne |
| 4 | `m_rTW*`; clip 102–133 | tail-walk |
| 5 | `m_idsTurn180`; clips 214–249, 250–285 | 180° turn |
| 6 | `m_asra`, `m_rsrg`, button `0x100` held | circling move (radius grows while held) |
| shared | turn/roll physics (`m_rTurnFall`, `m_aTurn180Fall`), `m_rGravity`, hit reaction (`m_aHitMax`), swim sounds, environment collision (`m_bCollEnv`) | every tick |

A second switch (`+0x32C`, 0–5) runs idle routines: after 600 idle ticks it randomly starts one involving a
global object (`[0x58A9D8]`), probably an ambient/companion event. Velocity is at `+0x260`, the brick at
`+0x14` (world matrix `+0x40`, position `+0x70`), input from the pad object at `[0x5896A4]+0xD0E8`
(buttons `+0xC`, previous `+0x10`). Other methods: ctor `0x19B2A8`, init `vf_06C` `0x19B5E0`, cleanup
`vf_074` `0x19C7A0` (releases effects/HUD), checkpoint save `vf_07C` `0x19E168` (stores the world matrix),
`vf_08C` `0x1ADCD8` (1.2 KB, not read yet).

## Animation clips (answers "clip ranges are probably in the executable")

`FUN_0019DF80(speed, ctrl, entry, loop_start, loop_end)` plays a range of the skeleton's frame pool on one
of two blend channels (`+0x3F4` selects), cross-fading between the three swim cycles. All ranges used:

| Loop frames | Entry | Probably |
|---|---|---|
| 0–5 | – | rest (stop) |
| 6–37 | 15 | slow swim |
| 38–69 | 50 | medium swim |
| 70–101 | 82 | fast swim |
| 102–133 | 102 | tail-walk |
| 134–165 | 152 | idle / hover |
| 166–196 | 166 | charge |
| 197–213 | 197 | brake / back up |
| 214–249 | 214 | 180° turn, part 1 |
| 250–285 | 250 | 180° turn, part 2 |
| 286–318 | 286 | second charge clip |

They tile the 319-frame pool of `Ecco.gdm` exactly.

## Port options (for deciding step 2)

1. **Model only:** convert `Ecco.gdm` to a Jaws `SKEL` + `GMDL` (+ textures) and place it, animated with
   the clip table above. Self-contained; no controller.
2. **Ecco movement in the mod:** port only states 0/1/3/5 (swim, brake, jump, turn) plus the shared
   physics and swim animations, reading Jaws input, driving the dolphin model's brick. Drops sonar, air,
   HUD, songs, charge, tail-walk, idle routines. Needs: the dolphin model (1), the engine calls those parts
   use mapped to Jaws (matching through the 506 paired functions' call sites), and a way to hand control
   from the shark to the dolphin.
3. **Full port:** everything in the tick plus the effects, HUD and sounds the config links to; the bulk of
   those assets and systems don't exist in Jaws.

Still open: `vf_08C`, the sub-state meanings in state 1, which button masks map to which pad buttons, and
`m_bSS` (read 11 times, the most-used flag).

## Step 2, Phase A: Ecco movement drives the shark (2026-10-21, user-confirmed working in-game)

User choice: the "middle" port, meaning all 7 movement states plus the idle routines, with no sonar, air, songs or HUD.
Plan: **A** Ecco physics drives the shark brick (this section), **B** convert `Ecco.gdm` into a Jaws `SKEL`/`GMDL` and play its clips,
**C** a clean handover from the shark to a dolphin.

Code: `mod/src/ecco.{h,cpp}`, toggled with **Shift+F2**. It is a structured C++ port of the 3D path of the tick:
- **States:** 0 idle/brake/back up, 1 swim with speed levels, 2 charge/super charge, 3 jump, 4 tail walk, 5 180° turn (34-entry
  yaw table at PS2 `0x490208`, sum π), 6 circling (visual offset + roll).
- **Physics:** gravity on the fraction of the body above the water, direction-dependent drag, thrust after integration.
- **Steering:** rate smoothing, turn-up auto-level and the idle look-at-camera routine.
- **Config:** 120NORTH's `DolphConfig` (node 2337).
- **Animation:** clip frames are simulated, because several state changes are timed by them. Nothing is drawn with them yet.

Frame mapping: Ecco basis E0 = −J0, E1 = J1, E2 = −J2 (Ecco's nose is −E2, the shark's is +Z). Positions are in Ecco units,
Jaws ÷ `scale` (default 4).

Hook and engine calls:
- **Tick hook:** the shark controller's tick is vtable slot `0x7F2944` (`0x7F28FC + 0x48` = `0x667FB0`, thiscall, no args).
- **Each frame:** the hook runs the stock tick (unless `skip_shark_tick 1`), adopts the brick position (so collision pushes and F8 teleports
  carry over; a jump of more than 100 units zeroes the velocity), then writes the brick's world matrix and its local matrix (solved through the
  parent's inverse, keeping the brick's ~2.1 row scale) and sets stale flag `0x20`.
- **Water height:** read through the function pointer at `0x8B2E9C`, `float f(const float* pos)`, which returns −2147483648.0 when
  there is no water. The water action sets it to `0x633260`/`0x633320`, which return the water brick's world Y (`[0x902EA4]+0xAC`), a flat plane.
- **Stick:** re-implemented from `FUN_0065eae0`, with a 0x1000 deadzone scaled to ±0x4000. The original prints "Nem Invert" every frame
  when byte `0x8D1DC1` is 0.
- **Pad:** `[[0x920E24]+0x88]+8`, laid out as buttons, previous buttons, X, Y. The swim bit is `2` or `0x800000`.

Keys:

| Key | Action |
|---|---|
| game swim button | swim (each tap adds a speed level) |
| right mouse button | charge |
| R | brake / back up |
| T, Y | 180° turn (Y turns the mirrored way) |
| C | circle |
| B | cruise |
| Q, E | roll |
| U | turn up |

Tuning file `C:\jaws_ecco.txt` takes `scale`, `body_length` (3.2), `invert_x`, `invert_y` and `skip_shark_tick`.

**Offline check (scratchpad harness, the real `ecco.cpp` with stubbed Windows calls):**
- Holding swim stays at level 0.5, about 0.087 Ecco units per frame.
- Tapping raises the level to 3.9, and top speed comes out at 0.675 Ecco units per frame (expected ≈ 0.66).
- Stick turns trace circles, and holding the stick pitches it into loops.
- With no input it coasts to a stop in state 0, and it bobs at the surface when slow.
- A steep fast breach jumps about 6 Ecco units (24 Jaws units) high on a parabola, then dives back in.
- Tail walk didn't trigger in the scenarios tried. It needs a near-vertical pitch.
- No NaNs.

Still to test in game: the sign of stick and mouse Y, whether the mouse drives pad X/Y, the scale, and how the stock tick and
collision interact with the overwritten transform.

## Step 2, Phase B1: Ecco's model on the player (2026-10-21, user-confirmed: no crash, model and textures fine, some actions janky from the mapped shark clips)

`scripts/build_ecco_dolphin.py [OUT] [--deploy NAME] [--size S]` builds custom level **`DOLPHIN`** on the blank FISH base.
In game: F9, then DOLPHIN. In that level the player shark's model node `GWside` (26124) shows Ecco.

Conversion (110L_BAY `Ecco.gdm` → Jaws skinned model):
- **Input:** Ecco rigs are rigid segments, with each vertex stored bone-local under one bone.
- **`SKEL` contents:** the rest mesh, which is Ecco's `GMDL` vertices in their original order (frame 0 rebuilds them to 5e-5). `WGHT` gives each vertex one bone at weight 1. `MTOB` is the inverse of the frame-0 world matrix, and `TRAN`/`ROTS` keep their values (both engines use `local = [R(q)ᵀ | TRAN]`).
- **Orientation:** Ecco's nose is local −Z and the shark's is +Z, so everything turns 180° about Y. A vector `v` becomes `diag(−1,1,−1)·v`, and a quaternion `(x,y,z,w)` becomes `(−x,y,−z,w)`.
- **Scale:** positions are scaled by 4 / 2.1, the Phase A physics scale divided by `GWside`'s transform scale. The dolphin comes out about 77% of the shark's length.
- **Bones:** 28 Ecco bones are padded to the shark's 40 with dummy root children, in case code reads bones by index.
- **Bone order:** `WGHT` indices follow the engine bone order. A round trip through `rip_skeletons.parse_bones` and Jaws skinning reproduces the `GMDL` to 1e-7.
- **Clips:** the stock controller looks clips up by name, so `ANIM` holds all 73 `Shark_GW_*` names, each mapped to a dolphin range (swim to swim, charges to charge, turns and slams to the 180° turns, landwalk to tail-walk). Bites and anything else unmapped get frames 6–69, two swim cycles, long enough for Pitbull04's +33-frame damage timing. The 11 `Ecco_*` ranges are added too. The header word after the clip count is Σ(strlen+1), checked on FISH. Root motion is zero.
- **Mesh and materials:** 3 materials are clones of the shark's skin `GMAT` 689 with Ecco's textures (body 512², eye, blowhole). The forehead star glyphs (`StarText` A–E) keep their vertices but get no triangles.
- **Node edit:** `GWside` gets `GMDL` 2839 / `SKEL` 2840, its vertex colours are resized to 1,247, and its AABB is recomputed. The ancestor `CHBR` sizes are fixed as well.

Next, Phase B2: in Ecco mode the mod should play the simulated Ecco clip (`Ecco_*` ranges) instead of whatever shark clip the stock controller requests.

## Step 2, Phase B2: Ecco mode plays the dolphin's own clips (2026-10-21, user-confirmed working)

`mod/src/ecco.cpp` `PoseDolphin`: after the shark tick, Ecco mode poses the model with the clip and frame that the simulated
`DolphCtrl` is playing. This only happens when the player skeleton has `Ecco.gdm`'s 319-frame pool (DOLPHIN level). The stock
shark is never touched.

Engine side (`Jaws.exe`; collected with the other engine findings of the port in `docs/exe_analysis.md` "Tick, input, water height and the animation runtime"):
- **Shark clip animator:** sits at **`ctrl+0xBC`**. `PlayClip` is `0x65E610`, which calls `0x4DCF70` (a two-slot cross-fader).
  Its per-tick update is **`0x4DD250`** (thiscall `(animator, int reset)`, `ret 4`), called by the shark tick at `0x66DF91`.
  A second animator at `ctrl+0x15C` runs when `ctrl+0x24C` is set.
- **Animator fields:**
  - `+0x10` skeleton model
  - `+0x14` frame
  - `+0x1C`/`+0x20` start/end
  - `+0x24`/`+0x28` cross-fade length/remaining
  - `+0x2C`/`+0x30`/`+0x34` slot B start/end/frame
  - `+0x3C` weight
  - `+0x44`/`+0x48` speeds
  - `+0x58` reference frame
  - `+0x60` flags (`8` loop; `1`/`2`/`4` select special per-bone paths)
- **Frame step:** frame += speed × `[engine+0xB4]`. Posing goes through `0x6F6150`; cross-fades use `0x6F6230`.
- **Other animators:** the generic clip-player action (`0x6F75A0`: start `+0x40`, end `+0x48`, speed `+0x50`, frame `+0x64`, loops
  `+0x88`) and `0x6F5EB0` (`thiscall (start, end, frame)`, pose at a float frame, root-motion delta) belong to other animated
  objects.
- **SKEL resource object** (loader `0x6F47D0`, from the skeleton model's vtable `+0x84`):
  - `+0x1C` root-motion array
  - `+0x20` frame count
  - `+0x24` morph frame count
  - `+0x40` vertex count
  - `+0x4C` morph data

Mod side:
1. Save the animator's first 0x80 bytes.
2. Write the Ecco clip range and frame, with speed 0, no cross-fade, weight 1 and the loop flag. A stopped clip uses the rest
   frames 0–5.
3. Call `0x4DD250(anim, 0)` so the engine poses the bones.
4. Restore the saved bytes, so the shark logic's own clip timing (and its "clip ended" checks) is unaffected.

## Step 3 (abilities): sonar, decompiled (2026-10-21, read-only)

User choice after B2: move on to Ecco's abilities, sonar first. All sonar classes (`NASonarAct`, `NASonarConeAct`,
`SendSonarAction`, `HasPowerSonarStar`, `DDTractorSonarAct`, `Sonarmap`) are **missing from `Jaws.exe`**, so a port is
a C++ rewrite in the mod, like the controller. Sources: Ghidra project `ECCO`. A raw MIPS scan for loads of the
`DolphConfig` sonar offsets found the trigger.

### Trigger: `FUN_001ABBE8` (called from `0x1ADAF0`, `DolphCtrl`'s helper range)

- **Conditions:** the pad's sonar button (bit `4` of buttons) is pressed and a depth value (`+0x228` of the second argument)
  is below −2, i.e. underwater.
- **Cooldown:** next allowed tick = now + `m_rSonarFrequency` (1.0 in 120NORTH) × ticks-per-second (`DAT_00589678`).
- **Normal pulse:** plays `m_idSonarSnd`, or `m_idPowerSonarSnd` when sonar type `+0x188` is 1 (power sonar, unlocked
  by `HasPowerSonarStar`).
- **Air cost:** if ability flag `0x2000` is set, costs `m_rSonarAirNeed` air (2.0) through `FUN_001AD5E0`, which
  subtracts from air `+0x88` with a floor of 0, or 10 in an easy mode.
- **Spawning:** calls `FUN_00304920(0x40000000, cone[type], actor, 2, type)`, where `cone[type]` comes from
  `m_idConeSonar`'s list.
- **Holding / double tap (re-read 2026-10-21, corrects "held after 15 ticks"):** while the button stays down
  (`+0x190` set) the held-state handler `FUN_00304510` runs and the 30-tick cooldown keeps being re-armed, so holding
  never fires again. A **new press within 15 ticks** of a pulse (`+0x198` = pulse tick + 15) starts the **magnet
  sonar** (`m_idMagnetSonarSnd`, then `FUN_00304588` while held).
- **Aiming:** with a target set (`+0x90`/`+0xB4`), the pulse is aimed at it.

### Visual and effect: `NASonarAct` (vtable `0x559388`, tick `0x304220`) and `NASonarConeAct` (`0x5592C8`, tick `0x304E40`)

- **Spawner `FUN_00304920`:**
  - shows a hidden template brick: clears `m_nFlags 0x100` and sets timers of +1 / +0x20 / +0x1E ticks (+0x150 in mode 2)
  - places it at the actor's head bone (`actor+0x1D4` bone list, stride 0x70)
  - clones its child (`FUN_0010A888(…, 0x800)`) as the cone, whose action gets the mode, the actor, the sound handle
    and the flags
- **Cone tick:** keeps the cone on the head bone, oriented from the camera position (`[game+0xB0]+0xE0`) through the
  head. It eases two scale/fade values towards 1 (×0.25 per tick); mode 2 also fades `+0x140`. When the timer runs out
  it hides itself (`0x100`) and stops.
- **Wave tick:** the wave model grows along Z each tick (`FUN_0016E1E8` scale). While its brick has collision bit `1`
  set, `FUN_0011AC78(game, brick, 1, −1, 0xE)` sends message **0xE (sonar)** to everything it touches. That is the
  gameplay effect: receivers react through their own `m_OnSonar` / `m_sonaract` actions (glyphs, creatures, doors).
  The strings `SONAR MESSAGE`, `MONOLIT SONAR!` and `No sonaract` are debug prints of those receivers.
- **Assets:** 120NORTH's dolphin actor (node 2315) carries the hidden cone meshes `sonarkup__Cone01_1/2/3` (*kúp* =
  cone) and wave cylinders `sonar__OilTank01_*`, already extracted to `~/Projects/ECCO/models/120NORTH/`. Their
  materials have no extracted texture map. Sounds live in the `ECCOCORE` bank (`audio/sfx/ECCOCORE/`); sound id
  `0x945` (`m_idSonarSnd`) is not matched to a file yet.

**Port consequence:** the trigger, timing, air cost and visuals can be rebuilt as-is. The gameplay half (message 0xE to
`m_OnSonar` receivers) has no counterpart in Jaws, so what sonar *does* to Jaws objects is a design choice.

## Step 3, sonar in the mod: visual + sound (2026-10-21, user-confirmed working)

User's choice: sonar shows and sounds like Ecco's but does nothing to Jaws objects yet. Drawn by the mod's D3D8 proxy,
so no level edit is needed and it works in any level while Ecco mode is on (best with the `DOLPHIN` model).

- **Key:** **F** or the **middle mouse button**, underwater only (head more than 2 Ecco units below the water surface,
  or anywhere when the level reports no water). A press fires; holding re-arms the 30-tick cooldown, as in Ecco. No
  magnet/power sonar, no air cost (the port has no air yet).
- **Code:** `mod/src/sonar.{h,cpp}`. `SonarTick` runs from the Ecco tick hook (`ecco.cpp`, after `PoseDolphin`):
  head = brick position + nose direction (−E2) × `sonar_head` (1.3 Ecco units). `SonarDraw` runs in `EndScene`
  with the last view/projection set while the back buffer was the render target (`DeviceProxy::SetTransform`), additive
  blend, depth test on, no depth write, colour from `TEXTUREFACTOR`; every touched render/texture state, transform,
  shader, texture, stream and index buffer is restored.
- **Behaviour, from the decompile:** the cone stays on the head, points from the camera through the head, scale
  `+0x34` eases to 1 at 0.25/tick, `+0x38` follows it at 0.25, gone after 32 ticks. The wave starts at the head and
  moves 2.4 Ecco units per tick along its spawn heading (`FUN_0016E1E8` is a local translate: row 3 += v · rows 0–2),
  alpha eases to 1 at 0.2 and scale (from 0.2) to 1 at 0.05, then a 6-tick end phase (scale at 0.25).
- **Choices of ours:** cone alpha = 1 − `+0x38`; wave phase 0 = 24 ticks (the spawner doesn't set the clone's timer);
  a linear fade over the end phase (Ecco eases alpha at only 0.02 there and then removes the wave); travel along the
  nose (which way Ecco's spawn frame faces isn't settled); colours.
- **Meshes, from 120NORTH's actor (node 2315):** cone template `Cone01#1` (node 2435, identity local) → mover brick
  2443 (collision) → wave `OilTank01#1` (node 2445; local rotation turns mesh Y onto the mover's Z, so the dome's
  axis is its direction of travel) → `OilTank01#2` (node 2454: scale 0.5, offset 0.8 along the axis). The `#2`/`#3`
  cone sets are the other sonar types (`#3`'s wave at scale 2). Each `OilTank` mesh is a shallow dome, radius 3.2,
  height 0.85.
- **Files:** `python3 scripts/stage_ecco_sonar.py [--sound WAV]` writes `C:\jaws_sonar_cone.obj`,
  `C:\jaws_sonar_wave.obj` (#1 + #2 merged) and `C:\jaws_sonar.wav` (default ECCOCORE sample 15, a guess, since the
  bank has no names; try `_50_` or `_46_` by ear). They are read when Ecco mode is switched on; missing meshes fall
  back to a generated cone/ring of the same size, a missing WAV plays nothing. Sound: winmm `PlaySoundA` from memory,
  async.
- **Tuning** in `C:\jaws_ecco.txt`: `sonar_head` (Ecco units), `sonar_alpha` (0.6), `sonar_ztest` (1; 0 draws
  through walls, in case the depth buffer isn't usable at `EndScene`).
- **Offline check:** the tick logic compiled with mingw and run under wine: pulse at the press, a second press during
  the cooldown ignored, the next press after it fires; cone gone in ~0.5 s, wave ~280 Jaws units in 1 s.
- **Not done yet:** any gameplay effect (Ecco's message 0xE has no Jaws receiver), magnet/power sonar, air, using the
  real head bone instead of a fixed offset.


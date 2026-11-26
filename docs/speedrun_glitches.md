# Speedrun research: Any% and BLOOOOD%

**In short:**
- The game runs at a fixed 30 fps; lag is slow motion.
- Story stages must be played in order; nothing in the shipped data skips one.
- Every in-engine cutscene can be skipped with **Enter**.
- Two real skips exist:
  - **The Arrival**: out of bounds, then a checkpoint restart. Vanilla, user-found.
  - **The Facility**: kill Mr. Shaw before the squid. Counts as completed, but so far only works with no-clip.
- Collision is swept, so speed alone can't pass a wall. Clips would have to come from wedges.
- "Current too strong" barriers are pushes, not walls. DOCKS's buoys push the hardest.

**Categories in mind:**
- **Any%:** new save → end of *The Final Chase*.
- **BLOOOOD%:** the same, on a save named `BLOOOOD` (1,000,000 points for upgrades).

No leaderboard or community glitch list was found (speedrun.com's "jaws" is the 1987 NES game). Research started 2026-10-18 from `Jaws.exe` (Ghidra, objdump) and the level files. Nothing is tested in-game unless marked so.

Rewritten for readability on 2026-11-27. Section numbers are unchanged, since other docs link to them. Old version: `docs/archive/speedrun_glitches_old_2026-11-27.md`.

---

## Contents

1. [Timing: fixed 30 fps](#1-timing-fixed-30-fps)
2. [Story progression: fixed order](#2-story-progression-fixed-order)
3. [Route data: entrances and returns](#3-route-data-entrances-and-returns)
4. [Movement: swim gears](#4-movement-swim-gears)
5. [BLOOOOD%: what the cheat does](#5-blooood-what-the-cheat-does)
6. [Collision: clip candidates](#6-collision-clip-candidates)
7. [Win conditions per stage](#7-win-conditions-per-stage)
8. [Cutscene skipping](#8-cutscene-skipping)
9. [The Facility: Shaw before the squid](#9-the-facility-shaw-before-the-squid)
10. [More sequence breaks to test](#10-more-sequence-breaks-to-test)
11. [The Arrival skip (vanilla)](#11-the-arrival-skip-vanilla)
12. [Checkpoints in every stage](#12-checkpoints-in-every-stage)
13. [How collision really works; push barriers](#13-how-collision-really-works-push-barriers)
14. [To test in-game](#14-to-test-in-game)
15. [Not done yet](#15-not-done-yet)

---

## 1. Timing: fixed 30 fps

**In short:** one game tick and one frame happen only every 33 ms or more. Lost time is dropped. So there's no speed-up from a higher frame rate, and a PC that can't hold 30 fps plays in slow motion.

- **Main loop:** WinMain's loop (`0x726BE0`) runs one engine tick (`[0x920E24]` vtable `+0x50` = `0x6C7800`) and one render (`+0x54`) only when ≥ 33 ms have passed on the millisecond timer (`0x725CF0`, QPC-based). Then it sets `last = now`.
- **Game clock:** each tick adds `engine+0xB4` (1.0; 0 while paused, flags `0x18000`) to `engine+0xB0`.
- **Gameplay never reads real time.** The other QPC users (`0x725CB0`, `0x725EB0`, `0x725F10`) are profiling counters and the "loaded in %.2f ms" print.

**For runners:**
- Max ~30.3 fps, one physics step per frame.
- Under real-time timing, lag costs time directly. Make sure the game holds 30 (settings, DXVK).
- All in-game timers count frames, including the timer deaths at `ctrl+0x5AC`/`0x5B0`.

---

## 2. Story progression: fixed order

**In short:** story progress is one number. Entrances test it with a plain comparison, and no shipped object raises it early. So stages 1–10 and 12 must all be played, in order.

### The progress number

Global **`0x8D011C`** = the last completed story stage. Stage numbers come from the table at `0x89CCF8` (12 bytes per entry, name at `+8`):

| # | Stage | # | Stage |
|---|---|---|---|
| 1 | The Arrival | 7 | A Taste for Blood |
| 2 | The Break Out | 8 | The Deep |
| 3 | The Dead of Night | 9 | The Facility |
| 4 | Hunted | 10 | Blood on the Beach |
| 5 | Predator in the Bay | 11 | Hot Pursuit (cut) |
| 6 | The Angry Armada | 12 | The Final Chase |

Other numbers: 0 / 13 / 14 = Open Ocean South / East / West, 15 Canals, 16 Underwater Caves, 17 Fisherman's Isle, 18 Title.

### The entrance check

**`MBLoadChecker`** (vtable `0x7D871C`, activation `0x495310`, tick `0x4954F0`) compares its `m_stage` (`PROP 0x080005D2`) with progress. `m_type` (`0x080005D1`) = 1 means a free area.

| Test | Result |
|---|---|
| stage ≤ progress | "Enter this completed stage" |
| progress = stage − 1 | "Enter this stage" |
| progress < stage − 1 | "This stage is locked." |

The prompt pauses the game (`0x69AC70(0x10000)`), but real time keeps running: confirm it at once.

### Everything that writes progress

All 40 references checked:

| Code | Class | What it does |
|---|---|---|
| `0x539750`, `0x546E20` | `MSMenu` / `MSSaveCompletedLoadMenuItem` | progress = max(progress, current stage `world+0x170`), except 0 and 13–17. Runs from the **Stage Completed Save** menu, in every level; not in the pause menu (checked in AQUARIUM). |
| `0x53B4A0` | `MSSaveGame` | Same max rule |
| `0x457BB0` | `BGSetMissionCompleted` | progress = current stage. Placed in ARMADA and CHASE only. |
| `0x5F93B0` | `Stage0Quest` (open zones) | If the dev field `PROP 0x080011CA` (`StoryMissionCompletedCheat`) ≠ −1, progress = that value; then 10 → 11, skipping Hot Pursuit. **It's −1 in every shipped level.** |
| `0x5F1E80` | `Stage4Quest` | Sets 3/4/5 from a world field. KATATAMA only, already behind the lock. |
| `0x647D50` | `MSPowerGenerator` | Sets 4. KATATAMA only. |
| `0x5350F0` | `MSStageSelect` (TITLE) | Level select: stage *i* → progress = *i* − 1, points = *i* × 20,000. Renames the profile `TEST` unless it's `SHAAARK`. |

**Level select** (cheat `SHAAARK`, or all licence plates, message 590) jumps to any stage. It presumably belongs in its own category.

---

## 3. Route data: entrances and returns

**Entrances:** all are area triggers that fire on **enter** and test a vertical column, so touching the edge of the radius at any depth is enough.

| Stage | Zone | Centre (X, Z) | Radius |
|---|---|---|---|
| 1 The Arrival | OPEN_S | (−1344, −2670) | polygon area (`ANPolyArea`) |
| 2 The Break Out | OPEN_S | (−1114, −1858) | 300 |
| 3 The Dead of Night | OPEN_S | (83, −1661) | 300 |
| 4 Hunted | OPEN_NW | (−2591, −651) | 415 |
| 5 Predator in the Bay | OPEN_S | (2872, −1600) | 415 |
| 6 The Angry Armada | OPEN_NE | (4269, 1616) | 515 |
| 7 A Taste for Blood | OPEN_S | (4262, −3658) | 115 |
| 8 The Deep | OPEN_NW | (−1917, 3816) | 615 |
| 10 Blood on the Beach | OPEN_NE | (2789, 217) | polygon area |
| 12 The Final Chase | OPEN_NW | (−3660, 1160) | 115 |

**Zone exits** (polygon areas, centres shown; each zone has its own coordinates):

| From | To South | To East | To West |
|---|---|---|---|
| OPEN_S | – | (3717, −1401) | (−3093, −1604) |
| OPEN_NE | (3372, −2015) | – | (952, 4310) |
| OPEN_NW | (−2730, −2207) | (922, 4032) | – |

**Where each stage sends you** (`GDLoad` names, `PROP 0x08001839`):
- **START → AQUARIUM directly** (1 → 2, no swim).
- **DEEPSEA → DEEPSEA2** (8 → 9).
- Back to OPEN_S: AQUARIUM, BEACH, KATATAMA, WRACK.
- Back to OPEN_NW: DOCKS, DEEPSEA2, CHASE.
- Back to OPEN_NE: ARMADA, TOWN.

**Rough legs** (straight lines; the arrival points aren't known):
- 3 → 4 crosses OPEN_S to the west exit (~3,200), then on to DOCKS (~1,600).
- 4 → 5 goes back across all of OPEN_S (~6,000 to KATATAMA).
- The Deep and The Final Chase are at the far side of OPEN_NW.
- The longest legs are 4→5, 7→8 and 10→12.

The real arrival points (F8 overlay on arrival) would turn this into a proper route.

---

## 4. Movement: swim gears

**In short:** top speed takes three timed taps, then holding. Plain straight swimming is the fastest way to travel.

Swim speed works in gears (`0x667010`, `ctrl+0x250`). Values from `SharkConfig`, the same in every level:

| Gear | `m_swimspeed` (units/frame) | `m_acceltime` (frames) |
|---|---|---|
| 0 | 0.2 × stick | 0 |
| 1 | 1.0 | 15 |
| 2 | 1.5 | 7 |
| 3 | 2.08 | 5 |

**Rules:**
- **A new press** shifts up one gear, but only if the speed is already ≥ that gear's speed − 0.3 (`m_swimpumpdspeed`). Otherwise nothing (debug prints `Valtas` / `Nem Valtas`). Max gear 3.
- **Holding** keeps the gear.
- **Releasing** for more than 5 frames drops to gear 0 (`m_noreleasetime` 30 − `m_nemlassultime` 5). Pressing again within 10 frames (`m_pushtime`) restores the old gear.
- Target speed = `m_swimspeed[gear]` × (1 + 0.5 × Speed ability).

**So:** tap, wait until speed ≈ 0.7, tap, wait until ≈ 1.2, tap, hold.
- Stock top speed: 2.08 × 30 ≈ **62 units/s**. The overlay's `Spd` shows it.
- Mashing does nothing extra. A short release is safe.

**User-tested 2026-10-18:**
- Straight-line swimming is fastest.
- Tapping from idle reaches top speed only slightly sooner than holding.
- Jumping out of the water slows the shark, even with a headbash.
- Charging a headbash at top speed also slows it.
- So the charge (`m_bigchargespeed` 2.0, air 2.1) and low air drag (0.99) aren't faster travel.

---

## 5. BLOOOOD%: what the cheat does

**In short:** `BLOOOOD` only gives 1,000,000 points. Spend them on **Speed** (travel ⅓ faster) and **Power** (5× damage).

- **`MSCharInputMenuItem`** (`0x541F40`): a profile named `BLOOOOD` gets points = 1,000,000 (`0x8D012C`). Abilities still have to be bought (pause menu → Abilities).
- `SHAAARK` instead writes the unlock flags `0x8D0154`–`0x8D0166`.

**Abilities:** save bytes `0x8D0124`–`0x8D0128`, levels 0–4, multiplier = level × 0.25 (`0x53AD50`).

| Ability | Controller field | `SharkConfig` mul | At level 4 |
|---|---|---|---|
| Accuracy | `+0x72C` | 1.0 | Bite/charge targeting ranges ×2 (`0x662DE2`) |
| Power | `+0x730` | 4.0 | **Damage ×5** (bite formula `0x65CB30`) |
| Speed | `+0x734` | 0.5 | **Swim ×1.5**, ~94 units/s |
| Hunger | `+0x738` | 1.333 | Max hunger 100 → 233 |
| Defense | `+0x73C` | 1.333 | Max health 100 → 233 |

- Buying Health or Hunger raises the maximum but **doesn't refill** the current value.
- To test: when the Abilities menu opens (message 333 "NOW YOU CAN UPGRADE YOUR ABILITIES!" suggests a point in the tutorial), and the cost of each level.

---

## 6. Collision: clip candidates

**In short:** the terrain step is skipped only while dead, in a death animation, or while biting a fixed object (FIXBITE). FIXBITE is the one clip candidate, but rare. In The Facility, the squid arena is sealed by objects added by script, not just rock.

### When terrain collision is skipped

Terrain collision is one step per frame, `0x65BFC0` (`docs/exe_analysis.md` "Collision step and no-clip"). It's skipped when:

- **`ctrl+0x810` ≠ 0.** Set only in the dead state (7, `0x669D8C`), cleared on activation (`0x664E80`). Not reachable alive.
- **State `0x10` = FIXBITE:** biting a fixed object (clips `SHARK_GW_FIXBITEA_NAGY`/`_KICSI`/`_GRAB`).
  - Velocity is zeroed; the shark is held relative to the target (`ctrl+0x3C`, position at `+0x598`).
  - **Idea:** bite a fixed object against a thin wall, let go, and see which side the push-out picks.
  - **User note:** few fixed objects can be bitten, and they break after a while. So it's rare and one-shot. Untested as a clip.
- **State `0x16`:** a death animation (`SHARK_GW_DIE_I17L31O_`).

**Object contacts** (boats, debris; `0x671AB0`) have their own 4-try push-out. Big moving objects pushing the shark into terrain are a second thing to try.

The stuck teleport: after 90 stuck frames the shark can be sent **back** to its last safe point (saved after 40 contact-free frames). So a half-clip that leaves the shark wedged gets undone, not completed. Details in §13.

### The shark's collision shape

- Terrain uses the spheres under `GWside` whose `PRIM` (class `0x20008007`) mask (`PROP 0x080018C9` = `0x8C01`) matches the query mask `0x18001`.
- Centre `0x080018CD`, radius `0x080018CE`, in bone space under `GWside`'s ×2.1 scale:

  | Sphere | Radius | World size |
  |---|---|---|
  | `ExcluderHead` | 0.7 | |
  | `ExcluderFinRight` / `Left` | 0.4 | |
  | `ExcluderBody` / `1` / `2` | 0.9 / 1.2 / 1.0 | about 0.8–2.5 in all |

- `MouthBrick` and `ExcluderFarok` (tail) have mask 0 and don't touch terrain.

### The Facility's squid arena (2026-11-23, static)

Goal: a vanilla way into Mr. Shaw's area (§9).

**No missing collision.** A coverage check compared every visible triangle over 4 units² with all 141k placed collision triangles. Only particle/effect meshes, the helipads and the placeholder squid lack collision. There's no visible wall you can just swim through.

**Script-added barriers seal the arena:**
- The end of the squid entrance movie (`squid_movie_end`, act 858; also `daralozartracserelo` 857):
  - adds **`BossSquidRoomCenter`** (3980, 18 collision meshes, around (0, −240, 0));
  - swaps the open dredge rollers `kotorohengerek` (3773, 12 meshes) for the closed **`kotorohengerek_osszezarva`** (3734, 9 meshes, at y −88, the shaft above).
- The squid's death (`squidkinyirva`, act 2545) removes both and adds `generator_room` (5976).
- The 8 `Kizaro_Lap_Kozepes` plates at the columns go one per broken column.

**Route after the squid:** generator room → control room (`compromb`, quest event 4; adds the opened door `ajto kinyilt` 5589) → front glass → `TorhetoUveg 1` starts Shaw.

**Clip candidates:**
1. Be inside the rollers' or room-centre's volume when they're added (end of the entrance cutscene, skipped or not). Which way does the push-out throw the shark?
2. The closed rollers are an object, so object contacts and terrain push-out may disagree at their edges.
3. FIXBITE against something next to those barriers.

---

## 7. Win conditions per stage

**In short:** each stage has one quest object, and events reach it from game code and level actions. Several stages end on an explosion object. **User result 2026-10-18: none of the early-ending leads below worked in normal play**; they're kept as a record of what the code does, and §10 retests some with no-clip.

### How a stage ends

- The active quest is global `0x8FE494`. Events arrive through its vtable slot 26 (`+0x68`).
- **Senders:**
  - 62 call sites in the exe (`push N; call [quest+0x68]`);
  - `NAQuestEvent` / `StageDocksQuestEvent` / `StageDeepSeaQuestEvent` actions send their `m_event` when started (`0x5ED520`/`0x5ED570`);
  - `GDMsgSend` actions send named messages (`MSG_PIER_DESTROYED`, `MSG_BOSSSQUID_COLUMN_DESTROYED`, …);
  - ship AI sends `MSG_SHIP_EVENT`.
- Event 10000 (`0x2710`) = "shark spawned", from `MLSharkCtrl` activation. Events 10000–10063 are only counted (`this+0x70+(id−10000)·4`).
- **Checkpoints:** slot 27 starts checkpoint action *n*. In DOCKS, DEEPSEA and DEEPSEA2 only when the state is *n* − 1, so those are strictly ordered.

**Explosion endings.**
- The target node carries an `NACollisionDetector` action. It adds the explosion node `m_delay` ticks after it starts; the explosion sends the event or starts the ending.
- No level control ever *starts* a detector; controls only stop one (DEEPSEA2's column destructors).
- So the engine starts it when the parent object is hit. Inferred, not traced. Every detector parent has `m_nFlags` bit `0x800`.

### The table

| Stage | Quest | What ends it | Order enforced? |
|---|---|---|---|
| 1 The Arrival (START) | `NATutorialQuest` `0x7ED3A8` (+ `MBStageTutorial`) | State 0x15 → **4 zodiac kills** (counter `+0x1F4`, counted only while state > 0x13; launched one by one) → timer → adds `AuroraComesMovie` (192) → `LoadOpen` → Stage Completed Save + `LoadAquarium` | **No** (lead 1) |
| 2 The Break Out (AQUARIUM) | `Stage2Quest` `0x7ED5F4` | Event 10 = **an orca dies**. Both senders (`MSOrca` `0x4FEE24`, `0x51D209`) play `Orca.Die`. One `MSOrca` (`Orca Action` 27723, boss at (1011, −190, −304)), live from the start. | Not in code, but **sequential in play** (user): the cage gates block the way |
| 3 The Dead of Night (BEACH) | `StageBeachQuest` `0x7ED9A4` | Kill all 12 party guests (`m_21plusyoungs`) → truck cutscene → event 1 = `Explosion 4`, added by the detector on **`Expltarget 1` (−296, 19, −24)** → refinery explodes → `MSG_OIL_REFINERY_MOVIE_END` → checkpoint action 5 | **No**: event 1 only checks "not already played" (`+0x210`) (lead 2) |
| 4 Hunted (DOCKS) | `StageDocksQuest` `0x7EDA78` | The quest tracks objectives `SHUTLIGHTS`, `OPENGATE`, `SNEAKIN`, `DESTROYBARGE`. The ending is started by `GDControl ToxicExpl` on **`Explosion 2` (−361, 11, 236)**, only while the shark is alive. | Checkpoints yes; the ending isn't tied to quest state (lead 3) |
| 5 Predator in the Bay (KATATAMA) | `Stage4Quest` `0x7ED6D0` + `MSAuroraBoss` | Event 4 ×3 (the platforms, `MSOilRig` `0x650010`) and event 6 (`MSPowerGenerator` `0x648998`), **in either order** → state 3 → Aurora boss. The boss's end isn't decoded. | Not in code, but **sequential in play** (user) |
| 6 The Angry Armada (ARMADA) | `Stage6Quest` `0x7ED7F8` | Waves from `m_wave_01..05` (2/6/7/1/1 boats) spawn near the shark. Only current-wave boats count. Thresholds 2, 3, 2, then a cutscene step (state 12), then 1 → `m_end_act` | Yes |
| 7 A Taste for Blood (WRACK) | `StageWreckQuest` `0x7EDCA8` | Every 30–59 ticks, counts the living divers (`m_scubadivers`, 4 `NAScubaRef`: (397, −8, 17), (279, 8, 90), (409, −20, 167), (243, −20, 13)). None left → `m_winmovie` | No: kill them in route order |
| 8 The Deep (DEEPSEA) | `StageDeepSeaQuest` `0x7EDDC0` | 4 `CTRLROOM_DESTROYED` messages (from `JTMineControl`) → event 1 + `m_onroomsdestroyed` (act 3) | No |
| 9 The Facility (DEEPSEA2) | `StageDeep2Quest` `0x7EDE50` + `NASquidBoss` | **4 of 8 `BossSquidColumn`s broken** → `m_winmovie`. Columns sit on a radius-73 ring round (0, −271, 0); each detector starts its destructor, which sends the message 100 ticks later. | No |
| 10 Blood on the Beach (TOWN) | `Stage9Quest` `0x7EE31C` | Event 10000 → "Kill %d people" (`MSG_HUMAN_EVENT` 0xE from group `tokill`; fail if too many escape) → event 1 → boat phase (`m_boattime` × 30 frames) → `mayor_yacht` sunk (state 6) → `m_raiser` delay → done | Yes |
| 12 The Final Chase (CHASE) | `Stage11Quest` `0x7ED88C` | Ship event 1 (sinking) from `orca_2_turbo` → `m_end_act` 388 (`BGSetMissionCompleted` at t = 0, credits at 190). Phase 2 starts when `orca_2_new` drops below half health or `ss_host` disappears. The 35 s intro has a `SkipAction`. | Yes |

**Notes:**
- **The Facility in play** (user): the player can't break the columns. The squid breaks them once it's blind, after the player eats its eyes, and that kills it. So "4 columns" and "squid dead" are the same event.
- **ARMADA's dev fields** `m_cheat`/`m_cpskip`: `m_cheat` ≠ 0 would restore a checkpoint at load, but it's 0 in the shipped data.
- **TOWN:** each destroy path sends one ship event, so no double count.

### The leads (all dead in normal play)

**Lead 1: the tutorial pier skip (START).**
- The quest listens for `MSG_PIER_DESTROYED` (`0x5EEF82`). On the next tick, if the state is < 0x16, it sends itself event 16 (`0x5EFA3B`).
- Event 16 sets state 0x15 and launches the first zodiac **from any earlier state**.
- The message comes from the three pier buildings' `GDMsgSend` actions: `EpuletEp 1` (1099, 2, −303), `EpuletEp` (2185, 0, −313), `EpuletEpKajalda 1` (1145, 0, −219). Each sinks (`MBSullyeszto`) once its 6 posts (`m_tamasztok`, damage 15) break.
- The normal order is … → piers → zodiacs → Aurora, so an early pier skips everything in between.
- The problem: the tunnel boulders (`TunnelBlockingDust`, (536, −13, 24)) sit between the start (−1136, −21, 49) and the piers.
- **Later confirmed in play as part of the Arrival skip (§11).**

**Side finding:** `MBStageTutorial`'s completion waits for flag `[0x8DA1C0]+0x12C`.
- Only `NAAuroraRope` sets it (`DDGameState.m_koteldied`, "the rope died"; `0x4BC8E3`, `0x4BCE98`, `0x4BD19A`).
- That's the cut rope fight, never placed (`docs/cut_content.md` §3 "How the rope fight worked"). So that path is dead, and the tutorial ends through the Aurora movie.
- Its activation (`0x4B12B0`) also jumps straight to state 4, so states 0–3 (boat damage → `ZodiacComingEvent`) are dead too.

**Lead 2: early refinery explosion (BEACH).**
- Normally a barrel from the truck phase hits `Expltarget 1` on the pier (flags `0x842`).
- Any hit there before the guests are dead should play the ending at once.
- The `Barrel generator` (−225, 22, 271), next to the `BridgeShooters`, isn't added by any control, so it may be live from the start.

**Lead 3: early toxic explosion (DOCKS).**
- `Explosion 2` (flags `0x12`) is in the world from the start and runs the ending once its controls start.
- Nothing references it by ID, so presumably the hit/explosion path starts it, e.g. an explosive barrel (`BGDetonator EBD`) at the toxic tank before the other objectives.

---

## 8. Cutscene skipping

**In short:** every in-engine story cutscene can be skipped with **Enter**, after a short grace period. A skip runs the same ending as watching it, so it never changes quest state. It saves about 13 minutes over a full run.

### How a skip works

A cutscene is a `GDPlayMovie` action:

| ID | Field |
|---|---|
| `0x080018A7` | `m_Movie` |
| `0x080018A8` | `m_ObjList` |
| `0x080018A9` | `m_SkipDelay` |
| `0x080018AA` | `m_CanSkip` |
| `0x080018AB` | `m_OnSkip` (an action ID) |
| `0x080018AC` | `m_KeepRunning` |

**The setup in the levels:**
1. The real camera movie has `m_CanSkip` = 0.
2. A second `GDPlayMovie` with `m_CanSkip` = 1 plays a dummy one-frame `GMOV` and keeps running. This is the **skip watcher** (named `ForSkip`, `FakeGdPlayMovie`, `SkipEnabler`, …).
3. The watcher is started a little after the cutscene begins (`SkipPreventor`, `SkipProtector`, `SkipKeslelteto` = "skip delayer").
4. Each tick (`0x6D95F0`), once past `m_SkipDelay`, a skip press makes it jump to the last frame, stop itself and start `m_OnSkip`.
5. `m_OnSkip` is usually **the same ending action** the cutscene's timeline starts at its last step: kill the movie node, give back `SharkCamera`, start the next step.

### The skip button

- **The key is Enter** (user, 2026-10-18). Esc does nothing.
  - That matches The Final Chase's prompt `]# SKIP` (`]` = the Enter icon).
  - The PC button table (`0x8ACAE8`) lists `SKIP` → Esc; that entry is stale. Enter is also `OK`/`START`/`CONT`.
- The check (`0x453A00`, engine vtable `0x7D2810` slot `+0x58`) fires on a **new press** of input bit `0x400` or `0x800`. Holding does nothing. A press before the watcher starts is lost, so press again.
- **Grace period:** 0.5–3 s for most cutscenes (15–90 ticks). Exceptions in Predator in the Bay: the power-plant explosion (6 s) and Brody's escape (`m_SkipDelay` 350, **11.7 s**).

### Spamming Enter can crash the game

User-observed, 2026-10-18. Cause not found.
- A watcher stops itself when it fires, so one cutscene can't be skipped twice.
- Chained skips almost never overlap. The one case: A Taste for Blood, where part B's skip still has a kill pending at t = 30 when part C's watcher arms at t = 25.
- Candidates:
  - a press on the same tick the timeline starts the ending itself, so the ending runs twice;
  - Enter's other jobs (pause, the Stage Completed Save menu) firing while a skip is still tearing the cutscene down.
- Needs a crash address (`PROTON_LOG=1`).

### Time saved per stage

Timeline length minus grace period, at 30 ticks/s. Whether every cutscene is on a given route isn't checked.

| Stage | Skippable cutscenes (saving) | Total |
|---|---|---|
| 1 The Arrival | Shaw's son's death ~17 s, Aurora / harpoon ending ~31 s | ~48 s |
| 2 The Break Out | Dolphin show 8, exhibition hall 6, pagoda 7.5, lab 16, meeting 28, ID card 8, `Scene1`/`Scene2` 9 + 8, escape 7 | ~98 s |
| 3 The Dead of Night | Opening 30, truck/barrels 28, refinery 13 | ~71 s |
| 4 Hunted | Barges out 32, fishermen ~15, ending ~7 | ~55 s |
| 5 Predator in the Bay | Flyover 12, Brody's escape 13, power plant 4, each oil rig 10 (×3), Aurora 9.5 | ~69 s |
| 6 The Angry Armada | Movie 601 12.5, movie 602 40 | ~53 s |
| 7 A Taste for Blood | Intro: skipping A goes straight to C, skipping B too (~51); part C 13; mayor's speech 47; mid 15; "Nemo" 15.5 | ~140 s |
| 8 The Deep | Intro: one skip ends both parts | ~51 s |
| 9 The Facility | Shaw's entrance 7, squid entrance 29, squid defeat 26, outro 41 | ~104 s |
| 10 Blood on the Beach | Intro 28, cinematics 9.01/9.02 14 + 9, others 6 + 9 | ~66 s |
| 12 The Final Chase | Intro 34.5, shark explodes 4 | ~38 s |

**Not skippable:**
- Short camera cuts (`NACutScene` outside a skippable movie): The Facility's column cams (2 s each), START's `CutSceneCamera` (250 ticks).
- WMV videos (`MPGPlay`, `m_skip`) only play in the title menu and after the final stage, so they don't matter.

### State a skip leaves behind

Found by comparing what each full timeline does to objects outside the movie with what the skip path does. Almost all differences are sounds, cameras and particles.

- **The Dead of Night truck cutscene:**
  - The movie hides the refinery (`Level3_facility`, 21 `FacilityLit`, 11 `Facility Spot`, `Facility_Pipeline`) and the pier tops (`molo_teteje_001 1–4`, `moloveg_teteje_001 1–2`). It shows them again only at ticks 820/860.
  - The skip path (`truckmoziszkipp`) kills the movie, and has an empty `show` step at t = 860.
  - So **after a skip they may stay hidden**, and runtime-hidden objects lose collision too. This assumes killing the movie cancels its pending steps; not traced.
  - Only visual: the ending trigger `Expltarget 1` isn't under these nodes.
- **Hunted part B:** `TugRef` (a tug boat with a float/destroy action) starts at t = 449, just after the skip action. An earlier skip never starts it. Probably cosmetic.
- **Dead of Night and Angry Armada** skips don't start `NAWaterYCamera 1` (underwater fog/far plane). It autostarts anyway (flags `0x2`), so harmless.
- **No skip advances or bypasses quest state.**

---

## 9. The Facility: Shaw before the squid

**In short (user find, 2026-11-23):** with no-clip (F7) the shark can pass from the squid arena to Mr. Shaw and kill him while the squid lives. **That ends the stage, and it counts as completed**: Blood on the Beach unlocks (user-tested). A full skip of the squid fight. It still needs a vanilla way past the arena's barriers (§6).

**Why it works** (from DEEPSEA2's scripting, `dump_gdcontrol.py`):
- **Shaw's phase starts** when the glass `TorhetoUveg 1` breaks (5927, at (1072, −207, −106), ~1,080 units from the squid room).
  - Its destructible hook (`m_robbcontrol` `0x08000673`) starts `mrshaw_entrancestarter` (act 5731) → Shaw's entrance movie → `moziszkipp` → `mrshawaktivalo`.
  - That adds the divers, 2 minisubs, the hiding places and `NAScubaRef MrShaw` (5948).
  - It also starts an escape countdown: explosion flashes from 20 s to ~115 s, and a `JTTimer` (5728, 120) that adds `EndMovieSharkDead` (the shark dies in the blast).
  - **Nothing checks the squid or the quest state.** Normally the wall keeps you out until the squid is dead.
- **Shaw's death** (`PROP 0x08000FE0`) runs `stageend` (act 5722 on `QuestStuff 1`):
  - adds the `ShawKilled` movie;
  - starts `stageend_mbscore` (`MBScore`, event 36);
  - stops the gameplay groups `jatekcuccok`/`jatekcuccok2`;
  - adds `outromovieoverlay` after 550 ticks.
  - **Also no squid or quest check.**
- The normal quest events (squid entrance 2, squid dead 3, control room 4, `destroyctrlcenter` 5) are never sent. Shaw's death ends the stage through its own script.

**Result:** the mission ends and returns to OPEN_NW, as after a normal finish. The squid's entrance and defeat cutscenes alone are ~55 s.

---

## 10. More sequence breaks to test

**In short:** the Shaw skip works because the ending hangs off an object that's in the level from the start, only walled off. These other stages have the same shape. §7's leads were dead in normal play because the targets couldn't be reached; with F7 no-clip and F8 they can be tested. If one works, it becomes a target for a real clip.

Found by tracing every script path to each level's `Stage Completed Save`, keeping only triggers live at load.

| Stage | Target (F8 coordinates) | What should happen | Why it might work |
|---|---|---|---|
| 2 The Break Out | The boss orca `Orca Root` ≈ (1011, −190, −304) | Kill it → event 10 → stage ends | Live from load; event 10 isn't gated; normally the cage gates keep you out |
| 4 Hunted | Toxic barge `HitCounter` (2083) at (−360, 0, 236); `Explosion 2` at (−361, 11, 236) | 2 hits (`BGDetonator` → `DeadCheck` → `ToxicExpl`) → ending → `Stage Completed Save` | Barge and explosion live from load; the ending ignores quest state. What counts as a hit (ram, bite, barrel) isn't known. |
| 3 The Dead of Night | `Expltarget 1` on the pier (−296, 19, −24) | A hit → refinery explosion and ending | Event 1 only checks "not already played" |
| 1 The Arrival | Pier buildings | **Done in vanilla (§11)** | |

**Checked, not breaks:**
- DEEPSEA's end zones (`palyavege` ×3) are added only after all control rooms are destroyed.
- KATATAMA's platforms and generator, and WRACK's four divers, already go in any order.

The trace script is a scratch tool; its long paths through shared props are noisy, so only short, named chains were followed.

---

## 11. The Arrival skip (vanilla)

**In short (user find, 2026-11-23):** no mod needed. Get out of bounds, touch a later tutorial bubble from under the map, restart from that checkpoint, then break a pier. **Needs a new game**: the tutorial bubbles only appear then (user). What hides them on a replay isn't traced.

### The route

1. **Out of bounds:** swim against the "current too strong" field close to a wall. The shark slips past it.
2. **Swim under the map** to where the tutorial bubble appears after the cage-diver kill and boulder blast. The bubble still comes to the shark, and touching it **sets a checkpoint**.
3. **Pause → restart from last checkpoint.** The shark respawns at the checkpoint, back in bounds, in part 2 of the tutorial. `SecondPart` is at (660, 0, 35), past the boulder.
4. **Skip the swimmers:** break a pier building's posts so it falls into the water. That spawns the Coast Guard zodiacs.
5. **Sink all the zodiacs** → Brody harpoons Jaws (`AuroraComesMovie`) → AQUARIUM.

### Why it works

- **The bubbles** are `TutorialQuestRef` objects along the route (1850–1857; e.g. `TutorialQuestRef 6` at (711, −11, 32), just past `TunnelBlockingDust` at (536, −13, 24)). The quest sets its checkpoint by which bubble the shark reaches, not by what's been done.
- **Restarting at `SecondPart`** (node 677) runs `CheckPointCleanUp` (act 678). It kills `TunnelBlockingDust` and clears the cage, the cage diver's boat markers, the armoured SeaSeeker and `LastSeaSeekerRef`: the skipped objectives. The stage is left consistent. `BeforeZodiacs` (679) has the same cleanup.
- **Step 4** is §7's lead 1 (`MSG_PIER_DESTROYED` → event 16 → zodiac phase from any earlier state), now confirmed in play.
- **Step 5** is the stage's normal ending.
- **No clip is involved.** The "current too strong" boundary is a `NAWhirl2000` current that pushes rather than blocks, so it can be out-swum (§13).

---

## 12. Checkpoints in every stage

**In short:** the Arrival skip works because START's checkpoint is set by *reaching* a spot and its restore script removes the barriers. Two other stages have a checkpoint set by reaching or breaking something: The Break Out's orca door and (ruled out) Hunted's gate.

### How checkpoints work

- Each stage's quest has:
  - `m_checkpoints` (`PROP 0x08001161`): respawn nodes by number (high slots are side-challenge spawns);
  - `m_checkpointactions` (`0x08001162`): what runs on "restart from last checkpoint".
- A checkpoint is set by an `MBCheckPointSet` action (`0x080011EF` = number) or by quest code (KATATAMA, TOWN, BEACH, ARMADA).
- Restarting respawns the shark at the checkpoint node, back in bounds.
- **Reach-set** below = set by getting somewhere or breaking something, which an out-of-bounds route could do early.

| Stage | # | Respawn (node, position) | Set by | Restore script | Reach-set? |
|---|---|---|---|---|---|
| 1 The Arrival | 0 | `SecondPart` 677 (660, 0, 35) | Tutorial bubble | `CheckPointCleanUp`: kill `TunnelBlockingDust`, clear cage, boat markers, armoured SeaSeeker, `LastSeaSeekerRef` | **Yes, used** |
| | 1 | `BeforeZodiacs` 679 (1104, 0, −183) | Tutorial bubble | Same | Yes |
| 2 The Break Out | 0 | `CheckPointSlide1` 1190 (351, −70, 190) | `NotPS2_NextSceneStarter` | Act 9: stop the intro | No |
| | 1 | `CheckPointGreattank` 1191 (43, −35, 13) | Breakout movie | Act 9 | No |
| | 2 | `CheckPointOrca` 1192 (1123, −187, −208), in the orca arena | **Breaking the iron door `ajto`** (7928, at (656, −82, 190)) | Act 10: stop the intro | **Yes** |
| 3 The Dead of Night | 0 | `AtTruckStart` 136 (44, 0, 295) | Quest code | Kill fuse boxes, opening overlay, `SwimmersTrigger`, 4 party guests, `crowd 1`; suspend the truck; add SFX | No |
| 4 Hunted | 0 | `CheckPoint Start` 1638 (−520, −10, −523) | Stage start | `Reload CP Start`: reset guards, map bricks, start quest | No |
| | 1 | `CheckPoint Gate` 1641 (197, −12, −10) | `NACollisionDetector CP Gate` on that node | `Reload CP Gate`: open the gate, kill the 3 fuse boxes, light paths and 2 guards, add barge/barrel markers | Yes, but past the gate (below) |
| 5 Predator in the Bay | 0 | `SharkPosReal 1` 213 (363, 0, −1083) | Quest code | – | No |
| | 1 | `Power Plant Shark Died Pos` 3802 (101, −10, 114) | Quest code | – | No |
| 6 The Angry Armada | – | None listed (quest code with `m_cpskip`) | | | |
| 7 A Taste for Blood | 0 | `CheckPoint 1` 31 (51, −10, 38) | Entering `ANPolyArea 1` (104, 0, 75), at the start | Kill that area and the intro | Yes, but it's the start |
| 8 The Deep | 0–3 | `chkpoint 1–4`: (−209, −573, 356), (1309, −483, −321), (−362, −483, −845), (−281, −575, −39) | Each control room's destruction | None listed | No |
| 9 The Facility | 0 | `csekkpojnt` 2542 (27, −79, 352) | Squid death | `facility eleszto`: post-squid state | No |
| 10 Blood on the Beach | 0, 1 | `CheckPointRebornPos` 144 (2739, −7, 741), `… 1` 143 (2755, −7, 900) | Quest code | Act 7: stop the intro, start `HordokElesztoje` | No |
| 12 The Final Chase | – | None | | | |

**The Break Out's orca door:** breaking `ajto` runs `AjtoBetortControl`. That plays the arena entrance (teleporting the shark in), sets checkpoint 2 and sends `InOrcaTank1`. Killing the orca then ends the stage (§10). Open: can the door be reached and broken before the earlier tanks?

**Hunted's gate checkpoint is not a skip.** Its trigger box (z −13.4 to −9.5) is just past the gate, so the gate must already be open (user, 2026-11-23).

---

## 13. How collision really works; push barriers

**In short:**
- Collision is **swept** along each frame's whole move, so speed alone can't pass a wall.
- After 8 push-out rounds the step gives up. A clip would have to come from a wedge where two surfaces push against each other (untested).
- "Current too strong" barriers are pushes: `NAWhirl2000` currents and `ANTol` buoys. DOCKS's buoys are uncapped and tightly packed.

### Swept collision

- The first time a brick moves in a frame, `0x697290` saves its start-of-frame world matrix (brick `+0xEC`, flag `0x80000000`; skipped when brick flag `0x8` is set).
- The pair test (`0x695F30` → `0x6E15D0`) gets the start and current matrices and keeps the **earliest time of impact** along the move.
- This replaces the older "overlap push-out, not a sweep" reading.

### The shark's step

- `0x65BFC0` runs up to **8 rounds** of query (`0x6C80C0`, mask `0x18001`) and push-out (`0x4E4DA0`: back along the contact normal by 1 − t + margin).
- If still colliding after round 8, it **gives up** and leaves the shark where the last push put it. The velocity becomes the last contact normal × `SharkConfig+0x920`, and a stuck frame is counted.
- After 90 stuck frames, a new press of input bit 4 does the "SafePoint Teleport".

### Where clips could come from (inference, untested)

- Where two surfaces push in opposite or sharp directions (a narrow gap, a wedge between walls, a wall meeting the seabed or an object), each push moves the shark into the other.
- After 8 rounds the shark is left wherever the last push put it, which could be the far side of one surface. The next frame's sweep starts from there.
- Holding swim into the wedge would repeat this every frame.
- **Recipe:** find a gap narrower than the shark, or a sharp corner between two separate collision pieces. Swim in at a shallow angle and hold, ideally with something else pushing (a current, held prey, an explosion). Jittering means the 8-round limit is being hit.
- **Holding prey** (`ctrl+0x204`) adds the prey's collision with its own push (`0x4E4F20`), whichever contact came first. A held object pressed into a wall may push the shark oddly.

**DOCKS gate:**
- The wings `RightGateWing`/`LeftGateWing` (2028/2029) are ~2.5 units thick (z −19.7 to −17.0), y −35 to +7.6, with mesh collision (`MREG` 0xA0E/0xA0D).
- `RightGateWing` also carries an **invisible box** (`PRIM 0x20005004`): 172 units wide (x 118.8–290.3), y −35 to **+19.7**, ~2.7 thick. Jumping over needs a ~20-unit leap plus the shark's size.
- The box runs through the two small piers beside it (`Kismolo_05 1`/`_06 1`, x 136–180 / 219–263, z −33.6 to −3.6, top 5.5). **The box–pier joints and the box–seabed edge are the wedge candidates.**

### Currents (`NAWhirl2000`)

**The Arrival's boundary is a current** (user, 2026-11-23): it pushes back, so it can be out-swum after a short struggle. A nearby wall helps a little.

**Fields:** `PROP 0x080013BB` + index: `m_targets`, `m_movetargets`, `m_noshark`, `m_moveit`, `m_traverseall`, `m_centerpull`, **`m_rad`** (`…13C1`, reach), `m_grad` (`…13C2`, 1 = linear falloff), **`m_force`** (`…13C3`), `m_turntodir`, `m_turnrate`. Runtime: `+0x154` rad, `+0x15C` grad, `+0x164` force.

**The push** (`0x63BD80`, vtable slot `+0x84`) follows the **path's direction**, with size `m_force × (1 − d / m_rad)`, where d is the 3D distance from the path line. Strongest on the line, zero at the edge.

| Level | Currents | Force | Radius | Notes |
|---|---|---|---|---|
| START | 21 (`NAWhirl2000 1–21`) | 3.0 | 50 | All identical. Two rows: y −6 along z −88…−24 (x −914…−1196), and y −28 along z 121…185 (x −927…−1196), joined by a line at x ≈ −1220 (z −9…140). Neighbours ~40–45 apart, so they overlap. |
| DEEPSEA | 4 control-room currents | 1.3 | 11 | Flags `0xA`: not in the world until a script adds them |
| DEEPSEA | 3 `VerticalWhirl` (mine whirls) | 6.0 | 13 | `m_centerpull` = 1, vertical, y −652 to −237 |
| KATATAMA | `NAWhirl2000 1` (126, −12, 220–271) | 1.0 | 50 | Very weak |
| WRACK | `WrackWhirl1` (−360, 0, 93), box x −504…−310 | **20.0** | 50 | ~7× START's; effectively impassable near its line |

**Why START's walls feel different though every current is the same** (inference):
1. Distance from the nearest line: the push fades toward the 50-unit edge, and the lines sit at fixed depths (y −6 or −28), so swimming well above or below weakens it.
2. Overlap: where two currents' areas overlap, both push.
3. Direction: you can swim across the flow instead of against it.

For scale: the shark tops out at 2.08 units/frame (× up to 1.5 with Speed), against a peak of 3.0. Whether `m_force` uses the same units isn't checked. **Best try:** cross where only one current reaches, as far from its line and depth as possible.

### Buoys (`ANTol`)

**`ANTol`** (*tol* = push) is attached to the **buoy template `BolyaDef`**, so every buoy of a level's boundary pushes.

**Fields:** `PROP 0x080002B2` + index: `m_type`, `m_radius`, `m_fmul`, `m_delay`, `m_forcemax`.

**The push** (tick `0x43F6A0`, vtable `0x7D18D4`):
- Every `m_delay` ticks, if the shark's **horizontal** (x, z) distance is inside the radius, it sends `MSG_WHIRL` (`0x5F`).
- Push = the buoy's Z axis × (1 − d² / r²) × `m_fmul`.
- It points along the buoy's own facing (from its world matrix at brick `+0x9C`), not away from the buoy. So overlapping buoys facing the same way add up.
- **Capped at `m_forcemax` only when `m_type` ≠ 0.**
- Depth doesn't matter.
- How the shark turns `MSG_WHIRL` into motion isn't traced.

**Because of the squared distance**, a buoy pushes near full strength for most of its radius. A DOCKS buoy (r 50, fmul 20, uncapped):

| Horizontal distance | 0 | 25 | 35 | 45 | 50 |
|---|---|---|---|---|---|
| Push | 20 | 15 | 10.2 | 3.8 | 0 |

**By level:**

| Level | Buoys | Type | Radius | fmul | Cap | Spacing (min / median / max) |
|---|---|---|---|---|---|---|
| **DOCKS** | 30 | **0** | 50 | 20 | **none** | 33 / 53 / 73: most points are inside 2 buoys |
| TOWN | 41 | 0 | 60 | 20 | none | 65 / 87 / 96 |
| ARMADA | 76 | 0 | 70 | 20 | none | 97 / 97 / 117 |
| FISH | 72 | 1 | 71 | 20 | 0.45 | 64 / 70 / 70 |
| GAUNTLET | 64 | 1 | 71 | 20 | 0.45 | 81 |
| KATATAMA | 38 | 1 | 60 | 20 | 0.45 | 65 / 90 / 117 |
| MINEMSHA | 45 | 1 | 71 | 20 | 0.45 | 21 / 44 / 44 |
| AQUARIUM, WRACK | Top-level `ANTol`s | 0 | 50 | 1 | none | – |
| OPEN_S / OPEN_NE / OPEN_NW | 41 / 40 / 39 | 1 / 1 / **0** | 500–1500 | 15–20 | 0.5 / 0.5 / none | – |

- A capped (type 1) buoy is effectively a flat 0.45 everywhere except the outer ~1 % of its radius.
- An uncapped (type 0) buoy pushes up to **20, about 44× more**. DOCKS packs them tightest; that's why it feels abusive. TOWN and ARMADA are the same kind with wider gaps.

**DOCKS's buoy line:** x −711 to 560, z −797 to −545 (the north edge, toward OPEN_NW).
- **Two gaps are wider than two radii**, so there's no push at their midpoints:
  - buoys 1662/1670, 124 apart, midpoint (553, −619);
  - buoys 1664/1672, 107 apart, midpoint (−701, −598).

  These are the line's turns at the east and west ends. Land or other collision may block them; untested.
- The next weakest spots (68–76 apart; ~8–11 push from each side at the midpoint, ~17–22 combined) are along z ≈ −795 near x −153, −80, −8, 184 and 258.

Engine side: `docs/exe_analysis.md` "Push barriers".

---

## 14. To test in-game

1. **Gear 3 timeout:** does it ever time out (`m_bigspeedtime` 150 frames; purpose unconfirmed)?
2. **FIXBITE next to walls** for clips (§6).
3. **BLOOOOD:** when the Abilities menu opens, upgrade costs, Speed ×1.5 on the overlay.
4. **Arrival points** in each zone after each stage (F8 overlay), to finish the route.
5. **Frame rate:** does it hold 30 everywhere on the runner's PC?
6. **Cutscene skip:** after skipping The Dead of Night's truck cutscene, are the refinery and pier tops still there? For the spam crash: which cutscene, and a `PROTON_LOG=1` log with the crash address.
7. **No-clip sequence breaks** (§10): AQUARIUM orca early, DOCKS toxic barge, BEACH `Expltarget 1`.
8. **Wedge clips** (§13): the DOCKS gate box–pier joints; The Facility's arena barriers (§6).
9. **DOCKS's zero-push buoy gaps** (§13).

**Done:**
- Tap vs hold: tapping from idle is quicker (2026-10-18).
- Jumps and charges as travel: both slower (2026-10-18).
- Tutorial pier skip, Dead of Night early refinery, Hunted early toxic explosion: dead in normal play (2026-10-18). The pier part works inside the Arrival skip (§11).
- The Facility's columns: only the blinded squid breaks them, and that kills it (2026-10-18).
- Shaw before the squid: works with no-clip, counts as completed (2026-11-23).

---

## 15. Not done yet

- **Win conditions:** the Aurora boss end in KATATAMA (`MSAuroraBoss`), and the engine path that starts `NACollisionDetector`s.
- **Cutscene skipping:** the Enter-spam crash; which key sets bit `0x400` vs `0x800`; whether killing a movie node cancels its pending steps.
- **Death and restart:** the pause menu's Restart re-activates the controller; does quest progress survive it?
- **The Arrival bubbles:** what hides them when replaying from an existing save.

Scratch helper scripts used (not in the repo): a class-from-vtable lookup via the static-init descriptor stores (`mov [desc], factory_vt`), an `ACTN` dumper with `CLAS`/`ACCM` names, a node-class dumper, the entrance table, and the completion trace (§10).

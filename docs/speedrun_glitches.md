# Speedrun research: Any% and BLOOOOD%

*Started 2026-10-18 from static analysis of `game_binary/Jaws.exe` (Ghidra + objdump) and the level files. Nothing here is tested in-game yet unless marked so.*

No Jaws Unleashed leaderboard or community glitch list turned up (speedrun.com's "jaws" is the 1987 NES game), so everything below comes from the code. Two categories in mind:

- **Any%**: new save → end of The Final Chase.
- **BLOOOOD%**: the same, on a save named `BLOOOOD` (1,000,000 points to buy upgrades with).

---

## 1. Timing: fixed 30 fps step, lag = slow motion

- WinMain's loop (`0x726BE0`, message loop at the end) runs one engine tick (`[0x920E24]` vtable `+0x50` = `0x6C7800`) and one render (`+0x54`) only when **≥ 33 ms** have passed on the millisecond timer (`0x725CF0`, QPC-based), then sets `last = now`. Lost time is dropped, never caught up.
- The tick advances the game clock `engine+0xB0` by `engine+0xB4` = **1.0 per tick** (0 while paused, flags `0x18000`). Gameplay never reads real elapsed time; the other QPC users (`0x725CB0`/`0x725EB0`/`0x725F10`) are profiling counters and the "loaded in %.2f ms" print.

Consequences:
- Max ~30.3 fps, one fixed physics step per frame. **No fps-unlock speedup** with the stock exe.
- **A PC that can't hold 30 fps runs the game in slow motion.** Under real-time timing, lag costs time directly, so runners should make sure the game holds 30 (graphics settings, DXVK).
- All in-game timers (mission timers, timer deaths at `ctrl+0x5AC`/`0x5B0`) count frames.

## 2. Story progression: fixed order, no lock bypass

Global **`0x8D011C`** = story progress (number of the last completed story stage). Stage numbers come from the table at `0x89CCF8` (12 bytes per entry, name at `+8`):

| # | Stage | # | Stage |
|---|---|---|---|
| 1 | The Arrival | 7 | A Taste for Blood |
| 2 | The Break Out | 8 | The Deep |
| 3 | The Dead of Night | 9 | The Facility |
| 4 | Hunted | 10 | Blood on the Beach |
| 5 | Predator in the Bay | 11 | Hot Pursuit (cut) |
| 6 | The Angry Armada | 12 | The Final Chase |

0 / 13 / 14 = Open Ocean South / East / West, 15 Canals, 16 Underwater Caves, 17 Fisherman's Isle, 18 Title.

**The entrance check `MBLoadChecker`** (vtable `0x7D871C`, activation `0x495310`, tick `0x4954F0`) compares its `m_stage` (`PROP 0x080005D2`, `m_type` = `0x080005D1`, 1 = free area) with the progress counter:
- stage ≤ progress (story stage) → "enter this completed stage"
- progress == stage − 1 → "enter this stage"
- progress < stage − 1 → "This stage is locked."

A plain integer comparison, so **missions have to be done in order**. The prompt sets the pause flag (`0x69AC70(0x10000)`), so the game is frozen while it's up but real time keeps running: confirm it at once.

**Every writer of `0x8D011C`** (checked all 40 references):

| Code | Class | What it does |
|---|---|---|
| `0x539750`, `0x546E20` | `MSMenu` / `MSSaveCompletedLoadMenuItem` | progress = max(progress, current stage number `world+0x170`), except 0 and 13–17. Runs from the **Stage Completed Save** menu (in every level; not in the pause menu, checked in AQUARIUM) |
| `0x53B4A0` | `MSSaveGame` | same max rule |
| `0x457BB0` | `BGSetMissionCompleted` | progress = current stage number (placed in ARMADA, CHASE only) |
| `0x5F93B0` | `Stage0Quest` (open zones) | if dev field `props+0x94` (`PROP 0x080011CA`, debug string `StoryMissionCompletedCheat`) ≠ −1, progress = that value; then 10 → 11, so Hot Pursuit is skipped and The Final Chase opens. **The field is −1 in every shipped level** |
| `0x5F1E80` | `Stage4Quest` | sets 3/4/5 from a world field (KATATAMA only, already behind the lock) |
| `0x647D50` | `MSPowerGenerator` | sets 4 (KATATAMA only) |
| `0x5350F0` | `MSStageSelect` (TITLE) | level select: chosen stage *i* → progress = *i* − 1, points = *i* × 20,000; renames the profile `TEST` unless it is `SHAAARK` |

So no shipped object advances progress early; there's **no story skip** in the data. Any% has to play stages 1–10 and 12, and the time is in movement, routing and how fast each mission ends.

Level select (cheat `SHAAARK`, or collecting all license plates, message 590) jumps straight to any stage, so it presumably belongs in its own category.

## 3. Route data: entrances and returns

Stage entrances (all area triggers fire on **enter** and test a vertical column, so touching the edge of the radius at any depth is enough):

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

Zone exits: OPEN_S → East (3717, −1401), → West (−3093, −1604); OPEN_NE → South (3372, −2015), → West (952, 4310); OPEN_NW → South (−2730, −2207), → East (922, 4032) (polygon areas, centres shown). Each zone has its own coordinates.

Where each story level sends you (raw `GDLoad` stage names, `PROP 0x08001839`):
- **START → AQUARIUM directly** (stages 1 → 2, no swim).
- **DEEPSEA → DEEPSEA2** (8 → 9).
- Every other stage returns to its zone: AQUARIUM, BEACH, KATATAMA, WRACK → OPEN_S; DOCKS, DEEPSEA2, CHASE → OPEN_NW; ARMADA, TOWN → OPEN_NE.

Rough legs (straight lines, ignoring terrain and the unknown arrival points): stage 3 → Hunted crosses OPEN_S to the west exit (~3,200) and on to DOCKS (~1,600); Hunted → Predator in the Bay goes back across all of OPEN_S (~6,000 to KATATAMA); The Deep / Final Chase sit at the far side of OPEN_NW. The longest legs are 4→5, 7→8, 10→12. Getting the real arrival points (`F8` overlay on arrival) would turn this into a proper route.

## 4. Movement: the swim gear system (`FUN_00667010`)

Swim speed works in gears (`ctrl+0x250`), with values from `SharkConfig` (same in every level):

| Gear | `m_swimspeed` (units/frame) | `m_acceltime` (frames) |
|---|---|---|
| 0 | 0.2 (× stick) | 0 |
| 1 | 1.0 | 15 |
| 2 | 1.5 | 7 |
| 3 | 2.08 | 5 |

- Each **new press** of swim shifts up one gear (debug print `Valtas`), but only if the current speed is already ≥ that gear's speed − `m_swimpumpdspeed` (0.3); otherwise `Nem Valtas` (no shift). Max gear 3.
- **Holding** keeps the gear. **Releasing** for more than 5 frames (`m_noreleasetime` 30 − `m_nemlassultime` 5) drops back to gear 0; pressing again within 10 frames (`m_pushtime`) restores the old gear.
- Target speed = `m_swimspeed[gear]` × (1 + `m_abspeedmul` 0.5 × Speed ability).

So **top speed is reached by three timed taps, then holding**: tap, wait until speed ≈ 0.7, tap, wait until ≈ 1.2, tap, hold. Stock top speed is 2.08 × 30 ≈ **62 units/s**; the overlay's `Spd` shows it. Mashing does nothing extra (presses below the threshold don't shift), and a short release is safe (up to 5 frames without losing the gear, 10 frames with a re-press).

**User-tested 2026-10-18:** the fastest movement is plain swimming in a straight line, and tapping swim from idle reaches max speed only slightly sooner than holding (matches the gear logic: the gain is the shift-up timing, a fraction of a second). Jumping out of the water slows the shark down, even with a headbash, and charging a headbash at max speed also slows it down. So charge (`m_bigchargespeed` 2.0, `m_bigchargeairspeed` 2.1) and the low air drag (`m_airdragfront` 0.99) don't make a faster travel move.

## 5. BLOOOOD%: what the cheat does

- `MSCharInputMenuItem` (`0x541F40`): a profile named `BLOOOOD` gets **points = 1,000,000** (`0x8D012C = 0xF4240`). Nothing else; abilities still have to be bought (pause menu → Abilities). `SHAAARK` instead writes the unlock flags `0x8D0154`–`0x8D0166`.
- Five abilities, save bytes `0x8D0124`–`0x8D0128`, levels 0–4, multiplier = level × 0.25 (`0x53AD50`):

| Ability | Controller field | `SharkConfig` mul | At max (level 4) |
|---|---|---|---|
| Accuracy | `+0x72C` | 1.0 | bite/charge targeting ranges ×2 (`0x662DE2`) |
| Power | `+0x730` | 4.0 | **damage ×5** (`0x65CB30` bite formula) |
| Speed | `+0x734` | 0.5 | **swim speed ×1.5** → ~94 units/s |
| Hunger | `+0x738` | 1.333 | max hunger 100 → 233 |
| Defense (health) | `+0x73C` | 1.333 | max health 100 → 233 |

- Buying Health/Hunger raises the maximum but **doesn't refill** the current value (`0x53AD50` only clamps down).
- Biggest wins for the category: **Speed** (every open-ocean leg ⅓ shorter) and **Power** (boss and kill objectives 5× faster). To test: whether the Abilities menu is open from the start of the tutorial (message 333 "NOW YOU CAN UPGRADE YOUR ABILITIES!" suggests it unlocks at some point) and the cost of each level.

## 6. Collision: clip candidates

Terrain collision is one step per frame, `FUN_0065BFC0` (see `exe_analysis.md` "Collision step and no-clip"): push-out along the contact normal up to 8 times, "stuck" after that, and after > 89 stuck frames a teleport **back** to the last safe point (saved after 40 collision-free frames). The step is skipped when:

- `ctrl+0x810` ≠ 0. Set only in the **dead** state (7) handler (`0x669D8C`, when an animation change is pending), cleared on controller activation (`0x664E80`, stage load/respawn). Not reachable alive.
- **State `0x10` = FIXBITE**: biting onto a fixed object (clips `SHARK_GW_FIXBITEA_NAGY`/`_KICSI`/`_GRAB`). Velocity is zeroed and the shark is held relative to the bite target (`ctrl+0x3C`, position saved at `+0x598`). **Best clip candidate:** bite a fixed object that sits against or inside a wall, let go, and see which side the push-out puts the shark on. A thin wall plus a release on the far side would be a clip. **User note 2026-10-18:** few fixed objects can be bitten, and they're destroyed after being bitten for a while, so the setup is rare and one-shot per object. Still untested as a clip.
- State `0x16`: a death animation (`SHARK_GW_DIE_I17L31O_`).

Object contacts (boats, debris; `FUN_00671AB0`) have their own 4-try push-out, so big moving objects pushing the shark into terrain is a second thing to try.

**Clip research, 2026-11-23 (static, for a vanilla route into Mr. Shaw's area in The Facility):**
- **Shark collision shape:** terrain contacts use the spheres under `GWside` whose `PRIM` (class `0x20008007`) mask (`PROP 0x080018C9` = `0x8C01`) matches the query mask `0x18001`: `ExcluderHead` r 0.7, `ExcluderFinRight`/`Left` 0.4, `ExcluderBody`/`1`/`2` 0.9/1.2/1.0, in bone space under `GWside`'s ×2.1 scale, so about **0.8–2.5 world units**. `MouthBrick` and `ExcluderFarok` (tail) have mask 0 and don't touch terrain. Fields: centre `0x080018CD`, radius `0x080018CE`.
- **(Corrected in section 13: the test IS swept from the start-of-frame position.)** Original note: `0x6C80C0` collects contacts at the current position and `0x4E4DA0` pushes the brick back along the contact normal by the penetration, then removes the velocity into the surface. A move longer than a sphere's size in one frame could in principle cross a thin surface. Top swim speed is ~3.1 units/frame (2.08 × 1.5 at max Speed), and normal play doesn't tunnel, so ordinary swimming isn't enough. Whether the charge, jump or a hit knockback moves farther per frame isn't measured (the mod's speed overlay can show it).
- **No missing collision in DEEPSEA2's terrain:** a coverage check (every visible triangle over 4 units² against all `PRIM`-linked `MREG` surfaces placed in the level, 141k collision triangles) found only particle/effect meshes, the helipad platforms and the placeholder squid without collision. There's no visible wall you can simply swim through.
- **What seals the squid arena is script-added objects, not just rock:** the end of the squid entrance movie (`squid_movie_end`, act 858; also `daralozartracserelo` 857 inside the movie) adds **`BossSquidRoomCenter`** (3980, 18 collision meshes, around (0, −240, 0)) and swaps the open dredge rollers `kotorohengerek` (3773, 12 meshes) for the closed ones **`kotorohengerek_osszezarva`** (3734, 9 meshes, at y −88, the shaft above the arena). The squid's death (`squidkinyirva`, act 2545) removes both and adds `generator_room` (5976). The 8 `Kizaro_Lap_Kozepes` plates at the columns are removed one per broken column. Onward route after the squid: generator room → control room (`compromb`, quest event 4, adds the opened door `ajto kinyilt` 5589) → front glass → `TorhetoUveg 1` starts Shaw. **Candidates:** (1) be inside the rollers' or room-centre's volume at the moment they're added (end of the entrance cutscene, also when it's skipped) and see which way the push-out throws the shark; (2) the closed rollers are an object, so object contacts (`0x671AB0`) and terrain push-out may disagree at their edges; (3) FIXBITE (state `0x10`) against something next to those barriers, since that state skips the terrain step entirely.
- **The 90-frame stuck teleport** returns the shark to its last safe point (saved after 40 contact-free frames), so a half-clip that leaves the shark wedged gets undone, not completed.

## 7. Win conditions per story stage

**How a stage ends.** Each story level has one quest object (the active one is the global `0x8FE494`). Events reach it through its vtable slot `+0x68` (slot 26). There are 62 send sites in the exe (`push N; call [quest+0x68]`), plus level objects:
- `NAQuestEvent` / `StageDocksQuestEvent` / `StageDeepSeaQuestEvent` actions send their `m_event` when started (`0x5ED520`/`0x5ED570`).
- `GDMsgSend` actions send named messages (`MSG_PIER_DESTROYED`, `MSG_BOSSSQUID_COLUMN_DESTROYED`, …).
- Ship AI sends `MSG_SHIP_EVENT`.
- The quest's slot 27 starts checkpoint action *n*. In DOCKS, DEEPSEA and DEEPSEA2 it only does so when the state is *n* − 1, so those checkpoints are strictly ordered.

Event 10000 (`0x2710`) comes from `MLSharkCtrl` activation ("shark spawned"). Events 10000–10063 are only counted (`this+0x70+(id−10000)·4`).

Several stages end on an **explosion object** that waits under a target node: the target carries an `NACollisionDetector` action that adds the explosion node `m_delay` ticks after it starts, and the explosion node sends the event or starts the ending.
- No level control ever *starts* a detector. Controls only stop one (DEEPSEA2's column destructors).
- So the engine starts it when its parent object gets hit. That's inferred, not traced in code. Every detector parent has `m_nFlags` bit `0x800`.

Level ↔ stage, from the entrance loaders: START 1, AQUARIUM 2, **BEACH 3 The Dead of Night**, **DOCKS 4 Hunted**, KATATAMA 5, ARMADA 6, WRACK 7, DEEPSEA 8, DEEPSEA2 9 The Facility, **TOWN 10 Blood on the Beach**, CHASE 12.

| Stage | Quest | What ends it | Order enforced? | Lead |
|---|---|---|---|---|
| 1 The Arrival (START) | `NATutorialQuest` `0x7ED3A8` (+ `MBStageTutorial`) | quest state 0x15 → **4 zodiac kills** (counter `+0x1F4` = 4, counted only while state > 0x13; the quest launches them one by one) → timer → adds `m_auroramoviestarter` (node 192, `AuroraComesMovie`) → `LoadOpen` → Stage Completed Save + `LoadAquarium` | **No**: see below | **Pier skip** |
| 2 The Break Out (AQUARIUM) | `Stage2Quest` `0x7ED5F4` | event 10 = an **orca dies**. Both senders (`MSOrca` `0x4FEE24` and `0x51D209`) play `Orca.Die` and send 10. AQUARIUM has one `MSOrca` (`Orca Action` 27723 on `Orca Root`, boss at (1011, −190, −304)), live from the start (only suspended in revisit mode) | Events 0–9 set the state directly, with no order check, but **in play the path is sequential** (user, 2026-10-18) | none: the cage gates (`InOrcaTank1–4` events from `Ketrec_Ajto`/`TorhetoRacs` destructibles) block the way |
| 3 The Dead of Night (BEACH) | `StageBeachQuest` `0x7ED9A4` | kill all 12 `m_21plusyoungs` (party guests) → truck cutscene → event 1 = `Explosion 4`, added by the detector on **`Expltarget 1` at (−296, 19, −24)** → `EndMovieStarter` (oil refinery explodes) → `MSG_OIL_REFINERY_MOVIE_END` → checkpoint action 5 | **No**: event 1 only checks "not already played" (`+0x210`), not the state | **Early refinery explosion** |
| 4 Hunted (DOCKS) | `StageDocksQuest` `0x7EDA78` | the quest only tracks state (objectives `SHUTLIGHTS`, `OPENGATE`, `SNEAKIN`, `DESTROYBARGE`). The ending cinematic is started by `GDControl ToxicExpl` on **`Explosion 2` at (−361, 11, 236)** (only while the shark is alive, `BGIsSharkDead`) | Checkpoints ordered; the ending isn't tied to the quest state | **Early toxic explosion** |
| 5 Predator in the Bay (KATATAMA) | `Stage4Quest` `0x7ED6D0` + `MSAuroraBoss` | event 4 ×3 (`MSOilRig` `0x650010`, the 3 platforms, `m_nOilPlatformDestroy` = 3) and event 6 (`MSPowerGenerator` `0x648998`), **in either order** → state 3 → Aurora boss | Not by the quest, but **in play the path is sequential** (user, 2026-10-18) | none; boss end not decoded |
| 6 The Angry Armada (ARMADA) | `Stage6Quest` `0x7ED7F8` | waves spawned near the shark from `m_wave_01..05` (2/6/7/1/1 boats). Ship events 0/1 from boats in the current wave count. Thresholds 2, 3, 2, then a cutscene step (state 12 sets `+0x598`), then 1 → `m_end_act` (`0x21C`) | Yes (wave by wave; only current-wave boats count) | none. `m_cheat`/`m_cpskip` dev fields: `m_cheat` ≠ 0 would restore a checkpoint at load, but it's 0 in the shipped data |
| 7 A Taste for Blood (WRACK) | `StageWreckQuest` `0x7EDCA8` | every 30–59 ticks counts living `m_scubadivers` (4 `NAScubaRef`: (397, −8, 17), (279, 8, 90), (409, −20, 167), (243, −20, 13)); none left → `m_winmovie` | No (any order) | kill the divers in route order |
| 8 The Deep (DEEPSEA) | `StageDeepSeaQuest` `0x7EDDC0` | `CTRLROOM_DESTROYED` messages (from `JTMineControl`); `m_ctrlroomcount` = 4 → 0 → event 1 + `m_onroomsdestroyed` (act 3) | No (rooms in any order) | none |
| 9 The Facility (DEEPSEA2) | `StageDeep2Quest` `0x7EDE50` + `NASquidBoss` | **4 of the 8 `BossSquidColumn`s destroyed** (`MSG_BOSSSQUID_COLUMN_DESTROYED` count > 3) → `m_winmovie`. The squid itself doesn't have to die. Columns sit on a radius-73 ring round (0, −271, 0); each one's detector starts its destructor, which sends the message 100 ticks later | No | none. **In play (user, 2026-10-18):** the player can't break the columns; the squid breaks them itself once it's blind, which the player causes by eating its eyes. Breaking the columns kills the squid and moves the mission on, so "4 columns" and "squid dead" are the same event |
| 10 Blood on the Beach (TOWN) | `Stage9Quest` `0x7EE31C` | event 10000 → "Kill %d people" (`MSG_HUMAN_EVENT` 0xE from group `tokill`; fail if escapes ≥ total − required) → event 1 → boat phase (`m_boattime` × 30 frames; ship events 0/1 from `m_boats`) → `mayor_yacht` sunk (state 6) → `m_raiser` delay → completion | Yes | each destroy path sends one ship event, so no double count |
| 12 The Final Chase (CHASE) | `Stage11Quest` `0x7ED88C` | ship event 1 (sinking) from `orca_2_turbo` while alive → `m_end_act` 388 (`BGSetMissionCompleted` at t = 0, credits at 190). Phase 2 starts when `orca_2_new` drops below half health or `ss_host` disappears. The 1,051-tick (35 s) intro has a `SkipAction` that starts the quest | Yes | skip the intro |

**Result (user, 2026-10-18): none of the leads below panned out.** Kept as a record of what the code does.

**Lead 1: the tutorial pier skip (START).**
- The tutorial quest listens for `MSG_PIER_DESTROYED` (`0x5EEF82`). It sets `+0x1C4`, and on the next tick, if the state is < 0x16, it sends itself event 16 (`0x5EFA3B`).
- Event 16 sets the state to 0x15 and launches the first zodiac **from any earlier tutorial state** (`if state < 0x15`).
- The message comes from the three pier buildings' `GDMsgSend` actions (`EpuletEp 1` (1099, 2, −303), `EpuletEp` (2185, 0, −313), `EpuletEpKajalda 1` (1145, 0, −219)). Each building sinks (`MBSullyeszto`) once its 6 support posts (`m_tamasztok`, damage 15) are broken.
- The normal order is …→ "Destroy the piers" → "Destroy the inflatable rafts" (zodiacs) → Aurora. So destroying a pier early skips every tutorial step in between, as long as the piers can be reached.
- The shark starts at (−1136, −21, 49), and the tunnel boulders (`TunnelBlockingDust`, (536, −13, 24)) sit between the start and the piers. They're cleared by the SeaSeeker step (`LastSeaSeekerRef`). Whether there's another way to the piers is the open question.

**Side finding:** `MBStageTutorial`'s completion path waits for flag `[0x8DA1C0]+0x12C`. Only `NAAuroraRope` sets that flag (`DDGameState.m_koteldied`, "the rope died"; `0x4BC8E3`, `0x4BCE98`, `0x4BD19A`; see `cut_content.md` "How the rope fight worked"), and `NAAuroraRope` is the cut rope tug-of-war, never placed in any level. So that path is dead, and the shipped tutorial ends through the quest's Aurora movie instead. Its activation (`0x4B12B0`) also jumps straight to state 4, so states 0–3 (boat-damage → `ZodiacComingEvent`) are dead too.

**Lead 2: The Dead of Night (BEACH) early ending.** Event 1 isn't gated by the quest state. Normally a barrel from the truck/barrel phase hits `Expltarget 1` on the pier (node flags `0x842`). If anything that counts as a hit reaches that target before the party guests are dead, the refinery explosion and the ending should play straight away. The barrel generator (`Barrel generator` (−225, 22, 271), next to the `BridgeShooters`) isn't added by any control, so it may be live from the start.

**Lead 3: Hunted (DOCKS) early ending.** Same pattern: `Explosion 2` (flags `0x12`, in the world from the start, (−361, 11, 236)) runs the ending once its controls start. Nothing in the level references it by ID, so they're presumably started by the hit/explosion path above, e.g. an explosive barrel (`BGDetonator EBD`) going off at the toxic tank before the lights, gate and sneak-in objectives.

---

## 8. Cutscene skipping

**Every in-engine story cutscene can be skipped**, and a skip jumps to the same ending as watching it out. So skipping saves the cutscene's length minus a short grace period, roughly 0.5–1 s per skip once you count the fade-out.

**How a skip works.** A cutscene is a `GDPlayMovie` action (class fields, PROP IDs: `m_Movie` `0x080018A7`, `m_ObjList` `…A8`, `m_SkipDelay` `…A9`, `m_CanSkip` `…AA`, `m_OnSkip` `…AB` = action ID, `m_KeepRunning` `…AC`). The levels drive it like this:
- The real camera movie has `m_CanSkip` = 0.
- The level also has a second `GDPlayMovie` with `m_CanSkip` = 1. It plays a dummy one-frame `GMOV` and keeps running (named `ForSkip`, `FakeGdPlayMovie`, `SkipEnabler`, …). It is the **skip watcher**.
- The watcher is started a little after the cutscene begins (`SkipPreventor`, `SkipProtector`, `SkipKeslelteto` = "skip delayer").
- On every tick (`0x6D95F0`) the watcher checks for a skip press. Once the time is past `m_SkipDelay` and a skip is pressed, it jumps its movie to the last frame, stops itself and starts `m_OnSkip`.
- `m_OnSkip` is usually **the same ending action** that the cutscene's own timeline starts at its last step: kill the movie node, give back `SharkCamera`, start the quest or the next step.

**The skip button.**
- The skip check (`0x453A00`, game-engine vtable `0x7D2810` slot `+0x58`) fires on a **new press** of input bit `0x400` or `0x800` (`current & ~previous`). Holding a key does nothing, and a press made before the watcher starts is lost, so press again.
- **The skip key is Enter** (user, 2026-10-18; Esc does nothing). That matches The Final Chase intro's prompt `]# SKIP` (`]` = the Enter icon). The PC button table (`0x8ACAE8`, token → key name) says `SKIP` → Esc, so that table entry is stale. Enter is also `OK`/`START`/`CONT` in the same table.
- **Spamming Enter while skipping can crash the game** (user, 2026-10-18). Cause not found. A watcher stops itself when it fires, so one cutscene can't be skipped twice. Chained skips almost never overlap: the only case is A Taste for Blood, where part B's skip still has a kill pending at t = 30 when part C's watcher arms at t = 25. Candidates: a press on the same tick the timeline starts the ending action itself (the ending runs twice), or Enter's other jobs (pause, the Stage Completed Save menu) firing while a skip is still tearing the cutscene down. Pinning it down needs a crash address (Proton log).
- **Grace period** before a skip counts: 0.5–3 s for most cutscenes (15–90 ticks). Exceptions: the Predator in the Bay power-plant explosion (180 ticks, 6 s), and Brody's escape in the same stage (`m_SkipDelay` 350, **11.7 s**).

**Rough time saved per stage** (cutscene timeline length minus the grace period, at 30 ticks/s, from the level scripts; whether every cutscene below is on a given route isn't checked):

| Stage | Skippable cutscenes (saving) | Total |
|---|---|---|
| 1 The Arrival | Shaw's son's death (~17 s), Aurora arrives / harpoon ending (~31 s) | ~48 s |
| 2 The Break Out | dolphin show 8 s, exhibition hall 6 s, pagoda 7.5 s, lab 16 s, meeting 28 s, scientist ID card 8 s, `Scene1`/`Scene2` 9 + 8 s, escape 7 s | ~98 s |
| 3 The Dead of Night | opening 30 s, truck/barrels 28 s, refinery explosion 13 s | ~71 s |
| 4 Hunted | barges out 32 s, fishermen (part B) ~15 s, ending (two parts) ~7 s | ~55 s |
| 5 Predator in the Bay | flyover 12 s, Brody's escape 13 s, power plant 4 s, each oil rig 10 s (×3), Aurora arrives 9.5 s | ~69 s |
| 6 The Angry Armada | movie 601 12.5 s, movie 602 40 s | ~53 s |
| 7 A Taste for Blood | intro: skipping part A goes straight to part C, skipping B too (~51 s), part C 13 s; mayor's speech 47 s; mid 15 s; "Nemo" 15.5 s | ~140 s |
| 8 The Deep | intro: one skip ends both parts (~51 s) | ~51 s |
| 9 The Facility | Mr. Shaw's entrance 7 s, squid entrance 29 s, squid defeat 26 s, outro 41 s | ~104 s |
| 10 Blood on the Beach | intro 28 s, cinematics 9.01 / 9.02 14 + 9 s, others 6 + 9 s | ~66 s |
| 12 The Final Chase | intro 34.5 s, shark explodes 4 s | ~38 s |

**Not skippable:** the short camera cuts (`NACutScene` actions outside a skippable movie), such as The Facility's column cams (60 ticks = 2 s each, one per broken column) and START's `CutSceneCamera` (250 ticks). WMV videos (`MPGPlay`, field `m_skip`) only play in the title menu and after the final stage, so they don't affect the run.

**State a skip leaves behind** (found by comparing, for each cutscene, actions the full timeline runs on objects outside the movie that the skip path never runs; almost all are sounds, cameras and particles):
- **The Dead of Night truck cutscene:** the movie hides the refinery (`Level3_facility`, its 21 `FacilityLit` lights, 11 `Facility Spot`s, `Facility_Pipeline`) and the pier tops (`molo_teteje_001 1–4`, `moloveg_teteje_001 1–2`). It only shows them again at ticks 820/860. The skip path (`truckmoziszkipp`) kills the movie and has an empty `show` step at t = 860, so **after a skip they may stay hidden**, and runtime-hidden objects also lose collision. This assumes killing the movie node also cancels its pending steps, which isn't traced. It would be a visual oddity: the ending trigger `Expltarget 1` is not under these nodes.
- **Hunted part B:** `TugRef` (the `tug_boat 5` copy, with an `MBLibegPusztul` float/destroy action) is started at t = 449, just after the skip action. Skipping earlier means it's never started. Probably cosmetic.
- The Dead of Night and The Angry Armada skips don't start `NAWaterYCamera 1` (the underwater fog/far-plane controller) the way the full timeline does. It autostarts (base flags `0x2`, like OPEN_S/KATATAMA where nothing starts it), so this is harmless.
- **No skip advances or bypasses quest state.** The skip paths start the same quest/next-step actions as the normal ending.

---

## To test in-game

1. ~~Tap vs. hold~~ (done 2026-10-18: tapping from idle is quicker). Still open: whether gear 3 ever times out (`m_bigspeedtime` 150 frames, purpose unconfirmed).
2. ~~Jump/breach and charge as travel~~ (done 2026-10-18: both slower than swimming).
3. FIXBITE next to walls for clips (few biteable fixed objects, and they break).
4. BLOOOOD: when the Abilities menu opens, upgrade costs, Speed ×1.5 on the overlay.
5. Arrival points in each zone after each stage (F8 overlay), to finish the route table.
6. Whether the frame rate holds 30 everywhere on the runner's PC.
7. ~~Tutorial pier skip~~ (2026-10-18: not a lead, user). Was: (section 7, lead 1): F8 to a pier building (e.g. (1099, 2, −303)) early in START, break its 6 posts, and check that the "destroy the rafts" phase starts. Then look for a legit way past the tunnel boulders.
8. ~~Dead of Night early refinery~~ (2026-10-18: not a lead, user). Was: (lead 2): get something to hit `Expltarget 1` (−296, 19, −24) before the party guests are dead.
9. ~~Hunted early toxic explosion~~ (2026-10-18: not a lead, user). Was: (lead 3): an explosive barrel at `Explosion 2` (−361, 11, 236) before the other objectives.
10. ~~The Facility columns~~ (2026-10-18, user): only the blinded squid breaks the columns (eat its eyes first), and that kills it.
11. **Cutscene skip** (section 8): Enter skips; one press after the grace period is enough. Check The Dead of Night after skipping the truck cutscene: are the refinery and the pier tops still there? For the spam crash: which cutscene, and a `PROTON_LOG=1` log with the crash address.

## Not done yet

- Win conditions: done for every story stage (section 7) except the Aurora boss end in KATATAMA (`MSAuroraBoss`) and the exact engine path that starts `NACollisionDetector`s.
- Cutscene skipping: done (section 8). Still open: the Enter-spam crash, which key sets bit `0x400` vs `0x800`, and whether killing a movie node cancels its pending steps.
- Death/restart behaviour (pause menu "Restart" re-activates the controller; whether quest progress survives it).

Helper scripts used (scratch, not in the repo): class-from-vtable lookup via the static-init descriptor stores (`mov [desc], factory_vt`), an `ACTN` dumper with `CLAS`/`ACCM` class names, a node-class dumper, and the entrance table above.

## 9. The Facility: Mr. Shaw fight reachable during the squid fight (2026-11-23)

**User find:** with no-clip (mod F7) the shark can pass through the wall from the squid arena and start the Mr. Shaw fight while the squid boss is still alive. Read from DEEPSEA2's scripting (`dump_gdcontrol.py`), static only:

- **What starts the Shaw phase:** breaking the glass `TorhetoUveg 1` (5927, at (1072, −207, −106), ~1,080 units from the squid room at (0, −271, 0)). Its destructible hook (`m_robbcontrol` `0x08000673`) starts `mrshaw_entrancestarter` (act 5731) → Shaw's entrance movie → `moziszkipp` → `mrshawaktivalo` (adds divers, 2 minisubs, the hiding places and `NAScubaRef MrShaw` 5948) plus the escape countdown: explosion flashes `vegerobbanto`/`vegerobbantosuru` from 20 s to ~115 s and a `JTTimer` (5728, value 120) that adds `EndMovieSharkDead` (the shark dies in the blast). **Nothing checks the squid or the quest state.** Normally the wall keeps the player out until the squid is dead.
- **What killing Shaw does:** `NAScubaRef MrShaw`'s on-death action (`PROP 0x08000FE0`) = `stageend` (act 5722 on `QuestStuff 1`): adds the `ShawKilled` movie, starts `stageend_mbscore` (`MBScore`, `m_event` 36), stops the gameplay groups `jatekcuccok`/`jatekcuccok2`, and adds `outromovieoverlay` after 550 ticks. **Also no squid or quest-state check.**
- **Quest events for comparison:** squid entrance → event 2, squid dead (`squidmeghalas`) → 3, control room (`compromb`) → 4, distance check `questmsgchkdist` → `destroyctrlcenter` → 5. Shaw's death sends none of them; it ends the stage through its own script.
- **User-tested 2026-11-23 (F7 no-clip): confirmed.** Killing Shaw while the squid is still alive ends the mission and returns the player to OPEN_NW, as after a normal finish. **The stage counts as completed:** Blood on the Beach unlocks (user-tested). So Shaw-first is a full skip of the squid fight; it only needs a vanilla way past the arena's barriers (section 6).
- **Original prediction:** killing Shaw before the squid should play Shaw's death, the score and the outro and finish The Facility with the squid alive and quest events 3–5 never sent. Unknowns: whether the score/outro or the next stage depends on the skipped quest state, whether the live squid fight interferes (its cutscenes, camera), and whether the 120 timer keeps running after Shaw's death. If it works it skips the squid fight (its entrance and defeat cutscenes alone are ~55 s), but only with no-clip, so it isn't a normal-rules route unless a real clip into that wall exists.

## 10. More Shaw-style sequence breaks to test with no-clip (2026-11-23)

The Facility's Shaw-first works because the stage's ending hangs off an object that is in the level from the start and is only kept out of reach by walls. A completion trace over all story levels (every script path that leads to the level's `Stage Completed Save`, keeping only triggers already live at load) and the section 7 table give these other candidates. Section 7's leads were judged dead in normal play (2026-10-18) because the targets couldn't be reached; with F7 no-clip and F8 they can now be tested directly. If one ends the stage, it becomes a target for a vanilla clip like the squid arena.

| Stage | Target (F8 coordinates) | What should happen | Why it might work |
|---|---|---|---|
| 2 The Break Out (AQUARIUM) | boss orca `Orca Root` ≈ (1011, −190, −304) | kill it → event 10 → stage ends | the orca is live from load (suspended only in revisit mode) and event 10 isn't gated; normally the cage gates keep the shark out |
| 4 Hunted (DOCKS) | toxic barge `HitCounter` (2083) at (−360, 0, 236), `Explosion 2` at (−361, 11, 236) | 2 hits on the counter (`BGDetonator` → `GDControl DeadCheck` → `ToxicExpl`) → ending cinematic → `Stage Completed Save` | the barge (`ToxicBargeBr`) and `Explosion 2` are live from load; the ending isn't tied to the quest state. What counts as a hit (ram, bite, explosive barrel) isn't known |
| 3 The Dead of Night (BEACH) | `Expltarget 1` on the pier at (−296, 19, −24) | a hit → `Explosion 4` → refinery explosion and ending | event 1 only checks "not already played"; the barrel generator near the `BridgeShooters` may be live from the start |
| 1 The Arrival (START) | pier buildings | **Done in vanilla, see section 11.** | |

Checked and **not** sequence breaks: DEEPSEA's end zones (`palyavege` ×3, distance checks that add `Stage Completed Save`) are added by the script only after all control rooms are destroyed; KATATAMA's platforms and generator already go in any order; WRACK's four divers already go in any order. The trace script is a scratch tool and its long paths through shared props are noisy, so only the short, named chains above were followed up.

## 11. The Arrival skip: vanilla route (user find, 2026-11-23)

**No mod needed.** The user's route through START. **The tutorial bubbles only appear when starting a new game** (user, 2026-11-23), so the route needs a fresh save. That's the normal case for a full-game run, but replaying the stage from an existing save won't work. What hides the bubbles on a replay isn't traced.

1. **Out of bounds:** swim right against the "current too strong" force field, close to a wall, and the shark slips out of bounds.
2. **Swim under the map** to where the tutorial bubble appears after the normal cage-diver kill and boulder blast. From under the map the bubble still comes to the shark, and touching it **sets a checkpoint**.
3. **Pause → restart from last checkpoint** puts the shark in part 2 of the tutorial, **back in bounds** (user): the restart respawns the shark at the checkpoint's own position, so the out-of-bounds swim leaves no trace. `SecondPart` sits at (660, 0, 35), past the boulder.
4. **Skip the swimmers:** break a pier building's support posts so it falls into the water. That spawns the Coast Guard zodiacs.
5. **Sink all the zodiacs** → Brody harpoons Jaws (the `AuroraComesMovie` cutscene) → on to AQUARIUM.

**Why it works (data):**
- The tutorial bubbles are `TutorialQuestRef` objects along the route (1850–1857, e.g. `TutorialQuestRef 6` at (711, −11, 32), just past `TunnelBlockingDust` at (536, −13, 24)). The quest advances its checkpoint by which bubble the shark reaches, not by what's been done before.
- Restarting at the **`SecondPart`** checkpoint (node 677, (660, 0, 35)) runs `CheckPointCleanUp` (act 678): it kills `TunnelBlockingDust` and clears the cage, the cage diver's boat markers, the armoured SeaSeeker and `LastSeaSeekerRef`, which are the objectives the route skipped. The restored stage is consistent, as if they had been done. (`BeforeZodiacs` (679) has the same cleanup.)
- Step 4 is section 7's lead 1 (`MSG_PIER_DESTROYED` → event 16 → zodiac phase from any earlier tutorial state), now confirmed in play. Step 5 is the stage's normal ending (4 zodiac kills → `AuroraComesMovie` → `Stage Completed Save` + `LoadAquarium`).

## 12. Checkpoints in every story level (2026-11-23)

**How checkpoints work (data):** each stage's quest action carries `m_checkpoints` (`PROP 0x08001161`, respawn nodes by checkpoint number; high slots are side-challenge spawns) and `m_checkpointactions` (`0x08001162`, what runs on "restart from last checkpoint"). A checkpoint is set by an `MBCheckPointSet` action (`0x080011EF` = checkpoint number) or by the quest's own code (KATATAMA, TOWN, BEACH, ARMADA). The Arrival skip (section 11) works because START's checkpoint is set by **reaching** a tutorial bubble and its restore script removes the barriers. Restarting also respawns the shark at the checkpoint node, back in bounds. Below, **reach-set** means the checkpoint is set by getting somewhere (or breaking something), which an out-of-bounds route could do early.

| Stage | # | Respawn (node, position) | Set by | Restore script does | Reach-set? |
|---|---|---|---|---|---|
| 1 The Arrival (START) | 0 | `SecondPart` 677 (660, 0, 35) | tutorial bubble (`TutorialQuestRef`) | `CheckPointCleanUp`: kill `TunnelBlockingDust`, clear cage, boat markers, armoured SeaSeeker, `LastSeaSeekerRef` | **yes, used** |
| | 1 | `BeforeZodiacs` 679 (1104, 0, −183) | tutorial bubble | same cleanup | yes |
| 2 The Break Out (AQUARIUM) | 0 | `CheckPointSlide1` 1190 (351, −70, 190) | next-scene starter (`NotPS2_NextSceneStarter`) | `CheckPointToDo` (act 9): stop the intro | no |
| | 1 | `CheckPointGreattank` 1191 (43, −35, 13) | breakout movie (`MovieAdministration`) | act 9 | no |
| | 2 | `CheckPointOrca` 1192 (1123, −187, −208), in the orca arena | **breaking the iron door `ajto` (7928, at (656, −82, 190))**: its destructible hook → `AjtoBetortControl` → orca-arena entrance movie (teleports the shark into the arena) + checkpoint 2 + `EventInOrcaTank1` | `CheckPointToDoOrca` (act 10): stop the intro | **yes: break the door early** |
| 3 The Dead of Night (BEACH) | 0 | `AtTruckStart` 136 (44, 0, 295) | quest code | kill fuse boxes, opening overlay, `SwimmersTrigger`, 4 party guests (`21+Young` 1/6/3/–), `crowd 1`; suspend truck model; add game SFX | no (quest) |
| 4 Hunted (DOCKS) | 0 | `CheckPoint Start` 1638 (−520, −10, −523) | stage start | `Reload CP Start`: reset guards, map bricks, start quest | no |
| | 1 | `CheckPoint Gate` 1641 (197, −12, −10) | **`NACollisionDetector CP Gate` on that node** → `SetCheckPoint Gate` | `Reload CP Gate`: **`QEvent_OpenGate`, gate wings opened, kill the 3 fuse boxes, light paths and 2 dock guards**, add the barge/barrel map markers | **yes: touch the gate checkpoint early** (the quest may only accept checkpoint *n* in state *n* − 1, section 7) |
| 5 Predator in the Bay (KATATAMA) | 0 | `SharkPosReal 1` 213 (363, 0, −1083) | quest code | – | no |
| | 1 | `Power Plant Shark Died Pos` 3802 (101, −10, 114) | quest code | – | no |
| 6 The Angry Armada (ARMADA) | – | none listed (quest code with `m_cpskip`) | | | |
| 7 A Taste for Blood (WRACK) | 0 | `CheckPoint 1` 31 (51, −10, 38) | entering `ANPolyArea 1` (104, 0, 75), at the start | kill that area and the intro movie | yes, but it's the start |
| 8 The Deep (DEEPSEA) | 0–3 | `chkpoint 1–4` (−209, −573, 356), (1309, −483, −321), (−362, −483, −845), (−281, −575, −39) | each control room's destruction (`bummcontroll`) | none listed | no |
| 9 The Facility (DEEPSEA2) | 0 | `csekkpojnt` 2542 (27, −79, 352) | squid death (`squidkinyirva`) | `csekkpontyintezo` → `facility eleszto`: the post-squid state (arena barriers removed, generator room added) | no |
| 10 Blood on the Beach (TOWN) | 0, 1 | `CheckPointRebornPos` 144 (2739, −7, 741), `… 1` 143 (2755, −7, 900) | quest code | `CheckPointToDo` (act 7): stop the intro, start `HordokElesztoje` | no |
| 12 The Final Chase (CHASE) | – | none | | | |

**Best new candidates:**
- **Hunted:** the gate checkpoint is a touch trigger at (197, −12, −10). If it can be touched before the lights are out (out of bounds or a clip) and the quest accepts it, restarting would open the gate and count the fuse boxes as done.
- **The Break Out:** the orca-arena door `ajto` at (656, −82, 190) is a destructible; breaking it plays the arena entrance, teleports the shark in, sets the orca checkpoint and sends the quest's `InOrcaTank1` event. Killing the orca then ends the stage (section 10). The question is whether the door can be reached and broken before the earlier tanks.

**Correction (2026-11-23):** the DOCKS gate checkpoint (`CheckPoint Gate`, trigger box z −13.4 to −9.5) sits just past the gate on the far side, and the gate must be open to reach it (user). It is not a pre-gate skip.

## 13. How terrain collision really works, and where clips come from (2026-11-23, static)

Supersedes the "per-frame overlap push-out, not a sweep" note in section 6.

- **Collision is swept.** The first time a brick moves in a frame, `0x697290` snapshots its start-of-frame world matrix (brick `+0xEC`, flag `0x80000000`; skipped when brick flag `0x8` is set). The pair test `0x695F30` → `0x6E15D0` gets both the start and current matrix and keeps the **earliest time of impact** along the move. So simply moving fast can't skip a wall: a whole frame's path is checked.
- **The shark's step (`0x65BFC0`) runs up to 8 rounds** of query (`0x6C80C0`, mask `0x18001`) + push-out (`0x4E4DA0`: back along the contact normal by (1 − t + margin)). If it still collides after round 8, it **gives up and leaves the shark where the last push put it**, sets the velocity to the last contact normal × `SharkConfig+0x920` and counts a stuck frame. After 90 stuck frames, a new press of input bit 4 does the "SafePoint Teleport".
- **Clip mechanism (inference):** in a spot where two surfaces push the shark in opposite or acute directions (a narrow gap, a wedge between two walls, a wall meeting the seabed or another object), each push-out moves the shark into the other surface. After 8 rounds it's left wherever the last push put it, which can be the far side of one surface. The next frame's sweep then starts from there. A steady push into the wedge (holding swim) would repeat this every frame. (Not how the Arrival works: there the shark doesn't clip through any wall, it just out-swims the `NAWhirl2000` current boundary after a short struggle, and a nearby wall helps only a little; user, 2026-11-23. The wedge idea is untested.)
- **Recipe to test:** find a gap narrower than the shark or a sharp concave corner between two separate collision pieces, swim into it at a shallow angle and hold, ideally with something else pushing (current, held prey, an explosion knockback). Watch for the shark jittering (that means the 8-round limit is being hit).
- **Holding prey uses a different loop:** while the shark holds prey (`ctrl+0x204`), the step also queries the prey's collision and pushes with `0x4E4F20`, choosing whichever contact came first. A held object pressed into a wall may push the shark oddly; untested lead.
- **DOCKS gate specifics:** wings `RightGateWing`/`LeftGateWing` (2028/2029) are ~2.5 units thick (z −19.7 to −17.0), y −35 to +7.6, with mesh collision (`MREG` 0xA0E/0xA0D). `RightGateWing` also carries an **invisible box** (`PRIM 0x20005004`) 172 units wide (x 118.8–290.3), y −35 to **+19.7**, ~2.7 thick, so jumping over the gate needs a leap of ~20 units plus the shark's size. The box runs straight through the two flanking small piers (`Kismolo_05 1`/`_06 1`, x 136–180 / 219–263, z −33.6 to −3.6, top 5.5): **the box ↔ pier junctions and the box ↔ seabed edge are the wedge candidates** to try.


**Arrival out-of-bounds correction (2026-11-23, user):** no terrain clip is involved. The "current too strong" boundary is a `NAWhirl2000` current (21 in START; also DEEPSEA 7, KATATAMA 1, WRACK 1), which pushes the shark back with a force rather than blocking it, so it can be out-swum after a short struggle. Swimming along a wall helps a little. The force code (`0x63BD80`, vtable slot `+0x84`) scales with `(1 − distance / radius)` from the current's path line (radius at `+0x154`, strength `+0x164`), so it's weakest near the edge of its radius; whether that's why the wall helps isn't checked.

### Current strengths (`NAWhirl2000`, 2026-11-23)

Fields (`PROP 0x080013BB` + index): `m_targets`, `m_movetargets`, `m_noshark`, `m_moveit`, `m_traverseall`, `m_centerpull`, **`m_rad`** (`…13C1`, reach), `m_grad` (`…13C2`, 1 = linear falloff), **`m_force`** (`…13C3`), `m_turntodir`, `m_turnrate`. Runtime values at `+0x154` (rad), `+0x15C` (grad), `+0x164` (force), matching the force function `0x63BD80`. The push follows the **path's direction** (a flowing current), with size `m_force × (1 − d / m_rad)`, where d is the 3D distance from the path line. So it's strongest on the line and zero at the edge.

| Level | Currents | force | rad | Notes |
|---|---|---|---|---|
| START | 21 (`NAWhirl2000 1–21`) | 3.0 | 50 | All identical. Two rows: y −6 along z −88…−24 (x −914…−1196) and y −28 along z 121…185 (x −927…−1196), joined by a north–south line at x ≈ −1220 (z −9…140). Neighbours are ~40–45 apart, so their areas overlap |
| DEEPSEA | 4 control-room currents (`NAWhirl2000 1/3/4/11`) | 1.3 | 11 | Flags `0xA` (not in world until a script adds them) |
| DEEPSEA | 3 `VerticalWhirl` (mine whirls) | 6.0 | 13 | `m_centerpull` = 1, vertical, y −652 to −237 |
| KATATAMA | `NAWhirl2000 1` (126, −12, 220–271) | 1.0 | 50 | Very weak |
| WRACK | `WrackWhirl1` (−360, 0, 93), box x −504…−310 | **20.0** | 50 | ~7× START's, effectively impassable near its line |

**Why START's walls feel different although every object is the same (inference):** what you feel depends on (1) your distance from the nearest path line, so the push fades toward the edge of the 50-unit radius, and the line sits at a fixed depth (y −6 or −28), so swimming well above or below it weakens it; (2) overlap, since where two currents' areas overlap both push; (3) direction, since you can swim across the flow instead of straight against it. For scale, the shark's swim gears top out at 2.08 units/frame (× up to 1.5 with Speed), against a peak of 3.0; whether `m_force` is in the same units isn't checked. Best try: cross where only one current reaches, as far from its line (and its depth) as possible.

### Buoy push barriers (`ANTol`) and why DOCKS is brutal (2026-11-23)

The other "current too strong" barrier is **`ANTol`** (*tol* = push), attached to the **buoy template `BolyaDef`**, so every buoy of a level's boundary line pushes. Fields `PROP 0x080002B2` + index: `m_type`, `m_radius`, `m_fmul`, `m_delay`, `m_forcemax`. Tick `0x43F6A0` (vtable `0x7D18D4`): every `m_delay` ticks, if the shark's **horizontal** (x, z) distance to the buoy is inside the radius, it sends `MSG_WHIRL` (message `0x5F`) with push = buoy's Z axis × (1 − d² / r²) × `m_fmul` (the test and the falloff both use the **squared** distance; corrected 2026-11-23, first written as 1 − d / r). The push points along the buoy's own facing (its Z axis, from the world matrix at brick `+0x9C`), not away from the buoy, so overlapping buoys facing the same way add up. **Only when `m_type` ≠ 0 is the push capped at `m_forcemax`.** Depth doesn't matter (y is ignored). How the shark turns `MSG_WHIRL` into motion isn't traced.

Because the falloff uses the squared distance, a buoy pushes near full strength for most of its radius and drops off only close to the edge. A DOCKS buoy (r 50, fmul 20, uncapped):

| Horizontal distance | 0 | 25 | 35 | 45 | 50 |
|---|---|---|---|---|---|
| Push | 20 | 15 | 10.2 | 3.8 | 0 |

| Level | Buoys | type | radius | fmul | cap | Spacing (min / median / max) |
|---|---|---|---|---|---|---|
| **DOCKS** | 30 | **0** | 50 | 20 | **none** | 33 / 53 / 73, so most points are inside 2 buoys |
| TOWN | 41 | **0** | 60 | 20 | none | 65 / 87 / 96 |
| ARMADA | 76 | **0** | 70 | 20 | none | 97 / 97 / 117 |
| FISH | 72 | 1 | 71 | 20 | 0.45 | 64 / 70 / 70 |
| GAUNTLET | 64 | 1 | 71 | 20 | 0.45 | 81 |
| KATATAMA | 38 | 1 | 60 | 20 | 0.45 | 65 / 90 / 117 |
| MINEMSHA | 45 | 1 | 71 | 20 | 0.45 | 21 / 44 / 44 |
| AQUARIUM, WRACK | top-level `ANTol`s | 0 | 50 | 1 | none | – |
| OPEN_S / OPEN_NE / OPEN_NW | 41 / 40 / 39 | 1 / 1 / **0** | 500–1500 | 15–20 | 0.5 / 0.5 / none | – |

With fmul 20, a type-1 buoy is effectively a flat 0.45 (the cap applies everywhere except the outermost ~1 % of the radius). An uncapped type-0 buoy pushes up to **20, about 44× more**, and DOCKS packs them tightest. That's why DOCKS feels abusive. TOWN and ARMADA are the same kind but with wider gaps.

**DOCKS buoy line:** x −711 to 560, z −797 to −545 (the north edge, toward OPEN_NW). Two gaps are wider than two radii, so **there's no push at their midpoints**: between buoys 1662/1670 (124 apart, midpoint (553, −619)) and 1664/1672 (107 apart, midpoint (−701, −598)). Those are the line's turns at the east and west ends; land or other collision may block them (untested). The next weakest spots (68–76 apart, ~8–11 push from each side at the midpoint, ~17–22 combined) are along z ≈ −795 near x −153, −80, −8, 184 and 258.

---

## Moved from CLAUDE.md (2026-11-25)

The text below was moved word for word from the root `CLAUDE.md`. It is newer than earlier sections of this file where they disagree.

**Speedrun research (2026-10-18, static only, `docs/speedrun_glitches.md`):** the main loop ticks only when ≥ 33 ms have passed and the game clock steps 1.0 per tick, so the game runs at a fixed ~30 fps and **lag is slow motion** (no fps speedup). Story progress = global `0x8D011C`. `MBLoadChecker` (vtable `0x7D871C`) locks entrances with a plain `stage − 1 == progress` test, and no shipped object raises progress early (all 40 writers checked), so stages go in order. START loads AQUARIUM directly; DEEPSEA chains into DEEPSEA2. Swimming works in **gears** (`FUN_00667010`, `ctrl+0x250`): speeds 0.2/1.0/1.5/2.08 units/frame. Each new swim press shifts up once the speed is within 0.3 of the gear's top, holding keeps the gear, and a release of more than 5 frames drops it. Target speed × (1 + 0.5 × Speed). `BLOOOOD` only sets points to 1,000,000 (`0x8D012C`). Abilities are Accuracy/Power/Speed/Hunger/Defense (`ctrl+0x72C`–`0x73C`, level × 0.25; `SharkConfig` muls 1/4/0.5/1.333/1.333): max Speed = ×1.5 swim, max Power = ×5 damage. User-tested 2026-10-18: straight-line swimming is fastest, tapping from idle reaches top speed sooner, jumps and headbash charges slow the shark down. Terrain collision is skipped in state `0x10` = **FIXBITE** (clip candidate, but few biteable fixed objects and they break) and `0x16` (death anim); `ctrl+0x810` is set only in the dead state.
**Win conditions (2026-10-18, `docs/speedrun_glitches.md` section 7):** the active quest is `0x8FE494`; events arrive via its slot 26 (`+0x68`), from 62 exe send sites plus `NAQuestEvent`/`GDMsgSend` actions. Stage ends: Break Out = any `MSOrca` death (event 10, one orca); Dead of Night (BEACH) = all 12 party guests → refinery explosion at `Expltarget 1` (event 1, **not state-gated**); Hunted (DOCKS) = toxic `Explosion 2`; KATATAMA = 3 rigs + generator in any order → Aurora boss; ARMADA = boat waves 2/3/2/·/1; WRACK = 4 scuba divers; DEEPSEA = 4 control rooms; The Facility = 4 of 8 squid columns broken (in play only the squid breaks them, once the player has eaten its eyes, and that kills it); TOWN and CHASE as before. **Tutorial lead:** `MSG_PIER_DESTROYED` (a pier building sinks after its 6 posts break) jumps `NATutorialQuest` to the zodiac phase (state 0x15) from any earlier step; **user result 2026-10-18: none of the leads (pier skip, BEACH/DOCKS early explosions, squid columns) panned out; Break Out and Predator in the Bay play strictly in sequence.** `NACollisionDetector`s are never started by scripts (only stopped), so the engine starts them when the parent is hit (parents carry `m_nFlags` `0x800`; inferred). Level ↔ stage correction: BEACH = 3 The Dead of Night, DOCKS = 4 Hunted, TOWN = 10 Blood on the Beach (the GDW mapping table above has these wrong). `MBStageTutorial`'s finish flag `[0x8DA1C0]+0x12C` is set only by the cut `NAAuroraRope`, so that path is dead in the shipped game.

**The Facility Shaw-first (2026-11-23, user find + static read, `docs/speedrun_glitches.md` section 9):** with F7 no-clip the Mr. Shaw fight can be started during the squid fight. It's started by breaking glass `TorhetoUveg 1` (5927), and Shaw's on-death action (`NAScubaRef` `PROP 0x08000FE0`) runs `stageend` (act 5722: Shaw death movie, `MBScore` event 36, outro); neither checks the squid or quest state, so killing Shaw first finishes the stage with the squid alive: **user-tested, ends the mission and returns to OPEN_NW** and **counts as completed** (Blood on the Beach unlocks, user-tested): a full squid-fight skip, pending a vanilla way out of the arena. Vanilla clip research: shark terrain collision = 6 spheres (~0.8–2.5 units), swept collision with ≤ 8 push-out rounds (corrected, see the next paragraph); DEEPSEA2 terrain has no missing collision; the squid arena is sealed by script-added `BossSquidRoomCenter` (3980) + closed rollers (3734). The phase has a 120 `JTTimer` → `EndMovieSharkDead`.

**Collision is swept, clips come from wedges (2026-11-23, `docs/speedrun_glitches.md` section 13):** the brick's start-of-frame matrix is snapshotted (`0x697290`, `+0xEC`) and pair tests take the earliest time of impact, so speed alone can't skip a wall. The shark step `0x65BFC0` runs ≤ 8 query + push-out rounds; if still colliding it leaves the shark where the last push put it (untested wedge-clip idea; the Arrival out-of-bounds is NOT a clip, the shark out-swims the `NAWhirl2000` current boundary, user). DOCKS gate checkpoint lies past the gate (needs it open); the gate has an invisible 172-unit box up to y +19.7, crossing the flanking piers (wedge candidates).

**Current barriers (`NAWhirl2000`, 2026-11-23, `docs/speedrun_glitches.md` section 13):** `PROP 0x080013BB`+index: `m_rad` `…13C1`, `m_grad` `…13C2`, `m_force` `…13C3`; push along the path = force × (1 − dist/rad). START 21 × force 3 / rad 50 (two rows at y −6 and −28 + a west line at x ≈ −1220), DEEPSEA 4 × 1.3/11 (script-added) + 3 vertical mine whirls 6/13, KATATAMA 1 × 1.0, WRACK `WrackWhirl1` **20**/50.

**Buoy push barriers (`ANTol`, 2026-11-23, `docs/speedrun_glitches.md` section 13):** on buoy template `BolyaDef`; `PROP 0x080002B2`+index `m_type`/`m_radius`/`m_fmul`/`m_delay`/`m_forcemax`; tick `0x43F6A0` sends `MSG_WHIRL` (0x5F) = buoy Z × (1 − d²/r², horizontal distance; corrected from 1 − d/r) × fmul, capped at `m_forcemax` only when `m_type` ≠ 0. The push follows the buoy's facing (not away from it), so overlapping buoys add up; near full strength for most of the radius (DOCKS: 15 at d 25, 10 at d 35). DOCKS/TOWN/ARMADA/OPEN_NW are type 0 (uncapped, up to 20 vs 0.45 elsewhere); DOCKS has 30 buoys only 33–73 apart (r 50), with zero-push gaps at (553, −619) and (−701, −598) (untested); its 68–76-wide gaps along z ≈ −795 still push ~17–22 combined. Engine detail: `docs/exe_analysis.md` "Push barriers".

**The Arrival skip (2026-11-23, user find, vanilla, `docs/speedrun_glitches.md` section 11):** out of bounds by out-swimming the "current too strong" field (a `NAWhirl2000` push, not a wall; no clip) near a wall → under the map to the tutorial bubble past the boulder (`TutorialQuestRef`s set checkpoints by reach) → restart from checkpoint = `SecondPart` (677), whose `CheckPointCleanUp` kills `TunnelBlockingDust` and the cage/SeaSeeker objectives → break a pier building (`MSG_PIER_DESTROYED` → zodiac phase, skipping the swimmers) → sink the zodiacs → Brody's harpoon cutscene → AQUARIUM. The bubbles only appear on a new game (user), so it needs a fresh save. Section 10 lists further no-clip retests (AQUARIUM orca early, DOCKS toxic barge, BEACH `Expltarget 1`).

**Cutscene skipping (2026-10-18, `docs/speedrun_glitches.md` section 8):** every in-engine story cutscene is skippable. A second `GDPlayMovie` (`m_CanSkip` `0x080018AA` = 1, dummy `GMOV`, `m_OnSkip` `…AB`) watches for a **new press** of input bit `0x400`/`0x800` (`0x453A00`). **The key is Enter** (user-confirmed; Esc does nothing, although the PC button table `0x8ACAE8` lists `SKIP` → Esc). **Spamming Enter while skipping can crash the game** (user); cause not found. The watcher only starts 0.5–3 s in (Predator in the Bay: 6 s and 11.7 s), so earlier presses are ignored. The skip runs the cutscene's own ending action, so it saves the full length (~0.6–2.3 min per stage, ~13 min total) and never changes quest state. Side effect to test: skipping The Dead of Night's truck cutscene may leave the refinery and pier tops hidden.

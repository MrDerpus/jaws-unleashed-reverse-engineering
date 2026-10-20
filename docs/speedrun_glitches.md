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

**Side finding:** `MBStageTutorial`'s completion path waits for flag `[0x8DA1C0]+0x12C`. Only `NAAuroraRope` sets that flag (`0x4BC8E3`, `0x4BCE98`, `0x4BD19A`), and `NAAuroraRope` is the cut rope tug-of-war, never placed in any level. So that path is dead, and the shipped tutorial ends through the quest's Aurora movie instead. Its activation (`0x4B12B0`) also jumps straight to state 4, so states 0–3 (boat-damage → `ZodiacComingEvent`) are dead too.

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

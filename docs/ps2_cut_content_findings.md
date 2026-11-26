# PS2 exe: what it says about cut content

**In short:** the PS2 program (`SLUS_210.62`) was searched for strings and tables. Main findings:
- **"Hot Pursuit"** is the title of the cut story stage between Blood on the Beach and The Final Chase.
- **"Deepsea Facility"** is the PS2 title of stage 9 (The Facility).
- Its stage-name table has a flag that switches from 1 to 0 exactly at Hot Pursuit. What the flag means isn't known.
- Every Hot Pursuit class uses the story-quest naming (`Stage…Quest`), which is the main evidence that it was a story stage.
- **The PS2 has no extra systems:** every PS2 class also exists on PC. Things that first looked cut (the squid boss) turned out to be shipped content.

The full Hot Pursuit story is in `docs/cut_content.md` §2; its decoded logic in `docs/exe_analysis.md` §10.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/ps2_cut_content_findings_old_2026-11-27.md`.

---

## Contents

1. [The stage-name table](#1-the-stage-name-table)
2. [Story-quest classes](#2-story-quest-classes)
3. [Hot Pursuit fields and text](#3-hot-pursuit-fields-and-text)
4. [Candy Wilson, Highlands Bay, Dolphin Passage](#4-candy-wilson-highlands-bay-dolphin-passage)
5. [Developer-only strings](#5-developer-only-strings)
6. [Checking against PC](#6-checking-against-pc)
7. [Later PC findings](#7-later-pc-findings)
8. [Old mistakes](#8-old-mistakes)

---

## 1. The stage-name table

A table in `.data` at `0x004CD8D8`, 12 bytes per entry (how it was found: `docs/ps2_disassembly_notes.md` §5):

```c
struct StageNameEntry {
    uint32_t name_ptr;   // address of the name in .rodata
    uint32_t zero;       // always 0
    uint32_t flag;
};
```

| # | Name | Flag |
|---|---|---|
| 1 | Open Ocean South | 1 |
| 2 | The Arrival | 1 |
| 3 | Break Out | 1 |
| 4 | Dead of Night | 1 |
| 5 | *(pointer into `.sdata`, not resolved; by position probably Hunted, stage 4)* | 1 |
| 6 | Predator in the Bay | 1 |
| 7 | Angry Armada | 1 |
| 8 | A Taste for Blood | 1 |
| 9 | The Deep | 1 |
| 10 | **Deepsea Facility** | 1 |
| 11 | Blood on the Beach | 1 |
| 12 | **Hot Pursuit** | **0** |
| 13 | The Final Chase | 0 |
| 14 | Open Ocean East | 0 |
| 15 | Open Ocean West | 0 |
| 16 | Grand Occasus Canals | 0 |
| 17 | Underwater Caves | 0 |
| 18 | Fisherman's Isle | 0 |
| 19 | *(pointer into `.sdata`)* | `0xFA` |

**The two titles:**
- **"Hot Pursuit"** sits exactly between Blood on the Beach (10) and The Final Chase (11). Before this, the stage was known only from class names.
- **"Deepsea Facility"** sits between The Deep (8) and Blood on the Beach: the PS2 title of stage 9.

**The flag:**
- It's 1 for every entry up to Blood on the Beach, and 0 from Hot Pursuit on.
- It's not a simple "cut" marker: the shipped Final Chase has 0 too.
- Maybe "has a numbered stage-select slot". The open-ocean zones and side areas have 0, and The Final Chase can't be replayed from the open ocean.
- **Unresolved:** the code that reads the flag wasn't found (`docs/ps2_disassembly_notes.md` §6).

---

## 2. Story-quest classes

From a full string sweep:

```
Stage0Quest, Stage2Quest, Stage4Quest, Stage6Quest, Stage9Quest, Stage11Quest,
StageBeachQuest, StageDocksQuest, StageDocksQuestEvent, StageWreckQuest,
StageDeepSeaQuest, StageDeep2Quest, StageDeepSeaQuestEvent,
StagePursuitQuest, StagePursuitQuestEvent, StagePursuitQuest2, StagePursuitQuest2Event
```

**Why this makes Hot Pursuit a story stage** (2026-08-12):
- Every class here uses the `Stage…Quest` pattern.
- No side challenge, shipped or cut, uses it. They use `…Mission`, `ANSideMission#`, `BGSideMission#` or `MBSideMission#`.
- Together with its place in the numbered stage list (§1), this makes it a story stage.

**Four Pursuit classes**, more than any shipped stage. On PC, `StagePursuitQuest` turned out to be a first draft and `StagePursuitQuest2` the full mission (`docs/exe_analysis.md` §10).

**Tutorial sub-goals** (shipped, not cut): `TutorialQuests` with `FirstQuest`, `BiteQuest`, `FirstBoatQuest`, `FirstCageQuest`, `FirstSeaSeekerQuest`, `DiversQuest`, `SunkenShipQuest`, `SwimmersQuest`, `DestroyPierQuest`.

---

## 3. Hot Pursuit fields and text

**Field names in the PS2 exe:**

```
m_GateIDList, m_GateCloserIDList, m_GateOpenPosIDList,
m_GateClosePosIDList, m_GateOpenerIDList            gates
m_OnBossFight, m_PursuitLostDist                    boss phase, lose distance
```

- The PC exe has the same fields; their use is decoded in `docs/exe_analysis.md` §10.
- The gates fit the canal locks of MINEMSHA (§7).
- Nearby strings `m_killpeople`, `m_peoplenum`, `m_people…` belong to some class not identified here; they're not among the Pursuit quests' fields on PC.

**The PS2 mission texts:**

```
"Destroy all the jet skis!\nPress ^CONT^ to continue."
"The jet skiers have escaped!\nMission failed!\nPress ^CONT^ to continue."
```

These are the texts the quest code itself shows. The PC exe has the same two, plus a separate goal text (§4).

---

## 4. Candy Wilson, Highlands Bay, Dolphin Passage

**Candy Wilson** (the PC goal text: *"…stop them from reaching the home of Amity Police Chief Candy Wilson"*):
- "Candy" and "Wilson" appear nowhere in `SLUS_210.62`.
- Nor in any of the 12 `STRDATA/*.MIC` files (`AQUARIUM`, `ARMADA`, `BEACH`, `CHASE`, `DEEPSEA`, `DOCKS`, `KATATAMA`, `MUSIC`, `TMYOPEN`, `TMYSTART`, `TOWN`, `WRACK`), checked 2026-08-15.
- **This says nothing about when the line was written.** The PS2 exe lacks the PC's whole mission-goal text pool, not just this line: shipped goals like "BEAT THE COLOSSAL SQUID BOSS!" and "FIND AND DESTROY THE FIVE CONTROL ROOMS" are missing too. The PS2 keeps its goal text somewhere not located, or has none.

**Highlands Bay:** a map name on PC that leads nowhere. Absent from the PS2 exe's map-name table.

**Dolphin Passage is not cut.** It's the shipped channel between OPEN_S and OPEN_NE (user-confirmed in-game; shared `MapItemPos_Dolphin Passage` position, `FromS`/`FromNE` markers). Whether the PS2 exe has the label string wasn't re-checked; that would only be a UI-text difference.

---

## 5. Developer-only strings

| String | Context |
|---|---|
| `ANShipDebug` | A debug ship class, among `ANPosition`, `ANVolumetricLight`, `ANSideMission21`, `ANShipGen` |
| `m_debugspheres` | A debug drawing field on a boss class (near `m_bosssprite1/2`, `m_reflector`, `m_lock_texture`, `m_scoretype`) |
| `m_todo` (×2) | Literal TODO fields in two classes: one near explosion, boss and ship fields; one near `MBCsik`, `DDThrow`, `MBScale`, `MBTeszt` (Hungarian "test"), `MBScore` |
| `"Placeholder Description"` | Fallback text on the ability screen (near `"DAMAGE %d"`, `"MOVEMENT %d"`, `"NUTRITION %d"`) |
| `REMOVED` | A state value next to `FLOOD`, `CHARGED`, `IDLE`, `FEAR`, tied to `TKSub`, `HalDaru`, `Sensor`, `m_crab`. Probably the mining site's submarine and crab entities; not "removed content". |

---

## 6. Checking against PC

**Always check a PS2 find against the PC exe and levels before calling it cut.** The PS2 exe keeps more readable detail, which is easy to mistake for extra content.

**The squid boss is shipped, not cut.**
- PS2 strings such as `NASquidBoss`, `NASquidCam`, `BossSquidBody_Idle/LeftToRightSlash/RightToLeftSlash/VerticalSlash/Dizzy/Grab/Charge`, `Tentacle_Repel/Grab/Dizzy` and `MSG_BOSSSQUID_COLUMN_DESTROYED` were first flagged as a cut boss.
- But the PC exe has the goal "BEAT THE COLOSSAL SQUID BOSS!", and `Squid` appears 137 times in PC `DEEPSEA2.GDW`.
- `CTRLROOM_DESTROYED`, `CTRLRoomcount`, `CTRLRooms`, `DEEPstate`, `DEEP2state` belong to the same shipped DEEPSEA/DEEPSEA2 content.
- A small unexplained difference: PS2 `DEEPSEA2.GDE` has 149 `Squid` hits against PC's 137.

**Class lists compared:**
- PC's `CLAS` has 311 classes, PS2's 302.
- PC's 9 extra are PC settings menus (`MSLanguageMenu`, `MSRefreshRateMenu`, `MSSaveEnableMenuItem`, …).
- **PS2 has no class the PC lacks.** No hidden extra systems.

---

## 7. Later PC findings

PC work after this (2026-08-12 on) answered several questions this doc left open. Full story: `docs/cut_content.md` §2.

- **MINEMSHA is Grand Occasus Canals** (SC15 Up a Creek): 50 `canal01`–`canal50` segments and 35 `canal_f` pieces. Real canals explain the gate fields.
- **Placed Hot Pursuit objects exist, mostly in MINEMSHA.**
  - `JetskiChase` and `ccjetski` appear only there.
  - `jetski_mountpoint` / `jetskipath` appear there and in OPEN_S and TOWN.
  - `jetski 1`, `JetskiChase` and `jetskipath` sit within ~3 units of each other at (−1254, 0, −787), in the same canal cove as SC15's trigger and treasure chest.
- **Still live on PC:** a jet ski spawns there every time the level loads, ridden by an NPC stuck in A-pose (user-tested).
- **A second site in OPEN_NE:** a bare marker node named `HOTPURSUIT` near the `Brody's House` map location. No house is built there (user-checked in-game).
- **The lighthouse** in the goal text: two candidates, a placeholder `Lighthouse02` (~4,270 units away) and a fully modelled one near the Coast Guard HQ. See `docs/cut_content.md` §2.
- **Playable restoration:** `scripts/build_pursuit_test.py` (`PURSUIT` custom level).

---

## 8. Old mistakes

| Old claim | Now |
|---|---|
| The squid boss is cut content | Shipped (§6) |
| The PS2 exe keeps Pursuit fields that the PC exe lost | The PC exe has them too and its quest logic is fully decoded (`docs/exe_analysis.md` §10) |
| Candy Wilson was written after the April 2006 PS2 build | Withdrawn 2026-10-11: the PS2 exe lacks all goal texts (§4) |
| Dolphin Passage is a cut map name | A shipped zone transition |
| `Quest`/`Quest2` may be two phases, like `StageDeepSeaQuest`/`StageDeep2Quest` | `Quest` is a first draft, `Quest2` the full mission |
| The only lighthouse is `Lighthouse02` | There's also a modelled lighthouse at the Coast Guard HQ |

# PS2 Cut-Content Findings

String and struct analysis of `GAME_GDWs/ps2/SLUS_210.62` (the PS2 executable), using the same technique that originally surfaced PC's cut-content evidence in `Jaws.exe`. Cross-checked against PC wherever possible to avoid false positives (see the "Corrections" section below for a near-miss caught during this pass).

---

## Confirmed Cut-Stage Titles

A stage-name string list in `SLUS_210.62` gives the following, in order:

```
Open Ocean South, The Arrival, Break Out, Dead of Night, Predator in the Bay,
Angry Armada, A Taste for Blood, The Deep, Deepsea Facility, Blood on the Beach,
Hot Pursuit, The Final Chase, Open Ocean East, Open Ocean West,
Grand Occasus Canals, Underwater Caves, Fisherman's Isle
```

Two titles here resolve previously-open questions from `mission_system.md` / `CLAUDE.md`:

- **"Hot Pursuit"** — the full title of the cut post-M10 story stage, previously known only via class names (`StagePursuitQuest`). Sits exactly where expected in the list, between "Blood on the Beach" (M10) and "The Final Chase" (M11).
- **"Deepsea Facility"** — the full title of M09, previously just an inferred label ("The Facility"). Sits between "The Deep" (M08) and "Blood on the Beach" (M10).

## The Mission-Name Table Structure

The string list above is backed by a data table in `.data`, base address `0x004cd8d8` (file offset `0x4cd8d8`). 12-byte entries:

```c
struct StageNameEntry {
    uint32_t name_ptr;  // vaddr into .rodata
    uint32_t zero;      // always 0 in observed entries
    uint32_t flag;
};
```

Decoded entries (`ptr`/`flag`, string resolved from `.rodata`):

| Entry | flag |
|---|---|
| Open Ocean South *(table starts here)* | 1 |
| The Arrival | 1 |
| Break Out | 1 |
| Dead of Night | 1 |
| *(unresolved pointer, into `.sdata` not `.rodata`)* | 1 |
| Predator in the Bay | 1 |
| Angry Armada | 1 |
| A Taste for Blood | 1 |
| The Deep | 1 |
| Deepsea Facility | 1 |
| Blood on the Beach | 1 |
| **Hot Pursuit** | **0** |
| The Final Chase | 0 |
| Open Ocean East | 0 |
| Open Ocean West | 0 |
| Grand Occasus Canals | 0 |
| Underwater Caves | 0 |
| Fisherman's Isle | 0 |
| *(unresolved pointer, into `.sdata`)* | 0xfa |

**Finding:** the `flag` field is `1` for every entry through "Blood on the Beach," then flips to `0` starting exactly at **"Hot Pursuit"** and stays `0` through "Fisherman's Isle." This is a real, verified structural distinction in the compiled data — since "The Final Chase" (a real, shipped M11 mission) also carries `flag=0`, this is likely **not** a simple cut/unused marker, but something more like "has a numbered stage-select slot" vs. "does not" (Open Ocean zones and side areas are also `flag=0`, and per `CLAUDE.md`, M11 is documented as "not revisitable from Open Ocean" — consistent with not needing a numbered slot). **Not fully resolved** — the exact semantic of the flag bit hasn't been traced to consuming code (see `ps2_disassembly_notes.md` for why that trace didn't succeed this pass).

## Jet-Ski / "Hot Pursuit" Mission Text Differs From PC

PS2's jet-ski mission objective/fail text:
```
"Destroy all the jet skis!\nPress ^CONT^ to continue."
"The jet skiers have escaped!\nMission failed!\nPress ^CONT^ to continue."
```

This is simpler than PC's version (`CLAUDE.md`'s "Cut Content" section): no mention of Candy Wilson, no police chief, no lighthouse framing. **"Candy" does not appear anywhere in the PS2 executable** — confirmed via full-binary string search. "Highlands Bay" and "Dolphin Passage" (PC-only cut map names) are likewise absent from the PS2 exe.

**Interpretation:** the Candy Wilson / police-chief-home framing was very likely written *after* this PS2 build (April 2006), sometime before the PC build (October 2006), then cut from both before ship.

## Richer Implementation Detail for the Cut Pursuit Mission

The PS2 exe retains fields stripped from PC's binary, suggesting a more developed mechanic than "chase jet skis":

```
m_GateIDList, m_GateCloserIDList, m_GateOpenPosIDList,
m_GateClosePosIDList, m_GateOpenerIDList         -- a gate-puzzle system
m_OnBossFight, m_PursuitLostDist                 -- boss/chase-loss mechanics
m_killpeople, m_peoplenum, m_people...           -- a hostage/kill-count mechanic
```

Also present: `MSG_BOSSSQUID_COLUMN_DESTROYED`, `CTRLROOM_DESTROYED`, `CTRLRoomcount`, `CTRLRooms`, `DEEPstate`, `DEEP2state` — see "Correction" below, this is **not** part of the cut Pursuit mission, it belongs to the real Colossal Squid boss (`DEEP`/`DEEP2` = `DEEPSEA`/`DEEPSEA2`).

## Full Story-Quest Class List

From a fuller string sweep of `SLUS_210.62` (beyond the earlier targeted keyword greps):

```
Stage0Quest, Stage2Quest, Stage4Quest, Stage6Quest, Stage9Quest, Stage11Quest,
StageBeachQuest, StageDocksQuest, StageDocksQuestEvent, StageWreckQuest,
StageDeepSeaQuest, StageDeep2Quest, StageDeepSeaQuestEvent,
StagePursuitQuest, StagePursuitQuestEvent, StagePursuitQuest2, StagePursuitQuest2Event
```

Note the cut Pursuit mission has **four** related classes (`Quest`, `QuestEvent`, `Quest2`, `Quest2Event`) — more than any single shipped mission — suggesting it may have been planned as a two-phase mission at some point (`Quest`/`Quest2` mirrors the `StageDeepSeaQuest`/`StageDeep2Quest` split used for the real two-part M08 Deep mission across `DEEPSEA.GDW`/`DEEPSEA2.GDW`).

Also found: `TutorialQuests` containing `FirstQuest`, `BiteQuest`, `FirstBoatQuest`, `FirstCageQuest`, `FirstSeaSeekerQuest`, `DiversQuest`, `SunkenShipQuest`, `SwimmersQuest`, `DestroyPierQuest` — internal names for the shipped tutorial's sub-objectives, not cut content.

## Other Dev-Only Strings Found

From the full strings sweep, not previously documented:

| String | Context |
|---|---|
| `ANShipDebug` | Debug-only ship class, sits among `ANPosition`, `ANVolumetricLight`, `ANSideMission21` (confirms known SC20 class number), `ANShipGen` |
| `m_debugspheres` | Debug visualization field on a boss class (near `m_bosssprite1/2`, `m_reflector`, `m_lock_texture`, `m_scoretype`) |
| `m_todo` (×2, different classes) | Literal TODO marker fields — one near explosion/boss/ship fields, one near `MBCsik`, `DDThrow`, `MBScale`, `MBTeszt` (Hungarian for "MBTest"), `MBScore` |
| `"Placeholder Description"` | Fallback UI text in the ability/upgrade stat screen (near `"DAMAGE %d"`, `"MOVEMENT %d"`, `"NUTRITION %d"`) |
| `REMOVED` | A state-enum value (alongside `FLOOD`, `CHARGED`, `IDLE`, `FEAR`) tied to `TKSub`, `HalDaru`, `Sensor`, `m_crab` — likely more detail for the Deepsea Facility mining-site content (submarine + crab entities), not "removed content" despite the name |

## Corrections Made During This Investigation

**Near-miss, caught before being reported as fact:** initially flagged a "cut Colossal Squid boss" from PS2 exe strings (`NASquidBoss`, `NASquidCam`, `BossSquidBody_Idle/LeftToRightSlash/RightToLeftSlash/VerticalSlash/Dizzy/Grab/Charge`, `Tentacle_Repel/Grab/Dizzy`, `MSG_BOSSSQUID_COLUMN_DESTROYED`). **This is real, shipped PC content, not cut** — PC's `Jaws.exe` has the loading-tip string `"BEAT THE COLOSSAL SQUID BOSS!"`, and `Squid` appears 137× in PC's `DEEPSEA2.GDW` (tied to M08/M09). One small, real, unexplained gap remains: PS2's `DEEPSEA2.GDE` has 149 squid-string hits vs PC's 137 — a modest quantitative difference in the encounter data, not a missing boss.

**Lesson for future passes:** always verify a PS2-exe string find against PC's `Jaws.exe` and GDWs before reporting it as cut content — the PS2 exe's richer, less-stripped reflection data makes it easy to mistake "PS2 kept more implementation detail for real content" for "PS2 has content PC doesn't."

**Also re-confirmed via a full class-registry diff:** PC's `CLAS` chunk lists 311 registered classes vs PS2's 302. PC's 9 extra are all PC-specific settings-menu classes (`MSLanguageMenu`, `MSRefreshRateMenu`, `MSSaveEnableMenuItem`, etc. — refresh rate / language / memory-card-format prompts). **PS2 has zero classes not also in PC.** This argues against PS2 having hidden extra *systems*, even though (per this document) it does retain some cut-mission implementation detail PC's binary lost.

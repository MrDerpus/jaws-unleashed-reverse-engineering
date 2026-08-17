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

This is simpler than PC's version (`CLAUDE.md`'s "Cut Content" section): no mention of Candy Wilson, no police chief, no lighthouse framing. **"Candy" does not appear anywhere in the PS2 executable** — confirmed via full-binary string search. **Re-confirmed and extended 2026-08-15: "Wilson" also has zero occurrences in `SLUS_210.62`, and both "Candy" and "Wilson" have zero occurrences across all 12 per-level string tables in `GAME_GDWs/ps2/STRDATA/*.MIC`** (`AQUARIUM`, `ARMADA`, `BEACH`, `CHASE`, `DEEPSEA`, `DOCKS`, `KATATAMA`, `MUSIC`, `TMYOPEN`, `TMYSTART`, `TOWN`, `WRACK`) — these `.MIC` files hadn't previously been checked as a possible separate localized-text location outside the main exe; this closes that gap. The Candy Wilson narrative is confirmed absent from every text-bearing PS2 file examined, not just the main executable. "Highlands Bay" (genuinely cut/unused — see `CLAUDE.md`) is likewise absent from the PS2 exe's map-name string table. **Correction (2026-08-14):** "Dolphin Passage" was previously grouped with Highlands Bay here as a "cut map name," but it is not cut — it's the real, shipped `OPEN_S`↔`OPEN_NE` zone-transition channel (user-confirmed in-game, verified in GDW data via a shared `MapItemPos_Dolphin Passage` position and matching `FromS`/`FromNE` transition markers — see `CLAUDE.md`/`docs/mission_system.md`'s "Cut / unused map areas" sections). Whether the PC exe's "Dolphin Passage" map label string is likewise absent from the PS2 exe wasn't re-verified after this correction — that would only speak to a PS2 UI-text difference, not to whether the underlying zone-transition content exists on PS2.

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

**This class list is also the primary evidence (2026-08-12) that Hot Pursuit was a cut *story* mission, not cut side content:** every class here uses the `Stage*Quest` naming pattern — no shipped or cut side challenge anywhere in the game uses that grammar (they use `...Mission`, `ANSideMission#`, `BGSideMission#`, `MBSideMission#` instead). Combined with Hot Pursuit's position in the stage-name list above (interspersed in the numbered M01–M11 sequence, not grouped with the free-roam zone names at the list's tail), this confirms story-mission status. Full writeup with both pieces of evidence in `mission_system.md`.

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

## PC-side follow-up (2026-08-12) — "Hot Pursuit" has a real, identified GDW and location

Later PC-side investigation (see `mission_system.md`'s "Cut story mission — Hot Pursuit" section for the full writeup) resolved several things this document left open:

- **The "gate-puzzle system" fields above (`m_GateIDList`, `m_GateOpenPosIDList`, etc.) are almost certainly canal lock/sluice gates, not an abstract puzzle mechanic.** `MINEMSHA.GDW` — previously an unidentified GDW in `mission_system.md`'s level table — turned out to be the dedicated GDW for **Grand Occasus Canals** (SC15 "Up a Creek"), confirmed by its BRTR containing 50 numbered `canal01`–`canal50` segments plus 35 `canal_f` variants. Real canals make the gate fields make immediate sense.
- **Real placed BRTR scene objects for Hot Pursuit exist and are concentrated almost entirely in `MINEMSHA.GDW`** (not spread across all 20 GDWs like the engine's usual shared-asset pool): `JetskiChase` and `ccjetski` appear only there; `jetski_mountpoint`/`jetskipath` appear there plus `OPEN_S.GDW`/`TOWN.GDW`. Resolving the full BRTR parent-child hierarchy (`scripts/resolve_brtr_hierarchy.py`) puts `jetski 1`, `JetskiChase`, and `jetskipath` within ~3 world units of each other at **(-1254, 0, -787)** — tight enough clustering to be deliberate level authoring, not leftover template data — sitting in the same small canal cove as the shipped SC15 mission trigger and its treasure-chest collectible.
- **Confirmed still live in the shipped PC build:** a user testing the PC release found a jet ski reproducibly spawns at this exact spot every time the level loads, ridden by an NPC stuck in A-pose (bind/rest pose — i.e. never told which animation clip to play). That's the shipped-but-unfinished spawner this document's field analysis predicted, now observed running.
- **A second, independent site was found (2026-08-12) in `OPEN_NE.GDW`:** a bare anchor node literally named `HOTPURSUIT` (no mesh, zero-size AABB — a level-designer reference marker, same grammar as other confirmed mission markers in this project), sitting near the `Brody's House` map-UI location. Investigated whether that map location was meant to be Candy Wilson's house — inconclusive, but the location does have no house actually built there in-game (confirmed by the user visiting it), consistent with a mapped destination that never got its building placed before the mission was cut. Full writeup in `mission_system.md`.
- **Still open:** the mission text's "near the lighthouse" framing doesn't reconcile with either site — the only placed `Lighthouse02` object found anywhere is ~4,270 units from the `HOTPURSUIT`/`Brody's House` cluster, not adjacent to it. Either the mission's setting changed during development, or the pursuit was meant to span multiple zones (`MINEMSHA.GDW`'s canals plus an `OPEN_NE.GDW` open-water endpoint).

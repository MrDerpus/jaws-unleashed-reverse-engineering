# Mission System — Jaws Unleashed

Sourced from `context.txt` (PS2 strategy guide, Wayne Pietra Jr., v2.07) and `game_binary/Jaws.exe` string analysis.

---

## Story Missions (11 total)

| ID | Stage | Title |
|---|---|---|
| M01 | 1 | Tutorial *(also "The Arrival", set in Red Reef Valley / Open Ocean: South)* |
| M02 | 2 | The Break Out |
| M03 | 3 | The Dead of Night |
| M04 | 4 | Hunted |
| M05 | 5 | Predator in the Bay |
| M06 | 6 | The Angry Armada |
| M07 | 7 | A Taste for Blood |
| M08 | 8 | The Deep |
| M09 | 9 | The Facility |
| M10 | 10 | Blood on the Beach |
| M11 | 11 | The Final Chase |

The `MSStageSelect` data structure has `m_Stage1ID`–`m_Stage18ID` — **18 stage slots** for 11 shipped missions. The 7 unused slots were likely reserved for cut story missions.

---

## Side Challenges (32 total)

| SC# | Title | Mechanic (from strategy guide) |
|---|---|---|
| SC01 | Barrels of Fun | Ship + buoys at three difficulty levels (`BarrelsOfFunMission`) |
| SC02 | Seal Whip | Kill seals; crew attempts rescues (`SealWhipMission`) |
| SC03 | Bay Patrol Blood Bath | Kill lifeguards (`BayPatrolBloodBathMission`) |
| SC04 | Dolphin Sightseeing Junket | Stop dolphins from escaping the boat's path (`MSDolphinSightseeingMission`) |
| SC05 | Dog Gone | Kill the dog and NPCs before surface timer expires (`MSDogGoneMission`) |
| SC06 | Flip the Bird | Destroy a rescue helicopter by biting its ladder (`FlipTheBirdMission`) |
| SC07 | Reality TV | Kill bungee jumpers as they dip into the water off South Amity Cliffs (`BGSideMission8`) |
| SC08 | Row Your Boat | Destroy a rowboat that weaves through fences within a time limit (`BGSideMission9`) |
| SC09 | Sheebang! | Grab a swimmer and smash them into a yellow buoy using the surface drag attack (`MBSideMission10`) |
| SC10 | The Bends | Kill %d divers at the Underwater Caves before any reach the surface (`TheBendsMission`) |
| SC11 | The Best Laid Plans | Destroy shark cages and kill the divers within a time limit (`MBSideMission12`) |
| SC12 | Trouble and Strife | Kill the TV crew within a time limit; offensive boats patrol the area (`TroubleAndStrifeMission`) |
| SC13 | To Kill a Killer | Narwhal challenge (`MSKillKillerMission`) |
| SC14 | Undertow | Kill water skiers mid-air off ramps — fail if they land (`ANSideMission15`) |
| SC15 | Up a Creek | Navigate and kill in the Grand Occasus Canals; fight the current (`UpACreekMission`); dedicated GDW is `MINEMSHA.GDW` (identified 2026-08-12) |
| SC16 | Head Rush | Throw grabbed swimmers at beach tents and citizens (`MBSideMission17`) |
| SC17 | Mine All Mine | Defend a blue whale carcass from attacking sharks for the timer (`MSMineAllMineMission`) |
| SC18 | Return to Sender | Throw explosive barrels at Environplus executive houses, kill them as they flee (`BGSideMission19`) |
| SC19 | Get Mr. Stripes | Chase and kill three injured fish through the minefield (`GetMrStripMission`) |
| SC20 | Losing Your Head | Drag banana boat to the piers, knock riders off, kill them in time (`ANSideMission21`) |
| SC21 | Scavenge | Collect %d tires in an underwater pit; Seaseeker and Coast Guard raft obstacles (`ANSideMission22`) |
| SC22 | The Gauntlet | Race through underwater caves from start box to end box; jellyfish, viper fish, thermals (`TheGauntletMission`) |
| SC23 | Manic Maze | Kill swimmers inside a shark-proof net maze before they escape (`BGSideMission24`) |
| SC24 | Catamaran Jam | Flip over %d catamarans within a time limit (`ANSideMission25`, `MSKatatamaMission`) |
| SC25 | Oh Puppy | Kill white seal pups before they reach Seal Island; avoid black adult seals (`OhPuppyMission`) |
| SC26 | Orca Revenge | Kill the orca at the Aquarium within a time limit (`MBSideMissionAQ`) |
| SC27 | Shark Frenzy | Kill %d sharks in time (`FrenzyMission`) |
| SC28 | Dolphin Frenzy | Kill %d dolphins in time (`FrenzyMission`) |
| SC29 | Thar She Blows | Blow up %d boats using explosive canisters in time (`ANSideMission33`) |
| SC30 | Deep Chase | Follow and kill divers through the ENVIRONPLUS mining tunnels before they reach safety *(no named class found)* |
| SC31 | Lights Out | Destroy %d guard tower spotlights in Grand Occasus Harbor using barrels (`BGSideMission31`) |
| SC32 | Swim for Life | Kill a white seal pup before it escapes to open ocean *(no named class found; may reuse `OhPuppyMission`)* |

---

## Complete Side Challenge Class Reference

All 32 side challenges have been mapped to their implementation classes. The **internal class number does not match the display SC number** — numbered classes (AN, BG, MB prefix) consistently use `internal = display + 1`, with a larger gap (AN33 → SC29, offset +4) where cut challenges compressed the display numbering. Named classes (e.g. `FlipTheBirdMission`) carry their own SC number in debug logs that also follows the +1 rule.

| Display SC# | Challenge | Primary Class | Objective / Mechanic |
|---|---|---|---|
| SC01 | Barrels of Fun | `BarrelsOfFunMission` | Ship + buoys; `m_BuoyIDEasy/Medium/Hard`, breakdown effects |
| SC02 | Seal Whip | `SealWhipMission` | Kill seals; `m_SealList`, `m_CrewList`, rescue race |
| SC03 | Bay Patrol Blood Bath | `BayPatrolBloodBathMission` | Kill lifeguards; `m_LifeguardList` |
| SC04 | Dolphin Sightseeing Junket | `MSDolphinSightseeingMission` | Stop dolphins escaping; `m_DolphinID`, boat speeds, path |
| SC05 | Dog Gone | `MSDogGoneMission` | Kill dog + fat NPC + surfer before surface timer; `m_DogID`, `m_FatID`, `m_SurfID` |
| SC06 | Flip the Bird | `FlipTheBirdMission` | `DESTROY THE HELICOPTER!` — bite the rescue ladder, pull heli into water; `m_HeliID`, `m_LadderBiteablePart` |
| SC07 | Reality TV | `BGSideMission8` | `KILL %d BUNGEE JUMPERS WITHIN %d SECONDS!` — reality TV bungee show, South Amity Cliffs |
| SC08 | Row Your Boat | `BGSideMission9` | Destroy a rowboat weaving through fences; `m_RowBoatIDList_e/m/h`, boundary zone |
| SC09 | Sheebang! | `MBSideMission10` | `Grab the swimmer and bang her into the yellow buoy within %d seconds` — surface drag attack |
| SC10 | The Bends | `TheBendsMission` | Kill %d divers before any reach the surface; `m_DiverList` |
| SC11 | The Best Laid Plans | `MBSideMission12` | `Destroy the shark cage and kill the diver within %d seconds`; `m_cages`, `m_divers` |
| SC12 | Trouble and Strife | `TroubleAndStrifeMission` | `KILL THE TV CREW IN %d SECONDS!`; `m_NumCrewEasy/Medium/Hard`, offensive boats, enter/leave box |
| SC13 | To Kill a Killer | `MSKillKillerMission` | Narwhal challenge; `m_NarwhalsID`; `MAKE THE NARWHALS ANGRY` |
| SC14 | Undertow | `ANSideMission15` | `KILL THE WATER SKIERS WHILE THEY ARE JUMPING OFF OF THE RAMPS!`; `m_ramprefs`, `m_ramproot` |
| SC15 | Up a Creek | `UpACreekMission` | Grand Occasus Canals (`MINEMSHA.GDW`); `m_CivilContainerID`; `CURRENT'S TOO STRONG.`; internal trigger node `SM16UpACreek` |
| SC16 | Head Rush | `MBSideMission17` | `Throw the swimmers at citizens or tents successfully hitting %d within %d seconds`; `m_swimmers` |
| SC17 | Mine All Mine | `MSMineAllMineMission` | `DEFEND THE WHALE CARCASS FOR %d SECONDS.`; `m_WhaleID`, `m_SharksID` |
| SC18 | Return to Sender | `BGSideMission19` | Throw barrels at Environplus houses, kill executives; `m_HouseIDList`, `m_ExecutiveIDList`, `m_BarrelFolder` |
| SC19 | Get Mr. Stripes | `GetMrStripMission` | Chase and kill injured fish through minefield; `m_FishList` |
| SC20 | Losing Your Head | `ANSideMission21` | `DRAG BANANA BOAT TO THE PIERS, KNOCK %d PEOPLE OFF, THEN KILL THEM WITHIN %d SECONDS.` |
| SC21 | Scavenge | `ANSideMission22` | `COLLECT %d TIRES IN UNDER %d SECONDS.`; `m_coll_refs`, `m_seeker_refs`, `m_ship_refs` |
| SC22 | The Gauntlet | `TheGauntletMission` | Race from `m_StartBox` to `m_EndBox` through caves; `m_EasyList/MediumList/HardList` of hazards |
| SC23 | Manic Maze | `BGSideMission24` | Kill swimmers inside net maze; `m_SwimmerContainer`, `m_NetContainer`; `You have left the maze.` |
| SC24 | Catamaran Jam | `ANSideMission25` + `MSKatatamaMission` | `FLIP OVER %d CATAMARANS IN %d SECONDS.`; `m_shiprefs`, `m_eflipnum/mflipnum/hflipnum` |
| SC25 | Oh Puppy | `OhPuppyMission` | Kill white seal pups before Seal Island; `m_WhiteSealList`, `m_BlackSealList` (avoid) |
| SC26 | Orca Revenge | `MBSideMissionAQ` | `Kill the orca within %d seconds.` — rematch of M02 boss at the Aquarium |
| SC27 | Shark Frenzy | `FrenzyMission` | Kill %d sharks in 60 seconds |
| SC28 | Dolphin Frenzy | `FrenzyMission` | Kill %d dolphins in 60 seconds |
| SC29 | Thar She Blows | `ANSideMission33` | `BLOW UP %d BOATS IN %d SECONDS.`; `m_dcrefs` (explosive canisters) |
| SC30 | Deep Chase | *(no named class found)* | `FOLLOW AND KILL THE DIVERS BEFORE THEY REACH SAFETY!`; mining tunnels |
| SC31 | Lights Out | `BGSideMission31` | `DESTROY %d GUARD TOWERS WITHIN %d SECONDS!`; `m_TowerList`, `m_TowerGuardList` |
| SC32 | Swim for Life | *(no named class found)* | Kill a white seal pup before it escapes; may reuse `OhPuppyMission` |

**Additional classes not directly mapped to a shipped SC:**
- `OrcaExplorationMission` — boats, police, scuba divers, cages at 3 difficulty levels; likely the M02 aquarium sequence logic or a cut challenge distinct from SC26
- `KillthemallMission` — **cut side challenge**; `m_SharkStart`; Hungarian visual targeting fields; not in shipped SC list

---

## Numbering Offset Pattern

For numbered mission classes, internal number = display SC# + 1 in almost all cases:

| Type | Example | Internal → Display |
|---|---|---|
| `ANSideMission` | AN15 → SC14 | +1 |
| `BGSideMission` | BG8 → SC07, BG9 → SC08 | +1 |
| `MBSideMission` | MB10 → SC09, MB12 → SC11 | +1 |
| `FlipTheBirdMission` | debug tag "SC07" → display SC06 | +1 |
| `ANSideMission33` | AN33 → SC29 | +4 (3 cut challenges) |
| `BGSideMission31` | BG31 → SC31 | 0 (anomaly or direct mapping) |

---

---

## Cut Content

### Down the Hatch (cut side challenge)

- **Class:** `MSHatchMission`
- **Evidence:** String `" -, Down the Hatch (unused!)"` in stage select list; class present in all 20 GDW CLAS chunks; not instantiated in any BRTR
- **Mechanic:** `SWALLOW %d COLLECTABLES WITHIN %d SECONDS.` — uses the shark's built-in swallow animation to eat spawned collectables before the timer expires; three difficulty levels
- **Relation to SC21 Scavenge / SC22 The Gauntlet:** Scavenge also involves collecting items (`m_coll_refs` = tires) and The Gauntlet is a race/survival challenge. Down the Hatch is a simpler eat-items-in-time challenge with no ships or seekers — likely an earlier proof-of-concept for the collect-and-eat mechanic that was superseded.
- **In-game prompt:** `Swallow!`

### Cut story mission — "Hot Pursuit" (formerly catalogued as two separate entries — corrected 2026-08-12)

**Correction:** earlier passes catalogued "Pursuit" (from the `StagePursuitQuest`/`StagePursuitQuest2` class names) and "Jet Ski Mission" (from the Candy Wilson mission text) as two separate cut missions. They are the same mission. `m_JetSkiIDList`/`m_GateIDList`/`m_GateCloserIDList` are fields declared directly on `StagePursuitQuest`; `m_JetSkiBossIDList`/`m_GateOpenPosIDList`/`m_GateClosePosIDList`/`m_GateOpenerIDList`/`m_OnBossFight`/`m_PursuitLostDist` are on `StagePursuitQuest2` — and the mission's UI strings sit immediately adjacent to these field blocks in `Jaws.exe`. `StagePursuitQuest2` reads as a revised version adding gates and a boss fight on top of the base chase (see `ps2_cut_content_findings.md`'s "Richer Implementation Detail" section for the PS2-side field list, which retains more of this than PC's stripped binary).

**Confirmed official title:** "Hot Pursuit" — found in `SLUS_210.62`'s (PS2 exe) stage-name string table, sitting exactly between "Blood on the Beach" (M10) and "The Final Chase" (M11) — see `ps2_cut_content_findings.md`. It was planned as a full numbered story stage, not a side challenge.

**Confirmed: cut story mission, not cut side content (2026-08-12) — two independent grounds:**
1. **Class naming convention.** Every real, shipped story mission's logic class follows a `Stage*Quest` pattern: `Stage0Quest`, `Stage2Quest`, `Stage4Quest`, `Stage6Quest`, `Stage9Quest`, `Stage11Quest`, `StageBeachQuest`, `StageDocksQuest`, `StageWreckQuest`, `StageDeepSeaQuest`/`StageDeep2Quest` (see `ps2_cut_content_findings.md`'s "Full Story-Quest Class List"). Side challenges use an entirely different naming grammar — `BarrelsOfFunMission`, `UpACreekMission`, `ANSideMission25`, `BGSideMission31`, `MBSideMission10`, etc. — never `Stage...Quest`. Hot Pursuit's classes (`StagePursuitQuest`/`StagePursuitQuest2`/`...QuestEvent`) follow the story-mission pattern exactly.
2. **List position.** In the PS2 stage-name list (see above), Hot Pursuit sits interspersed directly in the numbered M01–M11 sequence — right after "Blood on the Beach" (M10), right before "The Final Chase" (M11) — not grouped with the free-roam zone/side-area names (Open Ocean East/West, Grand Occasus Canals, Underwater Caves, Fisherman's Isle) that are all clustered together at the tail of the same list.

Together with the `MSStageSelect` data structure's 18 stage slots for only 11 shipped missions (see Story Missions section above), this points to Hot Pursuit having occupied one of those 7 unused slots — most likely as M11, with the shipped "The Final Chase" originally meant to follow it (or simply absorbing that slot number once Hot Pursuit was dropped).

**Clarification: Candy Wilson is not the boss.** `m_JetSkiBossIDList` is a *list* field (i.e. a roster of tougher "boss" jet-ski riders as enemies), and `m_OnBossFight` is a separate event trigger for that boss-fight segment — both distinct from Candy Wilson, who only ever appears in the recovered mission text as the person/house the player is protecting, never as a combat target. The boss encounter and the Candy Wilson narrative hook are two separate pieces of the mission, not the same thing.

**Full text (PC, `game_binary/Jaws.exe`, localised EN/FR/DE/IT/ES):**
- Goal: *"Locate the jet skiers near the lighthouse and stop the jet skiers from reaching the home of Amity Police Chief Candy Wilson."*
- *"Kill all the jet skiers!\nPress ^CONT^ to continue."*
- *"Destroy all the jet skis!\nPress ^CONT^ to continue."* — plus a typo'd duplicate sitting right next to it, *"Destroy all the jets kis!\nPress ^CONT^ to continue."*, apparently an unremoved draft line.
- Failure: *"The jet skiers have escaped!\nMission failed!\nPress ^CONT^ to continue."*

PS2's `SLUS_210.62` has the short/fail strings verbatim but is missing the full Candy Wilson goal text and "Kill all the jet skiers!" entirely, and has zero occurrences of "Candy" anywhere — see `ps2_cut_content_findings.md` for the full PS2-side writeup and its dating theory (Candy Wilson framing likely written after the April 2006 PS2 build, cut before the October 2006 PC ship).

**Real placed level content found (2026-08-12), not just code stubs:** scanning all 20 GDWs for jetski-prefixed BRTR object names (verified via the `0x080017D8` object-name PROP, not just string matches) found actual scene-graph nodes: `JetSki`, `Jetski_egyben` ("egyben" = Hungarian "in one piece" — the intact model), `JetskiGen` (spawner), `ANTargeting_jetski`, a set of `JetskiOverlay*` HUD/targeting-overlay elements, and `JetskiQuickRef`/`MediumRef`/`SlowRef` (speed-tier refs) — these are spread across many GDWs consistent with the usual bundled shared-asset pool (see "Shared Assets Across GDWs" in `CLAUDE.md`), so presence alone doesn't mean "used here." But `jetski_mountpoint`/`jetski_mountpoint_a` (vehicle mount points) appear in only 3 files (`MINEMSHA.GDW`, `OPEN_S.GDW`, `TOWN.GDW`), `jetskipath` (a waypoint route) in only 2 (`MINEMSHA.GDW`, `TOWN.GDW`), and `JetskiChase`/`ccjetski` in **only `MINEMSHA.GDW`** — breaking the shared-pool pattern and pointing to real, deliberate placement.

**`MINEMSHA.GDW` identified as Grand Occasus Canals (SC15 "Up a Creek"'s dedicated GDW) — see Level–Mission Mapping table below.** This retroactively explains `StagePursuitQuest2`'s gate fields (`m_GateOpenPosIDList`/`m_GateClosePosIDList`/`m_GateOpenerIDList`, previously unexplained for an open-water chase, flagged as a "gate-puzzle system" in `ps2_cut_content_findings.md`): they're almost certainly canal lock/sluice gates. Running `scripts/resolve_brtr_hierarchy.py` against `MINEMSHA.GDW` (not affected by the BRTR false-positive-offset bug documented elsewhere in this project — the naive chunk offset is already correct here) resolves `jetski 1`, `JetskiChase`, and `jetskipath` to world positions within ~3 units of each other at **(-1254, 0, -787)** — three independently-placed nodes converging tightly, consistent with deliberate authoring rather than an unused template dump. This sits in the same small canal cove as the shipped SC15 trigger `SM16UpACreek` (world (-1257.83, 0, -967.32), ~180 units away — "SM16" is the internal side-mission number, one higher than the shipped "SC15" display number per this project's established `ANSideMission` +1 numbering-offset pattern) and the side challenge's collectible `CGO_Treasurechest 15` (world (-830, -16, -890.99), ~450 units away, partially submerged).

**Live reproducible confirmation (user-found, 2026-08-12):** in the shipped PC game, a jet ski still spawns at this location every time the level is (re-)entered, ridden by an NPC permanently stuck in A-pose (bind/rest pose) — consistent with a vehicle-mount pilot whose animation controller was never wired to play a clip, exactly the failure mode expected from a cut mission whose spawner shipped but whose AI/animation hookup was never finished.

**Second, independent site found in `OPEN_NE.GDW` (2026-08-12):** while investigating whether the mission's "police chief's house" destination corresponds to the shipped `Brody's House` map-UI location in this GDW (a reasonable-looking but ultimately unconfirmed name-coincidence theory — see below), a bare, dimensionless anchor node literally named `HOTPURSUIT` was found at world `(612.5, 0, 3626.4)` — no mesh reference, no children, and its AABB payload is the same point repeated twice (min==max, zero-size box). That's the same grammar as other confirmed level-designer reference markers in this project (`TunnelBlockingDust`/`FromStart2` in `START.GDW`, `SM16UpACreek` in `MINEMSHA.GDW`) — a deliberate placement meant to be looked up by name/ID from code, not a coincidental string match. It sits ~338 units from the `MapItemPos_Brody's House` map marker (world `(929.7, 0, 3508.8)`).

**"Brody's House" investigated as a candidate for Candy Wilson's house — partially supportive, not conclusive.** `Brody` is not itself cut content: it's a real, separate animated character/skeleton with cutscene clips (`MBrody_AuroraCatchesMovie`, `MBrody_AuroraComesMovie`, `MBrody_EscapeAtL4`, `MBrody_GrabHarpoonMovie`, `MBrody_Kormanyoz` — "kormányoz" = Hungarian "steers/pilots") tied to the Aurora / Coast Guard Cutter content confirmed as real M05 material in `KATATAMA.GDW`; Brody-related data appears heavily in `START.GDW` (26 hits), `AQUARIUM.GDW` (24), and `KATATAMA.GDW` (16) — real, shipped mission content, not confined to the cut mission. "Wilson" and "Candy" were searched for as placed object names across every relevant GDW (`OPEN_NE/NW/S`, `TOWN`, `DOCKS`, `BEACH`, and — confirmed 2026-08-13 — `MINEMSHA.GDW` itself) and found nowhere — she has zero footprint in scene data anywhere, only the mission-text strings in `Jaws.exe`. **That mission text itself (2026-08-13):** "Candy Wilson" appears exactly 5 times total in `Jaws.exe` — once per localized language (EN/FR/DE/IT/ES), not duplicated per quest class — and it sits inside a large, shared "mission goals" localization string pool used by the game's briefing-screen UI generally (unrelated missions' goal text, e.g. M08/M09's "BEAT THE COLOSSAL SQUID BOSS!" and mining-site control-room text, sit immediately adjacent in the same table). This means static string analysis alone **cannot** determine whether `StagePursuitQuest`, `StagePursuitQuest2`, or both reference this specific string at runtime — that linkage would require disassembling actual code paths, not just reading constant string tables, and hasn't been attempted for this or any other mission in this project. **In-game confirmation (2026-08-12):** the user visited the `Brody's House` map location directly — there is no house built there at all, just open ground. That fits a location that was reserved/labelled for the mission's target house and never got its building placed before the mission was cut — a cleaner explanation than assuming the label itself was repurposed from a "Candy Wilson's House" that once existed under a different name. (Also corrected in-game: what looked like a "power station" near this area on an earlier pass turned out to be the separate `Eastside Homes` map location — low-poly cars and power-line towers, not an industrial structure, and not connected to Hot Pursuit.)

**Still unresolved:** the mission-goal text says "near the lighthouse," but the only placed `Lighthouse02` object found so far is ~4,270 units from the `HOTPURSUIT`/`Brody's House` cluster in `OPEN_NE.GDW` — not adjacent. Whether the mission was meant to span both `MINEMSHA.GDW` (canal chase) and `OPEN_NE.GDW` (open-water endpoint near a house, possibly near a lighthouse elsewhere in that zone) as one continuous sequence, or these are two separate development-time concepts that both got the same working title, isn't confirmed. The causal/scripted trigger logic connecting any of this is presumed hardcoded in `Jaws.exe`, not present in GDW data — same caveat as the BEACH submarine cut-objective finding elsewhere in this project.

### Cut character

- **Candy Wilson** — Amity Police Chief; referenced in the jet ski mission text only (all five languages); no class name, scene placement, or mesh

### Cut / unused map areas

Both names appear in the in-game map location string table alongside all shipped area names, but are absent from the shipped game and strategy guide:

| Name | Notes |
|---|---|
| **HIGHLANDS BAY** | Between ENVIRONPLUS MINING SITE and BRIDGEPORT SOUND in the string table; likely Open Ocean: East |
| **DOLPHIN PASSAGE** | Between AMITY ISLAND and OLD SOUTH BEACH PIERS; likely Open Ocean: South; may relate to SC04/SC28 |

### Cut objective — BEACH/BEACHPST submarine + blocking boulders (found 2026-07-30)

User reported a stationary underwater "drone" under the bridge in `BEACH.GDW`/`BEACHPST.GDW` that never activates (unlike similar mobile drones elsewhere in the level) but still drains player hunger on proximity, and recalled that `START.GDW`'s tutorial has a submarine which, when destroyed, blows up a boulder blocking the path to open the next area. Investigation found:

- **`TKSub`** — a fully code-complete miniature attack submarine class in the shared `CLAS` reflection registry (speed/turn/strafe controls, hover bob, torpedo firing points, carries a pilot diver, destructible rudder/propeller with a full death FX sequence). Referenced by a single ID field (not a spawn list) from `MSScooter`, alongside `m_ScooterID`, `m_RomboloID` ("Rombolo" = Destroyer), and **`m_TesztID`** ("Teszt" = Hungarian "Test") — the adjacent literal "Test ID" field suggests this Scooter/Sub/Rombolo/Teszt group was a dev-time vehicle-mount test harness, not a uniformly-finished system. No CHBR node named "Sub"/"TKSub" exists in BEACH's or START's static BRTR scene — it's spawned/mounted at runtime via that ID reference, not individually art-placed, so the exact stuck instance can't be located by name search.
- **The mechanic is proven working in `START.GDW`**: a cluster at world pos ~`(535.6, -12.5, 23.5)` — `TunnelBlockingDust`/`TunnelBlockingRockDust`, `TunnelRoom` (the gated room), `FromStart2` (checkpoint marker), and a `LastSeaSeekerMissionBrick` trigger nesting `KoVizbeEsik` ("rock falls into water") and `TitokzatosKod` ("mysterious code"). `Szikla1 127`, one of ~200 generic boulder props, sits on the dust marker as the likely blocking rock.
- **`BEACH.GDW` has a matching, never-opened blocking-boulder group**: `Level3_elzarokovek` ("Level3 Blocking Rocks" — BEACH is internally "Level3"), containing `Elzaroko01/02/03` ("Elzáró" = Hungarian "blocking/sealing") — three ~16-unit boulders clustered ~140 units past the bridge, plus an adjacent invisible collision-blocker plate (`Kizaro_Lap_Kozepes`, same mesh as the level's `LowTideBarrier`). The underwater canyon continues 200+ more units past the rocks to a surface-breaching rock at `Z≈570` — real, fully-built geometry sits sealed behind the barrier.
- **BEACH and BEACHPST (post-mission state) are byte-identical for this group** — same 3 rock positions and structure in both. A working "destroy to progress" objective should show the rocks cleared in the post-mission variant; they aren't, in either state — evidence this objective was never completed before shipping.
- **Working theory, not proven:** the inert BEACH submarine and the permanently-sealed `Elzaroko` boulders are two halves of one cut objective ("destroy the sub → open the canyon → reach the next area"), matching a mechanic proven to work elsewhere (`START.GDW`). The causal trigger itself (sub kill → rock destruction) isn't present in GDW data — presumed hardcoded in `Jaws.exe`'s mission logic. Not yet checked: `DOCKS.GDW`/`TOWN.GDW` for a matching transition marker on the far side of the sealed canyon; runtime instrumentation to confirm live.
- **Independent visual corroboration (2026-07-30):** the in-game Amity Island overview map (a normal, fully shipped UI asset — `OPEN_NE.GDW`'s `gtex_0123_id000002e9_512x256_rgba32.png`, see `CLAUDE.md`'s Texture Database section) shows a distinct rounded interior landform connected to the BEACH coastal cove by a lighter, stream-like break in the canopy art, geographically consistent with the sealed canyon's direction and its dead-end at the edge of BEACH's built geometry. Suggestive, not proof — it's a painted illustration, not literal terrain data.

---

## Challenge Modes (frenzy variants)

Four frenzy modes are separate from the 32 side challenges:
- Shark Frenzy
- Dolphin Frenzy
- Seal Frenzy
- Diver Frenzy

Implemented via `FrenzyMission` class.

---

## Level–Mission Mapping

| GDW | Story Mission | Notes |
|---|---|---|
| `START.GDW` | M01 — The Arrival (Tutorial) | Red Reef Valley |
| `AQUARIUM.GDW` | M02 — The Break Out | South Shore Aquarium |
| `ARMADA.GDW` | M06 — The Angry Armada | Bridgeport Sound |
| `BEACH.GDW` | M10 — Blood on the Beach | Amity Town Beach |
| `BEACHPST.GDW` | M10 post-mission variant | — |
| `CHASE.GDW` | M11 — The Final Chase | Not revisitable |
| `DEEPSEA.GDW` / `DEEPSEA2.GDW` | M08 — The Deep | Two sub-areas |
| `DOCKS.GDW` | M10 probable | Amity Public Docks |
| `FISH.GDW` | **Not M05** — SC17 Mine All Mine (corrected 2026-07-15) | Non-story area: Fisherman's Isle. Nodes literally named `MineAllMine Mission Shark 1-4`, `SideMissionRemainingTimeTextModel`, etc. confirm this; no oil-platform/shipyard/cutter content of any kind is present. |
| `GAUNTLET.GDW` | SC10 The Bends + SC22 The Gauntlet | The Underwater Caves |
| `KATATAMA.GDW` | **M05 — Predator in the Bay** (corrected 2026-07-15, moved from FISH.GDW) | Avril Bay — oil platforms (`DrillingPlatform 1/2/3`), shipyard `PowerPlant 1`, Coast Guard Cutter, `AURORA_LO0`. `MSKatatamaMission` class present but appears to be an unrelated single-field side-mission hunt target, not the SC24 mapping. Checked for cut content here (2026-07-15): none found so far, though nested-BRTR world positions weren't fully resolved for a spatial gap-hunt at the time. |
| `MINEMSHA.GDW` | SC15 — Up a Creek | **Grand Occasus Canals (identified 2026-08-12).** Named after Menemsha Harbour, Martha's Vineyard, but that's just the internal dev filename — BRTR contains 50 numbered `canal01`–`canal50` segments + 35 `canal_f01`–`canal_f35` variants + `fog canal 1/2/3` volumes, a fully-built dedicated canal level. Also hosts the bulk of the cut "Hot Pursuit" mission's leftover placed content (`JetskiChase`, mount points, patrol path) — see Cut Content section below. |
| `OPEN_NE.GDW` | Open Ocean: East free-play zone | Bridgeport Sound, Amity Town Beach, etc. |
| `OPEN_NW.GDW` | Open Ocean: West free-play zone | Grand Occasus Harbor, Water Ski Park, etc. |
| `OPEN_S.GDW` | Open Ocean: South free-play zone | Red Reef Valley, Seal Island, etc. |
| `TOWN.GDW` | M10 probable | Amity Town |
| `WRACK.GDW` | M07 — A Taste for Blood | Misty Ridge |
| `TITLE.GDW` / `TITLE0.GDW` | Title screen | TITLE0 has 0 meshes |

---

## Mission Engine Classes (from CLAS chunk)

| Class | Purpose |
|---|---|
| `MBMissionBrick` | Core mission object placed in BRTR scene |
| `MBAramlat` | Mission brick variant |
| `MSMissionGenerator` | Mission spawn/scenario system |
| `BGSetMissionCompleted` | Marks mission as completed in persistent state |
| `BGSideMission8/9/19/24/31` | Background persistent side mission state |
| `MBSideMission10/12/17/AQ` | Mission brick side missions |
| `OrcaExplorationMission` | Orca side mission |
| `BarrelsOfFunMission` | Barrels of Fun (SC01) |
| `BayPatrolBloodBathMission` | Bay Patrol Blood Bath (SC03) |
| `SealWhipMission` | Seal Whip (SC02) |
| `GetMrStripMission` | Get Mr. Stripes (SC19) |
| `KillthemallMission` | **Cut side challenge** — name not in shipped SC list |
| `FrenzyMission` | Frenzy challenge modes |

---

## "Sole Predator" — Original Working Title

*Sole Predator* was the working title before Majesco licensed the Jaws IP. The string appears in **extracted textures** as promotional/marketing copy describing the game's features — early promotional assets baked into the build that survived the title change. It is absent from class names, mission names, and script strings; the rename was applied to the code/data namespace but not to all texture assets.

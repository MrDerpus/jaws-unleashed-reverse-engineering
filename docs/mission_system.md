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
| SC15 | Up a Creek | Navigate and kill in the Grand Occasus Canals; fight the current (`UpACreekMission`) |
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
| SC15 | Up a Creek | `UpACreekMission` | Grand Occasus Canals; `m_CivilContainerID`; `CURRENT'S TOO STRONG.` |
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

### Cut story missions

- **Pursuit** — `StagePursuitQuest`, `StagePursuitQuest2`, `StagePursuitQuestEvent`, `StagePursuitQuest2Event` in class registry; two variants suggest a two-phase or branching cut story mission
- **Jet Ski Mission** *(untitled)* — fully localised in EN/FR/DE/IT/ES; objective: stop jet skiers near a lighthouse from reaching the home of cut character **Candy Wilson** (Amity Police Chief); fields `m_JetSkiBossIDList`, `m_JetSkiIDList`; failure: `"The jet skiers have escaped!"`

### Cut character

- **Candy Wilson** — Amity Police Chief; referenced in the jet ski mission text only (all five languages); no class name, scene placement, or mesh

### Cut / unused map areas

Both names appear in the in-game map location string table alongside all shipped area names, but are absent from the shipped game and strategy guide:

| Name | Notes |
|---|---|
| **HIGHLANDS BAY** | Between ENVIRONPLUS MINING SITE and BRIDGEPORT SOUND in the string table; likely Open Ocean: East |
| **DOLPHIN PASSAGE** | Between AMITY ISLAND and OLD SOUTH BEACH PIERS; likely Open Ocean: South; may relate to SC04/SC28 |

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
| `MINEMSHA.GDW` | Unknown | Named after Menemsha Harbour, Martha's Vineyard; identity unconfirmed |
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

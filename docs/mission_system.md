# Missions

**In short:** *Jaws Unleashed* has 11 story stages and 32 side challenges. Each is driven by a mission class in the game code. This doc lists them all, which class runs each, which level file holds each, and the collectibles system.

Cut missions (*Hot Pursuit*, *Down the Hatch*, …) are in `docs/cut_content.md`. Win conditions and speedrun details are in `docs/speedrun_glitches.md`.

Sources: the PS2 strategy guide by Wayne Pietra Jr., v2.07 (`context.txt`), the game's own strings and classes, and the level files.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/mission_system_old_2026-11-27.md`.

---

## Contents

1. [Story stages](#1-story-stages)
2. [Level files](#2-level-files)
3. [Side challenges](#3-side-challenges)
4. [Class numbers vs displayed numbers](#4-class-numbers-vs-displayed-numbers)
5. [Side challenges with opening cutscenes](#5-side-challenges-with-opening-cutscenes)
6. [Collectibles](#6-collectibles)
7. [Other mission classes](#7-other-mission-classes)
8. [Shared assets: present is not the same as used](#8-shared-assets-present-is-not-the-same-as-used)

---

## 1. Story stages

| Stage | Title | Level file | Where |
|---|---|---|---|
| 1 | The Arrival (tutorial) | `START` | Red Reef Valley, Open Ocean South |
| 2 | The Break Out | `AQUARIUM` | South Shore Aquarium, Open Ocean South |
| 3 | The Dead of Night | `BEACH` (`BEACHPST` = after the mission) | South Beach Cove, Open Ocean South |
| 4 | Hunted | `DOCKS` | Open Ocean West |
| 5 | Predator in the Bay | `KATATAMA` | Avril Bay, Open Ocean South |
| 6 | The Angry Armada | `ARMADA` | Bridgeport Sound, Open Ocean East |
| 7 | A Taste for Blood | `WRACK` | Misty Ridge, Open Ocean East/South edge |
| 8 | The Deep | `DEEPSEA` | ENVIRONPLUS Mining Site, Open Ocean West |
| 9 | The Facility | `DEEPSEA2` | Inside the mining site; not revisitable |
| 10 | Blood on the Beach | `TOWN` | Amity Town, Open Ocean East |
| 11 | The Final Chase | `CHASE` | Open ocean; not revisitable |

**Notes:**
- The level ↔ stage pairs come from the stage entrance loaders (`docs/speedrun_glitches.md`). CHASE's loader calls it stage 12.
- **Older notes had this wrong.** They put BEACH, DOCKS and TOWN all under *Blood on the Beach*, and stage 5 in FISH. The table above is the corrected version.
- The stage-select object `MSStageSelect` has **18 slots** for these 11 stages. The cut *Hot Pursuit* was stage 10 in a developer menu, between *Blood on the Beach* and *The Final Chase* (`docs/cut_content.md` §2).

---

## 2. Level files

| File | What it holds |
|---|---|
| `START` | Stage 1. Also hosts SC12 *Trouble and Strife*. |
| `AQUARIUM` | Stage 2 |
| `BEACH` / `BEACHPST` | Stage 3, before and after the mission |
| `DOCKS` | Stage 4 |
| `KATATAMA` | Stage 5: three oil platforms (`DrillingPlatform 1/2/3`), the shipyard power plant, the Coast Guard cutter, the Aurora |
| `ARMADA` | Stage 6 |
| `WRACK` | Stage 7. Also hosts SC19 *Get Mr. Stripes*. |
| `DEEPSEA` / `DEEPSEA2` | Stages 8 and 9. DEEPSEA chains into DEEPSEA2. |
| `TOWN` | Stage 10 |
| `CHASE` | Stage 11 |
| `FISH` | Fisherman's Isle, not a story level. SC17 *Mine All Mine*. |
| `MINEMSHA` | Grand Occasus Canals. SC15 *Up a Creek*. |
| `GAUNTLET` | The Underwater Caves. SC10 *The Bends* and SC22 *The Gauntlet*. |
| `OPEN_S` | Open Ocean South: Red Reef Valley, Seal Island, Misty Ridge, South Shore Aquarium, South Beach Cove, Old South Beach Piers, Fisherman's Isle |
| `OPEN_NE` | Open Ocean East: Bridgeport Sound, Amity Town Beach, Coast Guard HQ, South Amity Cliffs, Cable Junction, Crater Pass, Brody's House, Eastside Homes |
| `OPEN_NW` | Open Ocean West: Grand Occasus Harbor, Grand Occasus Canals, Water Ski Park, The Underwater Caves, ENVIRONPLUS Mining Site, North Amity Keys, Amity Swamp |
| `TITLE` / `TITLE0` | Menus. TITLE0 has no meshes. |

**About some of these files:**
- **`FISH` is not stage 5.** It holds pier and dock structures, beach houses and tourists, with nodes named `MineAllMine Mission Shark 1-4`. Stage 5's oil platforms and cutter are in `KATATAMA`.
- **`MINEMSHA`** is named after the real Menemsha harbour from the 1975 film; that's only the internal file name. It's a full canal level: `canal01`–`canal50`, `canal_f01`–`canal_f35`, and fog volumes. It also holds most of the cut *Hot Pursuit*'s leftovers.
- **KATATAMA was checked for cut content; none found.** It has exactly 3 platforms, as shipped. Its 35 unplaced meshes are small props and damage-state variants, which code swaps in.

**Side-challenge locations (from the guide):**

| Location | Challenge | Zone |
|---|---|---|
| Fisherman's Isle | SC17 *Mine All Mine* | South |
| Grand Occasus Canals | SC15 *Up a Creek* | West |
| The Underwater Caves | SC10 *The Bends*, SC22 *The Gauntlet* | West |
| North Amity Keys | SC23 *Manic Maze* | West, far north |

---

## 3. Side challenges

| SC | Title | Class | What you do |
|---|---|---|---|
| 01 | Barrels of Fun | `BarrelsOfFunMission` | A ship and buoys, three difficulties (`m_BuoyIDEasy/Medium/Hard`) |
| 02 | Seal Whip | `SealWhipMission` | Kill seals while the crew tries to rescue them (`m_SealList`, `m_CrewList`) |
| 03 | Bay Patrol Blood Bath | `BayPatrolBloodBathMission` | Kill the lifeguards (`m_LifeguardList`) |
| 04 | Dolphin Sightseeing Junket | `MSDolphinSightseeingMission` | Stop dolphins escaping the boat's path |
| 05 | Dog Gone | `MSDogGoneMission` | Kill the dog, a fat man and a surfer before a surface timer runs out |
| 06 | Flip the Bird | `FlipTheBirdMission` | "DESTROY THE HELICOPTER!": bite the rescue ladder and pull the helicopter into the water |
| 07 | Reality TV | `BGSideMission8` | "KILL %d BUNGEE JUMPERS WITHIN %d SECONDS!", at South Amity Cliffs |
| 08 | Row Your Boat | `BGSideMission9` | Destroy a rowboat weaving through fences, in time |
| 09 | Sheebang! | `MBSideMission10` | "Grab the swimmer and bang her into the yellow buoy within %d seconds" |
| 10 | The Bends | `TheBendsMission` | Kill the divers before any reach the surface |
| 11 | The Best Laid Plans | `MBSideMission12` | "Destroy the shark cage and kill the diver within %d seconds" |
| 12 | Trouble and Strife | `TroubleAndStrifeMission` | "KILL THE TV CREW IN %d SECONDS!", with patrol boats |
| 13 | To Kill a Killer | `MSKillKillerMission` | The narwhals: "MAKE THE NARWHALS ANGRY" |
| 14 | Undertow | `ANSideMission15` | "KILL THE WATER SKIERS WHILE THEY ARE JUMPING OFF OF THE RAMPS!" |
| 15 | Up a Creek | `UpACreekMission` | Kill a number of civilians in the canals, in time, against the current (see below) |
| 16 | Head Rush | `MBSideMission17` | Throw swimmers at people or tents, hitting %d within %d seconds |
| 17 | Mine All Mine | `MSMineAllMineMission` | "DEFEND THE WHALE CARCASS FOR %d SECONDS." |
| 18 | Return to Sender | `BGSideMission19` | Throw explosive barrels at Environplus houses; kill the fleeing executives |
| 19 | Get Mr. Stripes | `GetMrStripMission` | Chase and kill three injured fish through the minefield |
| 20 | Losing Your Head | `ANSideMission21` | "DRAG BANANA BOAT TO THE PIERS, KNOCK %d PEOPLE OFF, THEN KILL THEM WITHIN %d SECONDS." |
| 21 | Scavenge | `ANSideMission22` | "COLLECT %d TIRES IN UNDER %d SECONDS.", past a SeaSeeker and a Coast Guard raft |
| 22 | The Gauntlet | `TheGauntletMission` | Race through the caves from start box to end box, past jellyfish, viper fish and thermals |
| 23 | Manic Maze | `BGSideMission24` | Kill swimmers inside a shark-proof net maze before they escape |
| 24 | Catamaran Jam | `ANSideMission25` + `MSKatatamaMission` | "FLIP OVER %d CATAMARANS IN %d SECONDS." |
| 25 | Oh Puppy | `OhPuppyMission` | Kill white seal pups before they reach Seal Island; avoid the black adults |
| 26 | Orca Revenge | `MBSideMissionAQ` | "Kill the orca within %d seconds.": a rematch of stage 2's boss |
| 27 | Shark Frenzy | `FrenzyMission` | Kill %d sharks in 60 seconds |
| 28 | Dolphin Frenzy | `FrenzyMission` | Kill %d dolphins in 60 seconds |
| 29 | Thar She Blows | `ANSideMission33` | "BLOW UP %d BOATS IN %d SECONDS.", using explosive canisters |
| 30 | Deep Chase | *(no class found)* | "FOLLOW AND KILL THE DIVERS BEFORE THEY REACH SAFETY!", in the mining tunnels |
| 31 | Lights Out | `BGSideMission31` | "DESTROY %d GUARD TOWERS WITHIN %d SECONDS!", at Grand Occasus Harbor |
| 32 | Swim for Life | *(no class found)* | Kill a white seal pup before it escapes; may reuse `OhPuppyMission` |

**Frenzy modes:** besides the 32 challenges there are four frenzy modes: Shark, Dolphin, Seal and Diver Frenzy. All use `FrenzyMission`.

### More about SC15 *Up a Creek*

- The objective was confirmed by the user: kill a set number of civilians within a time limit.
- Its trigger node is `SM16UpACreek`. That's one higher than SC15, as in §4.
- `m_CivilContainerID` points to the civilian pool. It matches the markers `civil1WayPoint`–`civil5WayPoint` in its tree.
- Its other markers:
  - `vizbeeses` ("falling in water", 18 of them) are the civilians' start points.
  - `ground_afterescape` and `partramenekules` ("escape to shore", 11) are where a civilian escapes if not killed in time.
- Its message: "CURRENT'S TOO STRONG."
- **Its tree also holds the boat traffic**:
  - sailboats `vitorlas_a`/`_b`, a rowboat `ladik2` and a canoe;
  - each has a path, a crew slot and a controller node (`cc…`).
- **The cut *Hot Pursuit* jet ski was added to this traffic** as a fourth entry. See `docs/cut_content.md` §2.
- The goal text isn't pinned down. "KILL %d CIVILIANS.AND RETURN TO THE BUOY" and "KILL %d MORE PEOPLE" sit nearby in `Jaws.exe`, but probably belong to other missions. "KILL %d MORE PEOPLE" sits inside SC20's own field block.

---

## 4. Class numbers vs displayed numbers

**The number in a class name is usually one higher than the displayed challenge number.**

| Class | Shown as | Offset |
|---|---|---|
| `ANSideMission15` | SC14 | +1 |
| `BGSideMission8`, `BGSideMission9` | SC07, SC08 | +1 |
| `MBSideMission10`, `MBSideMission12` | SC09, SC11 | +1 |
| `FlipTheBirdMission` (debug tag "SC07") | SC06 | +1 |
| `ANSideMission33` | SC29 | **+4** |
| `BGSideMission31` | SC31 | 0 |

- The jump to +4 means classes 26–32 were removed: **at least 3 cut side challenges**. See `docs/cut_content.md` §5.
- `BGSideMission31` → SC31 doesn't fit the pattern. Unexplained.

---

## 5. Side challenges with opening cutscenes

**In short:** exactly 7 side challenges have opening cutscenes. The user wondered if they came from the 7 unused story slots. It's possible, but nothing proves it.

| SC | Challenge | Cutscene found | Level |
|---|---|---|---|
| 01 | Barrels of Fun | `SndMovieSM1`, exactly at its mission marker | Open ocean |
| 02 | Seal Whip | `MovieIndito` ("movie starter"), exactly at its marker | Open ocean |
| 03 | Bay Patrol Blood Bath | `SndMovieSM3`, 63 units from its marker | Open ocean |
| 06 | Flip the Bird | `SndMovieSM6` / `Ch7intro_StartMovie`, 56–117 units away | Open ocean |
| 07 | Reality TV | `Ch8intro_StartMovie`. Its class also has a `m_MovieID` field, the only side-mission class that does. | Open ocean |
| 12 | Trouble and Strife | `MovieSM12` | **`START`** (a story level) |
| 19 | Get Mr. Stripes | `Movie_MinefieldBoom` | **`WRACK`** (a story level) |

**How they were found:** cutscene triggers are placed `*Movie*` nodes in the levels, not fields of the mission class. `FlipTheBirdMission` has no movie field at all. So they were matched by position, to each mission's marker.

**For the theory:**
- Two of the seven live inside story levels, which normally hold story content only.
- Cutscenes are a lot of work for side content.

**Against, or at least no proof:**
- `GetMrStripMission` has one field, `m_FishList`. `TroubleAndStrifeMission` looks like an ordinary side mission. Neither has leftover story-quest fields.
- Neither uses the `Ch<N>intro` chapter naming.
- The data that would settle it, the values in `MSStageSelect`'s 18 slots, wasn't found. Every match in `TITLE.GDW` is the class definition, not a placed object. The real one is probably in TITLE's `SCRT` tree, which hasn't been parsed for this.

---

## 6. Collectibles

**In short:** the collectibles system (`CollectibleGameObject`) has 13 numbered categories. All are placed somewhere except **category 10, the Trident**, which was modelled but never placed.

The game's reward texts include "YOU'VE FOUND A TIN CAN", "YOU HAVE COLLECTED ALL LICENSE PLATES" and "YOU HAVE FOUND A %s AND YOU HAVE FOUND ALL RARE ITEMS!".

| # | Category | Placed? | Example |
|---|---|---|---|
| 01 | License Plate | Yes | `CGO_Licenseplates`, several levels |
| 02 | Human Skeleton | Yes | `CGO_Human`, BEACH/BEACHPST |
| 03 | Tin Can | Yes | `CGO_TinCan`, several levels |
| 04 | Megalodon Teeth | Yes | `CGO_Megaladon`, DEEPSEA |
| 05 | — | Number unused | No template or placement anywhere |
| 06 | Diamond Necklace | Yes | `CGO_Necklace`, WRACK |
| 07 | Treasure Chest | Yes | `CGO_Treasurechest`, several levels |
| 08 | Message in a Bottle | Yes | `CGO_Bottle`, ARMADA |
| 09 | Pirate Ship | Yes | `PirateShipCollectibles`, DOCKS (457.9, −14.3, −540.4) |
| **10** | **Trident** | **No** | Only the unused template `10 - Trident` |
| 11 | Body Bag | Yes | START (1116.1, −10.2, −315.6); TOWN `bodybag` (3184.2, −10.0, 321.2) |
| 12 | Mermaid | Yes | KATATAMA statue (249.8, 5.0, −324.8); the live mermaid in GAUNTLET |
| 13 | Nautilus | Yes | AQUARIUM (945.6, −191.1, −316.4) |

### Four naming styles

The level designers named placed collectibles in four different ways:

| Style | Where |
|---|---|
| `CGO_<Name>` | Categories 01–08, WRACK and others |
| `BSCollectibleGameObject <Name>` | AQUARIUM, KATATAMA, START |
| `<Name>Collectibles` | DOCKS: `PirateShipCollectibles`, `LicencePlateCollectibles`, `TinCanCollectibles` |
| Bare names | TOWN: `bodybag` |

- All are positioned marker nodes with no mesh of their own; the game spawns the pickup there.
- The unused templates are named `NN - Name`, e.g. `10 - Trident`.
- **The first check only searched `CGO_` names** and wrongly called categories 09–13 cut. The user had found four of them in-game, which led to the re-check.

### The Trident

- Checked against every naming style in all 20 levels: never placed.
- Its model exists: `TridentStaff` in WRACK, 208 triangles, inside the `10 - Trident` template.

### The Diamond Necklace (checked, real)

- The user remembered a 100% guide not listing it. That was a mix-up with the Trident; the guide does list it.
- Its marker is correctly wired:
  - `m_Template` (16456) points at `06 - Diamond Necklace`;
  - `m_myid` = 10 follows WRACK's licence plates (1–5) and tin cans (6–9).
  - PROP IDs `0x080004A1`–`0x080004A4`.
- **Live test:** the marker was scaled 10× in WRACK. The user saw it clearly in-game. WRACK was then restored.

### The Gauntlet's live mermaid

Category 12 has two different models.

**A static statue:**
- Template `Mermaid Include:12 - Mermaid` (GAUNTLET 13100); KATATAMA's collectible uses it.
- Plain models `Mermaid` + `hair`, 804 triangles, no skeleton.

**A swimming mermaid**, in SC22 *The Gauntlet* (`SM23TheGauntletMission`, 3358):
- Template `12 - Mermaid` (3360), with a flash effect and a bite target.
- Model **`MermaidModel 1`** (3362): mesh 1169, 926 triangles.
- Skeleton **`SKEL 946`**: 31 bones, 644 vertices.
- Clips:

  | Clip | Frames |
  |---|---|
  | `Mermaid_Pain` | 2–31 |
  | `Mermaid_Swim` | 32–61 |
  | `Mermaid_Left`, `Mermaid_Up` | one frame each |

  That's the standard set for creatures, minus an attack.
- AI: `Mermaid Action` (3361), class `MSGeneralFish`, the generic Jaws fish AI.
- So she swims around and you collect her by biting. The same on PS2. Only GAUNTLET has the skeleton.

**In Blender:**

```bash
blender -b --python scripts/import_skeleton_blender.py -- --name GAUNTLET --skel 946 --clip Mermaid_Swim
```

A saved copy: `skeletons/GAUNTLET/mermaid_skel946.blend`.

**Not the Appaloosa Mermaid demo's character**, who is blue with legs: `docs/ecco_leftovers.md` §10.

---

## 7. Other mission classes

| Class | What it is |
|---|---|
| `MBMissionBrick` | The core mission object placed in levels |
| `MBAramlat` | A mission brick variant |
| `MSMissionGenerator` | Mission spawning |
| `BGSetMissionCompleted` | Marks a mission as done in the save |
| `BGSideMission…`, `MBSideMission…`, `ANSideMission…` | Side challenges (§3) |
| `Stage…Quest` | Story stages: `Stage0Quest`, `StageBeachQuest`, `StageDocksQuest`, `StageWreckQuest` (stage 5), `StageDeepSeaQuest`, … |
| `OrcaExplorationMission` | Boats, police, divers and cages at 3 difficulties. Maybe stage 2's logic, or a cut challenge. |
| `KillthemallMission` | Not a shipped challenge: `m_SharkStart` and targeting fields. Probably cut. |
| `MSHatchMission` | Cut: *Down the Hatch* (`docs/cut_content.md` §5) |
| `StagePursuitQuest`, `StagePursuitQuest2` | Cut: *Hot Pursuit* (`docs/cut_content.md` §2) |
| `MSKatatamaMission` | One field, `m_PreyID`. A hunt target, listed with SC24. |

---

## 8. Shared assets: present is not the same as used

- **Every level file carries a common pool of assets.** Meshes, textures and props are copied into all 20 files. That's why 911 of 1,049 texture IDs appear in more than one level.
- **An asset is only used if a placed node points to it.** For meshes, that's PROP `0x08001873` on a `BRTR` node.
- So finding an asset in a file says nothing about whether it's used there, or whether it's cut.

**Example:** the "Free the Shark" protest signs are in all 20 files, but used only in AQUARIUM (stage 2), where protesters stand outside the aquarium.

# Class Registry — Jaws Unleashed Engine

> **Note (2026-07-17):** this doc dates from June 2025; `/CLAUDE.md` at the project root is the actively-maintained, current source of truth for format/mission findings. Checked this file's content against today's corrections (FDIR/SCRT/SKIP/BRTR structure, PROP alignment, mission cut-content list) — nothing here touches those topics incorrectly; the mission-class mappings below (`MSHatchMission`, `ANSideMission25`, `OrcaExplorationMission`, `KillthemallMission`, etc.) are consistent with CLAUDE.md's current cut-content and mission-mapping sections. No corrections needed this pass.

The `CLAS` chunk in every GDW file contains the engine's full reflection database, serialized as length-prefixed strings:

```
[uint32 length][class or property name string]
```

This means the engine self-documents. Class names, property names, and component definitions are all readable as plain text. No decompilation needed for high-level architecture discovery.

---

## Namespace Conventions

| Prefix | Domain |
|---|---|
| `GD` | Generic engine / rendering (GDModel, GDLight, GDFog) |
| `NA` | Gameplay / shark systems (NAPredator, NABiteTarget, NAWayPoint) |
| `MB` | Mission / boat systems (MBMissionBrick) |
| `MS` | Menu / spawn / scenario (MSMissionGenerator, MSKatatamaMission) |
| `ML` | Lighting / effects |
| `mc` | Mesh collections (mcMeshCollection) |
| `X` | Skeleton / bone (XSkeletonModel, XBone) |
| `AN` | Action nodes / AI zone volumes |
| `JT` | Gameplay interaction objects |
| `BG` | Background / persistent mission state |

---

## Rendering / Models

| Class | Purpose |
|---|---|
| `GDModel` | 3D model component; references geometry via `m_3dModelID` |
| `GDStripModel` | Triangle strip geometry model |
| `GDMovingModel` | Animated/moving model |
| `GDSkeletonModel` | Skeletal mesh model |
| `XSkeletonModel` | Extended skeleton model |
| `XExtendedSkeletonModel` | Further extended skeleton model |
| `NALODSkeleton` | LOD skeleton system |
| `MLEnvSkeletonModel` | Environment skeleton model |
| `NAPredatorModel` | Shark-specific model |
| `NAMorphModel` | Morph animation model |
| `NAVirtualModel` | Virtual / proxy model |
| `NAShadowModel` | Shadow mesh |
| `NAStencilVolume` | Stencil shadow volume |
| `mcMeshCollection` | Mesh resource container |
| `GDBrick` | Base engine object |
| `GDFixedBrick` | Static world object |
| `GDLibBrick` | Library/prefab object |

---

## Lighting / FX

| Class | Purpose |
|---|---|
| `GDLight` | Dynamic lighting |
| `GDExtendedLight` | Extended light properties |
| `GDFog` | Fog system |
| `NAParticle2004` | Particle system |
| `GDParticleTest` | Particle test component |
| `NAMotionBlur` | Motion blur |
| `GDMatAnim` | Material animation |
| `GDMorphAnim` | Morph animation |

---

## Water / Terrain

| Class | Purpose |
|---|---|
| `NAWater2004` | Primary water system (used in OPEN_ files) |
| `NAWater2003` | Earlier water version |
| `NAWaterGrid2000` | Original water grid (Ecco lineage) |
| `NASlideWater2004` | Sliding/shallow water |
| `NATextureGeneratorGrid` | Procedural water texture generation |
| `NATerrain` | Terrain system |
| `NAGrid` | Grid system |

---

## UI / Sprites

| Class | Purpose |
|---|---|
| `GDSprite` | Sprite object |
| `GDRotSprite` / `GDRotSpriteEX` | Rotating sprite |
| `GDFont` / `GDPptFont` | Font rendering |
| `GDTextSprite` / `GDPptTextSprite` | Text sprite |
| `GDShowSprite` | Display sprite |
| `GDScreen` / `GDViewport` | Screen and viewport |
| `GDTileMap` / `GDTile` | Tile-based map (minimap) |

---

## Camera / World

| Class | Purpose |
|---|---|
| `GDCamera` | Camera |
| `MBSharkCamera` | Shark-follow camera |
| `GDWorld` | World root object |
| `SharkWorld` | Shark-specific world root (layered on GDWorld) |
| `GDGraph` | Render graph |
| `GDNewMat` | Material |

---

## Gameplay / Shark Systems

| Class | Purpose |
|---|---|
| `NAPredator` | Shark/predator AI |
| `NABiteTarget` | Bite interaction component (see bite_system.md) |
| `NAChewingToy` | Physics-enabled prey/bait |
| `NAWayPoint` | AI navigation node |
| `NAMessenger` | Event/trigger messaging |
| `NATimeControl` | Time dilation / motion blur |
| `NAWhirl2000` | Whirlpool system |
| `JTMineWhirl` | Mine whirlpool interaction |

---

## Skeleton / Animation

| Class | Purpose |
|---|---|
| `XBone` | Skeleton bone |
| `XAnimation` | Animation clip |
| `XAnimationNames` | Animation name table |
| `XAnimationSet` | Animation set container |

---

## Mission / AI Areas

| Class | Purpose |
|---|---|
| `MBMissionBrick` | Mission system object |
| `MBAramlat` | Mission brick variant |
| `ANLaw` | AI law/rule zone |
| `ANBlock` | AI blocking volume |
| `ANPolyArea` | AI polygon area |
| `ANPolyArena` | AI arena zone |
| `ANUnitRef` / `ANHeliRef` / `ANSeekerRef` | AI unit references |
| `ANPosition` | AI position marker |
| `ANSideMission15` | SC14 Undertow — `KILL THE WATER SKIERS WHILE THEY ARE JUMPING OFF OF THE RAMPS!` |
| `ANSideMission21` | SC20 Losing Your Head — drag banana boat to piers, knock riders off, kill them |
| `ANSideMission22` | SC21 Scavenge — `COLLECT %d TIRES IN UNDER %d SECONDS.`; seekers + Coast Guard raft obstacles |
| `ANSideMission25` | SC24 Catamaran Jam — `FLIP OVER %d CATAMARANS IN %d SECONDS.` |
| `ANSideMission33` | SC29 Thar She Blows — `BLOW UP %d BOATS IN %d SECONDS.` using explosive canisters |
| `BarrelsOfFunMission` | SC01 Barrels of Fun — ship + buoys; `m_BuoyIDEasy/Medium/Hard` |
| `SealWhipMission` | SC02 Seal Whip — kill seals; `m_SealList`, `m_CrewList` |
| `BayPatrolBloodBathMission` | SC03 Bay Patrol Blood Bath — kill lifeguards |
| `MSDolphinSightseeingMission` | SC04 Dolphin Sightseeing Junket — stop dolphins escaping |
| `MSDogGoneMission` | SC05 Dog Gone — kill dog + NPC + surfer before surface timer |
| `FlipTheBirdMission` | SC06 Flip the Bird — destroy helicopter by biting the rescue ladder |
| `BGSideMission8` | SC07 Reality TV — kill bungee jumpers, South Amity Cliffs |
| `BGSideMission9` | SC08 Row Your Boat — destroy rowboat weaving through fences |
| `MBSideMission10` | SC09 Sheebang! — grab swimmer, smash into yellow buoy |
| `TheBendsMission` | SC10 The Bends — kill divers before any reach the surface |
| `MBSideMission12` | SC11 The Best Laid Plans — destroy shark cages + kill divers |
| `TroubleAndStrifeMission` | SC12 Trouble and Strife — kill TV crew in time; offensive boats |
| `MSKillKillerMission` | SC13 To Kill a Killer — narwhal challenge; `m_NarwhalsID` |
| `UpACreekMission` | SC15 Up a Creek — Grand Occasus Canals; fight the current |
| `MBSideMission17` | SC16 Head Rush — throw swimmers at beach tents/citizens |
| `MSMineAllMineMission` | SC17 Mine All Mine — defend whale carcass from attacking sharks; `m_WhaleID`, `m_SharksID` |
| `BGSideMission19` | SC18 Return to Sender — throw barrels at Environplus houses; kill executives |
| `GetMrStripMission` | SC19 Get Mr. Stripes — chase and kill injured fish through minefield |
| `TheGauntletMission` | SC22 The Gauntlet — race through underwater caves, start→end box; jellyfish/viperfish/thermals |
| `BGSideMission24` | SC23 Manic Maze — kill swimmers inside shark-proof net maze |
| `MSKatatamaMission` | SC24 Catamaran Jam (outer MS wrapper; `ANSideMission25` runs gameplay) |
| `OhPuppyMission` | SC25 Oh Puppy — kill white seal pups before they reach Seal Island; avoid black seals |
| `MBSideMissionAQ` | SC26 Orca Revenge — kill the orca at the Aquarium in time (rematch of M02 boss) |
| `FrenzyMission` | SC27 Shark Frenzy + SC28 Dolphin Frenzy — shared class; kill %d sharks or dolphins in 60s |
| `BGSideMission31` | SC31 Lights Out — destroy guard tower spotlights in Grand Occasus Harbor using barrels |
| `MSHatchMission` | **CUT** — "Down the Hatch"; `SWALLOW %d COLLECTABLES WITHIN %d SECONDS.`; not placed in any GDW |
| `OrcaExplorationMission` | Likely M02 aquarium story logic or cut challenge — boats, police, scuba, cages; distinct from SC26 |
| `KillthemallMission` | **CUT** — kill all targets in an area; Hungarian visual targeting fields; not in shipped SC list |

---

## Audio

| Class | Purpose |
|---|---|
| `GDSound` | Sound object |
| `GDSoundEvent2D` / `GDSoundEvent3D` | 2D/3D positional sound events |
| `GDSoundEventScope` / `GDSoundEvent3DB` | Sound event variants |
| `GDPlaySound` / `GDStopSound` | Sound control |
| `SoundManager` | Audio manager |

---

## Engine / Export / Utility

| Class | Purpose |
|---|---|
| `GDPath` / `GDGoPath` | Spline/path movement |
| `GDSpline` | Spline object |
| `GDEtalon` | Engine utility |
| `GDFolder` | Object grouping/folder |
| `GDPlayMovie` | Cutscene/movie playback (`MPGPlay` / `StreamPlay`) |
| `NACutScene` | In-engine cutscene driver |
| `GDPhysicDef` | Physics |
| `GDTestBrick` | Debug/test object |
| `PS2ExportSettings` | PS2 export config — confirms `.GDE` files are PS2 builds |

---

## Notes

- `SharkWorld` sits alongside `GDWorld` — shark-specific code was layered on top of the generic engine rather than integrated into it.
- `PS2ExportSettings` in the class registry confirms the PS2 port was planned from the start, not added late.
- `TITLE0.GDW` contains the most complete class list as it carries the full engine type database with no level content.
- The reflection system preserves property names like `m_hp`, `m_radius`, `m_damagemultiplier` directly in the binary — no decompilation needed to understand what each component does.

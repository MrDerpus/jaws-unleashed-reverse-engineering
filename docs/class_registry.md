# Class registry

**In short:** every level's `CLAS` chunk lists the names of all the engine's classes and their fields as plain text, so the engine largely documents itself. This doc is a catalogue of the notable classes, grouped by area.
- The prefix of a class name tells you its area (§1).
- **Field layouts** come from the exe: `scripts/dump_class_fields.py` lists all 6,457 registered fields of 691 class descriptors (`docs/exe_analysis.md` §4).
- **What a `PROP` ID means:** `scripts/gded_lineage.py prop LEVEL ID` (`docs/GDW_FORMAT.md`).
- Purposes below come from class and field names unless another doc confirmed them.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/class_registry_old_2026-11-27.md`.

---

## Contents

1. [Name prefixes](#1-name-prefixes)
2. [Models and scene objects](#2-models-and-scene-objects)
3. [Lighting and effects](#3-lighting-and-effects)
4. [Water and terrain](#4-water-and-terrain)
5. [UI and sprites](#5-ui-and-sprites)
6. [Camera and world](#6-camera-and-world)
7. [Shark and gameplay](#7-shark-and-gameplay)
8. [Vehicles](#8-vehicles)
9. [Skeletons and animation](#9-skeletons-and-animation)
10. [AI areas, triggers and spawners](#10-ai-areas-triggers-and-spawners)
11. [Missions](#11-missions)
12. [Audio](#12-audio)
13. [Engine utilities](#13-engine-utilities)
14. [Notes](#14-notes)

---

## 1. Name prefixes

| Prefix | Area | Examples |
|---|---|---|
| `GD` | Generic engine, rendering | `GDModel`, `GDLight`, `GDFog`, `GDControl` |
| `NA` | Gameplay and creature systems | `NABiteTarget`, `NAWayPoint` |
| `MB` | Missions, boats | `MBMissionBrick` |
| `MS` | Menus, spawning, scenarios | `MSMissionGenerator`, `MSKatatamaMission` |
| `ML` | Lighting, effects, controllers | `MLSharkCtrl`, `MLHalRaj` |
| `mc` | Mesh collections | `mcMeshCollection` |
| `X` | Skeletons, bones | `XSkeletonModel`, `XBone` |
| `AN` | Action nodes, AI areas, markers | `ANPosition`, `ANSideMission21` |
| `JT` | Interactive objects | `JTMineWhirl` |
| `BG` | Persistent mission state | `BGSetMissionCompleted` |

Note: `NAPredator` is the predator-vision screen effect, not the shark (§7).

---

## 2. Models and scene objects

| Class | Probably |
|---|---|
| `GDBrick` | Base scene object (layout: `docs/exe_analysis.md` §5) |
| `GDFixedBrick` | Static world object |
| `GDLibBrick` | Library / prefab object |
| `GDModel` | 3D model; mesh in `m_3dModelID` |
| `GDStripModel` | Triangle-strip model |
| `GDMovingModel` | Moving model |
| `GDSkeletonModel`, `XSkeletonModel`, `XExtendedSkeletonModel` | Skinned models |
| `NALODSkeleton` | Level-of-detail skeleton |
| `MLEnvSkeletonModel` | Skinned model attached to the environment |
| `NAPredatorModel` | Added with Defender PS2 (`docs/gwb_lineage.md`) |
| `NAMorphModel` | Morph (vertex) animation |
| `NAVirtualModel` | Virtual / proxy model |
| `NAShadowModel` | Shadow mesh |
| `NAStencilVolume` | Stencil shadow volume |
| `mcMeshCollection` | Mesh container |

---

## 3. Lighting and effects

| Class | Probably |
|---|---|
| `GDLight`, `GDExtendedLight` | Lights |
| `GDFog` | Fog (confirmed: `docs/rendering_system.md` §5) |
| `NAParticle2004` | Particles |
| `GDParticleTest` | Particle test |
| `NAMotionBlur` | Motion blur |
| `GDMatAnim` | Material animation |
| `GDMorphAnim` | Morph animation |

---

## 4. Water and terrain

| Class | Probably |
|---|---|
| `NAWater2004` | The shipping water (confirmed; `docs/water_system.md`) |
| `NAWater2003` | An earlier version |
| `NAWaterGrid2000` | The original, from Ecco |
| `NASlideWater2004` | Shallow, sliding water |
| `NATextureGeneratorGrid` | Generated water textures |
| `NAWaterYCamera` | Above/below-water switch (confirmed; `docs/water_system.md` §2) |
| `NATerrain`, `NAGrid` | Terrain and grids; use not checked |

---

## 5. UI and sprites

| Class | Probably |
|---|---|
| `GDSprite` | Sprite |
| `GDRotSprite`, `GDRotSpriteEX` | Rotating sprite |
| `GDFont`, `GDPptFont` | Fonts |
| `GDTextSprite`, `GDPptTextSprite` | Text |
| `GDShowSprite` | Display sprite |
| `GDScreen`, `GDViewport` | Screen and viewport |
| `GDTileMap`, `GDTile` | Tile map (the minimap) |

---

## 6. Camera and world

| Class | Probably |
|---|---|
| `GDCamera` | Camera (confirmed: far plane, `docs/rendering_system.md` §5) |
| `MLSharkCamera` | The follow camera and minimap (confirmed: `docs/exe_analysis.md` §7) |
| `MBSharkCamera` | Another shark camera class; not looked at |
| `GDWorld` | World root |
| `SharkWorld` | Jaws's world root on top of `GDWorld` (holds `m_teleportlist`) |
| `GDGraph` | Render graph |
| `GDNewMat` | Material |

---

## 7. Shark and gameplay

| Class | What |
|---|---|
| `MLSharkCtrl` + `SharkConfig` | **The player shark** (controller and tuning; `docs/exe_analysis.md` §6) |
| `NAPredator` | **The predator-vision screen effect, not the shark.** Fields `m_magnification`, `m_power`, `m_freqpower`, `m_strength`, `m_smoothrate`. |
| `NABiteTarget` | Something the shark can bite (`docs/bite_system.md`) |
| `NAChewingToy` | Physics prey / bait |
| `NAWayPoint` | AI navigation point |
| `NAMessenger` | Event messaging |
| `NATimeControl` | Slow motion, motion blur |
| `NAWhirl2000` | Currents (confirmed: push barriers, `docs/exe_analysis.md` §14) |
| `JTMineWhirl` | Mine-site current |
| `GDControl` | Level scripting (confirmed: `docs/exe_analysis.md` §8) |

---

## 8. Vehicles

**`TKSub`:** a small attack submarine.
- Movement: `m_faster`, `m_slower`, `m_maxyturn`, `m_turnaccel`, `m_crab` (sideways).
- Hover bob: `m_libegamp`.
- Damage thresholds per weapon: `m_MaxScooter`, `m_MaxDiver`, `m_MaxTorpedo`.
- Torpedo points: `m_ShotPosID`, `m_ShotPos2ID`.
- A pilot diver: `m_DiverID`, `m_DiverPosID`.
- A destructible rudder, and a propeller that blows off on death.

**`MSScooter`:** a vehicle-mount handler with single IDs:
- `m_ScooterID` (the sea scooter);
- `m_SubID` (a `TKSub`);
- `m_RomboloID` (*romboló* = destroyer ship);
- `m_TesztID` (*teszt* = test). A "test" ID next to the others suggests a development test harness.

---

## 9. Skeletons and animation

| Class | Probably |
|---|---|
| `XBone` | A bone |
| `XAnimation` | A clip |
| `XAnimationNames` | Clip name table |
| `XAnimationSet` | A set of clips |

The data format is in `docs/animation_system.md`.

---

## 10. AI areas, triggers and spawners

| Class | What |
|---|---|
| `ANLaw` | AI rule zone |
| `ANBlock` | AI blocking volume |
| `ANPolyArea`, `ANPolyArena` | AI polygon area / arena |
| `ANUnitRef`, `ANHeliRef` | AI unit references |
| `ANSeekerRef` | A SeaSeeker placement (class `0x0109C09B`, 74 fields). PROP = `0x080002E9` + field index. 0 = use the template's value; booleans: 0 inherit, 1 off, 2 on. Example: `docs/cut_content.md` §9 (the BEACH "submarine"). |
| `ANPosition` | Boat marker (98 fields; `docs/exe_analysis.md` §10) |
| `ANTol` | Buoy push (`docs/exe_analysis.md` §14) |
| Area trigger (class `0x01134132`, `ANSphereCheck`) | Entrance/exit zone: runs `m_enter_act`/`m_leave_act` when `m_target` (the shark) crosses a circle of `m_radius` (fields `0x0800028D`–`0x08000296`). FISH's exit, the open-ocean entrances, DEEPSEA's room checks. `docs/brtr_editing.md` §11 "Area triggers and level exits". |
| `OssLoadChecker` (action `0x0217B17A`) | Shows the enter/leave prompt (message 598) and starts `m_toact` on OK |
| `GDLoad` (action `0x02038036`/`0x02038037`) | Loads a stage; name in `PROP 0x08001839` |
| Creature generator (action `0x02129128`) | `MarlinGenAct`, `MantarayGen`, …: spawns wildlife from a template (`PROP 0x08000A78`), count `0x08000A79`, area `0x08000A82` |

---

## 11. Missions

**All side-challenge classes** (SC01–SC32, with titles and goals): `docs/mission_system.md` §3.

**Other mission classes** (`MBMissionBrick`, `MBAramlat`, `Stage…Quest`, `OrcaExplorationMission`, `KillthemallMission`, `MSHatchMission`, `MSKatatamaMission`): `docs/mission_system.md` §7.

**Class numbers vs displayed numbers** (e.g. `ANSideMission21` = SC20): `docs/mission_system.md` §4.

**Cut ones:** `MSHatchMission` (*Down the Hatch*), `StagePursuitQuest`/`2` (*Hot Pursuit*): `docs/cut_content.md`.

---

## 12. Audio

| Class | Probably |
|---|---|
| `GDSound` | Sound object |
| `GDSoundEvent2D`, `GDSoundEvent3D` | 2D/3D sound events |
| `GDSoundEventScope`, `GDSoundEvent3DB` | Sound event variants (`m_AW_Resource`/`m_UW_Resource` = above/underwater) |
| `GDPlaySound`, `GDStopSound` | Sound control |
| `SoundManager` | Audio manager |

How sounds are requested: `docs/audio_format.md`.

---

## 13. Engine utilities

| Class | Probably |
|---|---|
| `GDPath`, `GDGoPath` | Paths and path movement (boat routes are `GDPath`) |
| `GDSpline` | Spline |
| `GDEtalon` | Engine utility |
| `GDFolder` | Grouping |
| `GDPlayMovie` | Movie playback (`MPGPlay` / `StreamPlay`; `docs/exe_analysis.md` §13) |
| `NACutScene` | In-engine cutscene driver |
| `GDPhysicDef` | Physics |
| `GDTestBrick` | Debug / test object |
| `PS2ExportSettings` | PS2 export settings |

---

## 14. Notes

- **`SharkWorld` sits on top of `GDWorld`:** Jaws-specific code was layered over the generic engine.
- **`PS2ExportSettings`** is in the PC files. The engine exported to PS2 throughout; Defender already shipped on PS2 (`docs/gwb_lineage.md`).
- **`TITLE0` has a different field table** from the other 19 levels (from entry 979 on), so fixed `PROP` IDs don't work there (`docs/GDW_FORMAT.md`).
- **PC vs PS2:** PC has 311 classes, PS2 302. The 9 extra are PC settings menus; PS2 has no class the PC lacks (`docs/ps2_cut_content_findings.md` §6).
- Field names like `m_hp`, `m_radius`, `m_damagemultiplier` are readable straight from the files.

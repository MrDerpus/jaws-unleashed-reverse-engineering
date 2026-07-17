> **HISTORICAL DOCUMENT** — Earliest raw notes from initial GDW investigation. Heavily superseded. Key wrong claims: PS2 VIF/GIF as geometry barrier (wrong — PC DX8 GMDL is decoded), audio not extracted (wrong — ~4,000 WAV files extracted), BRTR unsolved (wrong — fully decoded, including nested parent-child transform composition, resolved 2026-07-16). Keep for research timeline context only. **`CLAUDE.md` is now the actively-maintained, current source of truth for this project** — check it first; `GDW_FORMAT.md` is a secondary reference.

# Jaws Unleashed Reverse Engineering Notes

## File Format
Primary world/container format:
- .GDW

Observed characteristics:
- Chunk-based
- Serialized object registry
- Reflection/property system
- Embedded DDS textures
- Skeletal animation support
- Runtime/editor metadata preserved



# Serialization Layer Theory [LIKELY]

Current suspected structure:

[Class Registry]
    ↓
[Property Reflection]
    ↓
[Component Schemas]
    ↓
[Object Archetypes]
    ↓
[Scene Instances]
    ↓
[Binary Assets]

Current investigation appears focused around:
- Component schemas
- Archetype/property metadata



# Major Discoveries

## Reflection System
Found serialized class/property reflection metadata.

Examples:
- NABiteTarget
- XSkeletonModel
- mcMeshCollection

Indicates:
- editor-driven engine
- runtime property introspection
- serialized gameplay objects

# Class Registry

Observed namespaces:

GD = Generic engine/rendering
NA = Gameplay/shark systems
MB = Mission/boat systems
MS = Menu/spawn/scenario systems
ML = Lighting/effects

Examples:
- GDModel
- GDSkeletonModel
- NAPredator
- NABiteTarget
- MBMissionBrick

# Property Reflection

## NABiteTarget

Observed properties:
- m_hp
- m_damagemultiplier
- m_nutrition
- m_radius
- m_eattype
- m_creature
- m_dragfactor
- m_shakefactor
- m_bitetargetmodel
- m_bitetargetmaterialindex
- m_dependentlimbs
- m_rubberskeletonid

Implications:
- Dismemberment system exists
- Material swapping exists
- Skeletal replacement system exists
- Shark bite interaction system is component-based

# Embedded Textures

DDS headers found at offsets:
- 5062817
- 11158738
- 14262787
...

Textures appear embedded directly inside GDW files.

# Important Offsets

## Registry Region
0x06F7B4A0
Contains:
- CLAS
- class registry metadata

## Skeleton System
0x06F7B7C0
Contains:
- GDModel
- GDSkeletonModel
- XSkeletonModel
- XBone

# Current Engine Theory

Likely structure:

[Header]
[Class Registry]
[Property Reflection]
[Serialized Objects]
[Meshes]
[Textures]
[Animations]

Likely editor-driven architecture.

# Useful Commands

## Search DDS headers
grep -oba "DDS" FISH.GDW

## Search class references
grep -oba "NABiteTarget" FISH.GDW

## Hex inspection
xxd -s OFFSET -l LENGTH FISH.GDW

# Open Questions

- Where are actual mesh buffers stored?
- Are DDS textures compressed independently?
- Are models inline or externally referenced?
- How are object transforms serialized?
- Are mission scripts bytecode or property-driven?

-------------


# Component Architecture [LIKELY]

The engine appears heavily component-driven.

Observed serialization pattern:

[property]
[class]
[property]
[class]

Examples:
- m_velocity -> NAChewingToy
- m_attackgroups -> NAChewingToy
- m_links -> NAWayPoint

Implications:
- Object composition system
- Editor-driven gameplay architecture
- Data-driven gameplay behaviors


# Gameplay Messaging System [CONFIRMED]

Observed properties:
- m_onactivatemessagetargets
- m_ondeactivatemessagetargets
- m_onactivatemessagetype

Associated class:
- NAMessenger

Implications:
- Event-driven gameplay scripting
- Trigger activation system
- Object messaging/event propagation


# Waypoint / AI Navigation System [CONFIRMED]

Class:
- NAWayPoint

Observed properties:
- m_links
- m_waypointgroups
- m_autolink
- m_autolinkrange
- m_dependencytype

Implications:
- Graph-based AI navigation
- Automatic path linking
- Possibly fish schooling/shark patrol systems


# NAChewingToy System [LIKELY]

Observed properties:
- m_velocity
- m_angularvelocity
- m_gravity
- m_attackgroups
- m_sensorgroups
- m_target

Implications:
- Physics-enabled prey/bait system
- Generic interactive object type
- Supports movement and targeting


# Group-Based Interaction System [LIKELY]

Observed properties:
- m_attackgroups
- m_sensorgroups
- m_backgroundgroups

Implications:
- Collision masks
- AI targeting channels
- Gameplay interaction filtering


# Time Control System [CONFIRMED]

Class:
- NATimeControl

Observed properties:
- m_timespeed
- m_motionblurport
- m_motionalpha

Implications:
- Time dilation effects
- Motion blur control
- Possibly cinematic/gameplay slow-motion systems


# Important Observation [CONFIRMED]

Current regions still primarily contain:
- class names
- property names
- component definitions

NOT yet:
- transform matrices
- scene object coordinates
- instantiated runtime payloads

Meaning:
actual scene/world object serialization may exist later in the file.


# Anatomy / Dismemberment Framework [CONFIRMED]

Observed body-part properties:
- m_head
- m_body
- m_leftarm
- m_rightarm
- m_leftleg
- m_rightleg
- m_lefthand
- m_righthand
- m_leftfoot
- m_rightfoot

Observed related systems:
- m_dependentlimbs
- m_rubberskeleton
- m_dismembermaterialindex

Implications:
- Componentized anatomy system
- Limb-specific interactions
- Dismemberment framework
- Bone attachment hierarchy


# Chunk Format Theory [LIKELY]

Observed structure:

[FOURCC][uint32 size][payload]

Examples:
- CLAS
- WDIM
- GNRL
- RSPR
- VERS

Chunks may contain nested subchunks.


# WDIM Chunk [LIKELY]

Observed chunk:
WDIM

Chunk size:
0x28 bytes

Observed float-like values:
~5000.0
~2000.0
~5000.0

Possible meaning:
- World dimensions
- Streaming bounds
- Level extents


# Embedded GDED Containers [CONFIRMED]

Multiple full GDED headers observed inside a single GDW file.

Possible implications:
- Nested serialization containers
- Streaming regions
- Mission packages
- Independent subdocuments

**RESOLVED (2026-07-15/17):** each GDW carries a second, complete, independently-embedded GDED archive concatenated after the primary archive's `ENDF` (own preamble, own VERS/CLAS/RSRC/BRTR chain). Confirmed (via `OPEN_S.GDW`, 11 such embedded archives) to be **bundled loading-screen scenes** for level transitions — not nested serialization, not mission packages, not streaming regions. The primary archive's `FDIR` chunk stores a real `[offset][size][name]` index entry pointing at each one. See CLAUDE.md's GDW Archive Format section (FDIR note) for the exact mechanics, and `project_infinite_ocean`/`project_custom_map_feasibility` in memory for the investigation history.


# Suspected Geometry Pipeline [LIKELY]

Observed chunk types:
- GMDL
- VERT
- NORM
- UVUV
- STRI
- SKEL
- BONE
- WGHT
- GMAT
- GTEX

Implications:
- Full mesh serialization pipeline exists
- Skeletal meshes supported
- Triangle strip rendering used
- Material/texture systems chunk-based


# Transform-Related Chunks [CONFIRMED]

Observed chunks:
- POSI
- ROTS
- TRAN

Implications:
- Position serialization
- Rotation serialization
- Transform systems exist as binary chunks


# Confirmed Structural Relationships

Observed repeated patterns:

- GMDL -> VERT
- STRI -> GMDL
- SKEL -> GMDL

Implications:
- GMDL likely acts as mesh container
- VERT likely stores vertex buffers
- STRI likely stores triangle strips / indices
- SKEL likely binds to skinned mesh data


# Confirmed Geometry Structure

Observed chunk hierarchy:

GMDL
 ├── MATR
 ├── MATS
 ├── GMAT
 ├── TSET
 ├── TANG
 ├── VIND
 ├── VERT
 │    ├── POSI
 │    ├── NORM
 │    └── UVUV

Confirmed:
- POSI contains float32 vertex positions
- UVUV contains UV coordinates
- VIND likely contains uint16 index buffers
- chunk format appears:
    [4-byte ID][uint32 size][data]
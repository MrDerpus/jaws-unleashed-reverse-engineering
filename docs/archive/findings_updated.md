> **HISTORICAL DOCUMENT** — Early research notes, duplicate of `_findings.md` with a ChatGPT session link. Content is heavily superseded — notably its closing conclusion that mesh extraction "likely requires PS2 render pipeline decoding / VIF/GIF packet analysis" is **wrong**: the PC build uses DirectX 8, not the PS2 VIF/GIF pipeline, and GMDL/VERT/POSI/VIND geometry is fully decoded and extracting cleanly (11,948 meshes, `scripts/rip_meshes.py`) with no PS2-specific decoding involved. **`CLAUDE.md` is now the actively-maintained, current source of truth for this project** — check it first; `GDW_FORMAT.md`, `serialization_format.md`, and `class_registry.md` are secondary references.

# Jaws Unleashed Reverse Engineering Notes
https://chatgpt.com/share/6a0c4599-632c-83ec-87be-d4c90c9570f1

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

**RESOLVED (2026-07-15/17):** each GDW carries a second, complete, independently-embedded GDED archive concatenated after the primary archive's `ENDF` (own preamble, own VERS/CLAS/RSRC/BRTR chain). Confirmed (via `OPEN_S.GDW`, 11 such embedded archives) to be **bundled loading-screen scenes** for level transitions — not nested serialization, not mission packages, not streaming regions. The primary archive's `FDIR` chunk stores a real `[offset][size][name]` index entry pointing at each one. See CLAUDE.md's GDW Archive Format section (FDIR note) for the exact mechanics.


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

# Texture Extraction Breakthrough [CONFIRMED]

## First Successful GTEXT Texture Extraction

Successfully identified and extracted a valid texture resource from `FISH.GDW`.

Confirmed internal structure:

```text
GTEXT
    ↓
TGAN0
    ↓
raw texture payload
```

Observed example:

```text
0003d44c: GTEXT
0003d46c: TGAN0
```

The texture payload was successfully extracted and reconstructed into a viewable image.

This represents the first confirmed successful asset extraction from the game.


# GTEXT Texture Structure [CONFIRMED]

Observed metadata fields:

| Offset | Suspected Meaning | Value |
|---|---|---|
| `0x18` | width | `128` |
| `0x1C` | height | `128` |
| `0x20` | bits-per-pixel | `32` |

Strongly suggests:

```text
128x128 RGBA32 textures
```

Observed payload size:

```text
65536 bytes
```

This exactly matches:

128 × 128 × 4 = 65536

Implications:
- Texture extraction offset is mostly correct
- Texture payload boundaries are valid
- Raw image data is recoverable


# TGAN0 Payload Block [LIKELY]

Observed structure:

```text
GTEXT
    metadata
    ↓
TGAN0
    payload
```

The payload appears self-contained and sequentially packed.

Observed repeating GTEXT spacing:

```text
4188 bytes
```

Implications:
- Structured resource packing
- Consistent texture serialization
- Batch extraction should be possible


# TRUEVISION-XFILE Discovery [CONFIRMED]

Observed string:

```text
TRUEVISION-XFILE
```

Implications:
- TGA lineage confirmed
- Custom TGA-inspired texture system
- Possible internal runtime TGA reconstruction

Current theory:
- Engine stores wrapped/custom texture payloads
- Not literal standalone `.tga` files
- GTEXT acts as a texture resource wrapper


# Particle Texture Discovery [LIKELY]

First successfully extracted texture appears to be:
- particle effect texture
- sparkle/glow mask
- collectible particle effect
- foam/bubble/splash mask
- grayscale luminance mask

Observed behavior:
- texture appears intentionally monochromatic
- runtime tinting likely applied dynamically

This matches observed gameplay behavior where:
- particle effects change colour dynamically
- multiple systems reuse the same mask textures

Possible runtime tint usage:
- blood = red
- foam = white
- collectible glow = yellow
- toxic effects = green

This behavior was common in:
- PS2-era engines
- memory-constrained rendering systems


# RSRC Internal Structure [UPDATED THEORY]

Initial recursive chunk parsing inside RSRC failed.

Current understanding:

Outer GDW structure uses:

```text
[FOURCC][uint32 size][payload]
```

Examples:
- CLAS
- RSRC
- BRTR
- SCRT

However:

RSRC internally appears to use:
- typed binary resource records
- resource payload streams
- non-standard nested structures

Instead of recursively nested FOURCC chunk trees.


# Updated Engine Architecture Theory [LIKELY]

Current strongest theory:

```text
CLAS = reflection/type system
RSRC = packed resource payloads
BRTR = resource tree/index system
SCRT = scripts/runtime logic
```

Additional current theories:
- GTEXT contains texture payload resources
- BRTR may map resource IDs to names
- Resource names may not exist locally beside texture payloads
- Resource IDs may be referenced through BRTR indexing structures


# Confirmed Reverse Engineering Milestones

Successfully achieved:
- top-level GDW chunk parsing
- 4-byte alignment reconstruction
- RSRC discovery
- GTEXT discovery
- TGAN0 discovery
- first successful texture extraction
- first successful rendered game asset recovery

This confirms:
- GDW files are structured asset containers
- textures are recoverable
- payload extraction is viable
- reverse engineering progress is reproducible


# Current Next Goals

Planned next steps:
- batch GTEXT extraction
- texture catalog generation
- BRTR analysis
- resource ID correlation
- model resource discovery
- mesh extraction experiments
- possible Blender reconstruction pipeline




# Runtime Object Reconstruction [CONFIRMED]

Successfully reconstructed serialized gameplay object hierarchies from PROP-based object regions.

Observed structure:

```text
PROP
    ↓
object properties
    ↓
transform data
    ↓
bounds data
    ↓
hierarchy links
```

Successfully reconstructed:
- object names
- transform matrices
- local-space positions
- bounding volumes
- hierarchy grouping

Examples:
- Hammerhead SkeletonModel
- Hammerhead Head Fixed Brick
- Hammerhead Body Fixed Brick
- Hammerhead Tail Fixed Brick
- Hammerhead BiteTarget

Implications:
- Runtime gameplay entities serialized directly inside GDW
- Hierarchical attachment system exists
- Componentized collision/body-part system exists
- Scene graph reconstruction is possible


# Transform Matrix Discovery [CONFIRMED]

Observed transform blocks contain float32 matrix-like structures.

Observed values:

```text
0.9947
-0.0029
-0.1027
```

Strongly suggests:
- local-space rotation matrices
- transform basis vectors
- attached object transforms

Observed object positions:
- head regions positioned forward
- tail regions positioned rearward

This spatially matches expected shark anatomy.


# Bounds Reconstruction [CONFIRMED]

Observed bounds data:

```text
[-1.8, -1.8, -3.06]
[ 1.8,  1.8,  2.42]
```

Implications:
- Axis-aligned bounding boxes serialized directly
- Collision extents recoverable
- Spatial visualization possible


# Hierarchy Reconstruction [CONFIRMED]

Successfully grouped runtime objects using:
- ChildLink IDs
- shared hierarchy grouping

Generated reconstructed hierarchy examples:

```text
Hammerhead SkeletonModel
├── Head Fixed Brick
├── Body Fixed Brick
├── Tail Fixed Brick
```

Implications:
- Runtime scene graph serialization exists
- Parent-child attachment system exists
- Gameplay hit regions attached to skeleton hierarchy


# Runtime Visualization Breakthrough [CONFIRMED]

Successfully visualized reconstructed gameplay object layouts in 3D.

Visualization included:
- attachment points
- collision regions
- bounds boxes
- hierarchy placement

Observed layouts correctly matched:
- shark anatomy
- expected spatial organization
- gameplay collision regions

This confirms:
- transform decoding is mostly correct
- bounds decoding is mostly correct
- local-space hierarchy reconstruction is valid


# PRIM Reinterpretation [UPDATED THEORY]

Initial theory:
- PRIM contained raw geometry buffers

Updated understanding:

PRIM appears to represent:
- render nodes
- render primitive descriptors
- render hierarchy objects

Observed structure:

```text
PRIM
    ↓
PRPS
    ↓
PROP
    ↓
CHBR
```

Implications:
- PRIM participates in scene hierarchy
- PRIM likely references geometry indirectly
- PRIM appears to represent render graph structures


# Geometry Extraction Investigation [UPDATED]

Initial geometry extraction attempts targeted:
- repeating 0x800-byte packet regions
- structured binary blocks
- low-ASCII regions

Initial results:
- candidate point clouds exported to Blender
- only sparse/noisy point clouds produced

Further investigation strongly suggested:
- incorrect float32 interpretation
- likely palette/texture packet regions
- possible PS2 GPU upload structures


# Palette / CLUT Discovery [LIKELY]

Observed repeating colour ramp patterns:

```text
69 69 69
64 64 64
5f 5f 5f
```

Observed RGBA-like patterns:

```text
ff 00 ff ff
```

Implications:
- indexed texture palettes likely exist
- CLUT-style texture system likely used
- texture packets may have been mistaken for geometry packets

This also explains:
- previously incorrect texture colours
- blue/pink texture extraction artifacts
- improved results after channel correction


# Texture Extraction Improvements [CONFIRMED]

Texture extraction significantly improved after:
- BGR/RGB channel correction
- vertical flipping
- palette interpretation improvements

Successfully recovered:
- fish sprites
- whale texture atlases
- level-local assets
- environmental textures

Confirmed:
- GDW files contain level-specific asset collections
- large amount of texture reuse exists between levels


# Current Geometry Theory [UPDATED]

Current strongest theory:

```text
GDModel
    ↓
m_3dModelID
    ↓
mcMeshCollection
    ↓
actual geometry payload
```

Implications:
- GDModel likely acts as runtime render component
- actual geometry likely stored separately
- resource ID indirection system likely exists


# Important Failed Assumptions

## False Geometry Region

Offset:
```text
0x6FB887C
```

Initially believed to contain:
- geometry packets
- vertex buffers

Later evidence strongly suggested:
- palette data
- indexed texture upload packets
- GPU texture transfer structures

This region should NOT currently be treated as confirmed geometry.


# Current Reverse Engineering Status

Successfully identified:
- serialization architecture
- reflection system
- runtime object hierarchy
- gameplay component system
- transform serialization
- bounds serialization
- render graph structures
- texture resource system
- palette/CLUT structures

Partially identified:
- geometry resource pipeline
- render packet systems
- mesh resource references

Not yet solved:
- actual mesh vertex decoding
- triangle strip reconstruction
- Blender-ready geometry extraction
- skeletal animation extraction
- VIF/GIF packet decoding


# Current Best Geometry Leads

Most promising identifiers:
- mcMeshCollection
- m_3dModelID
- GMDL
- VERT
- STRI
- VIND

Most likely remaining challenge:
- PS2-specific packed geometry encoding
- DMA/VIF/VU packet decoding
- fixed-point vertex compression


# Overall Conclusion

Current reverse engineering strongly suggests:
- Jaws Unleashed uses a sophisticated component-driven engine
- Runtime gameplay objects serialize directly inside GDW files
- Reflection metadata is preserved
- Hierarchical gameplay entities are reconstructable
- Texture extraction is viable
- Runtime spatial layouts are recoverable
- Render graph structures are partially understood

Actual mesh extraction likely requires:
- PS2 render pipeline decoding
- VIF/GIF packet analysis
- packed geometry stream reconstruction

**RESOLVED — this was wrong.** The PC `.GDW` geometry pipeline needed none of the above: it's a straightforward DirectX-8-era `GMDL`→`VERT`/`TANG` container hierarchy (`POSI`/`NORM`/`UVUV` float32 vertex data, `VIND` uint16 triangle-list indices), fully decoded and extracting cleanly — 11,948 meshes across all 20 GDWs via `scripts/rip_meshes.py`. No PS2 VIF/GIF decoding was ever needed for the PC build; that pipeline only applies to the separate PS2 `.GDE` files (see CLAUDE.md's "PS2 Version Data" section), which use a genuinely different, quantized, triangle-strip-based `GMDL`/`STRP` format — also now decoded (`scripts/rip_meshes_ps2.py`).
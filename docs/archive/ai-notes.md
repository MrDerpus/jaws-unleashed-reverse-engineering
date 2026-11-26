> **HISTORICAL DOCUMENT** — Early research notes from initial GDW investigation (ChatGPT session). Many claims here are superseded or corrected. **`CLAUDE.md` is now the actively-maintained, current source of truth for this project** — check it first. `GDW_FORMAT.md`, `serialization_format.md`, and `class_registry.md` are secondary references. Key corrections since this doc was written: audio IS fully extracted (GSMP/SMPB, ~2,873 PC PCM files + 1,128 SMPB voice-line files — **not** PS2 VAG/ADPCM as theorized below, that was the wrong lead for the PC `.GDW` files); mesh extraction IS working (11,948 OBJs across all 20 GDWs); BRTR IS decoded (full scene graph, including nested parent-child transform composition, resolved 2026-07-16); the game uses DX8 not DX9/PS2; `SCRT` (listed below as "scripting system, SUSPECTED") is RESOLVED (2026-07-08) — not scripting at all, a plain named screen-overlay object tree, same PRPS/CHBR/PROP format as BRTR; `SKIP` and PS2-only `BNCH` are also fully decoded now (sector-alignment padding, and a name-dictionary + transform-record chunk, respectively).

# JAWS / GDW Reverse Engineering Findings
(link to full conversation history with Chat-GPT)[https://chatgpt.com/share/6a0c4599-632c-83ec-87be-d4c90c9570f1]

# Overview

This document contains discoveries, commands, outputs, interpretations, and theories related to reverse engineering the `.GDW` archive format used by the game.

The project initially began as texture extraction research and has evolved into broader engine architecture reconstruction.

Current confirmed systems:
- Archive chunk structure
- Texture system
- Audio system
- Reflection/class metadata system
- Object serialization structures
- Engine subsystem discovery

---

# Useful Commands

This section documents commands that have proven useful during reverse engineering.

---

# 1. Locate String Signatures

## Command

```bash
grep -oba "GTEXT" FISH.GDW
```

## Purpose

Searches the archive for occurrences of the `GTEXT` marker.

> **Correction (2026-10-03):** "GTEXT" is not a real tag: it's the `GTEX` tag followed by a size field whose low byte is `0x54` (`'T'`). The grep works because most 24-bit texture sizes end in `0x54`, but it also misses some textures and hits false matches. Walk the `RSRC` chunk chain instead (see `CLAUDE.md` texture section).

## Result

Multiple valid texture blocks were discovered.

Example:

```text
250960:GTEXT
316588:GTEXT
562508:GTEXT
```

## Importance

This was the first major breakthrough in identifying texture structures inside the archive.

## Confidence

CONFIRMED

---

# 2. Hex Dump Around Offset

## Command

```bash
xxd -s 0x3DE00 -l 128 TITLE0.GDW
```

## Purpose

Displays hexadecimal data around a specific archive offset.

## Result

Confirmed:
- FDIR chunk
- ENDF chunk
- archive footer structure

Example:

```text
0003de00: 4644 4952
0003de30: 454e 4446
```

## Importance

Confirmed chunk boundaries and archive termination structure.

## Confidence

CONFIRMED

---

# 3. Dump Around Texture Block

## Command

```bash
xxd -s <offset> -l 256 FISH.GDW
```

## Purpose

Inspect binary structure around GTEXT blocks.

## Findings

Confirmed:
- stable texture header structure
- payload alignment
- deterministic offsets

## Importance

Allowed construction of the deterministic texture parser.

## Confidence

CONFIRMED

---

# 4. Search For Audio Signatures

## Commands

```bash
grep -oba "VAG" FISH.GDW
grep -oba "VAGu" FISH.GDW
grep -oba "SoundManager" FISH.GDW
```

## Purpose

Searches for PS2 audio markers and sound system structures.

## Findings

Discovered:
- VAG audio references
- SoundManager system
- sound event structures

Example:

```text
GDSoundEvent3D
GDPlaySound
GDStopSound
SoundManager
```

## Importance

Confirmed existence of:
- audio engine
- sound event system
- likely PS2 ADPCM audio

## Confidence

HIGH

---

# 5. Extract Human Readable Strings

## Command

```bash
strings -td FISH.GDW | grep -i sound
```

## Purpose

Extract readable strings and offsets related to sound systems.

## Findings

Discovered:
- gameplay sound references
- sound event classes
- serialized engine field names

Examples:

```text
m_soundevent
m_sounddelay
m_SoundBankList
```

## Importance

Confirmed:
- object-oriented sound system
- serialized engine metadata
- sound bank architecture

## Confidence

HIGH

---

# 6. Reflection Metadata Discovery

## Command

```bash
xxd -s 0x06FB5000 -l 4096 FISH.GDW
```

## Purpose

Inspect large metadata region discovered near CLAS-related structures.

## Findings

Discovered:
- engine class names
- member field names
- serialized reflection metadata

Examples:

```text
GDLight
GDFog
GDModel
GDPhysicDef
GDPath
```

## Importance

This was a MASSIVE breakthrough.

Confirmed:
- reflection system
- object metadata serialization
- engine architecture exposure

## Confidence

VERY HIGH

---

# Confirmed Archive Chunk Types

| Chunk | Description | Confidence |
|---|---|---|
| FSIZ | file size metadata | CONFIRMED |
| VERS | version information | CONFIRMED |
| EXBY | unknown archive metadata | UNKNOWN |
| GNRL | general archive data | LIKELY |
| WDIM | world/dimension metadata | SUSPECTED |
| RSPR | unknown subsystem | UNKNOWN |
| CLAS | class/reflection database | VERY HIGH |
| RSRC | resource system | HIGH |
| BRTR | resource tree | HIGH |
| SCRT | scripting system | SUSPECTED |
| FDIR | file directory/footer | HIGH |
| ENDF | archive terminator | CONFIRMED |

---

# Texture System

# Confirmed Texture Structure

| Offset | Meaning |
|---|---|
| +0x00 | GTEXT |
| +0x04 | block size |
| +0x18 | width |
| +0x1C | height |
| +0x20 | bits per pixel |
| +0x24 | TGAN |
| +0x54 | payload start |

---

# Confirmed Texture Formats

| Format | Status |
|---|---|
| RGB24 | CONFIRMED |
| RGBA32 | CONFIRMED |

---

# Texture Payload Math

## Formula

```text
payload_size = block_size - 0x54
```

## Importance

This discovery enabled:
- deterministic extraction
- reliable parsing
- clean texture exports

---

# Texture Findings

Confirmed:
- raw uncompressed textures
- texture atlases
- UI textures
- particle textures
- animated material support

Possible:
- palette textures
- swizzled textures
- lookup textures

---

# Audio System

# Confirmed Audio Structures

Discovered:
- GDSoundEvent2D
- GDSoundEvent3D
- GDPlaySound
- GDStopSound
- SoundManager
- m_SoundBankList

---

# Audio Findings

Strong evidence suggests:
- PS2 VAG/ADPCM audio
- sound bank system
- event-driven audio engine

---

# Reflection / Serialization System

# Major Discovery

The engine appears to use:
- reflection metadata
- serialized class systems
- object field serialization

Pattern discovered:

```text
[length][classname]
[length][fieldname]
```

---

# Confirmed Engine Classes

| Class | Purpose |
|---|---|
| GDLight | lighting |
| GDFog | fog system |
| GDModel | 3D models |
| GDPhysicDef | physics |
| GDPath | spline/path system |
| GDGoPath | path movement |
| GDParticleTest | particles |
| GDPlayMovie | movie/cutscene playback |
| GDMorphAnim | morph animation |
| GDMatAnim | material animation |
| GDCamera | camera system |

---

# Confirmed Engine Features

The engine appears to support:

- dynamic lighting
- fog systems
- animated materials
- morph animation
- matrix animation
- path systems
- particle systems
- movie playback
- physics systems
- recolouring systems
- LOD systems
- sound event systems

---

# Major Project Milestones

| Milestone | Status |
|---|---|
| chunk parsing | COMPLETE |
| texture extraction | WORKING |
| deterministic parser | COMPLETE |
| audio system discovery | CONFIRMED |
| reflection metadata discovery | CONFIRMED |
| engine class discovery | CONFIRMED |
| object serialization theory | VERY LIKELY |
| scene reconstruction potential | POSSIBLE |

---

# Active Theories

| Theory | Confidence |
|---|---|
| CLAS = reflection database | VERY HIGH |
| VAGu = audio subtype marker | MEDIUM |
| object instances exist near metadata | HIGH |
| serialized transforms/vectors exist | HIGH |
| mesh payloads exist in archive | VERY HIGH |
| SCRT = scripting system | MEDIUM |

---

# Future Work

Planned areas of research:
- object instance parsing
- vector/transform extraction
- mesh extraction
- sound bank reconstruction
- PS2 audio decoding
- scene graph reconstruction
- Blender export pipeline
- archive rebuilding
- texture replacement/modding
- path/spline extraction


# Tooling & Parser Evolution

This section documents scripts created during reverse engineering of the GDW archive format.

The evolution of these scripts reflects major discoveries in archive structure understanding.

---

# Initial Texture Extraction Script

## Purpose

The first texture extractor attempted to:
- locate GTEXT blocks
- identify image payloads
- export raw texture data

## Method

Initial extraction relied on:
- heuristic offset searching
- guessed payload boundaries
- guessed image sizes

## Result

Partial success:
- some textures extracted correctly
- many textures corrupted
- colours often incorrect
- payload overlap occurred

## Importance

This script proved:
- GTEXT blocks contained image data
- textures were embedded directly in the archive

## Status

OBSOLETE

Replaced by deterministic parser.

---

# Deterministic Texture Parser

## Purpose

Rebuild texture extraction using confirmed archive structure.

## Major Discoveries Used

Confirmed structure:

| Offset | Meaning |
|---|---|
| +0x00 | GTEXT |
| +0x04 | block size |
| +0x18 | width |
| +0x1C | height |
| +0x20 | BPP |
| +0x24 | TGAN |
| +0x54 | payload start |

---

# Payload Math

## Formula

```text
payload_size = block_size - 0x54
```

## Importance

This was one of the largest breakthroughs in the project.

It allowed:
- deterministic extraction
- proper payload boundaries
- elimination of overlap/corruption

---

# Supported Formats

| Format | Status |
|---|---|
| RGB24 | WORKING |
| RGBA32 | WORKING |

---

# Texture Export Pipeline

## Workflow

```text
GTEXT chunk
→ parse header
→ calculate payload boundaries
→ extract raw pixel data
→ convert to PIL image
→ export PNG
```

---

# Major Improvements

The deterministic parser significantly improved:
- texture centering
- colour accuracy
- atlas reconstruction
- extraction reliability

---

# Remaining Issues

Some textures still appear:
- visually scrambled
- colour shifted
- structurally unusual

Possible causes:
- swizzled textures
- indexed/palette textures
- lookup textures
- non-standard GPU formats

---

# Contact Sheet Generator

## Purpose

Generate overview sheets of extracted textures.

## Result

Allowed:
- visual pattern recognition
- texture family classification
- atlas identification
- detection of UI/particle systems

## Importance

This became a major analysis tool during texture research.

---

# Raw Texture Dumps

## Purpose

Unknown formats were dumped as:
```text
.raw
```

files for manual inspection.

## Importance

This allowed:
- external analysis
- testing alternate decoders
- identifying possible non-standard formats

---

# RGB24 Discovery

## Discovery

Some textures used:
```text
24-bit RGB
```

instead of:
```text
32-bit RGBA
```

## Result

Adding RGB24 support nearly doubled extraction success.

## Importance

This was a major breakthrough in texture recovery.

---

# Current Parser Status

| Feature | Status |
|---|---|
| deterministic parsing | COMPLETE |
| payload boundaries | SOLVED |
| RGB24 | WORKING |
| RGBA32 | WORKING |
| PNG export | WORKING |
| texture atlas recovery | WORKING |
| palette textures | UNSOLVED |
| swizzled textures | UNSOLVED |

---

# Future Tooling Plans

Planned tools:
- class database extractor
- object instance parser
- mesh extractor
- sound bank parser
- PS2 ADPCM decoder
- scene reconstruction tools
- Blender export pipeline
- GDW repacker/modding tools

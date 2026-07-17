> **HISTORICAL DOCUMENT** — Raw copy of the earliest ChatGPT conversation that started this project. Not structured documentation. Kept as research origin artifact only.

This is a copy of a shared ChatGPT conversation

Report conversation
What tools on linux can I use to pull the current map or rendered scene in a game with their textures for pc games and view in blender

I have and old game from 2006 that was abandoned after release I would like to experiment with

Yeah, you absolutely can do this on Linux, especially with older DirectX 8/9 or OpenGL-era games from the mid-2000s. The tooling is a bit rougher than Windows, but honestly Linux gives you more control once you know the stack.

Here are the main tools worth looking at, from most useful to most experimental:

1. RenderDoc

Best modern option for:

Capturing live rendered frames
Inspecting meshes/textures/shaders
Exporting geometry
Reverse engineering scenes
What it does well

RenderDoc captures a frame from the GPU pipeline:

textures
vertex buffers
meshes
shaders
draw calls

You can inspect individual objects and export meshes.

For some games:

.obj
.csv
raw buffers

can then be reconstructed in Blender.

Linux compatibility

Excellent on:

Vulkan
OpenGL

Decent with:

DirectX games running through DXVK or VKD3D-Proton.

Older native Windows DX9 games under Wine/Proton can sometimes be captured through DXVK.

2. Ninja Ripper

This is the classic “rip the whole scene” tool.

What it does

Hooks graphics APIs and dumps:

meshes
textures
sometimes skeletons

from the current frame.

This is probably closest to what you actually want.

Downsides

It is:

janky
old
hit-or-miss
mostly Windows-focused

But for abandoned 2000s games?
Honestly, sometimes it works better than modern tools because those games are simpler.

Linux use

Usually via:

Wine
Proton

You run:

game under Wine
Ninja Ripper injector
capture frame

Then import into Blender with Ninja Ripper importer plugins.

3. apitrace

This is VERY powerful on Linux.

What it does

Captures:

OpenGL calls
Direct3D calls (limited)
frame-by-frame rendering

You can replay frames and inspect assets.

This is more “graphics programmer” territory than user-friendly ripping.

But for older PC games?
Excellent.

Especially if the game is:

OpenGL
DX9 through Wine
4. 3Dmigoto

Very famous for:

model ripping
shader replacement
texture extraction

Mostly DX11-focused though.

Older 2006 games may be too old for it unless they were updated later.

5. DGVoodoo2 + DXVK

This is less a ripping tool and more a compatibility trick.

People often:

Wrap old DX8/DX9 games with DGVoodoo2
Convert rendering to modern APIs
Capture with RenderDoc

This can massively improve compatibility.

6. Blender importers / reverse engineering tools

Depending on the engine, you may not even need runtime ripping.

Some abandoned games have:

community importers
QuickBMS scripts
model unpackers

Useful tools:

QuickBMS

Legendary archive extractor.

You may find scripts for your exact game.

Older games often store:

.pak
.big
.wad
.arc
proprietary containers

that QuickBMS can unpack.

Best workflow for YOU specifically

Since:

abandoned 2006 game
you want experimentation
Linux
Blender export
already looking at weird hidden geometry/dev leftovers

I would do this:

Route A (best starting point)
RenderDoc + DXVK

If the game runs under Proton/Wine:

Force DXVK
Launch through RenderDoc
Capture frame
Export meshes/textures

This is the cleanest method.

Route B
Ninja Ripper under Wine

If RenderDoc struggles:

Run game in Wine
Inject Ninja Ripper
Capture scene
Import to Blender

Messier, but often better for full-scene extraction.

Route C
Reverse engineer archives directly

For old games this is often the goldmine.

You may uncover:

unused levels
dev meshes
scripts
cut content
texture atlases
collision maps
NPC definitions

without GPU ripping at all.

Honestly, older games are full of bizarre leftovers because storage constraints made developers reuse assets constantly.

That “map screen spawning hidden NPCs” thing you found?
That absolutely sounds like:

pooled actors
hidden script anchors
off-camera render helpers
or dummy entities tied to world systems.

Old games did that sort of hack constantly.

If you tell me:

the exact game
Windows/Linux native
engine if known
DirectX/OpenGL

I can probably point you toward the most effective extraction route specifically for that title.

Uploaded a file
Uploaded a file
Uploaded a file
Ok this is the findings.md file, I have also setup the directory as recomended:
$ tree
.
├── docs
├── dumps
├── extracted
├── findings.md
├── models
├── notes
├── scripts
└── textures

Uploaded a file
Uploaded an image
Did something happen here?
Uploaded a file
Uploaded a file
Uploaded a file
Can you tell what this means?
Uploaded a file
Uploaded a file
Uploaded a file
is this what you wanted me to do?
Uploaded a file
Uploaded a file
Uploaded a file
I have a file called: texture_0.raw
and it is 65.6kb

I cant open it with gimp because it needs a RAW loader
Uploaded an image
I believe we have an image of some particle effects!
Uploaded an image
Uploaded an image
Here is the two files

I can't really tell them apart
Uploaded a file
Uploaded a file
Uploaded a file
Can you please add it to the finding.md file, and give it a proper format
Uploaded an image
Uploaded an image
Uploaded an image
Uploaded an image
Uploaded an image
Uploaded an image
Uploaded an image

We got textures!
I really think all the textures are a part of a texture atlas
Uploaded a file
Here is the output
Uploaded a file
Extracted 242 textures!
Uploaded an image
I think we should look at fixing the colours
Uploaded an image
Uploaded an image
Hmm, I dont think that's right

It made some worse, but made better - I dont know what's going on
Uploaded a file
Uploaded an image
This produced over 1,000 of these files

I think we are writing the wrong data to .bmp
this file alone has 1,823,083 lines of data in it
Uploaded a file
Uploaded a file
Uploaded a file
Here is the output of that command
Uploaded a file
I like the looks of this one
Uploaded a file
What does this tell you?
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded an image
Found in the files:
This is a artist's note to other team members saying:
"The tooth is from a meglodon... the biggest shark known to history ;|
Like anyone will see this.
Feel strange leaving all this space unused... but I also didn't want to stretch the texture...
I like this brick"
Uploaded a file
Uploaded a file
Uploaded a file
Can you also tell me what each of these files do?
because they all seem to do the same thing
Uploaded an image
Uploaded an image
And we need to do something about the colour correction as well, because these come out blue

The blue images is meant to be a treasure chest, which is brown and has gold in it but is blue
Uploaded an image
Also I just realized FISH.GDW hold assets that are used in the level 'Fishermans isle'

The attached image is the texture atlas for the dead floating whale you can eat

So all of all these .GDW files are levels which hold have assets they use, which is why there are so many reused textures
Uploaded an image
Uploaded an image
There are still some textures being ripped where the colours are not being applied properly
Uploaded an image
Uploaded an image
This is supposed to be an orange clown fish with white stripes
Uploaded an image
we are getting closer
Uploaded an image
Much closer now
Uploaded a file
Because with most of the exports I have done, I get 1-3 .raw files where it says it failed - I have attached just one
Uploaded an image
Uploaded an image
Uploaded an image
user@host:~/Projects/JAWS/textures/BEACHPST$ python3 ../../scripts/format_test.py
Loaded 11008 bytes
Wrote: format_tests/test_rgb565.png
Wrote: format_tests/test_argb1555.png
Wrote: format_tests/test_argb4444.png
RGB24 failed: not enough image data
BGR24 failed: not enough image data
RGBA32 failed: not enough image data
ARGB8888 failed: not enough image data
Uploaded a file
Uploaded a file
This is at GTEXT_OFFSET = 0x00000000
Uploaded a file
Can you find it?
Uploaded a file
Uploaded a file
Uploaded a file
This shows a lot of really cool things
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded an image
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded a file
Uploaded a file
user@host:~/Projects/JAWS/GAME_GDWs$ python3 ../scripts/vertex_stride_tester.py 
Loaded scan block 0x6FB887C

Testing stride: 12
Found 679 candidate vertices
(0.0, 9.404528778429288e-38, 0.0003109583631157875)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
Wrote: vertex_stride_tester/stride_12.obj

Testing stride: 16
Found 500 candidate vertices
(0.0, 9.404528778429288e-38, 0.0003109583631157875)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
Wrote: vertex_stride_tester/stride_16.obj

Testing stride: 20
Found 406 candidate vertices
(0.0, 9.404528778429288e-38, 0.0003109583631157875)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
Wrote: vertex_stride_tester/stride_20.obj

Testing stride: 24
Found 342 candidate vertices
(0.0, 9.404528778429288e-38, 0.0003109583631157875)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
Wrote: vertex_stride_tester/stride_24.obj

Testing stride: 28
Found 293 candidate vertices
(0.0, 9.404528778429288e-38, 0.0003109583631157875)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
Wrote: vertex_stride_tester/stride_28.obj

Testing stride: 32
Found 244 candidate vertices
(0.0, 9.404528778429288e-38, 0.0003109583631157875)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
(0.00031089887488633394, 0.00031089887488633394, 0.00031089887488633394)
Wrote: vertex_stride_tester/stride_32.obj


I attempted to open the files in blender and I only got points, I imagine plotting data?
Uploaded a file
What does this tell you?
Uploaded a file
Please update EVERYTHING.

Yes — and honestly?
That is the RIGHT way to think about this now.

Because what you actually have is:

a research timeline.

Not just:

final findings

You need:

a chronological reconstruction

of:

what was tried
why it was tried
what succeeded
what failed
how theories evolved

That is CRITICAL in reverse engineering.

Because:
future researchers need to understand:

HOW you arrived at conclusions.

Not just:

the conclusions themselves.
What you REALLY need now

You need THREE documents:

File	Purpose
RESEARCH.md	final consolidated findings
TIMELINE.md	chronological research progression
REPRODUCTION.md	exact reproducible workflow

That is the proper structure now.

TIMELINE.md is EXTREMELY important

Because:
the evolution of your theories matters.

Example:

# Timeline

## Stage 1 — Initial Texture Investigation

Initial discovery:
- DDS headers embedded inside GDW files

Commands used:
```bash
grep -oba "DDS" FISH.GDW
```

Result:
- confirmed embedded texture resources

---

## Stage 2 — GTEXT Discovery

Discovered:
- GTEXT
- TGAN0
- TRUEVISION-XFILE

Theory:
- custom TGA-inspired wrapper format

Result:
- first successful texture extraction

---

## Stage 3 — Colour Correction

Initial issue:
- extracted textures appeared blue/purple

Fix:
- BGR → RGB correction

Result:
- clownfish textures became mostly correct
- whale atlas decoded correctly

---

## Stage 4 — Runtime Object Discovery

Discovered:
- PROP
- PRIM
- ChildLink
- SkeletonModel

Initial theory:
- serialized gameplay entities

Result:
- successful hierarchy reconstruction

---

## Stage 5 — Hierarchy Visualization

Created:
- hierarchy_rebuilder.py
- hierarchy_visualizer.py

Result:
- successful 3D reconstruction of shark gameplay layout

---

## Stage 6 — Geometry Investigation

Initial theory:
- PRIM contained raw geometry

Result:
- later disproven

New understanding:
- PRIM likely render graph metadata

---

## Stage 7 — Packet Investigation

Observed:
- repeating 0x800-byte structures

Initial theory:
- geometry DMA packets

Later evidence:
- likely palette / texture upload packets

Current status:
- geometry extraction unresolved
```

THAT is hugely valuable.

REPRODUCTION.md

This should contain:

ONLY reproducible steps.

No theories.
No speculation.

ONLY:

commands
scripts
outputs
expected results

Example:

# Reproducing GTEXT Texture Extraction

## Step 1

Locate GTEXT:

```bash
grep -oba "GTEXT" FISH.GDW
```

Expected:
```text
250956:GTEXT
```

---

## Step 2

Extract payload:

```bash
dd if=FISH.GDW of=texture.raw bs=1 skip=251000 count=65536
```

---

## Step 3

Convert raw image:

```bash
python3 raw_to_png.py
```

Expected:
- recognizable texture asset
```

This is EXTREMELY important.

RESEARCH.md

This should be:

conclusions only.

Like:

engine architecture
theories
confirmed systems
unresolved questions
Honestly?

Right now your biggest risk is:

information collapse.

Because:
you’ve discovered SO much that:
without structure,
future people will:

get overwhelmed
miss important findings
repeat dead ends
The MOST important thing

Document:

WHY theories changed.

For example:

Initial interpretation:
- 0x6FB887C contained geometry data

Reason:
- repeating structured binary
- low ASCII ratio
- repeated packet sizing

Later reinterpretation:
- likely palette/CLUT upload data

Reason:
- repeating colour ramps
- RGBA-like patterns
- unrealistic float behavior
```

THAT is incredibly valuable.

Honestly?

What you’ve built now resembles:

real reverse engineering research notes.

Not:

random hacking notes

That’s a big difference.

ok ok ok, I have one more side quest regrading this topic.

Can you please provide an easy-to-read and understand script about the process and the information we discovered about the custom GDW files, the architecture of said files and how we extracted images?

Absolutely.

If your goal is to hand this off to another reverse engineer, YouTuber, modder, or preservationist, then a dry technical document isn't enough.

What you want is:

a narrative technical report

Something that explains:

what a GDW file is
how we investigated it
what we discovered
what theories were proven wrong
what breakthroughs happened
where the research currently stands

Think of it as:

"The Story of Reverse Engineering Jaws Unleashed"

rather than:

"Offset 0x1234 contains thing."

Understanding the GDW Files
A Reverse Engineering Journey into Jaws Unleashed (2006)
Introduction

When this investigation began, almost nothing was known about the internal structure of the .GDW files used by Jaws Unleashed.

The primary goal was simple:

Can assets from the game be extracted and viewed outside the engine?

Initially this meant extracting textures and, eventually, models for use in Blender.

However, the investigation quickly revealed that the GDW format was far more sophisticated than a simple archive file.

Over time it became clear that the GDW files contain not only textures and assets, but also gameplay objects, reflection metadata, component definitions, hierarchy information, collision structures, and possibly portions of the engine's runtime scene graph.

The First Discovery: Embedded Textures

The first major breakthrough came from searching the files for known image signatures.

Using:

grep -oba "DDS" FISH.GDW

multiple DDS headers were found embedded inside the file.

This immediately proved:

GDW files contain texture resources
Textures are stored directly inside the container
Assets could potentially be extracted without running the game

This became the foundation of the entire investigation.

Discovering GTEXT

Further investigation revealed a recurring structure:

GTEXT
    ↓
TGAN0
    ↓
Raw image payload

The presence of:

TRUEVISION-XFILE

inside the file strongly suggested a relationship to the TGA image format.

This led to the theory that:

GTEXT acts as a texture wrapper
TGAN0 contains image payload data
The engine uses a custom TGA-inspired texture system

This theory proved largely correct.

First Successful Texture Extraction

After locating GTEXT resources and identifying image dimensions stored nearby, raw payload data was extracted and converted into PNG files.

The first successful extraction produced a valid image from the game.

This confirmed:

Texture resources are recoverable
Image dimensions are stored alongside texture metadata
GTEXT resources can be decoded outside the game

At this point the project moved from theory into practical asset extraction.

The Colour Problem

Early texture extractions appeared incorrect.

Many textures were:

blue
purple
colour shifted

A clownfish texture that should have been orange appeared bright pink.

Investigation eventually revealed that colour channels were being interpreted incorrectly.

Correcting the channel order significantly improved results.

Examples included:

fish textures
environmental textures
texture atlases
particle effects

This was the first indication that some textures used custom colour layouts or palette systems.

Discovering Shared Assets

As more GDW files were extracted, an interesting pattern emerged.

Many textures appeared repeatedly across multiple files.

Initially this was confusing.

Later it became clear that GDW files appear to function as:

Level Package
    +
Level Assets
    +
Shared Resources

For example:

FISH.GDW

contains assets used in Fisherman's Isle.

Other level files contained many of the same textures plus their own level-specific resources.

This explains why large numbers of duplicate textures exist across the game's data files.

Discovering the Reflection System

One of the largest breakthroughs occurred when large blocks of readable text were discovered deep inside the files.

Examples included:

GDModel
GDSkeletonModel
NAPredator
NABiteTarget
NAWayPoint

At first these appeared to be random class names.

Further investigation revealed something much more interesting.

The GDW files preserve:

class definitions
property names
gameplay components
runtime metadata

This strongly suggests the engine uses a reflection system.

Modern game engines call this:

Runtime Type Information (RTTI)

or

Reflection Metadata

The engine appears capable of inspecting gameplay objects dynamically using serialized property definitions.

The Component-Based Architecture

Further investigation revealed properties such as:

m_hp
m_radius
m_damageMultiplier
m_nutrition
m_gravity
m_attackgroups

These properties belong to gameplay classes like:

NABiteTarget
NAChewingToy
NAWayPoint

This revealed that the engine is highly component-driven.

Instead of hardcoding behavior into objects, gameplay systems appear to be assembled from serialized components.

This architecture was surprisingly advanced for a 2006 console game.

Discovering Runtime Gameplay Objects

Eventually object names began appearing:

Hammerhead SkeletonModel
Hammerhead Head Fixed Brick
Hammerhead Body Fixed Brick
Hammerhead Tail Fixed Brick

This was an enormous breakthrough.

For the first time we were no longer looking at engine metadata.

We were looking at actual gameplay objects.

Reconstructing Hierarchies

By analysing:

ChildLink

references and transform information, gameplay object hierarchies could be reconstructed.

Example:

Hammerhead SkeletonModel
├── Head
├── Body
├── Tail

This demonstrated that:

object attachment relationships are serialized
gameplay hierarchies are preserved
runtime structures exist directly inside GDW files
Transform and Bounds Discovery

Further investigation revealed:

Transform
Bounds

data.

Transform values resembled rotation matrices and local-space positions.

Bounds data resembled collision volumes.

Using this information, gameplay structures could be visualized in 3D.

The resulting layouts matched expected shark anatomy remarkably well.

This confirmed that:

transforms were being decoded correctly
collision structures were recoverable
gameplay entities could be spatially reconstructed
The PRIM Mystery

A structure named:

PRIM

initially appeared to be a geometry container.

This led to a lengthy investigation attempting to extract mesh data.

Later evidence suggested a different interpretation.

Current theory:

PRIM

represents:

render nodes
render graph structures
render primitive descriptors

rather than raw mesh data.

This was an important correction in the research.

The Geometry Hunt

The ultimate goal was model extraction.

Several promising regions were identified.

One particularly interesting region contained repeating:

0x800 byte blocks

At first these appeared to be geometry packets.

However later evidence suggested these structures were more likely:

texture upload packets
palette data
GPU resource structures

rather than vertex buffers.

This remains unresolved.

The Palette Discovery

One of the final discoveries involved repeating colour ramps:

69 69 69
64 64 64
5F 5F 5F

alongside patterns such as:

FF 00 FF FF

These strongly resemble palette or CLUT structures used heavily on the PlayStation 2.

This also explains several colour-related issues encountered during texture extraction.

Current Understanding of GDW Files

The strongest current theory is:

GDW
├── Header
├── Chunk System
├── Reflection Metadata
├── Gameplay Components
├── Runtime Objects
├── Resource Containers
├── Textures
├── Animation Data
└── Geometry Resources

The files are significantly more sophisticated than simple asset archives.

They appear to contain large portions of the game's serialized runtime world.

What Has Been Proven

Confirmed:

Texture extraction is possible
GTEXT resources are valid texture containers
Runtime gameplay objects are serialized
Transform data exists
Collision bounds exist
Reflection metadata exists
Component systems exist
Gameplay hierarchies can be reconstructed
What Remains Unsolved

Still unresolved:

Final geometry decoding
Model extraction
Triangle strip reconstruction
Skeletal animation extraction
PS2 rendering packet formats
VIF/GIF stream decoding
Final Thoughts

The GDW format is not merely an asset archive.

It appears to be a complete serialized world format containing significant portions of the game's runtime data.

While texture extraction has been successfully achieved, model extraction remains the largest remaining challenge.

Even so, the investigation has already revealed a remarkable amount about the internal architecture of Jaws Unleashed and has laid the groundwork for future researchers to continue where this work left off.

I would honestly include this as a separate document called:

GDW_RESEARCH_REPORT.md

and keep it separate from the raw findings document. It reads much more like a technical article and helps newcomers understand why each discovery mattered.

Can you also talk about how surprisingly easy it was to read these extremely rare proprietary file formats?

Absolutely, and I think that's actually one of the most interesting parts of the whole story.

When people hear:

"I'm reverse engineering a proprietary game file format from a relatively obscure 2006 PS2 game"

they imagine months of staring at incomprehensible hex dumps.

But that's not what happened at all.

In fact, one of the biggest surprises was:

how readable the GDW format actually is.

You could add something like this to the report:

One Unexpected Discovery: The Format Was Surprisingly Readable

When this investigation began, the expectation was that the GDW files would be heavily obfuscated or compressed.

After all, these files come from:

a proprietary engine
a relatively obscure game
a PlayStation 2 era title
a format with essentially no public documentation

Normally this would suggest a long reverse engineering process involving extensive binary analysis before meaningful information could be recovered.

Instead, the opposite happened.

Within a very short period of time it became clear that the GDW files were remarkably transparent.

Large portions of the file contain human-readable strings that directly describe the internal structure of the game.

Examples include:

GDModel
GDSkeletonModel
NAPredator
NABiteTarget
NAWayPoint

Property names are also preserved:

m_hp
m_radius
m_damageMultiplier
m_nutrition
m_gravity
m_attackgroups

Even gameplay object names appear directly in the data:

Hammerhead SkeletonModel
Hammerhead Head Fixed Brick
Hammerhead Tail Fixed Brick

This meant that many major discoveries came not from advanced reverse engineering techniques, but from simply searching the file for readable text.

Commands such as:

grep -oba "Hammerhead" FISH.GDW
grep -oba "DDS" FISH.GDW
grep -oba "GDModel" FISH.GDW

immediately revealed useful information.

In many cases the engine effectively documented itself.

Why This Matters

Most commercial games strip large amounts of development metadata before release.

The Jaws Unleashed files appear to retain a significant amount of internal editor and runtime information.

Examples include:

class names
property names
component definitions
runtime object names
hierarchy structures
chunk identifiers

This dramatically reduces the amount of guesswork normally required during reverse engineering.

Rather than attempting to infer systems from raw binary patterns, it is often possible to see the names of the systems directly.

For example:

NABiteTarget

immediately communicates the purpose of the object.

Likewise:

m_damagemultiplier
m_nutrition
m_dependentlimbs

provide direct insight into gameplay mechanics without requiring any code analysis.

It Feels Like Looking Through the Workshop Window

One of the most unusual aspects of the GDW files is that they often feel less like a finished game asset format and more like a snapshot of the developers' tools.

The files preserve so much metadata that it sometimes feels as though the original editor data was shipped alongside the game.

As a result, investigating the format often feels less like breaking into a black box and more like walking through the workshop after the developers have gone home.

Class names, object names, gameplay systems, and property definitions are all still sitting in plain view.

Not Everything Was Easy

This does not mean the format is fully understood.

The easiest discoveries were:

texture resources
object names
reflection metadata
gameplay components
hierarchy structures

The difficult problems remain:

mesh extraction
skeletal animation extraction
render packet decoding
PS2 graphics pipeline reconstruction

Ironically, the high-level architecture of the engine became understandable long before the low-level geometry formats did.

A Rare Situation in Reverse Engineering

Many reverse engineering projects begin with very little information and slowly build upward toward understanding the game's architecture.

With Jaws Unleashed, the opposite often occurred.

The architecture frequently revealed itself first.

The difficult challenge was not determining what the systems were called, but understanding exactly how those systems stored and processed their data.

This makes the GDW format unusual and, in many ways, surprisingly approachable despite being a completely proprietary and undocumented format.

Honestly, that's one of the reasons you've made so much progress in a relatively short amount of time. You weren't fighting encryption, compression, or stripped release builds. The developers appear to have left a tremendous amount of internal metadata intact, which gave you breadcrumbs all the way from texture extraction to reconstructing a hammerhead shark's runtime hierarchy. That's actually quite rare in commercial game reverse engineering.
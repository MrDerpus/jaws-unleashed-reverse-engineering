# Game World Builder: history of the tool and its games

**In short:** *Jaws Unleashed* was made with **Game World Builder (GWB)**, the same in-house level editor that Appaloosa used for *Ecco the Dolphin: Defender of the Future*. The editor saves levels in the `GDED` file format. The game engine that loads them is called **Diesel Power**.

We have GWB files from five points in time:

| When | Game | `GDED` version |
|---|---|---|
| May 1999 | *Ecco: Defender* prototypes | 2.1.1.6 (oldest found) |
| 2000–2002 | *Ecco: Defender*, all builds (Dreamcast and PS2) | 2.1.12.1 |
| Feb 2001 | *Ecco: Sentinels of the Universe* (cancelled sequel) | 2.3.2.1 |
| 2006 | *Jaws Unleashed* (PC and PS2) | 2.6.3.16 |

Jaws continued from the cancelled *Sentinels* code, not from the shipped *Defender*. After Jaws, Appaloosa closed. The same team became Twofish.hu. Their unreleased *EdgeRacers* may or may not have used GWB.

Credit: the user said from the start that Jaws and Defender share an editor. Claude doubted it at first. The evidence below proved the user right.

This doc was split out of `docs/GDW_FORMAT.md` on 2026-11-27. The file format itself is described there.

---

## Contents

1. [Editor and engine: the names](#1-editor-and-engine-the-names)
2. [How we know Jaws was made with GWB](#2-how-we-know-jaws-was-made-with-gwb)
3. [What changed in each version](#3-what-changed-in-each-version)
4. [May 1999 prototypes (2.1.1.6)](#4-may-1999-prototypes-2116)
5. [*Defender*, 2000–2002 (2.1.12.1)](#5-defender-20002002-21121)
6. [*Sentinels of the Universe*, 2001 (2.3.2.1)](#6-sentinels-of-the-universe-2001-2321)
7. [*Jaws Unleashed*, 2006 (2.6.3.16)](#7-jaws-unleashed-2006-26316)
8. [Classes and fields across the games](#8-classes-and-fields-across-the-games)
9. [Other games checked](#9-other-games-checked)
10. [After Jaws](#10-after-jaws)
11. [An unproven idea: version numbers as dates](#11-an-unproven-idea-version-numbers-as-dates)
12. [Tools](#12-tools)

---

## 1. Editor and engine: the names

- **Game World Builder (GWB)** is the editor. It builds the levels.
- **Diesel Power** is the game engine that runs them.
- Both are Appaloosa's own in-house tools.

**Source.** The back cover of the European Dreamcast *Ecco: Defender* (2000, catalogue MK-51033-50) reads:

> "GameWorld Builder™ Software Technology & Diesel Power™ Game Engine are the property of Appaloosa Interactive Corp"

The user supplied the scan: [`docs/sources/Ecco_Defender_Dreamcast_PAL_back_cover.png`](sources/Ecco_Defender_Dreamcast_PAL_back_cover.png).

**Things to keep in mind:**
- That Jaws still runs on Diesel Power is an inference from the shared code. The name appears nowhere in Jaws, its PS2 version, the level files or the 2001 press kit.
- Jaws' credits name neither tool.
- An unrelated Swedish engine by GRIN was also called "Diesel". Watch for it when searching.
- In these docs, "the engine" means Diesel Power.

**The press kit.** Appaloosa's PS2 press kit (September 2001) describes the GWB "3D tool suite":
- in development since early 1999, for *Ecco* on Dreamcast;
- ported to PS2, with all of Ecco's levels, in under three months.

Copy: [`docs/sources/Appaloosa_PS2_press_information_2001-09.pdf`](sources/Appaloosa_PS2_press_information_2001-09.pdf), from [Sega Retro](https://segaretro.org/images/8/86/PS2PressInformation_2001-09_Ecco_Appaloosa_info.pdf).

Its description matches the Jaws files closely:

| Press kit (2001) | Jaws data |
|---|---|
| "built around standard **bricks** (objects)" | `BRTR` (brick tree), `CHBR` (child brick), `GDBrick` |
| "**actions** (procedures)" | `ACTN` blocks (`GDControl`, quests, …) |
| "**resources** (meshes, textures, sfx, collision data)" | `RSRC`: `GMDL`, `GTEX`, `GSMP`, `MREG` |
| "type classes" with a `GD` prefix | engine-wide `GD` classes (`GDModel`, `GDControl`, …) |
| exporters turn textures into console formats and meshes into triangle strips | PS2 `.GDE`: native PS2 textures, `STRP` strips |

**The editor's name in the games:**
- The words "Game World Builder" or "GWB" never appear in the Jaws files.
- They appear once in Defender: "Created with Game World Builder, © 2000 Appaloosa Interactive", in its `460_Credits` level.
- That line is gone from Sentinels, Defender PS2 and Jaws.

---

## 2. How we know Jaws was made with GWB

Defender's PS2 levels are `.GDE` files in the same format as Jaws'. Example: `DATA/110L_BAY.GDE` (20 MB).

| | Defender PS2 `110L_BAY.GDE` | Jaws PS2 `FISH.GDE` |
|---|---|---|
| First line | `GDED BINARY FORMAT, VERSION 2.1.12.1` | `GDED BINARY FORMAT, VERSION 2.6.3.16` |
| Class tables | `CLAS` with `BRCM` + `ACCM` | same |
| Scene tree | `CHBR`, `PRPS`, `PROP` | same structure |
| Resources | `ACTN`, `GMDL`, `GTEX`, `MREG`, `STRP` | same tags |
| Engine classes | `GDModel`, `GDControl`, `GDBrick`, `GDPath`, `GDLight` | same names |

The differences are what you'd expect from an older version of the same tool:
- Defender's chunks are packed together. Jaws pads each to 4 bytes.
- Defender starts with `LDSC`. Jaws starts with `FSIZ VERS EXBY`.
- Defender has no `SKIP FDIR ENDF` footer.

**Conclusion:** Jaws was built with GWB, about five years and several versions after Defender.

---

## 3. What changed in each version

**The order of changes.** These dates come from date stamps inside the files, not from the version numbers.

| When | Change |
|---|---|
| 1998 | Oldest format stamps: `WDIM` 1998-03-04, `GNRL` 03-31, `GMDL`/`GMAT`/`TANG` 04-09, `GTEX` 04-14 |
| May 1999 | **2.1.1.6**: the core format already complete; packed chunks |
| by Jan 2000 | **2.1.12.1**: adds `KADI` (Dreamcast) and a loading picture |
| Dec 2000 – Feb 2001 | **2.3.2.1** (Sentinels): 4-byte chunk padding; new `EXTR` and `Tile` chunks |
| 2002-04-10 | `SKEL` (skeleton) format revised |
| about 2003-06-26 | New file header `FSIZ VERS EXBY`. Every Jaws `VERS` holds this date. |
| 2005-05-15 | `GTEX` (texture) format revised |
| 2005-07-07 | New footer `SKIP FDIR ENDF`, holding loading-screen scenes |
| after 2.5.7.12 | Every value aligned to its own size |
| after 2.5.12.6 | `RSRC` gets a header (stamp 2005-12-08); `GMDL` revised 2005-12-05 |
| 2.6.1.17 | Oldest version Jaws will load |
| 2.6.3.16 | Final Jaws version (PS2-only stamp 2006-03-16) |

**Top-level chunks by game:**

| Game | Chunks, in file order |
|---|---|
| Defender 1999 | `GNRL WDIM RSPR CLAS RSRC BRTR SCRT` |
| Defender Dreamcast | `GNRL KADI WDIM RSPR CLAS RSRC BRTR SCRT` |
| Defender PS2 | `LDSC GNRL WDIM RSPR CLAS RSRC BRTR SCRT` |
| Sentinels | `GNRL WDIM RSPR CLAS RSRC BRTR SCRT EXTR Tile` |
| Jaws | `FSIZ VERS EXBY GNRL WDIM RSPR CLAS RSRC BRTR SCRT SKIP FDIR ENDF` |

Notes:
- Dreamcast builds of both Ecco games put a loading picture (`TITL`/`TSCR`, a PVR image) in front of the `GDED` first line.
- Sentinels pads chunks, but the class-name lists inside `CLAS` are still packed. Jaws pads those too.
- What the editor was used for between 2001 and 2005 is unknown.

---

## 4. May 1999 prototypes (2.1.1.6)

**In short:** the oldest GWB files found. The format was already complete. Its game code differs a lot from the 2000 release, including sharks that grab Ecco.

The user supplied both discs on 2026-11-26. Files: `~/Projects/ECCO/ecco3d_may1999/` and `~/Projects/ECCO/e3demo_may1999/`.

### The two discs

**"Ecco 3D" (1999-05-06)**
- The boot header calls it "File Viewer", version 0.100.
- One level: `AT.GDE` (Atlantis, 10.3 MB).
- It prints joystick debug text that the E3 build lacks. It looks like a level-viewer build.

**E3 demo (1999-05-08)**
- Levels: `1_TITLE`, `2_OPEN`, `3_REEF`, `5_ATLANTIS`, `6_VICTIM`, `7_LOADING`, plus four small loading levels.
- 16 `.INP`/`.GSG` pairs, probably recorded demo input. Not decoded.
- `START.TXT` chains the levels and the recordings into a self-running demo.
- Audio tracks 4–9 hold music.

### The format

- First line `GDED BINARY FORMAT, VERSION 2.1.1.6`, at the very start of the file. There's no loading picture yet.
- Top level `GNRL WDIM RSPR CLAS RSRC BRTR SCRT`. No `KADI` yet.
- Packed chunks. Our `gded_lineage.py` reads the files unchanged.
- Same resource types as later games: `GTEX GTAN GMAT GMDL MREG SKEL GSFX GSQD GMOA GSCR`.
- Only 1998 date stamps. Revisions stamped 1999-04-13 (`GSFX`), 1999-07-01 and 1999-11-10 (`GMDL`) only show up in the April 2000 files.

### Classes only in 1999

- **Size:** 67 bricks, 272 actions, 2,361 fields. By April 2000: 122 bricks, 580 actions, 5,240 fields.
- **The older dolphin controller:** `TRDolphCtrl` and `TRMorphDolph`. `DolphCtrl` is also already there.
- **An older camera set:** `TRCameraCtrl`, `TRCameraMap`, `TRCameraOut`, `TRCameraTPV`, `TRFadeCamera`.
- **Generic enemy AI:** `TRGenEnemy`, `TRGenAttack`, `TRGenChase`, `TRGenResting`, and `TRSuicide` (14 placed in Reef).
- **Atlantis building-opening sequences:** `LoBuildingOpenAct` and `LoBuildingOpenAct2`, placed 4 + 4.
- **Sharks:** `SharkTank` (5 placed in `3_REEF`) and `SharkTrap`.
- **Others:** `NAVirtualModell`, `DDEnemyTest`, `DDMetalCrabAct`, `DDCrabLaserShot`, `DDTileAct`, `Hatchery`, `NASpotAct`, `Octhelp`.

**The sharks:**
- `SharkTank` is a shark enemy with fields for search, chase, attack and sounds. Its animation parts include `harap_part` (Hungarian *harap* = bite).
- `SharkTrap` (not placed) is a crystal trap that explodes on a following shark.
- Neither is in Sentinels or Jaws. They are Ecco enemies, not ancestors of the Jaws shark.

### The cut shark attack

In May 1999, sharks could **grab Ecco and drag him**. This is a reading of the decompiled code; it wasn't run.

- `TRSharkTank` is a full shark controller with cruise, turn-around and attack states.
- In attack it turns toward Ecco, lunges and sends `DAMG` 30 (damage).
- While holding him, it sends `DRAG` / `PULL` each frame with the position of one jaw or body bone. It also sends `STOP`, whose meaning isn't known.
- `Shark_1` sends the same messages. Ecco's controller (`Ctrl.cpp`) receives them.
- By 2000 nothing sends `DRAG`/`PULL` any more, but Ecco's controller still handles them, a leftover of the cut attack. Jaws has neither.

Summary with open questions: `docs/ecco_leftovers.md` "Cut shark grab attack". The decompiled text stays local: `~/Projects/ECCO/ecco1999_decomp/`.

### Source-file names

- The 1999 programs name 30 source files in their error messages. For example `gdbrick.cpp`, `gdgame.cpp`, `gdtile.cpp`, `ctrl.cpp`, `dolphin.cpp`.
- No later program keeps any `.cpp` names.
- `gdtile.cpp` shows the tile grid (Sentinels' `Tile` chunk) already existed in 1999.
- The 2000 link map places the 1999-only classes in files: `SharkTank` in `Octhelp.cpp`, `SharkTrap` in `Sharktrp.cpp`, `Shark_1` in `Shark_1.cpp`, `DDVictimAct` in `Victim.cpp`. So their code was still in the 2000 program, even though the editor no longer listed them.

### Evidence: reverse-engineering the 1999 program

**Asserts.**
- The source code isn't on the discs. 57 `GDASSERT` error messages survive, each with the checked expression.
- Each call passes the source file and line number. `scripts/sh4_asserts.py` reads them from the code: 65 call sites, 2 lines unresolved.
- Result: `docs/ecco1999_asserts.txt`.
- Each source file's code is one continuous block in the program.

**May 6 vs May 8.** Line numbers match in 19 files and differ in 5: `ctrl.cpp`, `dcfile.cpp`, `dcrender.cpp`, `gdcommon.cpp` and `gdgame.cpp`. Those five were edited in the two days between the builds.

**Function names**, copied over from the 2000 `ECCO.ELF` debug symbols by `scripts/ecco1999_match.py`:
- 2,553 functions named, and 11,315 more given a source file, out of 20,463.
- Output: `docs/ecco1999_function_names.tsv` and `docs/ecco1999_function_files.tsv`. They are applied in Ghidra project `ECCO99`.

What worked:
- **Vtables.** 1999 vtables use 8-byte slots; 2000 uses 4. Factories are found by slot 0 (`GetClassName`), constructors via slot 1 (`Create`). About 0.2% of matches look suspicious.
- **1999 action vtables are one slot shorter:** `GetFactory` = slot 7, `Execute` = slot 9, `OnActivate` = slot 11. Tables of the same shape are aligned as a group.
- **Call-graph voting and gap filling** add a little.
- **Source files.** A function between two matches from the same file gets that file. Checked on the asserts: 39 of 44 right.

What didn't work:
- **Exact code matching** finds nothing, because the two compilers produce different code.
- **String matching** is weak, because the 2000 compiler reaches strings through packed blocks.

**Ghidra setup** for readable output (scripts in `scripts/ghidra/`):
- `SetFpscrZero.java` plus `sh4_fpmode_filter.py` handle the FPU mode forks.
- `SplitReadOnly.java` and `SetWritable.java` make code read-only, so constants fold.
- `CreateFuncs.java` adds 7,751 missed functions.
- `UnapplyNames.java` undoes the names.

### Not done yet

- Comparing the 1999 levels with their shipped versions.
- Decoding the `.INP`/`.GSG` recordings.
- The program's version check.

---

## 5. *Defender*, 2000–2002 (2.1.12.1)

**In short:** every *Defender* build from January 2000 to the 2002 PS2 port uses version 2.1.12.1, about 300 level files in all. The format stayed the same; the classes changed.

### February 2000 prototype

From Hidden Palace; the user supplied it on 2026-11-26.
- Version 0.800, header date 2000-02-04, marked "sample disk for use in the office only".
- 41 levels dated 2000-01-24 to 02-17, all 2.1.12.1. So 2.1.12.1 was the format by January 2000.
- Oldest Defender data on hand: sound banks from 1999-08-23 and an input recording from 1999-06-04.
- Classes: February 112 bricks / 521 actions; April 122 / 580.
- **Localization was added between mid-February and April 2000.** New in April: `GDLanguageGroup`, `GDPropLanguage`, `GDPropLangIDList`, and others.
- February-only classes, which never came back: `MLMultiModel`, `MLMultiSkelModel`, `MLModelAlpha`, `MLRepHal`, `MLVmi`.
- It has three levels that are in no later build: `docs/ecco_leftovers.md` "Cut Defender levels in the Feb 2000 prototype".

### European vs US Dreamcast masters

| | European (PAL) | US |
|---|---|---|
| Version | `MK-51033-50 V1.003` | `MK-51033 V1.000` |
| Files up to | 2000-05-13 | 2000-07-14 |
| Levels | 48, all 2.1.12.1 | same 48 |
| Classes | 121 bricks / 523 actions | 123 / 529 |

- 13 files are identical. 37 differ, including the program.
- **Biggest US changes:**
  - `470_FOCI` +1.39 MB, a much expanded level: +84 meshes, ~280 more placed models, ~240 more lights.
  - `320_RESISTANCE` +597 KB: +159 meshes, each with collision.
  - `460_CREDITS`: about 23 more credit lines, for Sega of America staff.
- **The US files were exported with a newer editor.** Their class lists include `MBLovedek` (later in Jaws), `NAHair` (in Sentinels and Jaws), `MBMermaid`, `MBMissile`, `MBCameraAct`, `MLCamAct`, `MLSmooth` and `DDPaintBall`. Only `DDPaintBall` is placed. The `MB…` classes and the hair system existed by mid-2000.

### Retail Dreamcast vs PS2

| | Dreamcast (retail PAL) | PS2 (US, `SLUS_203.94` v1.01) |
|---|---|---|
| Dates | up to 2000-05-13 | levels 2001-09 to 2002-02 |
| Levels | 46 readable | 48 |
| First chunk | PVR loading picture, then `GNRL KADI …` | `LDSC` |
| Classes | 121 bricks / 523 actions | 132 / 627 |

- **Dreamcast-only:** `ControllerConfig`, `TBGrass`, `GDPause`, `MLFLB`, `MLPod`, `TRPlantation`.
- **PS2-only:** mostly PS2 platform code, such as the memory card, shadows, menus and a gallery.
- **Some PS2 additions are newer engine code that Jaws also has:**
  - Also in Sentinels and Jaws: `GDControl` (Jaws' level scripting; ~1,050 placed in Defender PS2), `GDPropControl`, `GDPropColor`.
  - In Defender PS2 and Jaws, but not Sentinels: `GDMultiTexture`, `NAPredatorModel`, `NAModelFade`, `NASubdivide`, `GDPropExtRenderSet`.
  - In Sentinels but not Jaws: `DDTBModel`, `GD3dScaleSprite`, `TBGrid`, `DDClipModel`, `DDRenderTexture`.
- **Field changes:** the PS2 port adds `m_ExtRenderSetting` to several classes (Jaws has it too), and `m_tasknum` for a PS2 task system. Full list: `docs/defender_dc_ps2_field_diff.txt`.

**What this means:** the PS2 port kept the old file format but took in newer engine code. Some classes reached Jaws without passing through the Sentinels files we have. Whether they went from the port to Jaws, or both took them from a shared branch, can't be told.

### `LDSC`: the PS2 loading picture

- Defender PS2's first chunk is a 512×256, 16-bit loading picture. The Dreamcast builds use a PVR picture instead.
- Jaws still has an `LDSC` reader, with a different layout: a list of pictures. No Jaws file uses it.
- So the loading screen was reworked after Defender, then replaced by the loading scenes in `FDIR`.

### A 1999 map header

- Defender PS2's map files `TERKEP/242_PUMP.TKP` and `340HWGEN.TKP` start with `GD-DCK … gyozo … (C) 1999 Appaloosa Multimedia Kft`.
- *Terkep* is Hungarian for "map". *Kft* means a Hungarian limited company.
- `gyozo` is also an exporter name in the Jaws files. Same person, both games.

---

## 6. *Sentinels of the Universe*, 2001 (2.3.2.1)

**In short:** the cancelled Defender sequel, also called *Ecco II*. It is the only version found between Defender and Jaws. Many changes we used to credit to Jaws were already made here. Jaws was made after Sentinels was cancelled, and carried on its code.

### Where the files come from

**1. An Appaloosa Dreamcast dev kit**, supplied by the user and read without running anything:
- **`kat2`:** a recovered dev-kit hard disk, 304 files, 113 of them `.GDE` levels.
  - The `Ecco` folders hold 103 Defender levels (2000-04-15 to 11-09).
  - The `ecco2` folders hold Sentinels.
  - A deleted second partition was also recovered.
- **The Katana disk image** (4.55 GB): 147 version-2.1.12.1 and 5 version-2.3.2.1 files. No "Diesel" string.
- **Four Defender discs** (up to 2000-11-09), 39–50 levels each, all 2.1.12.1.
  - Two of them hold debug and retail program builds; the debug one is junk.
  - **The `144 M` disc and the disk's `Z` folder hold `ECCO.ELF` with full debug symbols:** 12,156 named functions. See `docs/exe_analysis.md` "Ecco: Defender debug symbols".
- **Two Sentinels discs:**
  - Each holds the program `0.BIN` (2001-02-19), 9 levels and a `CONFIG.TXT` that picks the starting level.
  - Disc 1 starts at `000_Title`. Disc 2 starts in `180_Atlantis`.
  - The user's `download-check/Ecco 2 build (1)`/`(2)` archives are identical to these.

**2. The public Feb 19, 2001 prototype disc.** The user supplied it on 2026-11-26; files in `~/Projects/ECCO/ecco2_feb19_proto/`.
- Same program as the dev-kit discs.
- It has older copies of three levels: `100_Atlantis`, `110_Ancient`, `120_Galleon`.
- Its raw 2352-byte sectors must be cut to 2048 bytes (bytes 16–2063 of each) before `gdrom_ls.py` can read them.

### When the version changed

- The earliest Sentinels files (2000-10-24/25) are still 2.1.12.1. Sentinels started from Defender's levels.
- `120_CReef_North` from 2000-12-01 is still 2.1.12.1.
- The 2.3.2.1 files date from 2001-02-16 to 02-21.
- So the version changed between December 2000 and February 2001.

The 2.3.2.1 levels: `000_Title`, `100_Atlantis`, `110_Ancient`, `120_Galleon`, `180_Atlantis`, `211_IceWorld`, `410_HangLand`, `420_HangCaverns`.

### What changed between Feb 16 and Feb 21

- **`110_Ancient`:** same nodes; some meshes and sounds re-exported. The class list gained 14 new classes, none of them placed. So the editor was updated that week.
- **New classes** include `MABelugaHarc` (beluga fight), `MBRemete` (hermit), `MLFokaCtrl` (seal), `MLKutatoAct` (explorer) and `MLCapaSok`.
- **`MLCapaSok`** (*cápa* = shark) is an unused Ecco 2 shark enemy. It has 32 fields for speeds, bite animations, bone bending, damage and health. It is not in Jaws, so it isn't an ancestor of the Jaws shark (`MLSharkCtrl` + `SharkConfig`).
- **`100_Atlantis`:** 31 resources re-exported.
- **`120_Galleon`:** tiny changes. Its `EXTR` entry went from 1 copy to 3 (see below).

### Chunks only in Sentinels

**`EXTR`: a table that finds nodes by name.**
- Layout: a count, then (name, node ID) pairs.
- The only name used is **`SoulContainer`**. The soul-effect code looks it up, takes the node's first child and copies it. Hungarian error messages: "Nem tudok clonozni" = "I can't clone".
- In `120_Galleon` and `410_HangLand` the node is a container holding a soul-effect template: particles, flares, lights and an emitter.
- In other levels the ID is stale: it points at a missing or wrong node.
- `120_Galleon` has the same entry 3 times. The loader adds entries rather than replacing them. So each load and save in the editor probably added a copy (inferred).
- Not in Defender or Jaws.
- Code addresses (Sentinels `0.BIN`):

  | Address | What |
  |---|---|
  | `0x8C0241B8` | Top-level chunk switch |
  | `0x8C03C268` | Adds the pairs to an array on the world object |
  | `0x8C03C1F4` | Looks up a name |
  | `0x8C186424` | Soul effect |

**`Tile`: a 3D grid saying which objects are in each cell.**
- The last chunk of each level. It carries a stamp of 1999-04-29.
- Layout:
  1. grid origin;
  2. cell size (20–80 units);
  3. grid dimensions;
  4. for each cell, a start index into a shared list of node IDs; each run ends with 0.
- Every entry is a scene node ID, mostly models. Only part of each level's models are listed.
- Whether the game used it for drawing or for collision isn't confirmed.
- Example, `420_HangCaverns`: 30×18×11 cells of 30 units, list length 5,132.
- Not in Jaws.

### The damaged dev-kit Atlantis files

- The Feb 21 `100_Atlantis` and `180_Atlantis` on the dev kit are corrupt. They are the same on the disc and on the kit's hard disk.
- In `100_Atlantis`, a 0x158000-byte block of junk sits after the texture `ATLANTIS\A_vf13.TGA` (at 0x80449). The scene tree after it is cut off: only about 395 of ~1,600 nodes are readable.
- `180_Atlantis` has no scene tree at all.
- It looks like a bad copy, not an editor bug. The cause is unknown.
- **The intact Sentinels Atlantis is the Feb 19 prototype's `100_Atlantis`.**
- To read the damaged file anyway, skip 0x158000 bytes at the first non-tag after the `RSRC` children.

---

## 7. *Jaws Unleashed*, 2006 (2.6.3.16)

**Background:** Jaws was developed under the working title *Sole Predator*. It was shown as a tech demo in 2004 while Appaloosa looked for a publisher; Majesco then took on the Jaws licence, and it shipped in 2006.

**In short:** Jaws' loader still contains code for older file versions. Those checks date the format changes between 2001 and 2006.

### Version checks in the loader

- `Jaws.exe` keeps the version as one number, one byte per part: 2.6.3.16 = `0x02060310`.
- It compares the version in 30 places. The PS2 Jaws program has the same checks. The Ecco programs have none.

| Version | What changes | Code |
|---|---|---|
| after 2.5.7.12 | Every value is aligned to its own size. Older files are packed inside chunks. | about 25 read helpers |
| after 2.5.12.6 | `RSRC` starts with a header. Each resource gets an ID and flags: enabled, language, engine. | `0x6ECE40` → `0x6ECBB0` |
| before 2.6.1.17 | Rejected: "Export version (%d) too old. (2.6.1.17 required)" | `GDLoadGame` `0x693180` |

All shipped files are 2.6.3.16, so the code for older versions is never used. It's what tells us when those changes came in.

### The file header and footer

- **`FSIZ`** (file size) is passed to a loading-progress function that is empty in the retail game.
- **`FDIR`** has its own stamp, 2005-07-07. It lists up to 5 loading-scene archives stored after the end of the file.
- `FSIZ` and `FDIR` are read by a separate handler (`0x6C3D90`).
- **`VERS` and `EXBY` are never read.**
- The header reader calls the format a "Game Designer file". Whether `GDED` stands for "Game Designer" isn't stated anywhere.

### `EXBY`: who exported each level

`EXBY` holds the login name of the person who exported the file.

| Login | PC files | PS2 files |
|---|---|---|
| `jts` | AQUARIUM, ARMADA, BEACH, BEACHPST, DOCKS, KATATAMA, OPEN_*, START, TITLE, TITLE0 | — |
| `gyozo` | DEEPSEA, DEEPSEA2, FISH, GAUNTLET, MINEMSHA, TOWN, WRACK | — |
| `martens` | CHASE | KATATAMA, TITLE, TITLE0 |
| `balage` | — | AQUA2, AQUARIUM, OPEN_NE, OPEN_NW, TOWN |
| `Zolcsika` | — | ARMADA, BEACH, BEACHPST, CHASE, DEEPSEA, DEEPSEA2 |
| `SAN` | — | DOCKS, MINEMSHA, START, START2 |
| `Neszta` | — | FISH, GAUNTLET, WRACK |
| `AnChoR` | — | OPEN_S |

**Matched against the published credits:**
- `jts` = **Tamás Jutasi**, a Jaws programmer. Defender's US credits print "Tamás Jutasi 'JTS'". Confirmed.
- `Neszta` = **Neszta Volkai**, a Jaws level designer.
- `SAN` is probably Sándor Mezei, a level designer on Jaws, Defender and PS1 *Wacky Races*. Unconfirmed.
- `balage` and `Zolcsika` each fit more than one credited name.
- `gyozo`, `martens` and `AnChoR` match nobody credited.

---

## 8. Classes and fields across the games

### Class counts

Counted over all levels of each game.

| | Defender (89 levels) | Sentinels (8) | Jaws (20) |
|---|---|---|---|
| Brick classes | 138 | 116 | 311 |
| Action classes | 708 | 382 | 484 |
| Primitive classes | 9 | 9 | 19 |
| Property classes | 46 | 41 | 60 |

56 brick and 78 action classes are in all three.

### New in Sentinels, kept in Jaws

None of these are in Defender:
- **The whole skeleton system:** `XBone`, `XSkeletonModel`, `XExtendedSkeletonModel`, `XAnimation`, `XAnimationSet`. Unchanged from Sentinels to Jaws.
- **`MLHalRaj3`**, Jaws' fish school. It is already placed once in Sentinels' `420_HangCaverns`. So the rewrite of Ecco's fish school was done for Sentinels, not Jaws.
- Other bricks: `MLEnemy`, `MLArea`, `NAHair`, `MBCsik`, `GDExtendedLight`, `GDSphereSector`.
- 28 actions, including `NAGenerator`, `NARubberSkeleton`, `NACollisionDetector`, `GDRelocator`, `MLFogAct`.
- Property classes: `MLPropBoxArray`, `MLPropPointArray`, `MLPropSectionArray`.

### Sentinels' `SharkCtrl` is not the Jaws shark

- Every Sentinels level lists a `SharkCtrl` class, along with Xbox and network-play classes. None are placed or in the Sentinels program. The class lists show the editor's full registry, which held more than the game.
- `SharkCtrl`'s 25 fields are dolphin-style jump and charge physics, like Ecco's `DolphConfig`. Probably for a shark form of Ecco.
- No Jaws class shares even 3 field names with it. Jaws' shark is `MLSharkCtrl` plus `SharkConfig` (445 fields).

### The field table and `PROP` IDs

- The last part of `CLAS`, `PRIM`, lists every (field, class) pair.
- **A `PROP` ID is `0x08000000` plus an index into this table.** So each level carries its own dictionary of field names.
- Examples: `0x080017D8` = `GDBrick.m_Name`; `0x08001873` = `GDModel.m_3dModelID`.
- Sizes: Defender 4,546; Sentinels 3,921; Jaws 6,662.
- 19 of the 20 Jaws levels have the same table. `TITLE0` differs from entry 979 on, so tools with fixed `PROP` IDs only work on the other 19.
- Every ID is named in `docs/scene_graph.md`.

### Field changes

Full list: `docs/lineage_field_diff.txt`.

| Class | Defender → Sentinels | Sentinels → Jaws |
|---|---|---|
| `GDBrick` | +`m_WireColor`; −`m_Color`, `m_Difficulty`, `m_Time` | +`m_Viewport`, `m_ExecFilter`, `m_CameraFilter`, `m_RoomMask`, and others |
| `GDModel` | −`m_ColiListID`, `m_ColliGroup`, `m_LodModelID` | +`m_ChannelSetting`, `m_ExtRenderSetting`, `m_ModelColor` |
| `GDSkeletonModel` | +`m_nMorphKeyNum`, `m_nSkelKeyNum` | +`m_EditorKeyNum` |
| `GDLoad` | — | +`m_Async`, `m_Progress`, …: loading in the background with a progress screen |
| `GDCamera` | — | −`m_WaterLevel` |
| `GDReference` | — | +`m_Addons` |
| `GDControl` | unchanged | +`Separator01`–`09` (editor layout only) |
| `MLHalRaj` | +`mincolor`, `maxcolor` | — |
| `TRSplash` | −`m_Sound1`–`3` | — |
| `DDGameState` | 18 Ecco fields → 3 | → 5 Jaws fields |
| `NAWhirl2000` | — | `m_noecco` → `m_noshark` |
| `MLHalRaj3` | new (29 fields) | +`m_aramspeed`, `m_fearspeed` |

**What this shows:**
- Most of the edits we had credited to Jaws were made in Sentinels.
- Only the `NAWhirl2000` rename and the second `DDGameState` rewrite are from the Jaws era.

**Correction (2026-11-26):** `m_ExtRenderSetting` was never in Defender Dreamcast. The PS2 port added it, and Jaws has it, so Sentinels didn't remove it.

---

## 9. Other games checked

None of these used GWB.

| Game | Result |
|---|---|
| *C: The Contra Adventure* (PS1, 1998) | No GWB trace at all |
| *Wacky Races* (PS1, Appaloosa, 2000) | Not GWB, but uses GWB's resource names |
| *Wacky Races* (Dreamcast, Infogrames) | Not GWB; a different studio |
| *Ecco* "Jun 9, 2007 prototype" (Xbox 360) | Not GWB; an emulated 1992 Mega Drive game |

### *C: The Contra Adventure* (1998)

Checked as a possible GWB 1.x.
- No `GDED`, no GWB chunk tags, no GWB class or resource names, no 1998 GWB date stamps.
- Levels use their own format: `DATA/CDI`, `POS`, `PRE`, `SND/*.SGG`, and more.
- Appaloosa traces: an "Appaloosa Staff" credit, and Hungarian level names such as `ALAGUT` (*alagút* = tunnel).
- **Conclusion:** GWB's formats were being designed in 1998, alongside Contra, but Contra didn't use them. No GWB 1.x has been found.

### Appaloosa's *Wacky Races* (PS1, 2000)

- PAL `SLES_024.68`; files dated 2000-06 to 08-30.
- No `GDED`, no GWB classes, no scene tree.
- **But its data uses GWB's resource conventions.** References are written as type tag + ID, like GWB's `['GTEX'][id]`, with GWB's type names: `GMAT`, `GTEX`, `GMDL`, `GSMP`.
- Every track file starts with `FIMW00.1` and a date stamp, 2000-07-10, in GWB's style.
- The credits list a Hungarian team and a separate "Development tools" credit.
- **Most likely a sibling, not an early GWB.** It is a separate PS1 engine fed by Appaloosa's shared asset tools. Its data is later than Defender's 2.1.12.1, and it has none of GWB's core parts.

### Infogrames' *Wacky Races* (Dreamcast, 2000)

- Made by Infogrames Sheffield, with an all-UK staff.
- Levels are `.NWB` files with embedded PVR textures, a different format.
- No `GDED`, no Appaloosa, GWB or Diesel strings.
- The only shared file is Sega's standard sound driver, which tells us nothing.

### *Ecco the Dolphin* "Jun 9, 2007 prototype" (Xbox 360)

- The Xbox Live Arcade *SEGA Vintage Collection* release of the 1992 Mega Drive game, made by Digital Eclipse.
- Its contents are an emulator, ROM data, XMA music and "how to play" pictures.
- No GWB, no Novotrade or Appaloosa.

### Cancelled Appaloosa projects

Mermaid tech demo (2001), Parrot demo (design only), *Smurfs* (2002, PS2).
- No files are public.
- Defender's US master already lists `MBMermaid` (mid-2000), so the mermaid project was in GWB by then.
- *Smurfs* shows no visible GWB link on video.
- Details: `docs/ecco_leftovers.md` §11 "Cancelled Appaloosa projects and the Smurfs video".

---

## 10. After Jaws

- Appaloosa closed. The same Budapest team carried on as **Twofish.hu**.
- Their first game, ***EdgeRacers***, was finished but shelved. Its engine is unknown. It is the most likely game to use GWB after Jaws.
- ***SmartyAnts*** (2010) was probably built on GarageGames' **Torque** engine. Its installer was built in `c:\Torque\anttools\`.
- **So GWB / Diesel Power ended with Jaws or with *EdgeRacers*.**

Details and sources (an interview with Ed Annunziata; the installers): `docs/ecco_leftovers.md` "After Appaloosa: Twofish.hu".

---

## 11. An unproven idea: version numbers as dates

**The user doubts this. Treat it as a coincidence, not as evidence.** Nothing else in this doc relies on it.

The observation: from 2.5 on, the last three numbers read like year.month.day, and three of them sit close to date stamps in the same files.

| Version | Read as a date | Nearby stamp |
|---|---|---|
| 2.5.7.12 | 2005-07-12 | `FDIR` 2005-07-07, five days earlier |
| 2.5.12.6 | 2005-12-06 | `GMDL` 2005-12-05 and `RSRC` 2005-12-08; this version's check is the `RSRC` header |
| 2.6.3.16 | 2006-03-16 | PS2-only stamp 2006-03-16 |

- For the Ecco versions, the last two numbers could still be month.day: 2.3.2.1 = 1 February, before the Sentinels files of mid-February.
- But the second number doesn't fit a year there, so the date reading only holds from 2.5 on.

---

## 12. Tools

All read-only. Run them with `python3 -I`.

- **`scripts/gdrom_ls.py DISC_DIR [--extract OUT REGEX]`** lists a GD-ROM dump, with file dates and each level's version.
- **`scripts/gded_lineage.py`** compares GWB files:
  - `info`: version, top-level chunks, class-table sizes.
  - `compare A=GLOB B=GLOB …`: which classes groups of files share. Add `@VER` to pick a version.
  - `fields`: per-class field differences. It produced `docs/lineage_field_diff.txt`.
  - `prop FILE ID…`: names `PROP` IDs from that file's own table.
  - `placed FILE [CLASS…]`: roughly how many of each class are placed.
- **`scripts/sh4_asserts.py`** and **`scripts/ecco1999_match.py`**: for the 1999 program (section 4).

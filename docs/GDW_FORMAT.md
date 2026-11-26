# GDW Format — Research Reference

Consolidated findings on the `.GDW` archive format used by *Jaws Unleashed* (PC, 2006, Appaloosa Interactive). This document covers everything confirmed, suspected, and ruled out about the format and its asset extraction pipeline.

> **Note (2026-07-17):** this snapshot dates from June 2025 and predates many later corrections. `/CLAUDE.md` at the project root is now the actively-maintained, current source of truth — cross-check findings there before trusting anything below that looks uncertain or contradicts it. Several stale claims below have been annotated in place; others may remain.

---

## Overview

`.GDW` files are the primary world/level container format for Jaws Unleashed. Each file corresponds to a game level and contains all assets that level uses — textures, serialized gameplay objects, reflection metadata, audio references, and likely geometry. There is significant texture reuse between levels.

Known level files:

| File | Level |
|---|---|
| `FISH.GDW` | Fisherman's Isle |
| `BEACH.GDW` / `BEACHPST.GDW` | Beach |
| `DOCKS.GDW` | Docks |
| `TOWN.GDW` | Town |
| `OPEN_S.GDW` / `OPEN_NE.GDW` / `OPEN_NW.GDW` | Open ocean zones |
| `DEEPSEA.GDW` / `DEEPSEA2.GDW` | Deep sea |
| `MINEMSHA.GDW` | Grand Occasus Canals (SC15 "Up a Creek") — identified 2026-08-12, see `mission_system.md`; "Menemsha" is just the internal dev filename |
| `AQUARIUM.GDW` | Aquarium |
| `ARMADA.GDW` | Armada |
| `CHASE.GDW` | Chase |
| `GAUNTLET.GDW` | Gauntlet |
| `KATATAMA.GDW` | Katatama |
| `WRACK.GDW` | Wrack |
| `START.GDW` | Start/hub |
| `TITLE.GDW` / `TITLE0.GDW` | Title screen |

**Special files:**
- `TITLE0.GDW` — not a level. Contains the full engine class registry and title screen model references. No extractable textures. Useful as a reference for the complete class list.
- `OPEN_S.GDW` / `OPEN_NE.GDW` / `OPEN_NW.GDW` — open ocean zones. Much larger (337–432MB vs ~120–150MB for regular levels) due to `NATerrain` and `NAWater2004` data. Internally structured differently — the unusual repeating chunk tags (`HHHH`, `TTDT`, `DTTD`, `XXHX` etc.) were guessed here as terrain/water grid data. **Flagged as needing re-verification (2026-07-17), not confirmed either way this session:** CLAUDE.md later established (2025-06-29) that ALL static terrain/rocks/water-planes/dock geometry is present as regular named `BRTR` mesh instances with no separate BSP/heightmap container — it's unclear whether that finding is in tension with this HHHH/TTDT claim (e.g. these tags could be a real but separate open-world-only LOD/streaming system unrelated to the base terrain mesh instances) or whether this claim was simply wrong. Not independently re-checked.
- `_FISH.GDE` — from the **North American PlayStation 2 release**. Produced by the engine's built-in `PS2ExportSettings` pipeline. Likely transformed for PS2 hardware and may not be directly parseable with the same tools as the PC `.GDW` files.

---

## Engine lineage: Game World Builder, shared with *Ecco the Dolphin: Defender of the Future* (confirmed 2026-10-11)

**Credit where it's due:** the user said from the start that *Jaws Unleashed* was made with the same editor as Appaloosa's *Ecco the Dolphin: Defender of the Future*. Claude was hesitant at first and called the claim unverified, since nothing in the Jaws files names the tool. The user then supplied the evidence below, and the comparison proved them right.

**Editor vs. engine (user information, 2026-11-24):** two separate in-house Appaloosa tools. **Game World Builder** is the editor used to build the world environments (the levels this format stores). The runtime game engine is called **Diesel Power**, a custom engine. **Source:** the back cover of the European (PAL) Dreamcast release of *Ecco the Dolphin: Defender of the Future* (© Sega Enterprises 2000, catalogue MK-51033-50) reads: "GameWorld Builder™ Software Technology & Diesel Power™ Game Engine are the property of Appaloosa Interactive Corp" (scan supplied by the user, 2026-11-24; copy in [`docs/sources/Ecco_Defender_Dreamcast_PAL_back_cover.png`](sources/Ecco_Defender_Dreamcast_PAL_back_cover.png)). Both names are trademarks there, and the wording itself separates the two: GWB is the "software technology" (tool suite), Diesel Power the "game engine". The cover is Ecco's, from 2000; that Jaws (2006) still runs on Diesel Power is an inference from the shared codebase (62 Ecco classes, same `GDED` format), since the name appears nowhere in `Jaws.exe`, the PS2 exe, any GDW or the 2001 press kit (searched 2026-11-24), and Jaws' own credits don't name either tool. Name clash to keep in mind when searching: GRIN's unrelated Swedish engine was also called "Diesel". In these docs, "the engine" means Diesel Power, and the `GDED` file format is the GWB output it loads.

**The tool:** Appaloosa's own PS2 press information kit (September 2001; copy in [`docs/sources/Appaloosa_PS2_press_information_2001-09.pdf`](sources/Appaloosa_PS2_press_information_2001-09.pdf), from [Sega Retro](https://segaretro.org/images/8/86/PS2PressInformation_2001-09_Ecco_Appaloosa_info.pdf); this PDF was exported from Word in January 2020, author field "Csaba Soltesz") describes the **Game World Builder™ ("GWB") 3D tool suite**, in development since early 1999 for *Ecco the Dolphin* on Dreamcast and ported, with all of Ecco's levels, to PS2 in under three months. *Defender of the Future*'s credits name GWB; *Jaws Unleashed*'s credits don't. The press kit's description of GWB matches the Jaws format closely:

| Press kit (2001) | *Jaws Unleashed* data |
|---|---|
| "built around standard **bricks** (objects)" | `BRTR` (brick tree), `CHBR` (child brick), `GDBrick` / `GDStdBrick` |
| "**actions** (procedures)" | `ACTN` blocks (`GDControl`, quests, …) |
| "**resources** (meshes, textures, sfx, collision data)" | `RSRC`: `GMDL`, `GTEX`, `GSMP`, `MREG` |
| "type classes" with a `GD` prefix (GDReal, GDVect, GDMatrix, GDAngle) | engine-wide `GD` classes (`GDModel`, `GDControl`, `GDPath`, …) |
| exporters convert textures to console formats and meshes into triangle strips | PS2 `.GDE`: native GS textures, `STRP` triangle strips |

**Span of the toolset (summary, 2026-11-26):** GWB's own format stamps start in 1998; every *Defender* build (Jan 2000–2002) is 2.1.12.1, *Sentinels* (Feb 2001) 2.3.2.1, *Jaws* (2006) 2.6.3.16. Appaloosa's *Contra* (1998) has no GWB, its PS1 *Wacky Races* (2000) only GWB resource tags. Cancelled projects in between (Mermaid demo 2001, *Smurfs* 2002) have no public files. After Appaloosa, the Twofish team's *SmartyAnts* (2010) was probably built on GarageGames' Torque, so Jaws may be the last GWB / Diesel Power game. Details in "Format history 2001–2006" and the title entries after it, and `docs/ecco_leftovers.md`.

The literal strings "GWB" / "Game World Builder" and those four type names don't occur in the Jaws files (a few "GWB" byte matches are random bytes inside pixel data), so the identification rests on the format below, not on a name.

**The proof: Defender's PS2 level files are the same format.** The *Defender of the Future* PS2 disc stores its levels as `.GDE` files too (e.g. `DATA/110L_BAY.GDE`, 20 MB). Checked read-only:

| | Defender PS2 `110L_BAY.GDE` | Jaws PS2 `FISH.GDE` |
|---|---|---|
| Preamble | `GDED BINARY FORMAT, VERSION 2.1.12.1` | `GDED BINARY FORMAT, VERSION 2.6.3.16` |
| Top-level chunks | `LDSC` `GNRL` `WDIM` `RSPR` `CLAS` `RSRC` `BRTR` `SCRT` | `FSIZ` `VERS` `EXBY` `GNRL` `WDIM` `RSPR` `CLAS` `RSRC` `BNCH` `BRTR` `SCRT` `SKIP` `FDIR` `ENDF` |
| Class tables | `CLAS` with `BRCM` + `ACCM` | same |
| Scene tree | `CHBR` ×2,896, `PRPS` ×4,033, `PROP` ×54,821 | same structure |
| Actions / resources | `ACTN` ×811, `GMDL` ×1,611, `GTEX` ×1,216, `MREG` ×412, `STRP` ×513 | same tags |
| Engine classes | `GDModel`, `GDControl`, `GDBrick`, `GDStdBrick`, `GDPath`, `GDLight` | same names |

The differences fit an older version of the same tool. Defender's chunks are packed (no 4-byte padding; its first chunk starts at `0x29`, straight after the preamble's line breaks). It opens with `LDSC` where Jaws has `FSIZ`/`VERS`/`EXBY`. It has no `SKIP`/`FDIR`/`ENDF` footer (the part Jaws uses for embedded loading-screen archives) and no `GSMP` audio in that file. **Conclusion: *Jaws Unleashed* was built with Game World Builder, the same tool suite as *Defender of the Future*, about five years and several versions later (2.1.12.1 → 2.6.3.16).**

**Lead (noted 2026-10-11), followed up 2026-11-25:** [Hidden Palace](https://hiddenpalace.org/Ecco_the_Dolphin:_Defender_of_the_Future_(Feb_17,_2000_prototype)) hosts a *Defender of the Future* Dreamcast prototype dated 17 February 2000. Every Defender build checked since is still 2.1.12.1 (see the version table below). The missing link turned out to be a different game: see the next section.

### Format versions across Appaloosa builds (checked 2026-11-25)

Source: an Appaloosa Dreamcast development-kit dump supplied by the user (a Katana dev-kit hard-disk image, its `kat2` folder tree, four *Defender* GD-ROM builds and two *Sentinels of the Universe* GD-ROM builds), plus the Defender Dreamcast/PS2 and Jaws data already on hand. Everything was read only; nothing from the kit was run.

| Game / build | File dates | `GDED` version | Chunk padding |
|---|---|---|---|
| *Ecco: Defender of the Future*, Dreamcast dev-kit builds and prototypes | 1999-09 to 2000-11 | **2.1.12.1** (every one of ~300 level files) | packed |
| *Ecco: Defender of the Future*, PS2 US release | 2001 | **2.1.12.1** | packed |
| ***Ecco the Dolphin: Sentinels of the Universe*** (cancelled Defender sequel, user-identified), Dreamcast dev-kit discs and folders | 2001-02-16 to 2001-02-21 | **2.3.2.1** | **4-byte padded** |
| *Jaws Unleashed*, PC and PS2 | 2006 | **2.6.3.16** | 4-byte padded |

- **The dev kit (inventory, 2026-11-25):**
  - **`kat2`** is a recovered Katana dev-kit hard disk, 304 files. 113 are `.GDE` levels; the rest are `.KAT` (71), `.AFS` (38), `.DAT` (20), `.INP` (18), `.VDS`, `.ADX`, `.PVR`, `.ELF` and others. The recoverer's note says `?` in names became `$`, and that a second, deleted partition was recovered, holding deleted `ECCO` and `ecco2` folders.
  - **`Ecco` folders:** 101 + 2 Defender levels, dated 2000-04-15 to 2000-11-09.
  - **`ecco2` folders (Sentinels):** the earliest files are 4 levels (`120_CReef_North`, `180_Atlantis`, plus `.Id_NN` duplicates) dated **2000-10-24/25**, still 2.1.12.1, i.e. Sentinels started on Defender's levels and format. Then `120_CReef_North` 2000-12-01 (2.1.12.1), then the 2.3.2.1 levels of 2001-02-16 to 2001-02-21.
  - **The two Sentinels discs** each hold `0.BIN` (the program, 2001-02-19), the 9 levels, `AUDIO64.DRV`, `DSP.FPB`, `DUMMY.DAT` and a `CONFIG.TXT` that picks the boot level (`#start` / `#gameover` / `#loader` / `#levels` sections). Disc 1 boots `000_Title`; disc 2 boots straight into `180_Atlantis`, its older 2.1.12.1 copy. The dev-kit folders have the same `config.txt` files.
  - **The four Defender discs** (dated up to 2000-06-05 and 2000-11-09) hold 39–50 levels each, all 2.1.12.1. Two have separate `/DEBUGBIN/0.BIN` and `/RETAILBIN/0.BIN` program builds (2000-04-17 / 2000-06-01). The `DEBUGBIN` build turned out to be cross-linked junk (512 KB of code + level data). **The `144 M` disc and the hard disk's `Z` folder carry an unstripped `ECCO.ELF` with `0.MAP`: 12,156 named functions and DWARF v1 class layouts** (2026-11-25, `docs/exe_analysis.md` "Ecco: Defender debug symbols").
  - **The Katana disk image** (4.55 GB, two partitions) has 147 `GDED` 2.1.12.1 and 5 2.3.2.1 preambles and no "Diesel" string.
- **`Appaloosa Multimedia Kft`:** the Ecco *Defender* PS2 map files `TERKEP/242_PUMP.TKP` and `340HWGEN.TKP` contain the header `GD-DCK … gyozo … (C) 1999 Appaloosa Multimedia Kft` (*Kft* = Hungarian limited company; "gyozo" is probably a person's name). *Terkep* is Hungarian for "map".
- **Timeline (user context, 2026-11-25):** *Jaws Unleashed* was made after *Sentinels of the Universe* was cancelled. With the data below, that means Appaloosa carried the cancelled sequel's code line (format 2.3, skeleton system, `MLHalRaj3`, the reworked Ecco classes) into Jaws, rather than going back to the shipped *Defender* code. The cancellation date isn't recorded here; the latest Sentinels files on hand are from 2001-02-21.
- **Sentinels is the only intermediate version found.** Its 2.3.2.1 levels (`000_Title`, `100_Atlantis`, `110_Ancient`, `120_Galleon`, `180_Atlantis`, `211_IceWorld`, `410_HangLand`, `420_HangCaverns`) sit between Defender and Jaws. Some levels on the same discs are still 2.1.12.1 (`120_CReef_North` from 2000-12, and an older `180_Atlantis` on the second disc), so the version change can be dated to between December 2000 and February 2001.
- **2.3 already has Jaws' 4-byte chunk padding**; 2.1 is packed. The class-name lists inside `CLAS` (`BRCM`/`ACCM`) are still packed in 2.3, though, while Jaws pads those too.
- **Top level** (see also "Format history 2001–2006" below for when Jaws' additions arrived)**:** Defender DC has `GNRL KADI WDIM RSPR CLAS RSRC BRTR SCRT` and Defender PS2 has `LDSC GNRL …`. Sentinels has `GNRL WDIM RSPR CLAS RSRC BRTR SCRT EXTR` followed by one `Tile` chunk at the very end. Jaws adds `FSIZ VERS EXBY` in front and `SKIP FDIR ENDF` behind, and has neither `EXTR` nor `Tile`. So the size/version header and the embedded-archive footer came after February 2001. Dreamcast builds of both Ecco games put a 0x40018-byte PVR loading image (`TITL`/`TSCR`) before the `GDED` preamble.
- **Sentinels-only chunks (2026-11-25):**
  - **`EXTR` = a named-reference table: name → `BRTR` node ID (decoded 2026-11-26).** Layout: `uint32` count + count × (`uint32` length + string, `uint32` node ID). The Sentinels loader (`0.BIN` `0x8C0241B8`, the top-level chunk switch) passes it to `0x8C03C268`, which *appends* the pairs to an array on the world object (`+0xD2E8` array, `+0xD2E4` count; freed by `0x8C03C18C` when the world resets). `0x8C03C1F4` looks a name up and returns its node ID. The only name ever used is **`SoulContainer`**: the soul effect code (`0x8C186424`, called from several places, not traced further) looks it up, takes that node's first child and clones it (failure messages "Nem tudok clonozni" = "I can't clone", "Nem megy a clonozas2" = "cloning fails 2"). In `120_Galleon` (node 140) and `410_HangLand` (node 1635) the target is a `GDContainer` holding the template: a `GDStdBrick` with the `EnemySoul` action, an `NAParticle2000` (`Bubble.tga`), three `NAFlare`s (`Sprites\ray.tga`), two `GDLight`s, a `TREmitterBox`/`TREmitter` and a `TR3dSprite`. So `EXTR` lets code find a template node by name instead of by a hard-coded ID. Contents per level: `000_Title` `SoulContainer`→140 (no such node, stale), `100_Atlantis` →791 (no such node), `120_Galleon` the same entry **three times**, `211_IceWorld` →140 (a `GDModel` ice sign `JEGBBtabla01`, stale), `410_HangLand` →1635, `110_Ancient` and `420_HangCaverns` empty. The duplicates and stale IDs suggest the editor kept the entry when levels were copied and didn't update it. (Correction: older notes said `EXTR` was empty in most levels.) `EXTR` exists only in Sentinels: Defender's `ECCO.ELF`, `Jaws.exe`, the Jaws PS2 exe and all Jaws files have neither the tag nor `SoulContainer`.
  - **`Tile` = a uniform 3D spatial grid of scene models (decoded 2026-11-25).** Mixed-case tag, the last chunk of each 2.3.2.1 level that has a `BRTR`, one per file, not padded. Layout: `uint32` stamp `0x0131079D` (= 19990429, a date like the Jaws block stamps), `float[3]` grid origin, `float[3]` cell size (20–80 units), `uint32` nx, ny, nz, `uint32` list length L, then nx·ny·nz `uint32` cells, then L `uint32` list entries. Each cell is an index into the list, where a 0-terminated run of entries starts; cells can point into another cell's run (shared tails), and every run ends cleanly. Sizes match exactly in all 6 levels (e.g. `420_HangCaverns`: 30×18×11 cells of 30 units from (−200, −300, −250), L = 5,132, 44 + 23,760 + 20,528 = 44,332 bytes). **Every list entry is a `BRTR` node ID** (100% in all 5 non-empty levels): mostly `GDModel` and `MLEnvModel`, plus a few `GDStdBrick`, `GDMovingModel`, `GDLight` and `TRGift` nodes, and only a subset of each level's models (e.g. 433 of ~2,550). So it says which objects occupy each cell; whether the game used it for draw culling or collision lookup isn't confirmed. `000_Title` has an empty grid (L = 0). Jaws has no `Tile` chunk.
- **Sentinels quirk:** in the two Atlantis files that carry the PVR loading image (`100_Atlantis`, `180_Atlantis` on disc 1), the `RSRC` size field is exactly 0x158000 bytes short. Resources (`GMDL`, `GMAT`, `MREG`) continue past it up to `BRTR`, so a walker stops after `RSRC`; cause unknown.
- **Class tables (union over all levels of each game):**

| | Defender (89 levels) | Sentinels (8) | Jaws (20) |
|---|---|---|---|
| Brick classes (`BRCM`) | 138 | 116 | 311 |
| Action classes (`ACCM`) | 708 | 382 | 484 |
| Primitive classes (`CPCM`) | 9 | 9 | 19 |
| Property classes (`PRCM`) | 46 | 41 | 60 |

  56 brick classes and 78 action classes are in all three. **Classes that first appear in Sentinels and survive into Jaws** (none of them are in Defender):
  - bricks: the whole skeleton system (`XBone`, `XSkeletonModel`, `XExtendedSkeletonModel`, `XAnimation`, `XAnimationSet`), `MLHalRaj3`, `MLEnemy`, `MLArea`/`MLArea2`, `NAHair`, `MBCsik`, `GDExtendedLight`, `GDSphereSector`;
  - actions: `NAGenerator`, `NARubberSkeleton`, `NAHairTurbulence`, `NACollisionDetector`, `NAModifyColliGroups`, `NAParticleSplash`, `GDRelocator`, `MLFogAct`, `MLEnvAct`, `MBFadeAct`, `PModelDistFade`, `PExplosion`, `PTimer` and others (28 in all);
  - property classes: `MLPropBoxArray`, `MLPropPointArray`, `MLPropSectionArray`.
- **The shark-fish-school link:** `MLHalRaj3`, Jaws' shipped fish school, which `docs/ecco_leftovers.md` had called Jaws-only, is already placed once in Sentinels' `420_HangCaverns`. So the rewrite of Ecco's `MLHalRaj` happened for Sentinels in 2000–2001, not for Jaws. Also placed in Sentinels: `NARubberSkeleton` (13), `MLEnemy` (9), `NAGenerator` (9).
- **Sentinels already lists a `SharkCtrl` action class** in every 2.3.2.1 level's class table, along with `GDXBoxWorld` and network-play classes (`LoNetGame`, `PushBallNetServer`, …). None of these are placed, and their names don't occur in the Sentinels executable `0.BIN` (74 of its 548 listed classes are missing from `0.BIN`). So the class tables reflect the editor's class registry, which held more than that Dreamcast game build. `SharkCtrl` is not Jaws' `MLSharkCtrl` by name, and nothing links the two beyond the name.
- **`CLAS` `PRIM` = the field table; `PROP` IDs index it (found 2026-11-25).** The last sub-chunk of `CLAS`, `PRIM` (not the per-node collision `PRIM`), is `uint32` count + count × (field name, class name) strings (packed up to 2.3, padded in 2.6). **A `PROP` ID is `0x08000000 | index` into this table**, so every level carries its own dictionary of property names: `0x080017D8` = `GDBrick.m_Name`, `0x080017DA` = `GDBrick.mtx`, `0x08001873` = `GDModel.m_3dModelID`, `0x080018D8` = `GDPrimRegions.regions`. This names every previously unknown ID (see `docs/scene_graph.md`). Sizes: Defender 4,546 entries (120 North), Sentinels 3,921 (420 HangCaverns), Jaws 6,662. **19 of the 20 Jaws levels have the identical table; `TITLE0` has 6,657 entries and only its first 979 match**, so its `PROP` IDs mean different fields from index 979 on. Tools that hard-code `PROP` IDs are only valid for the 19 matching levels.
- **Field-level diff (2026-11-25; full list in `docs/lineage_field_diff.txt`):** union over all levels, Defender 769 classes / 6,106 fields, Sentinels 455 / 4,101, Jaws 714 / 6,662. 125 classes are in all three; 69 of those have identical fields. Notable changes:

| Class | Defender → Sentinels | Sentinels → Jaws |
|---|---|---|
| `GDBrick` | +`m_WireColor`; −`m_Color`, `m_Difficulty`, `m_Time` | +`m_Viewport`, `m_ExecFilter`, `m_CameraFilter`, `m_CreatorDistance`, `m_GenMapBound`, `m_RoomMask`, `m_ExportFilter` |
| `GDModel` | −`m_ColiListID`, `m_ColliGroup`, `m_LodModelID` (and `m_ExtRenderSetting`, see note) | +`m_ChannelSetting`, `m_ExtRenderSetting`, `m_ModelColor` |
| `GDSkeletonModel` | +`m_nMorphKeyNum`, `m_nSkelKeyNum` | +`m_EditorKeyNum` |
| `GDLoad` | — | +`m_Async`, `m_Progress`, `m_idLoader`, `m_idProgressOver` (async loading with a progress screen) |
| `GDCamera` | — | −`m_WaterLevel` |
| `GDReference` | — | +`m_Addons` |
| `GDControl` | unchanged (17) | +`Separator01`–`09` (editor layout only) |
| `MLHalRaj` | **+`mincolor`, `maxcolor`** | — |
| `TRSplash` | **−`m_Sound1`–`3`** | — |
| `DDGameState` | **18 Ecco fields → 3** (`m_fustemit`, `m_monocam`, `m_sidecam`) | → 5 (`m_angry`, `m_csonakdied`, `m_darabnum`, `m_enemyrange`, `m_koteldied`) |
| `NAWhirl2000` | — | **`m_noecco` → `m_noshark`** |
| `MLHalRaj3` | (new in Sentinels, 29 fields) | +`m_aramspeed`, `m_fearspeed` (31) |

  **Correction (2026-11-26):** the "Defender" column merged Dreamcast and PS2. Split by platform, `m_ExtRenderSetting` is **not** in Defender Dreamcast at all; the PS2 port added it (to `GDModel`, `GD3dSprite`, `NAGlowAct`, `NARingAct`, with the property class `GDPropExtRenderSet`), and Jaws has it. So Sentinels didn't remove it; it's a PS2-port / Jaws feature. `m_ColiListID`, `m_ColliGroup`, `m_LodModelID` are in both Defender versions and were really dropped by Sentinels. See "Defender: retail Dreamcast vs PS2" and `docs/defender_dc_ps2_field_diff.txt`.
  So most edits that `docs/ecco_leftovers.md` had put in Jaws already happened in Sentinels; only `NAWhirl2000`'s switch and the second `DDGameState` rewrite are Jaws-era. The skeleton classes (`XBone`, `XExtendedSkeletonModel`, …) are unchanged from Sentinels to Jaws.
- **Sentinels' `SharkCtrl` is not the Jaws shark.** Its 25 fields are dolphin-style jump and charge physics (`m_aJumpVertSpeed`, `m_rChargeAccelRatio`, `m_rGravity`, `m_rWaterDrag`, …) plus `m_idMorph` and `m_idSplash`, mirroring Sentinels' `DolphConfig`. No Jaws class shares even 3 field names with it. Jaws' shark is `MLSharkCtrl` (one field, `m_cfg`) plus `SharkConfig` (445 fields). So it's likely an Ecco-side controller (for example for a shark morph), unrelated to Jaws' shark despite the name.
- **Tools (2026-11-25):** `scripts/gdrom_ls.py DISC_DIR [--extract OUT REGEX]` lists a GD-ROM dump (`disc.gdi` + `.iso` tracks) with file dates and each `.GDE`'s version. `scripts/gded_lineage.py` has five commands: `info` (version, top-level chunks, class-table sizes), `compare A=GLOB[,GLOB][@VER] B=…` (class-name overlaps between groups; the table above is `Def=<Defender DC + PS2>`, `Sent=<Sentinels>@2.3`, `Jaws=GAME_GDWs/*.GDW`), `fields` (same group syntax; per-class field diff, produced `docs/lineage_field_diff.txt`), `prop FILE ID…` (name `PROP` IDs from that file's own table) and `placed FILE [CLASS…]` (heuristic count of placed nodes/actions per class). All are read-only; run them with `python3 -I`.
- **Format history 2001–2006, from the loaders (2026-11-26).** `Jaws.exe` keeps the file version as one packed `uint32` (`0x008B97CC`, one byte per number: 2.6.3.16 = `0x02060310`), filled by the header reader `0x6BBAC0`, and compares it at 30 places (the PS2 exe `SLUS_210.62` has the same cutoffs). The Ecco programs have no such checks; they only contain their own version and the writer's format string `" FORMAT, VERSION %d.%d.%d.%d."`. The cutoffs:

| Version | What it switches | Where |
|---|---|---|
| > **2.5.7.12** | every value read from a binary file is aligned to its own size (`int` to 4, `short` to 2, also strings/name lists); older files are packed inside chunks | ~25 read helpers (`0x6BC240`…`0x6C0326`, `StoreInput::OnActivate` `0x711990`); PS2: 33 |
| > **2.5.12.6** | `RSRC` starts with a header `[uint32 stamp][uint32 mode]` (+ name list if mode 1); mode 1 = every resource is `[id][flags]` + block, where flags bit 0 = enabled, bits 16–23 = language + 1, bits 24–30 = a second engine selector (`engine+0x7C`), `0x20` = followed by an `OBPR`. Shipped files: stamp **20051208**, mode 1, empty list | `0x6ECE40` → `0x6ECBB0` |
| < **2.6.1.17** | rejected: "Export version (%d) too old. (2.6.1.17 required)"; a second check in `0x6C3FD0` rebuilds a max-ID counter for older files | `GDLoadGame` `0x693180` |

  All shipped files are 2.6.3.16, so the two older branches are dead code that dates the changes. Other findings from the same code:
  - **`FSIZ`, `FDIR` are read by a separate handler** (`0x6C3D90`, a virtual method; not in `GDLoadGame`'s switch). `FSIZ`'s value is stored at `[0x8B9C60]+0x2C` and passed to `0x729E50`, an empty function in the retail exe (most likely a loading-progress hook compiled out). `FDIR` checks its own stamp **20050707** (`0x0131F313`) before reading up to 5 directories.
  - **`VERS` and `EXBY` are never read**; no code references the tags, so they fall through as unknown chunks.
  - **Logins vs published credits (2026-11-26):** the Jaws credits are in `Jaws.exe` ("APPALOOSA INTERACTIVE CREDIT LIST"). `jts` = **Tamás Jutasi**, credited as a programmer on Jaws; the Defender US master's credits print him as "Tamás Jutasi 'JTS'" (confirmed). PS2 `Neszta` = **Neszta Volkai**, credited as a Jaws level designer (direct match). PS2 `SAN` plausibly = Sándor Mezei (Jaws level designer, also credited on Defender and PS1 *Wacky Races*), unconfirmed. `balage` (three Balázses in the Jaws credits: Makó, Soós, Haui) and `Zolcsika` (Zoltán Somorjai, level designer, or Zoltán Weszely, artist) are ambiguous. `gyozo`, `martens` and `AnChoR` match no credited name in Jaws, Defender or PS1 *Wacky Races* (no Győző is credited in any of them). Published credits only.
  - **`EXBY` = "exported by": the exporter's login name** (decoded 2026-11-26; was "unknown"). PC files: `jts` (63 archives incl. embedded ones; AQUARIUM, ARMADA, BEACH, BEACHPST, DOCKS, KATATAMA, OPEN_*, START, TITLE, TITLE0), `gyozo` (15; DEEPSEA, DEEPSEA2, FISH, GAUNTLET, MINEMSHA, TOWN, WRACK), `martens` (3; CHASE). PS2 files were exported by others: `balage` (AQUA2, AQUARIUM, OPEN_NE, OPEN_NW, TOWN), `Zolcsika` (ARMADA, BEACH, BEACHPST, CHASE, DEEPSEA, DEEPSEA2), `SAN` (DOCKS, MINEMSHA, START, START2), `Neszta` (FISH, GAUNTLET, WRACK), `martens` (KATATAMA, TITLE, TITLE0), `AnChoR` (OPEN_S). `gyozo` is also the name in the 1999 Defender PS2 `.TKP` map headers (above), so the same person exported files for both games.
  - **`LDSC`:** Defender PS2's first chunk is a loading-screen image (`uint32` size, then 512, 256, 2, 1 and 512×256 16-bit pixels; the Dreamcast builds use the `TITL`/`TSCR` PVR image instead). `Jaws.exe` still has an `LDSC` handler (`0x717430`) with a different layout (count + 4 ints per entry, then that many data blocks, i.e. a list of images); no Jaws file has the chunk. So the loading-screen chunk was reworked after Defender and then replaced by the embedded loading-scene archives (`FDIR`).
  - The header reader's error calls the format a **"Game Designer file"** ("This is not a valid Game Designer file."), in all three programs. Whether `GDED` stands for "Game Designer" isn't stated anywhere.
- **Unconfirmed idea: the version numbers might be dates (2026-11-26).** The user doubts this (not impossible, but unlikely in their view); treat it as an unproven coincidence, not as evidence. The observation: in the Jaws era the last three numbers read as year.month.day, and three of them match format date stamps in the same files: **2.5.7.12** (2005-07-12) is 5 days after the `FDIR` stamp 20050707 (the footer arrived around then); **2.5.12.6** (2005-12-06) sits between the `GMDL` stamp 20051205 and the `RSRC` stamp 20051208, and its check is exactly the `RSRC` header; **2.6.3.16** (2006-03-16) equals the PS2-only stamp 20060316. 2.6.1.17 would be 2006-01-17. For the Ecco builds the last two numbers still fit month.day (Sentinels 2.3.2.1 = 1 Feb, files dated 16–21 Feb 2001; Defender 2.1.12.1 = 1 Dec, before its 2000 builds), but the second number doesn't match a year there (1 and 3), so the year reading only holds from 2.5 on. The dating below does not rely on this idea; it uses the date stamps only.
- **Resulting order of changes (dates are the format stamps, not the version numbers):** Defender 2.1.12.1 (builds from 2000) → Sentinels 2.3.2.1 (files Feb 2001; padded chunks, `EXTR`, `Tile`) → `SKEL` revision 20020410 → `VERS` container date **20030626** (the `FSIZ`/`VERS`/`EXBY` header is most likely from about then; `VERS` carries that date in every file) → `GTEX` 20050515 → footer (`FDIR` stamp 20050707) → per-value alignment (versions after 2.5.7.12) → `RSRC` header (versions after 2.5.12.6, stamp 20051208; `GMDL` 20051205) → minimum loadable 2.6.1.17 → final 2.6.3.16 (PS2-only stamp 20060316). How the versions map onto calendar dates is not established. Still unknown: what the editor was used for between 2001 and 2005 (see the open problems).
- **Other titles checked for GWB (2026-11-26):** Appaloosa's own releases after 1999 were *Wacky Races* (PlayStation, 2000), *Ecco: Defender* (Dreamcast 2000, PS2 2002) and *Jaws Unleashed* (2006) (user). The separate Infogrames *Wacky Races* port (Dreamcast 2000 / PS2 2001) was checked on the Dreamcast PAL release (Europe, En/Fr/De/Es/It/Nl; files dated 1999-11 to 2000-05-14): **not GWB.** Its levels are `MAPS/MAP000`–`026.NWB` (plus `CARS`, `BOSS`, `AWARD`, `MOVIE` `.NWB`): a different container with embedded `PVRT` textures and no chunk tags; there is no `GDED` preamble anywhere on the disc (the few raw `GDED`/`CHBR`/`BRTR` hits are chance matches inside compressed data), and no "Appaloosa", "Game World Builder" or "Diesel" string. The program (`1ST_READ.BIN` + `WACKY.BIN`) has no GWB class names. Its credits read "A game developed by Infogrames Studios Ltd., Sheffield House", with an all-UK staff list, so it's an unrelated in-house Infogrames Sheffield game. The only shared file is `AUDIO64.DRV`, Sega's standard Dreamcast sound driver, which says nothing about lineage.
- **Cancelled Appaloosa projects (user information, 2026-11-26):** Mermaid tech demo (2001), Parrot demo (design only), *Smurfs* (2002, PS2). No files exist publicly. The US Defender master's class registry already has `MBMermaid` (mid-2000), so the mermaid project was in GWB by then; *Smurfs* shows no visible GWB link on video. Details: `docs/ecco_leftovers.md` "Cancelled Appaloosa projects", "Smurfs video (2002)".
- **Twofish / *SmartyAnts* (2010, checked 2026-11-26):** after Appaloosa closed, its people founded Twofish (user). The *SmartyAnts* Windows and Mac installers are only online launchers (DirectX redistributable / a Java bootstrapper, package `hu.twofish`); the game came from `s3.amazonaws.com/SA_boot`, now gone, so no game data. The installer's debug path `c:\Torque\anttools\release\installer.pdb` points to GarageGames' **Torque** engine (fits its Direct3D 9 and Mac/Linux support), so GWB/Diesel Power probably ended with Jaws; signed by Smarty Ants, Inc. (Burlingame, CA). Faint echo: the installer's own archive header holds `0x20041020`, read as a YYYYMMDD stamp. Details: `docs/ecco_leftovers.md` "After Appaloosa: Twofish and SmartyAnts".
- **Appaloosa's own *Wacky Races* (PlayStation, PAL `SLES_024.68`, files dated 2000-06 to 2000-08-30), checked 2026-11-26: no GWB container, but GWB resource conventions.** The disc has no `GDED` preamble, no GWB class names and no "Game World Builder"/"Diesel" string. Tracks are `CC`/`CT`/`DR`/`DT`/`SH` `*.WMI`, plus `.GSV`, `.STR` and `.TIM` files. Its credits (in the game data, "APPALOOSA CREDITS") list a Hungarian team, including a separate "Development tools" credit. But the data uses GWB's resource conventions: typed references written as a resource-type tag + ID, exactly like GWB's `['GTEX'][id]`, with GWB's own type names: `GMAT` 7,331, `GTEX` 7,050, `GMDL` 1,799, `GSMP` 1,304 occurrences (e.g. repeated `['GMAT'][id] … ['GTEX'][…]` material records, `TEXP` 55, GMAT IDs 600–132,159). Every `.WMI` file starts with the magic `FIMW00.1` followed by `uint32` **20000710**, a YYYYMMDD stamp in the same style as GWB's block stamps. So it's most likely built from the same Appaloosa asset pipeline (resource types and stamps), converted to a PlayStation-specific format, rather than shipping GWB's `GDED` files. No `CHBR`/`PRPS`/`BRTR` scene-graph tags (the few hits are noise), so the scene format is different. **Not an early GWB version (assessment 2026-11-26):** its data (Jun–Aug 2000) is later than GWB 2.1.12.1, which Defender DC already shipped with in spring 2000, and GWB's own block stamps go back to 1998; it lacks everything that defines GWB (bricks/actions scene graph, `CLAS`, `GDED`); its exe (`SLES_024.68`) has only 484 strings and no `GD…` class names (one "OUT OF MEMORY in WPU_BrickWall" message, inconclusive). More likely a sibling: a separate PS1 runtime fed by Appaloosa's shared resource toolchain (the credits list a separate "Development tools" team).
- ***C: The Contra Adventure* (PlayStation, US `SLUS_004.99`, files dated up to 1998-07-15, disc 1998-08-10), checked 2026-11-26 as a possible GWB 1.x: no GWB traces at all.** No `GDED` preamble, no chunk tags (`CHBR`, `PRPS`, `PROP`, `BRTR`, `CLAS`, `RSRC`, `WDIM`, `GNRL`), no `GD…` class names, none of GWB's resource type names (`GMAT`/`GTEX`/`GMDL`/`GSMP`, unlike PS1 *Wacky Races*) and none of the 1998 block stamps (19980304, 19980331, 19980409); the 7 raw `GDED` hits are chance matches in image data. Its levels use their own split format (`DATA/CDI`, `DATA/POS`, `DATA/PRE` per level, `DATA/SND/*.SGG` sound banks, `DATA/BIN/*.SMO`/`.SSO`/`.TMI`); the exe and overlays only list those paths (no editor, version or source-file strings). Appaloosa traces: an "Appaloosa Staff" credit and partly Hungarian level names (`ALAGUT` = *alagút* "tunnel", `PIRAMIS` with Hungarian spelling while its sound bank is `PIRAMID1`/`2`). **Conclusion:** GWB's block stamps (March–April 1998) show the editor's formats were being defined during 1998 alongside Contra, not used by it; GWB-style resource tags appear by 2000 (PS1 *Wacky Races*), the full format in *Ecco: Defender* (2000). No GWB 1.x found; the 2000-02-17 Defender prototype (checked 2026-11-26) is also 2.1.12.1.
- **Defender 17 February 2000 prototype (Hidden Palace release, user-supplied 2026-11-26): still 2.1.12.1.** Boot header `MK-0000 V0.800`, region JUE, dated 2000-02-04, title "THIS IS A SAMPLE DISK FOR USE IN THE OFFICE ONLY / DO NOT SELL / DO NOT CARRY OUT FROM THE OFFICE". 41 levels dated 2000-01-24 to 2000-02-17, all 2.1.12.1, top level `GNRL KADI WDIM RSPR CLAS RSRC BRTR SCRT`; its `SOUND/*.KAT` banks go back to 1999-08-23 (`LOADING.KAT`), `DSP.KAT` 1999-09-17, `WFALLENTER.INP` 1999-06-04, the oldest Defender data on hand. So no older GWB format is reachable through Defender builds: 2.1.12.1 was already the format by January 2000. Class tables: Feb 112 bricks / 521 actions / 9 / 38 vs April 122 / 580 / 9 / 40. Feb-only: `MLMultiModel`, `MLMultiSkelModel`, `MLModelAlpha`, `MLRepHal`, `MLVmi` (none survive into Sentinels or Jaws). New by April: 12 bricks (`DDArea`, `DDMapParams`, `GDLanguageGroup`, `GDPptFont`, `GDPptTextSprite`, `NALensReflection`, `NALightning`, `TRRewardReference`, …), 62 actions, and the property classes `GDPropLanguage`/`GDPropLangIDList`, i.e. **the localization system was added between mid-February and April 2000**. The prototype's three levels missing from all later builds are in `docs/ecco_leftovers.md` "Cut Defender levels in the Feb 2000 prototype".
- **Defender: European vs US Dreamcast masters (2026-11-26).** The disc in `dreamcast/…(Jul 6, 2000 build).` (touched once on 2026-10-21, one level copied to its `compare/` folder, never written up) is the **US master**: boot header `MK-51033 V1.000`, region U, dated 2000-06-19, files up to 2000-07-14. The retail PAL disc checked above is `MK-51033-50 V1.003`, region E, header dated 2000-05-09, files up to 2000-05-13. Both have the same 48 levels, all 2.1.12.1. **13 files are byte-identical** (mostly the `_DEMO` levels, `000_GAMEOVER`, `001_INTRO`, the three `ARRIVAL` levels, `CONFIG.TXT`); **37 differ**, including `0.BIN` (+7 KB). Biggest changes in the US master: `470_FOCI` +1.39 MB (+84 `GMDL`, +1 `SKEL`, ~+240 `GDLight`, ~+280 placed `GDModel`, i.e. a much expanded level), `320_RESISTANCE` +597 KB (+159 meshes, each with its own `MREG` collision), `330_MHQ` +97 KB, `460_CREDITS` +184 KB (~23 more credit text lines: Sega of America localization, test, marketing and PR staff; "Presented by SEGA" and British spellings removed). Class tables: PAL 121 bricks / 523 actions, US 123 / 529, April prototype 122 / 580. **The US files list classes the PAL ones don't:** `MBLovedek` (*lövedék* = projectile; later in Jaws), `NAHair` (in Sentinels and Jaws; its field list appears in the US credits file), `MBMermaid`, `MBMissile`, `MBCameraAct`, `MLCamAct`, `MLSmooth`, `DDPaintBall` (also in Sentinels). Only `DDPaintBall` is placed (once, `330_MHQ`); the rest are just in the editor's class registry, so the US files were exported with a newer editor build that already had `MB…` classes and the hair system by mid-2000. Defender PS2 has only `DDPaintBall` of these; it lacks the other seven, including `MBLovedek` and `NAHair`, which Jaws has. April prototype → PAL: +4/−5 bricks, +21/−78 actions.
- **Defender: retail Dreamcast vs PS2 (2026-11-26).** Until now, all Defender Dreamcast files examined came from dev builds (the dev kit, the 2000-04-08 prototype; user's note). Now compared with the **retail PAL Dreamcast release** ("Europe (En,Fr,De,Es)", files dated up to 2000-05-13; 46 readable levels, all 2.1.12.1, top level `GNRL KADI WDIM RSPR CLAS RSRC BRTR SCRT` behind the PVR loading image; `000_LOADER`/`000_TITLE` have no plain preamble) and the **US PS2 release** (`SLUS_203.94` v1.01, exe dated 2002-01-24, 48 levels dated 2001-09-25 to 2002-02-06, also 2.1.12.1, `LDSC` first; no `EXBY`). Class tables (union): DC 121 bricks / 523 actions / 9 / 40, PS2 132 / 627 / 9 / 46. **DC-only:** `ControllerConfig`, `TBGrass`, `GDPause`, `MLFLB`, `MLPod`, `TRPlantation`. **PS2-only: 13 bricks, 108 actions, 6 property classes**, mostly PS2 platform code (memory card, `PS2Shadow`, `PS2Mesh`, `PS2SaveInit`, settings/menu `P…` actions, `Gallery…`, `DD3dMap…`, `DDMakeTiffShot`). **Some of the PS2 additions are newer engine code shared with the Sentinels → Jaws line:**
  - also in Sentinels (2001) and Jaws: `GDControl` (Jaws' level scripting; placed ~1,050× in Defender PS2) with `GDPropControl`, `GDPropColor`, `GDPropAbsVectList`, `PCheckJoy`, `PRotExplosion`;
  - **in Defender PS2 and Jaws but not in Sentinels:** `GDMultiTexture`, **`NAPredatorModel`** (~500 placed in PS2, ~60 in Jaws), `NAModelFade` (~450 / ~710), `NASubdivide`, `GDPropExtRenderSet` (counts from `gded_lineage.py placed`, a heuristic);
  - also in Sentinels but not Jaws: `DDTBModel`, `GD3dScaleSprite`, `TBGrid`, `DDClipModel`, `DDRenderTexture`, `GDPropIntID`. `MBTaskMan`/`MBTaskReport` share only the `MB` prefix with Jaws' mission classes.
  **Field level** (`docs/defender_dc_ps2_field_diff.txt`; DC = PAL + US levels, 585 classes / 4,792 fields; PS2 682 / 5,292; 574 shared classes, 538 with identical fields, 36 changed): the PS2 port adds `m_ExtRenderSetting` to `GDModel`, `GD3dSprite`, `NAGlowAct`, `NARingAct` (render-setting extension, also in Jaws); `m_tasknum` to `DDJelzoAjto`, `TRFishCtrl`, `TRGift` (goes with the PS2 `MBTaskMan`/`MBTaskReport` task system); `GDFollow.m_RotSpeed`, `TRActivate.m_NeedExec`, `NAFlare.m_fixedsizepower`, `DDTextModel.aliasprocess`/`shadowfactor`, `DDStageDetentAct.m_belsoterkep`/`m_kulsoterkep` (inner/outer map), and small gameplay tweaks; it drops a few (`MLSnakeAct.basephase`/`maxangles`, `TRFoeLake.m_IsStartedMusic`, `DDLegKalapacsAct.m_pbox`/`m_targetgroup`).
  So the PS2 port (2001–2002) kept the 2.1.12.1 file format but took in engine classes from the newer code line, and contributed or shared classes that reach Jaws without passing through the Sentinels files we have. This corrects the earlier idea that the port was built purely from the shipped Defender code (only the file format is old). Whether the classes moved from the port to Jaws or both took them from a common engine branch can't be told from the files.
- **Editor credit:** the string "Created with Game World Builder, © 2000 Appaloosa Interactive" occurs only in Defender's `460_Credits` level (dev-kit and 2000-04 builds). It isn't in Sentinels, Defender PS2 or Jaws. The dev-kit disk image has no "Diesel" string.

---

## Archive Structure

**Engine version:** All 20 GDW files share the identical header `GDED BINARY FORMAT, VERSION 2.6.3.16` with an internal date of `20030626` (June 26, 2003), stored as a string in the `VERS` chunk (`Jaws.exe` holds the same string, next to `misc_core_open`). **Correction (2026-10-21):** this is the container format's version date, not an engine freeze. Individual block formats kept changing until December 2005 (see "Block format date stamps" below).

### Text variant: `GDED TEXT FORMAT` (2026-11-25, loads in-game)

The same container exists as text, the format the Game World Builder editor could save. Jaws can't write it (writer code is dead), but `GDLoadGame` still reads it: a full level converted to text loaded and played, and a hand-edited fog colour took effect (user-confirmed). Syntax, from the readers' text branches:

```
GDED TEXT FORMAT, VERSION 2.6.3.16.\r\n\r\n     (exactly these 4 raw bytes after the version)
Chunk: PROP {                                    (chunk; sizes are implicit, "}" ends it)
  CLASSID: 2131-1-8                              (bits 0-11, 12-23, 24-31 = PROP 0x08001853)
  COLOR: 0.56, 0.69, 0.79, 1
}
INT: -5   SHORT: 3   REAL: 1.5   SET: ACD (bit n = 'A'+n, '-' = 0)   ResID: GTEX (0000 = 0)
STRING: "name" ('-' = none)   VECTOR: x, y, z   MATRIX: 12 values   BUFFER: hex byte tokens
```

Labels are free (anything before `:`); arrays are one value per line. Limits: `FDIR`'s 24-byte names are read raw, the loading-screen sub-archives stay binary (appended, `FDIR` offsets absolute), NaN/Inf can't be expressed. The bytes of a binary GDW don't say which reader reads which value, so conversion uses a load trace from the mod (`scripts/gdw_to_text.py`). Size about 2.3× the binary, load about 20 s for a 105 MB level. Judged not practical for editing (user); kept as a curiosity. Engine side: `docs/exe_analysis.md` "GDED text format".

### Block format date stamps (found 2026-10-21)

Data blocks carry a format-version number that is a literal **YYYYMMDD date**, and `Jaws.exe`'s loaders compare against it (every exe hit is a `cmp [esp+x], imm` or `cmp eax, imm`). Found by scanning all 20 GDWs, the PS2 `.GDE`s and the exe for date-shaped uint32s and keeping those that sit in block headers:

| Block | Stamp | Date | Note |
|---|---|---|---|
| `WDIM` | 19980304 | 4 Mar 1998 | |
| `GNRL` | 19980331 | 31 Mar 1998 | |
| `GMAT` | 19980409 | 9 Apr 1998 | after the empty `OBPR` (`0x0130E079`) |
| `GMOV` | 19991005 | 5 Oct 1999 | |
| `GSMP` | 20001201 | 1 Dec 2000 | `0x013131B1` |
| `SKEL` | **20020410** | **10 Apr 2002** | all 752 skeletons; the loader also checks `> 20001009` (morph-frame count) and `≥ 20020410` (running-position track) |
| `GTEX` | 20050515 | 15 May 2005 | the "stamp `0x0131F253`" in the texture header |
| `GMDL` | 20051205 | 5 Dec 2005 | all 11,948 meshes |
| `RSRC` | 20051208 | 8 Dec 2005 | |
| (PS2 only) | 20060316 | 16 Mar 2006 | 360 blocks in the `.GDE`s, also checked by `Jaws.exe`; block not identified |

The exe also compares against stamps not seen in the data (1998–2006, e.g. 19980902 in several loaders, 20030218, 20050707), probably formats with no blocks in the shipped files or older revisions still accepted. **The only 2001–2002 date anywhere is the `SKEL` stamp (April 2002)**, i.e. the skeleton format's last revision falls between *Ecco: Defender* and *Sole Predator*. Values 20011008–20011013 that a raw scan finds are chance byte patterns in pixel data, not headers. The 1998 stamps predate GWB's early-1999 start, so the oldest formats may come from earlier Novotrade/Appaloosa tools (inference). Other dates in the exe: PE timestamp and `__DATE__` 14 Sep 2006, `(c) 2004 Majesco Entertainment`, libpng 1.0.5 (Oct 1999), IJG JPEG (1996).

**Development history and engine lineage:**

The engine predates Jaws Unleashed by several years. Appaloosa Interactive built the same underwater engine for *Ecco the Dolphin: Defender of the Future* (2000). The game was then developed under the working title *Sole Predator* and demonstrated as a tech demo in 2004 while Appaloosa searched for a publisher. A publisher subsequently acquired the Jaws license and the game shipped in 2006 as *Jaws Unleashed*.

**Correction (2026-10-21):** this used to say the engine was frozen in June 2003. That date (`20030626`) is only the container format's version; the block format stamps (see "Block format date stamps") show the skeleton format revised in April 2002 and the texture, mesh and resource formats in May–December 2005, so the engine kept changing during Jaws development. Several things visible in the files show old code carried forward:

- `SharkWorld` sits alongside `GDWorld` in the class registry — shark-specific code was layered on top of the generic engine rather than integrated into it
- The water system has multiple versioned classes (`NAWaterGrid2000`, `NAWater2003`, `NAWater2004`, `NASlideWater2004`) — these represent evolution layers carried forward from Ecco through Sole Predator
- `PS2ExportSettings` is baked into the class registry — the PS2 port was planned from the start, not added late in development
- The engine feels more sophisticated than typical 2006 AA titles because it had been in active development since at least 2000

GDW files are **chunk-based binary containers** using little-endian byte order. The top-level structure is:

```
[4-byte FOURCC tag][uint32 size][payload]
```

Chunks may contain nested subchunks using the same pattern. Multiple full `GDED` headers have been observed inside single GDW files, suggesting nested serialization containers or streaming sub-documents.

**CORRECTED/RESOLVED (2026-07-17):** this is now fully explained. Every GDW's declared `ENDF` is not the true end of the file — a second, complete, independent `GDED BINARY FORMAT...` archive (own `VERS/EXBY/GNRL/WDIM/RSPR/CLAS/RSRC/BRTR` chain, but no `FSIZ`/`SCRT`/`SKIP`/`FDIR`/`ENDF` of its own) is concatenated immediately after. `FDIR`'s single entry stores this second archive's exact `[offset, size]`. Confirmed on `OPEN_S.GDW` to be **bundled loading-screen scenes** for level transitions (not nested/streaming sub-documents in a general sense) — bounded story levels carry one small embedded archive, open zones carry several (one per destination they connect to). See CLAUDE.md's `FDIR` note for the full mechanics.

### Known Top-Level Chunks

| Chunk | Confidence | Description |
|---|---|---|
| `FSIZ` | CONFIRMED | ~~File size metadata~~ **CORRECTED (2026-07-17):** payload is NOT total file size — it's the exact byte offset where `SKIP` begins (equivalently, where `SCRT` ends). |
| `VERS` | CONFIRMED | Container version date string `20030626` (same in every file). Never read by the game. |
| `ENDF` | CONFIRMED | ~~Archive terminator~~ **CORRECTED (2026-07-17):** terminates only the FIRST of two concatenated embedded archives in the file — not the true physical EOF. See `FDIR` row and the note above. |
| `FDIR` | **CONFIRMED (2026-07-17, was HIGH)** | Real offset+size index, not just names: 8-byte header (magic/build-date + entry_count), then per-entry `[uint32 offset][uint32 size][24-byte name]`. Points at the second embedded archive described above. Any edit growing a chunk before this offset must patch this field by the same delta. |
| `CLAS` | VERY HIGH | Class/reflection database |
| `BRCM` | LIKELY | Appears immediately after CLAS in all files — likely class/brick registry map |
| `RSRC` | HIGH | Packed resource payloads — does NOT follow recursive chunk structure internally |
| `BRTR` | HIGH | ~~Resource tree / index (maps resource IDs to names or offsets)~~ **CORRECTED — this description is wrong.** CLAUDE.md confirms: `BRTR` is the pre-built **scene graph** — all placed object instances with world-space transforms, mesh references, vertex colours, and AABBs (2,782 `CHBR` nodes in `FISH.GDW`, 1,161 with mesh refs). Not a resource-ID lookup table. |
| `GNRL` | LIKELY | General archive data — decodes to two uint32s; first looks like a `19980331`-style build/format date, second (`35210` in FISH.GDW) is close to but not exactly the max real `BRTR` node ID — inconclusive, not confirmed to mean anything at runtime. |
| `WDIM` | LIKELY | World dimension bounds — observed floats ~5000×2000×5000, likely streaming/level extents |
| `SCRT` | **RESOLVED (2026-07-08), was SUSPECTED "Scripting system"** | Not scripting, not obfuscated. A small top-level `PRPS`/`CHBR`/`PROP` tree (same format as `BRTR`) holding named screen-space overlay objects (`GDScreen`, water reflection/transparency layers, motion blur). The offset originally suspected for this was a false-positive tag match inside `RSRC`; the real `SCRT` is a top-level chunk, sibling of `BRTR`. |
| `SKIP` | **RESOLVED (2026-07-08), missing from this table** | Pure `0xFF`-filled sector-alignment padding, sized so `FDIR` lands on a 512-byte file-offset boundary. Sits between `SCRT` and `FDIR`. |
| `RSPR` | UNKNOWN | Unknown subsystem — always empty (0 bytes) in `FISH.GDW` |
| `EXBY` | **CONFIRMED (2026-11-26)** | "Exported by": `uint32` length + the exporter's login name (`jts`, `gyozo`, `martens` on PC). Never read by the game. See "Format history 2001–2006". |

### High-Frequency Object Chunks (seen across all level files)

| Chunk | Count (approx) | Description |
|---|---|---|
| `PROP` | 88K–225K per file | Property block — core serialization unit |
| `PRPS` | 2K–8K | Property set container |
| `CHBR` | 1K–5K | Child brick reference |
| `GMDL` | 1K–3K | Geometry model container |
| `GMAT` | 1K–4K | Geometry material |
| `VERT` | ~12K total | Vertex data |
| `VIND` | ~12K total | Vertex index buffer |
| `TSET` | ~12K total | Triangle set (submesh ranges; corrected 2026-10-01, not textures) |
| `TANG` | ~12K total | Tangent data |
| `MATR` | ~12K total | Material |
| `POSI` | ~12K total | Position data |
| `TRAN` | ~26K total | Transform |
| `ROTS` | ~16K total | Rotation |
| `TMTX` | ~39K total | Transform matrix — prominent in ARMADA, DOCKS, DEEPSEA2, KATATAMA, WRACK |
| `ACTN` | ~21K total | Action / animation action |
| `GTEX` | ~21K total | Geometry texture reference (distinct from 5-byte `GTEXT` texture blocks). **Corrected 2026-10-03:** every texture is a `GTEX` chunk; "GTEXT" is `GTEX` + a size field whose low byte is `0x54` (`'T'`). See `CLAUDE.md` texture section. |
| `MSHH` | ~1.4K total | Mesh header — contains named model references (e.g. `Shark2Reference`) |
| `CHLD` | ~12K total | Child relationship |
| `APRO` / `BPRO` / `CPRO` / `OBPR` | various | Property block variants |
| `TCAM` | ~12K total | Texture camera — prominent in DOCKS |
| `LUDL` / `LVDL` / `DLUD` / `MTOB` | ~12–14K each | Unknown — likely LOD or render-distance data |

### WDIM Chunk

Size: `0x28` bytes. Contains float-like values interpreted as world extents (~5000, ~2000, ~5000). Likely defines level streaming bounds or world-space dimensions.

---

## Texture System

### GTEXT Structure

> **Correction (2026-10-03):** "GTEXT" is not a separate tag. Walking `RSRC` as a chunk chain shows every texture is a `GTEX` chunk; the "T" is the low byte (`0x54`) of the size field that follows the tag. The real split is plain payload (258/321 FISH textures; the layout below) vs. payload carrying an `OBPR` block (63/321). New textures can be written byte-exactly: `scripts/gdw_textures.py`, see `docs/brtr_editing.md` "Custom textures".

Textures are stored as `GTEXT` blocks. The header layout is fully confirmed:

| Offset | Field | Notes |
|---|---|---|
| `+0x00` | `GTEXT` signature | 5-byte ASCII marker |
| `+0x04` | block size | uint32, includes header + payload |
| `+0x08` | texture ID | uint32 |
| `+0x18` | width | uint32, pixels |
| `+0x1C` | height | uint32, pixels |
| `+0x20` | bits-per-pixel | uint32 — `32` or `24` for known formats |
| `+0x24` | `TGAN0` marker | also contains `TRUEVISION-XFILE` string |
| `+0x54` | ~~pixel payload start~~ **wrong, see correction below** | |

> **Correction (2026-07-29):** pixel data actually starts at `+0x42`, immediately after an 18-byte standard TGA 1.0 header that begins at `+0x30` — not `+0x54`. The `+0x54` figure conflated that real header with a *trailing* TGA 2.0 footer (`"TRUEVISION-XFILE.\0"` + 8 offset bytes) that sits after the pixel data, not before it. Reading from `+0x54` skipped the first 18 bytes of real pixel data and read footer garbage instead — a non-integer-pixel shift that produced diagonally-sheared/wrapped images. `payload_size = block_size - 0x54` is still correct (it already yields the right total pixel byte count); only the **read start offset** was wrong. See `CLAUDE.md`'s "Texture System (GTEXT)" section for full detail. `scripts/rip_textures.py` is fixed.

**Payload size formula (still correct):**
```
payload_size = block_size - 0x54
```

### Pixel Formats

| BPP | Format | Handling |
|---|---|---|
| `32` | ~~RGBA32, read directly~~ **wrong — see correction** | |
| `24` | RGB24 | Stored as BGR — swap to RGB on read |
| Other | Unknown | Dump as `.raw` for manual inspection |

> **Correction (2026-07-29):** 32bpp is **not** straight RGBA. Like GTEX (see `rendering_system.md`), it's native little-endian `D3DFMT_A8R8G8B8`, byte order **B, G, R, A** — same BGR-family convention as the 24bpp row above, just with an alpha byte appended. The old "read directly as RGBA" assumption produced a systematic R/B channel swap (subtle blue tint on naturally warm-toned textures, e.g. a kelp texture rendering blue-teal instead of green/brown). This was hard to notice while the `+0x54` offset bug above was also active, since the resulting image was already visibly corrupted by the shift. `scripts/rip_textures.py` now reads 32bpp with PIL raw mode `'BGRA'`.

Textures are stored with the origin at bottom-left (standard DX/OpenGL convention) and must be vertically flipped on export. `rip_textures.py` handles this with `FLIP_VERTICAL = True`.

### Texture Types Observed

- Particle effect masks (monochromatic, runtime-tinted)
- Texture atlases (multi-object sprite sheets)
- UI textures
- Environmental textures
- Character/creature textures

### Palette / CLUT Textures

Some textures use indexed colour with a CLUT (Color Look-Up Table). Colour ramp patterns like:
```
69 69 69
64 64 64
5F 5F 5F
```
and RGBA markers like `FF 00 FF FF` indicate palette structures. These textures extract incorrectly with the current pipeline (wrong colours, scrambled appearance). This is the primary remaining unsolved texture problem.

> **Note (2026-07-29):** re-evaluate this claim before investigating a real CLUT/palette format — "wrong colours, scrambled appearance" is exactly the symptom of the `+0x54` offset bug and the RGBA/ARGB byte-order bugs corrected above and in `CLAUDE.md`, both of which were active when this section was written. Confirm textures still look wrong under the fixed `scripts/rip_textures.py` before assuming a genuine indexed-color format is involved.
>
> **Separately, a genuine 8bpp indexed/CLUT format was decoded (2026-07-29)** — distinct from the above, and not the explanation for it. `rip_textures.py` was dumping unsupported-BPP blocks as `.raw`; of ~59 such dumps across all 20 GDWs, only 2 were real textures (both 64×64 8bpp, `TITLE.GDW` and `GAUNTLET.GDW`, the same shared UI icon — the other 57 are false-positive `GTEXT` string matches inside unrelated binary data, detectable by nonsensical multi-billion-pixel declared dimensions). Format: `[768-byte palette: 256 × 3-byte RGB entries][width×height index bytes]` — file size is exactly `768 + width*height`. Both confirmed palettes are an identical linear inverted grayscale ramp (`palette[i] = (255-i,255-i,255-i)`). `rip_textures.py` now decodes this via palette lookup (`idx8.png` output). See `CLAUDE.md`'s "Texture System (GTEXT)" section.

### Extraction Pipeline

```
GTEXT block
  → read header (width, height, BPP)
  → calculate payload_offset = GTEXT_offset + 0x42   # corrected 2026-07-29, was +0x54
  → calculate payload_size = block_size - 0x54
  → extract raw bytes
  → convert to PIL image (32bpp: BGRA→RGBA, 24bpp: BGR→RGB)   # 32bpp swap corrected 2026-07-29, was read directly
  → flip vertical
  → export PNG
```

**Primary script:** `scripts/rip_textures.py` — set the `name` variable to the GDW stem (e.g. `'FISH'`). Outputs go to `textures/<NAME>/`.

---

## Reflection / Class System

### CLAS Chunk

The `CLAS` chunk contains a serialized class and property reflection database. This was a major discovery — the engine preserves full runtime type information inside the GDW files, including class names, property names, and component definitions.

The serialization pattern is length-prefixed strings:
```
[uint32 length][class or property name string]
```

This means the engine effectively self-documents. Readable strings can be located with:
```bash
strings -td FISH.GDW | grep -i <term>
grep -oba "ClassName" FISH.GDW
```

### Class Namespace Conventions

| Prefix | Domain |
|---|---|
| `GD` | Generic engine / rendering |
| `NA` | Gameplay / shark systems |
| `MB` | Mission / boat systems |
| `MS` | Menu / spawn / scenario |
| `ML` | Lighting / effects |
| `AN` | AI zones and area volumes |
| `JT` | Gameplay interaction objects |
| `mc` | Mesh collections |
| `X` | Skeleton / bone / animation |

### Confirmed Engine Classes

**Rendering / Models:**

| Class | Purpose |
|---|---|
| `GDModel` | 3D model component |
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

**Lighting / FX:**

| Class | Purpose |
|---|---|
| `GDLight` | Dynamic lighting |
| `GDExtendedLight` | Extended light properties |
| `GDFog` | Fog system |
| `NAParticle2004` | Particle system |
| `GDParticleTest` | Particle test component |
| `NAMotionBlur` | Motion blur |

**Water / Terrain:**

| Class | Purpose |
|---|---|
| `NAWater2004` | Primary water system (used in OPEN_ files) |
| `NAWater2003` | Earlier water system version |
| `NAWaterGrid2000` | Original water grid |
| `NASlideWater2004` | Sliding/shallow water |
| `NATextureGeneratorGrid` | Procedural water texture generation |
| `NATerrain` | Terrain system |
| `NAGrid` | Grid system |

**UI / Sprites:**

| Class | Purpose |
|---|---|
| `GDSprite` | Sprite object |
| `GDRotSprite` / `GDRotSpriteEX` | Rotating sprite |
| `GDFont` / `GDPptFont` | Font rendering |
| `GDTextSprite` / `GDPptTextSprite` | Text sprite |
| `GDShowSprite` | Display sprite |
| `GDScreen` / `GDViewport` | Screen and viewport |
| `GDTileMap` / `GDTile` | Tile-based map (likely UI or minimap) |

**Camera / Rendering:**

| Class | Purpose |
|---|---|
| `GDCamera` | Camera |
| `MBSharkCamera` | Shark-follow camera |
| `GDWorld` / `SharkWorld` | World root object |
| `GDGraph` | Render graph |
| `GDNewMat` | Material |

**Gameplay / Shark Systems:**

| Class | Purpose |
|---|---|
| `NAPredator` | Shark/predator AI |
| `NABiteTarget` | Bite interaction component |
| `NAChewingToy` | Physics-enabled prey/bait |
| `NAWayPoint` | AI navigation node |
| `NAMessenger` | Event/trigger messaging |
| `NATimeControl` | Time dilation / motion blur |
| `NAWhirl2000` | Whirlpool system |
| `JTMineWhirl` | Mine whirlpool interaction |

**Animation:**

| Class | Purpose |
|---|---|
| `XBone` | Skeleton bone |
| `XAnimation` | Animation clip |
| `XAnimationNames` | Animation name table |
| `XAnimationSet` | Animation set container |

**Mission / AI Areas:**

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

**Audio:**

| Class | Purpose |
|---|---|
| `GDSound` | Sound object |
| `GDSoundEvent2D` / `GDSoundEvent3D` | 2D/3D sound events |
| `GDSoundEventScope` / `GDSoundEvent3DB` | Sound event variants |
| `GDPlaySound` / `GDStopSound` | Sound control |
| `SoundManager` | Audio manager |

**Engine / Export:**

| Class | Purpose |
|---|---|
| `GDPath` / `GDGoPath` | Spline/path movement |
| `GDSpline` | Spline object |
| `GDEtalon` | Engine utility |
| `GDFolder` | Object grouping/folder |
| `GDPlayMovie` | Cutscene/movie playback |
| `GDPhysicDef` | Physics |
| `GDTestBrick` | Debug/test object |
| `PS2ExportSettings` | PS2 export configuration — confirms `.GDE` files are PS2 exports |

### Selected Property Reflection

**NABiteTarget:**
- `m_hp`, `m_damagemultiplier`, `m_nutrition`, `m_radius`, `m_eattype`
- `m_creature`, `m_dragfactor`, `m_shakefactor`
- `m_bitetargetmodel`, `m_bitetargetmaterialindex`
- `m_dependentlimbs`, `m_rubberskeletonid`

Implies: dismemberment system, material swapping, skeletal replacement, component-based bite interactions.

**NAChewingToy:**
- `m_velocity`, `m_angularvelocity`, `m_gravity`
- `m_attackgroups`, `m_sensorgroups`, `m_target`

**NAWayPoint:**
- `m_links`, `m_waypointgroups`, `m_autolink`, `m_autolinkrange`, `m_dependencytype`

Implies: graph-based AI navigation with automatic path linking.

**NAMessenger:**
- `m_onactivatemessagetargets`, `m_ondeactivatemessagetargets`, `m_onactivatemessagetype`

Implies: event-driven trigger/scripting system.

**NATimeControl:**
- `m_timespeed`, `m_motionblurport`, `m_motionalpha`

Implies: time dilation and motion blur control (cinematic slow-motion).

**Anatomy / Dismemberment:**
- `m_head`, `m_body`, `m_leftarm`, `m_rightarm`, `m_leftleg`, `m_rightleg`
- `m_lefthand`, `m_righthand`, `m_leftfoot`, `m_rightfoot`
- `m_dependentlimbs`, `m_rubberskeleton`, `m_dismembermaterialindex`

Implies: componentized anatomy with limb-specific interactions and dismemberment.

---

## Object Serialization

### PROP Blocks

Runtime gameplay objects are serialized using `PROP` blocks:

```
[PROP][uint32 size][uint32 prop_id][payload]
```

### Known Property IDs

| ID | Meaning | Payload |
|---|---|---|
| `0x080017D8` | Object name | uint32 length + null-terminated string |
| `0x080017DA` | Transform | up to 12 × float32 (local-space rotation matrix + position) |
| `0x080017DF` | AABB bounds | 6 × float32: min XYZ, max XYZ |
| `0x080018CB` | Child link ID | uint32 — used to group objects into hierarchies |

### Hierarchy Reconstruction

Objects are grouped by shared `ChildLink` ID. Within a group, the root is typically a `SkeletonModel` and children are body-part components (head, body, tail, bite targets etc.).

Successfully reconstructed example:
```
Hammerhead SkeletonModel
├── Hammerhead Head Fixed Brick
├── Hammerhead Body Fixed Brick
└── Hammerhead Tail Fixed Brick
```

Transform values represent local-space rotation matrices and positions. Bounds are axis-aligned bounding boxes. Spatial layouts match expected anatomy when visualized.

**Pipeline (archived scripts, now in `scripts/archive/`):** `scripts/object_parser.py` → `dumps/object_parser/objects.txt` → `scripts/hierarchy_rebuilder.py` → `dumps/hierarchy_rebuilder/scene_hierarchy.txt`

**SUPERSEDED (2026-07-16):** this `ChildLink`-ID cross-referencing approach was an early attempt before the real mechanism was found. CLAUDE.md now confirms `BRTR` parent-child nesting is **physical, not ID-based**: a child `CHBR` node sits directly inside its parent's `PRPS` payload, and nested transforms are LOCAL to the parent (not world-space) — world position requires composing the full ancestor chain (`world = parent_world ∘ local`) starting from the root "World" `PRPS` node. Current extractor: `scripts/resolve_brtr_hierarchy.py` → `scenes/<NAME>_resolved_hierarchy.json`. Validated: resolved node count (2,782) exactly matches the flat-scan `CHBR` tag count in `FISH.GDW`.

**Known bug, found 2026-07-30, not yet patched into either script:** both `rip_brtr_scene.py` and `resolve_brtr_hierarchy.py` locate `BRTR` with a naive `data.find(b'BRTR')`, which on some GDWs lands on a false-positive 4-byte match inside `RSRC` instead of the real top-level chunk (same class of bug as the `SCRT` false-positive elsewhere in this doc) — symptom is a nonsense declared size and, in the hierarchy resolver, an `AssertionError: expected root PRPS at start of BRTR`. Confirmed affected: `KATATAMA`, `BEACH`, `BEACHPST`, `START` (not yet swept across the rest). Fix: scan every match, keep only ones where the bytes at `+8`/`+12`/`+16` decode to `magic==0x01025024`, `root_count==1`, next tag `PRPS`, then take the largest such match (small embedded loading-screen sub-archives also pass this check but are far smaller). See CLAUDE.md's note under `scripts/rip_brtr_scene.py` for the exact fix snippet and verified real offsets.

### Important Note

~~The PROP regions currently decoded contain class/property **schema definitions** and **archetype metadata**, not necessarily fully instantiated world-space scene objects. Actual scene object instances with world-space transforms may exist in a separate region later in the file.~~

**RESOLVED — this uncertainty no longer applies.** `BRTR`'s `CHBR` nodes ARE the fully-instantiated world-space scene: 2,782 nodes in `FISH.GDW`, 1,161 with resolvable mesh references, full world transforms, AABBs, and (908 of them) baked per-vertex lighting colour. This has been extracted (`scripts/rip_brtr_scene.py`), hand-edited and reloaded live in-game successfully (see CLAUDE.md's "Live BRTR Editing" section), and even had new content injected into it — see CLAUDE.md's "Custom map feasibility" note.

### Surrounding PROP Structure

```
PRIM
  └── PRPS
        └── PROP
              └── CHBR
```

`PRIM` is a render node / render graph descriptor, not a raw geometry container. It references geometry indirectly rather than storing vertex data directly.

**DECODED (2026-10-03): `PRIM` is a node's collision link.** A `CHBR` node may carry a `PRIM` sub-chunk after its `PRPS`: class `0x20003002`, a zero ID, and its own `PRPS` with `PROP 0x080018D8` = `['MREG'][region_id]`, pointing the node at its `MREG` collision region (598 in FISH). A copied or generated `PRIM` gives an inserted object working collision (user-confirmed). See `CLAUDE.md` (Mesh reference clarification / BVH layout) and `docs/brtr_editing.md`.

**CORRECTED (2026-07-17):** this nesting order is wrong for `BRTR`/`SCRT` scene objects — CLAUDE.md's fully-decoded, byte-verified structure is `CHBR[size]` → `magic(0x0107402F)` + `node_id` → `PRPS[size]` → a flat list of `PROP` entries (mesh ref, name, transform, AABB, flags, etc.), i.e. `CHBR` is the OUTER container and `PROP` entries are direct children of `PRPS`, not the reverse. `PRIM` was not encountered decoding a real node this way — may apply to a different sub-system, or may be a mistaken early read. Individual `PROP` entries are each independently padded to a 4-byte boundary before the next tag (a general alignment rule that also applies at the top chunk level — missing this causes a full parse desync when decoding a property list by hand).

---

## Geometry Pipeline

### Confirmed GMDL Chunk Hierarchy

Fully confirmed by the working `rip_meshes.py` extractor. **11,948 `.obj` files extracted across all 20 GDWs.**

```
GMDL  [variable size]
  [12-byte sub-header: mesh_resource_id, count, hash]
  MATR  [52]        material colour properties
  MATS  [20]        material set
  GMAT              material definitions (GMAT1, GMAT2 sub-entries)
  TSET  [variable]  triangle sets / submeshes, one per MATS material (corrected 2026-10-01)
  TANG  [variable]  triangle data container
    VIND            uint16 triangle LIST index buffer (groups of 3 per triangle)
    TNOR            per-triangle normals
    TFLG            per-triangle flags
  VERT  [variable]  vertex data container
    POSI            float32 XYZ positions  (12 bytes/vertex)
    NORM            float32 XYZ normals    (12 bytes/vertex)
    UVUV            float32 UV coords      (8 bytes/vertex — one pair per vertex)
  VCOL              vertex colours         (16 bytes/vertex — RGBA float32, baked lighting)
```

Key implementation notes:
- `TANG` and `VERT` are **container chunks** — sub-chunks appear inside their payloads, not at the GMDL level
- Index buffer is a **triangle list**, not a strip (groups of 3 uint16 indices per triangle)
- `max(VIND)` must be `< POSI count` — use this to validate meshes and skip false positives
- V coordinate flip (`1.0 - v`) required for standard UV convention in OBJ output
- GMDL blocks with no POSI/VIND, or where max index ≥ vert count, are skipped
- **Triangle winding must be reversed on export (found + fixed 2026-08-17):** raw `VIND` order is DirectX clockwise-front; swap the last two indices per triangle (`a c b`) for OBJ/OpenGL's counter-clockwise-front convention. Verified via cross-product-vs-stored-`NORM` check: 0/1,422 sampled triangles agreed unswapped, 1,422/1,422 agreed swapped. This is what was causing meshes/levels to look "flipped or mirrored" — `BRTR` world positions and rotation matrices were independently checked and are NOT mirrored (positions validated against the real Amity Island map texture, rotation determinants are positive/proper for 1,153/1,161 FISH.GDW objects). All 20 GDWs re-extracted with the fix (2026-08-17); placed-object/mesh counts matched pre-fix totals exactly, confirming no regression. See CLAUDE.md's GMDL Chunk Hierarchy section for full detail.

### Model Types

| Class | Purpose |
|---|---|
| `GDModel` | General model — references geometry via `m_3dModelID` |
| `GDStripModel` | Triangle strip model class (name from class registry; PC format uses triangle lists in VIND) |
| `mcMeshCollection` | Mesh resource container |

### MSHH — Mesh Header

`MSHH` chunks contain named model references. In `TITLE0.GDW` these are immediately followed by names like `Shark2Reference`, `MSDolphinReference`, `MLHalRaj3Reference`. This links a named mesh resource to its geometry data in the RSRC chunk.

### Geometry Linkage (confirmed)

```
BRTR CHBR node
  → PROP 0x08001873: [GMDL tag][mesh_resource_id]
    → linear scan of RSRC for GMDL block whose 12-byte sub-header[0] == mesh_resource_id
      → TANG→VIND (triangle list) + VERT→POSI/NORM/UVUV (vertex data)
```

`rip_brtr_scene.py` builds the `resource_id → mesh_idx` mapping at runtime by scanning GMDL blocks in order.

### Dead End — `0x6FB887C` in `FISH.GDW`

This region was investigated extensively as a potential geometry source. It was **conclusively ruled out** by `scripts/vertex_stride_tester.py`.

At every tested stride (12, 16, 20, 24, 28, 32 bytes), all extracted "vertices" collapsed to the same degenerate value (`~0.0003, 0.0003, 0.0003`). This is characteristic of palette/CLUT colour ramp data being misread as float32 — not a vertex buffer. Do not revisit this region as a geometry source.

### PC vs PS2

This project targets the **PC version** of Jaws Unleashed, which uses **DirectX 8** (`d3d8.dll`). Older notes referencing DirectX 9 or PS2 VIF/GIF DMA packet decoding as the geometry barrier are incorrect for this platform. The PC geometry format uses standard DX8 vertex buffers — float32 XYZ positions, normals, and UVs — as confirmed by the working `rip_meshes.py` extractor. **Mesh extraction is complete: 11,948 `.obj` files extracted across all 20 GDWs.**

---

## Audio System

**Audio extraction is complete.** Two chunk types are fully parsed and exported. All outputs go to `audio/`. Scripts: `scripts/rip_smpb.py` (and `rip_smpc.py`); the original `rip_gsmp.py` was never in the repo, see `docs/audio_format.md`.

### GSMP (raw PCM sample blocks)

Header (24 bytes after the 8-byte chunk header): `[uint32 sample_id][uint32 flags][uint32 hash][uint32 category][uint32 sample_rate][uint32 byte_count]`

Audio data is signed 16-bit PCM mono immediately following the header.

| flags value | meaning |
|---|---|
| `0x01` or `0x81` | standard raw PCM block |
| base \| `0x20` | SMPB-type block (see below) |
| `0x44` | GSFX property block (no audio — contains volume float + GSMP ID reference) |

Category values: `2` = SFX, `3` = music (long loops, 2–3.5 min at 22050 Hz), `6` = ambient.

**Extracted: ~2,873 files across all 20 GDWs.**

### GSMP+SMPB (embedded voice lines)

A variant identified by `data[pos+16:pos+20] == b'OBPR'`. Contains an OBPR sub-chunk replacing the hash/category fields, then a 16-byte secondary header at `pos+16+8+obpr_size` (`[magic][field][sample_rate][byte_count]`), the PCM, and the usual 8 loop bytes (corrected 2026-11-23; read as 20 bytes before, which skipped 2 samples).

These appear to be unused/cut NPC voice lines present in the GDW files but not triggered in the shipped game.

**Extracted: 1,128 files across all GDWs.**

### WMV Cutscenes

Pre-rendered cutscenes in Windows Media Video format live in `movie/` in the game install directory. Audio extracted via ffmpeg to `audio/wmv/`. All WMA2 stereo 48000 Hz. Notable: `INTRO.WMV` (43s), `SHARK.WMV` (79s), `OUTSCENE.WMV` (53s), `PSYCHO.WMV` (157s), `JAWSC4–11.WMV` (unlockable 1975 film clips).

### Unlocated: in-game cutscene voice acting

Voice acting heard during in-engine cutscenes (driven by `NACutScene` / `MPGPlay` / `StreamPlay`) has **not been located**. The 20 GDW files and WMV movies appear to be the complete audio data. Possible remaining locations: unknown RSRC sub-chunks, obfuscated SCRT data, or BRTR audio-source nodes (1,621 non-mesh CHBR nodes include `Audio`-prefixed objects).

### Reflection metadata (engine audio classes)

- `GDSoundEvent2D`, `GDSoundEvent3D`, `GDSoundEventScope`, `GDSoundEvent3DB`
- `GDPlaySound`, `GDStopSound`
- `SoundManager`
- `m_SoundBankList`, `m_soundevent`, `m_sounddelay`

---

## Key Investigation Commands

```bash
# Find all GTEXT texture blocks
grep -oba "GTEXT" GAME_GDWs/FISH.GDW

# Find class/property metadata
grep -oba "NABiteTarget" GAME_GDWs/FISH.GDW
strings -td GAME_GDWs/FISH.GDW | grep -i sound

# Find DDS texture headers (alternate format)
grep -oba "DDS" GAME_GDWs/FISH.GDW

# Find specific PROP property IDs (binary search)
grep -oba $'\xd8\x17\x00\x08' GAME_GDWs/FISH.GDW | head

# Hex inspection at offset
xxd -s 0x06FB5000 -l 4096 GAME_GDWs/FISH.GDW
xxd -s 0x06F7B4A0 -l 256 GAME_GDWs/FISH.GDW
```

### Important Known Offsets (FISH.GDW)

| Offset | Contents |
|---|---|
| `0x06F7B4A0` | CLAS chunk — class registry metadata |
| `0x06F7B7C0` | Skeleton system — GDModel, GDSkeletonModel, XBone |
| `0x06FB5000` | Large reflection metadata region |

---

## Current Status

### Complete / Working

| System | Status | Output |
|---|---|---|
| Top-level chunk parsing | COMPLETE | — |
| GTEXT texture extraction (RGB24, RGBA32, 8bpp indexed) | COMPLETE | 4,923 PNGs across 20 GDWs (updated 2026-07-29, see `CLAUDE.md`) |
| GTEX texture extraction | COMPLETE | 2,787 PNGs across 20 GDWs (updated 2026-07-29, see `CLAUDE.md`) |
| Global texture ID database | COMPLETE | `textures/texture_db.json` — 1,049 unique IDs, 7,710 entries |
| Reflection metadata (CLAS) | CONFIRMED | class names, property names extracted |
| GMDL mesh extraction | COMPLETE | 11,948 `.obj` files across 20 GDWs |
| BRTR scene graph decoding | COMPLETE | 2,782 CHBR nodes in FISH.GDW; 1,161 with mesh refs |
| World-space scene reconstruction | COMPLETE (fixed 2026-10-01) | `scripts/brtr_scene_graph.py` + `rip_brtr_scene.py`, all 20 GDWs: nested composition, absolute-transform flag (`m_nFlags` `0x20000000`), reference instancing (`PROP 0x080017F0`), SC17 whale relocation. Earlier output placed nested meshes with raw local transforms and omitted every reference copy. See CLAUDE.md "Reference Instancing…" |
| Blender scene import | COMPLETE | `scenes/import_fish_blender.py` |
| Audio extraction — GSMP | COMPLETE | ~2,873 WAV files |
| Audio extraction — SMPB | COMPLETE | 1,128 WAV files (NPC barks, GSFX-triggered, **not** cut; corrected 2026-07-29, see CLAUDE.md) |
| WMV cutscene audio | COMPLETE | `audio/wmv/` via ffmpeg |
| d3d8 proxy mod | WORKING | freecam (F2), screenshot (F3), fog (F4), sim pause (F5), foliage hide (F6); **2026-10-01:** real shark XYZ + heading overlay, F8 teleport box + hand-editable bookmarks file, F11 invincibility + infinite hunger (replaces the old god mode removed 2026-08-12). See `mod/README.md` and `docs/exe_analysis.md` |
| `Jaws.exe` static analysis | STARTED (2026-10-01) | Ghidra project + player shark controller, brick memory layout, death paths, reflection field table, see `docs/exe_analysis.md` |

### Open Problems

| System | Status | Notes |
|---|---|---|
| Static environment geometry | **RESOLVED (2025-06-29)** | All terrain tiles, rocks, water planes, and dock structures ARE in BRTR as named mesh instances with full world transforms — no separate BSP/heightmap. |
| Skeletal animation | **RESOLVED (2026-07-17)** | `SKEL`/`BONE`/`WGHT`/`ROTS`/`BROT`/`MTOB`/`CHLD`/`ANIM` fully decoded — bind mesh, per-vertex weights, recursive bone hierarchy, per-bone quaternion keyframes sliced by named clips. Extractor `scripts/rip_skeletons.py` verified on all 30 of FISH.GDW's skeletons. Blender armature/animation import still not written. See CLAUDE.md's Skeletal Animation System section. |
| SCRT scripting chunk | **RESOLVED (2026-07-08)** | Not obfuscated, not scripting — a plain named screen-overlay object tree (same PRPS/CHBR/PROP format as BRTR). |
| In-game cutscene voice acting | NOT FOUND | Present in neither GSMP, SMPB, nor WMV files. |
| Parent-child hierarchy transforms | **RESOLVED (2026-07-16)** | Physical nesting, not ID-based; local transforms compose through the full ancestor chain to world space. See `scripts/resolve_brtr_hierarchy.py`. |
| Texture–mesh material assignment | **RESOLVED (2026-10-01)** | TSET submesh ↔ MATS → GMAT → TEXP, same-GDW textures only (`scripts/gdw_materials.py`). Per-submesh `usemtl` in mesh + scene OBJs, per-face materials in `scenes/import_fish_blender.py`. All 20 GDWs regenerated. The 2026-08-17 heuristic misread TSET counts as texture IDs. See CLAUDE.md "TSET Format" |
| Palette / indexed textures | UNSOLVED (unverified this session) | Some small textures decode incorrectly — likely CLUT/indexed format. Not re-checked in this pass; the PS2 side's palette/PSMT8 format IS fully decoded (see CLAUDE.md's PS2 Version Data section) but that's a separate format from whatever's wrong here on PC. |
| New: brand-new BRTR node insertion | **SOLVED (2026-10-03)** | Was "unsolved" since 2026-07-17. Inserting new nodes works (`scripts/insert_brtr_node.py`, `build_scene.py`); the July attempts all cloned node 302, a hidden render-layer companion. Custom meshes, collision, textures, transparency, Blender scene export and a stripped blank base level all work now. See `docs/brtr_editing.md`. |

---

## Engine Architecture — Confirmed Layout

```
GDW (little-endian, chunk-based)
├── [44-byte text preamble]  "GDED BINARY FORMAT, VERSION 2.6.3.16.\r\n\r\n\x00\x00\x00"
├── FSIZ   [4 bytes]         payload = byte offset where SKIP begins (NOT total file size)
├── VERS   [13 bytes]        version string
├── EXBY   [10 bytes]        exporter's login name ("gyozo" in FISH)
├── GNRL   [8 bytes]         general archive data
├── WDIM   [40 bytes]        world dimension bounds (~5000×2000×5000)
├── RSPR   [0 bytes]         unknown, always empty
├── CLAS   [~250 KB]         class/reflection database — length-prefixed class+property strings
├── RSRC   [~111 MB]         packed resource payloads
│    ├── GMDL blocks         geometry models (VIND/POSI/NORM/UVUV/TSET etc.)
│    ├── GTEXT blocks        textures (TGA-wrapped RGB24/RGBA32)
│    ├── GTEX blocks         sprite/overlay textures
│    └── GSMP blocks         PCM audio samples
├── BRTR   [~5.4 MB]         pre-built scene graph — all placed object instances
│    └── CHBR nodes          one per placed object (name, transform, mesh ref, AABB, vcol)
├── SCRT   [~12 KB]          top-level (NOT inside RSRC), screen-overlay object tree — resolved, not obfuscated scripting
├── SKIP   [variable]        0xFF-filled padding so FDIR lands on a 512-byte boundary
├── FDIR   [40 bytes]        real offset+size index — points at a second, complete, embedded GDED archive
├── ENDF   [0 bytes]         terminates the FIRST embedded archive only — NOT the true EOF
└── [second embedded GDED archive] own VERS/EXBY/GNRL/WDIM/RSPR/CLAS/RSRC/BRTR chain, no FSIZ/SCRT/SKIP/FDIR/ENDF —
      confirmed (on OPEN_S.GDW) to be a bundled loading-screen scene for level transitions
```

**Corrected (2026-07-17):** the original version of this diagram put `SCRT` inside `RSRC` and called it obfuscated scripting, and omitted `RSPR`/`SKIP` and the second embedded archive entirely. See the corrected chunk table above and CLAUDE.md for full details.

The engine is **component-driven and editor-authored**. Runtime gameplay objects are assembled from serialized components with reflected properties. The format preserves a remarkable amount of internal metadata — class names, property names, and object names are all stored as readable strings, making many systems self-documenting. The container version date `20030626` (June 2003) is not an engine freeze: block formats were still revised in 2005 (see "Block format date stamps").

---

## Moved from CLAUDE.md (2026-11-25)

The text below was moved word for word from the root `CLAUDE.md`. It is newer than earlier sections of this file where they disagree.

## GDW Archive Format

`.GDW` files are chunk-based binary containers (little-endian).

**Engine lineage (confirmed 2026-10-11, the user's claim; Claude was hesitant until it was checked):** the format is Appaloosa's **Game World Builder (GWB)** output, the same tool suite as *Ecco the Dolphin: Defender of the Future*. Defender's PS2 `.GDE` levels start `GDED BINARY FORMAT, VERSION 2.1.12.1` (Jaws: 2.6.3.16) and use the same chunks (`GNRL` `WDIM` `RSPR` `CLAS`/`BRCM`/`ACCM` `RSRC` `BRTR` `SCRT`, `CHBR`/`PRPS`/`PROP`, `ACTN`, `GMDL`, `GTEX`, `MREG`, `STRP`) and `GD` classes, packed without 4-byte padding. Appaloosa's 2001 press kit (`docs/sources/Appaloosa_PS2_press_information_2001-09.pdf`) describes GWB as built from "bricks, actions and resources". Details: `docs/GDW_FORMAT.md` "Engine lineage".

**Editor vs. engine (user information, 2026-11-24):** Game World Builder is Appaloosa's in-house **editor** for building the world environments; the runtime **engine** is a separate in-house custom engine called **Diesel Power**. Source: the PAL Dreamcast *Ecco: Defender* back cover (2000, MK-51033-50): "GameWorld Builder™ Software Technology & Diesel Power™ Game Engine are the property of Appaloosa Interactive Corp" (user's scan, `docs/sources/Ecco_Defender_Dreamcast_PAL_back_cover.png`). That Jaws still uses Diesel Power is inferred from the shared Ecco codebase; the name isn't in `Jaws.exe`, the PS2 exe, any GDW or the 2001 press kit. Not to be confused with GRIN's unrelated "Diesel" engine.

**Format date stamps (2026-10-21):** block format versions are literal **YYYYMMDD dates** that `Jaws.exe`'s loaders `cmp` against: `WDIM` 19980304, `GNRL` 19980331, `GMAT` 19980409, `GMOV` 19991005, `GSMP` 20001201, **`SKEL` 20020410** (all 752 skeletons), `GTEX` 20050515 (the texture "stamp `0x0131F253`"), `GMDL` 20051205, `RSRC` 20051208, PS2-only 20060316. The `VERS` string `20030626` is the container version date, **not an engine freeze** (older docs said so; corrected). The only 2001–2002 date anywhere in the files or exe is the April 2002 skeleton revision; raw-scan hits like 20011008–13 are pixel-data noise. Exe: PE timestamp 14 Sep 2006, `(c) 2004 Majesco`, libpng 1.0.5 (1999). Table: `docs/GDW_FORMAT.md` "Block format date stamps".

**File header:** A 44-byte plain-text preamble before the first chunk:
```
GDED BINARY FORMAT, VERSION 2.6.3.16.\r\n\r\n\x00\x00\x00
```
Chunks start at byte offset 44 (0x2C).

**Chunk structure:**
```
[4-byte FOURCC tag][uint32 size][payload]
```

Chunks may contain nested subchunks. Known top-level chunks (in order as they appear):

| Chunk | Offset (FISH.GDW) | Size | Description |
|---|---|---|---|
| `FSIZ` | 0x2C | 4 | File size metadata |
| `VERS` | 0x38 | 13 | Version string |
| `EXBY` | 0x50 | 10 | Unknown — small header block |
| `GNRL` | 0x64 | 8 | General archive data (8-byte placeholder in FISH.GDW) |
| `WDIM` | 0x74 | 40 | World dimension bounds (~5000×2000×5000) |
| `RSPR` | 0xA4 | 0 | Unknown — always empty in FISH.GDW |
| `CLAS` | 0xAC | ~250 KB | Class/reflection database |
| `RSRC` | 0x3D43C | ~111 MB | Packed resource payloads (contains GMDL, GTEXT, GTEX, GSMP, etc.) |
| `BRTR` | 0x6A42B40 | ~5.4 MB | **Scene graph / resource tree** — see Scene System section |
| `SCRT` | 0x6F77FC8 | 12,576 | **Screen/overlay object tree** — see note below. Not scripting, not obfuscated. |
| `SKIP` | 0x6F7B0F0 | 264 | **Sector-alignment padding** — payload is all `0xFF` bytes, sized so the following `FDIR` starts on a 512-byte file-offset boundary. See note below. |
| `FDIR` | 0x6F7B200 | 40 | File directory footer |
| `ENDF` | 0x6F7B230 | 0 | Archive terminator |

Each chunk (including nested ones) is padded to a 4-byte boundary before the next tag begins — account for this when walking the chain, or offsets will drift.

**FDIR chunk structure** (32-byte entries, 8-byte header) — corrected 2026-07-17, FDIR is a real offset index, not just names:
```
Header: [uint32 magic/build-date][uint32 entry_count]
Entry:  [uint32 offset][uint32 size][24 bytes name, null-padded]
```
FDIR names are sub-archive identifiers, not individual asset names (e.g. `FISH00`, `TITLE00`–`TITLE0F`, `AQUARI00`). Each entry's `offset`/`size` point at a second, complete, independently-embedded `GDED BINARY FORMAT...` archive concatenated after the primary archive's `ENDF` (see note below) — verified on `FISH.GDW`: entry `FISH00` decodes to `offset=0x6F7B400, size=14415320`, which exactly matches that archive's real start and satisfies `offset+size == EOF`. **Any edit that grows a chunk before this offset (e.g. appending to `RSRC` or `BRTR`) must patch this field by the same delta**, or the game will seek to the wrong place for the second archive. Individual textures/meshes have no stored names in FDIR; they are identified by their numeric resource ID.

**Note on the second embedded archive (found 2026-07-15, mechanics decoded 2026-07-17):** every GDW's declared `ENDF` is not the true end of the file — a second, complete, independent `GDED BINARY FORMAT...` archive (own preamble, own `VERS/EXBY/GNRL/WDIM/RSPR/CLAS/RSRC/BRTR` chain) is concatenated immediately after, padded to reach it with `0xFF` bytes just like `SKIP`. This second archive has **no `FSIZ`, `SCRT`, `SKIP`, `FDIR`, or `ENDF` of its own** — it just ends at true EOF right after its own `BRTR`. Confirmed on `OPEN_S.GDW` (11 such embedded sub-archives) to be **bundled loading-screen scenes** for level transitions (e.g. one named `OPEN_S00`/`LevelLoaderKAT`, holding progress-bar/hint-text UI objects for transitioning to `KATATAMA.GDW`) — not terrain, not cut content. Bounded story levels carry one small (~14MB) embedded archive (mostly a shared/duplicate stub); open zones carry many more, proportional to how many destinations they connect to. `FISH.GDW`'s own second archive has a ~14MB `RSRC` and a tiny (~6KB) `BRTR` (a handful of `CHBR` nodes), consistent with a small loading-screen scene but not independently re-verified by node name.

**Note on PROP-level alignment (found 2026-07-17):** the "padded to a 4-byte boundary before the next tag" rule (see below) also applies **inside** `PRPS` payloads, i.e. individual `PROP` entries are each individually 4-byte-aligned, not just top-level GDW chunks. Missing this causes a full parse desync when decoding a `CHBR` node's property list by hand — probably a general rule for all nested tag sequences in this format (TSET/TANG/VERT sub-chunks not re-verified against it, but suspected to hold there too).

**Note on `SCRT` (corrected 2026-07-08 — do not trust earlier "obfuscated scripting chunk" claim):** There are two `SCRT`-tagged byte sequences in `FISH.GDW`. The one previously documented at offset `0x1105ECC` **inside** `RSRC` is a **false-positive tag match** — its "size" field decodes to over 1 billion, which is impossible, meaning it is not a real chunk header at all, just a coincidental 4-byte pattern inside unrelated binary/compressed data (the printable-ASCII-but-noise bytes seen there are not obfuscated script code, they're just whatever data happens to sit next to the coincidental match). The **real** `SCRT` chunk is a normal **top-level** chunk (sibling of `BRTR`/`FDIR`, not nested in `RSRC`) at `0x6F77FC8`, and it is **not obfuscated** — it uses the same plain `PRPS`/`CHBR`/`PROP` tree format as `BRTR` (see Scene / Object System section). Its root node is named `"Screen"` and its 20 `CHBR` children are named render/overlay targets: `Whale, GDScreen 3-7, CrowdScreenek, WaterSurface, TransparencyAbove/Below/Blur, ReflectionAbove/Below/Blur, ScreenWater/Above/Below, MotionBlur, ZZZ, XXX`. This is a small **screen-space post-processing overlay tree** (water surface reflection/refraction targets, transparency layers, motion blur, crowd billboard, a "Whale" screen effect) tied to the `GDScreen`/`GDOverlay`/`GDForceOverlay` engine classes seen in `CLAS` — not a scripting/gameplay-logic chunk. It reuses the same object-name property (`0x080017D8`) as `BRTR` CHBR nodes, plus a second, still-undocumented property range (`0x08001980`–`0x08001993`) specific to these screen objects. The PS2 `_FISH.GDE` file has the equivalent chunk (also top-level, 8,772 bytes, 14 `CHBR` children) but its nodes use a different but parallel ID range (`0x08001957`–`0x0800196A`) and have no name property set — see PS2 Version Data section.

**Note on `SKIP` (decoded 2026-07-08):** `SKIP` is sector-alignment padding, nothing more. Its payload is entirely `0xFF` bytes, and its size is always exactly what's needed so the byte offset immediately after it (where `FDIR` begins) lands on a multiple of 512. Confirmed across FISH, TOWN, START, AQUARIUM, TITLE0 (PC) and `_FISH.GDE` (PS2) — sizes vary per file (20–428 bytes) because `SCRT` ends at a different arbitrary offset each time, but the post-`SKIP` offset is always `% 512 == 0` in every case checked. No further structure to parse.

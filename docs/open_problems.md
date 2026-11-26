# Open problems

**In short:** what's still unknown or unfinished, by topic. Each item links to the doc with the details. Solved items are listed briefly at the end.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/open_problems_old_2026-11-27.md`.

---

## Contents

1. [Level scripting (`GDControl`)](#1-level-scripting-gdcontrol)
2. [Skeletons](#2-skeletons)
3. [Custom levels](#3-custom-levels)
4. [Draw distance](#4-draw-distance)
5. [Property values and render flags](#5-property-values-and-render-flags)
6. [Undecoded data](#6-undecoded-data)
7. [Cut content](#7-cut-content)
8. [Speedrun: push barriers](#8-speedrun-push-barriers)
9. [Engine history (GWB)](#9-engine-history-gwb)
10. [To do](#10-to-do)
11. [Solved](#11-solved)

---

## 1. Level scripting (`GDControl`)

Scripting is decoded and custom triggers work (`docs/brtr_editing.md`). Still open:

- What node flag `0x400000` does (ops `0x2000`/`0x4000`).
- Why "kill" leaves an object solid. Suspend, hide, or clearing `0x10`/`0x40` each remove it fully (user-tested).
- Spawn modes 3 vs 4.
- How quest code starts controls that no other control starts.
- Whether the dangling `missing#` targets are deleted objects or runtime-created ones.
- Which engine code creates group-node actions at load. Not traced.

---

## 2. Skeletons

Skinning and animation are solved (`docs/animation_system.md`). Still open:

- Bone names.
- How bodies bind to the shared human skeleton (`GlobalSkeletonAnim`) at runtime.
- Playback rate.
- `MORF`.

---

## 3. Custom levels

Custom levels work end to end (`docs/custom_level_tutorial.md`). Still open:

- **The fade-out test for very large objects:** pivot, bounding sphere or distance? Worked around by tiling.
- **`OssLoadChecker.m_type` values** ↔ prompt slots.
- **Exits to other destinations** than the base level's own. Needs a new `GDLoad` stage name per zone.
- **Strip lists** for base levels other than FISH.
- **The minimap** still shows FISH's map picture.
- **Level music:** whether to drop the 41 MB `SndMusic`. Undecided.

---

## 4. Draw distance

The mod's `Shift+F4` far view works (user-confirmed 2026-11-25, used in normal play). Still open (`docs/rendering_system.md`):

- **Why an underwater far plane past ~400 breaks visibility:** shipwreck flicker, barriers only up close, NPC culling. Maybe the same mechanism as the large-object fade.
- **What crashed at 2500.**
- **The camera's linked objects** at `+0x2E4` / `+0x2EC`. Their `+0x50` is the far plane used when crossing the surface.

---

## 5. Property values and render flags

Every `PROP` ID has an exact name, from the level's `CLAS` field table (`docs/scene_graph.md`). What's open is what the **values** mean:

- **Bit layouts** of the named fields, e.g. `m_Viewport`. Only `0x20003` = above + underwater is confirmed.
- **Hidden companion nodes:** which of `m_StaticLights`, `m_RenderSetting` or missing vertex colours hides the companion layer.
- **`TFLG` per-triangle flags.** Generated collision with all edge bits set works.

---

## 6. Undecoded data

- **`MOIL`** inside `GMOA` (~66 KB). Maybe AI path or navigation data.
- **Unused material data:** extra `TEXP` layers beyond the base texture, and `GMAT` colour, shininess and transparency parameters.
- **PS2 `BNCH`:** how its ~1,272 80-byte transform records map to the 3,495 names.

---

## 7. Cut content

Details in `docs/cut_content.md`.

### Hot Pursuit restoration

The quest plays end to end in `PURSUIT` (`scripts/build_pursuit_test.py`). To do:
- End the jet ski's route in open water. It rams the bank at the canal's north-west corner.
- Several jet skis, plus boss jet skis (`m_JetSkiBossIDList`).
- Solid gates.
- On-screen goal text, via message overrides.
- Maybe an open-water version near the lighthouse, matching the goal text.

Not yet understood:
- `ANPosition` fields beyond route, speed and crew.
- Why some boats (top-level sailboats with tiny boxes) aren't removed outside their box.
- The details of `RequestStage` flag 2.
- `0x69AC70(0x8000)` on the fail path.

### Hot Pursuit's original scope

- Did the mission span MINEMSHA (canals) and OPEN_NE (lighthouse, `HOTPURSUIT` marker) as one sequence, or were they two separate ideas?
- Which lighthouse the goal text means. The modelled Coast Guard HQ one is the best candidate, but it's ~5,900 units from the `HOTPURSUIT` marker.

### Aurora rope fight

`NAAuroraRope` is decompiled (`docs/cut_content.md` §3). Still open:
- `NARope` base fields (segment setup).
- `NAAuroraRopeBuoyRopeInteractor`.
- The state set to 6 on reel-in.
- `MBAurora`'s collision mask `0x4000`.
- **Placing a working rope in START.** Needs the rope, `MBAurora`, rock excluders, HUD wiring and a movie.
- Side item: the `Kotelszakito` copies in FISH and `OPEN_*`.

### Old Brody

The older Brody model on the boss Aurora is checked (`docs/cut_content.md` §4). Open: compare it with the beta screenshots and trailer.

---

## 8. Speedrun: push barriers

- How the shark turns buoy (`ANTol`) and current (`NAWhirl2000`) pushes into motion.
- Whether a terrain clip exists without no-clip.

See `docs/speedrun_glitches.md` §13.

---

## 9. Engine history (GWB)

Most lineage questions are answered (`docs/gwb_lineage.md`). Still open:

**Defender builds:**
- Retail Dreamcast vs the dev builds, in detail.
- The PS2 Defender program's loader.
- Testing the Feb 2000 prototype's three cut levels in an emulator (`docs/ecco_leftovers.md` §8).

**Jaws symbols from `ECCO.ELF`:**
- More function names: loosen the call-graph thresholds, or match non-virtual engine code by hand.
- Finish the `GDBrick`/`GDBase` mapping: `+0x18`, `+0xE8`, `+0xF0`, `+0xF4`.
- Whether `EXTR`/`SoulContainer` code shows up in Defender's symbols.

**The May 1999 Defender builds** (`docs/gwb_lineage.md` §4):
- What the shark's `STOP` message means. How `Ctrl.cpp` `0x8C0455BC` moves Ecco on `DRAG`/`PULL`.
- `SharkTrap` (a 5 KB `Execute`) in detail.
- The `Victim.cpp` classes.
- Names for the slot-7 `GetFactory` getters.
- Compare the 1999 levels (`2_OPEN`, `3_REEF`, `5_ATLANTIS`, `6_VICTIM`, `7_LOADING`) with their shipped versions.
- Decode the `.INP`/`.GSG` demo recordings.
- The 2 unresolved assert line numbers.
- The second slot block (~2,600 slots) outside the main vtable block.
- Match the "Ecco 3D" viewer program (May 6) separately. Same asserts; 5 files differ.

**Exporter logins** (`docs/gwb_lineage.md` §7): `balage` and `Zolcsika` are ambiguous; `gyozo`, `martens` and `AnChoR` are unmatched. Only compare against published credits; don't research private people.

### Other titles
- Did any Appaloosa title from 2001–2005 use GWB? No GWB 1.x has been found either.
- **Mermaid demo and *Smurfs*:** no files are public. If one surfaces, check the `GDED` preamble, version and class registry. Whether Jaws's cage sparkle (`0x1DA`) came from *Smurfs* needs its files.
- ***EdgeRacers*** (Twofish.hu, finished but shelved): engine unknown. Ways to answer: a build, a former developer's memory (Ed Annunziata wasn't on the GWB games; former Appaloosa staff, e.g. at A&R Atelier, would know), or in-game video.
- ***SmartyAnts*** (2010): the installers hold no game data. Files to look for, e.g. on the Wayback Machine:
  - `http://s3.amazonaws.com/SA_boot/SmartyAnts.start.pack`, `…/launcher.exe`, `…/updater.exe`, `…/dx.pack`, `…/contentState.txt`;
  - `…/SmartyAnts-Launcher.jar` (Mac; maybe under a folder like `macus/`);
  - the folder listing `…/SA_boot/`;
  - the same under `smartyants.com.nefficient.co.kr/SA_boot/`.

  The user found none (2026-11-26). If a `.pack` turns up, check for a `GDED` header, GWB tags and `EXBY` logins, and for Torque traits (`.cs`/`.dso` scripts, `.dts`/`.dif`/`.dae` models).

---

## 10. To do

- **Sweep all levels for stray objects** (user request, 2026-11-25), like MINEMSHA's `k2 03`:
  - nodes outside the playable area;
  - meshes from another level's set at an odd scale;
  - shrunk or hidden copies;
  - nodes nothing refers to (no child list, `GDControl`, reference or action).

  Aim: find real leftovers without spotting them in-game. Expect mostly junk.
- **Housekeeping:** `particle_compare/` holds extracted game textures. Keep it out of the public repo.

---

## 11. Solved

Kept short; details are in each topic's doc.

**Formats and scenes:** FISH whale position, scene mesh-index mismatch, static terrain (in `BRTR`), skeletal animation, parent-child hierarchy, `SCRT`, `SKIP`, texture–mesh link, Blender mirroring, `BRTR` false-positive offset, `PRIM`, `STRI`/BVH layout, "GTEXT" (not a tag), class ID → name, all `PROP` IDs named (2026-11-25).

**Level editing (2026-10-03/04):** new nodes, custom meshes, collision, textures and transparency, Blender scene export, blank base levels (`--minimal`, `--blank`), in-game reload (F10), `GDControl` scripting, custom triggers, large-object fading (tiling), area triggers and exit zones, stage redirect, message tables, the custom-level kit and tutorial, custom levels as their own stage (F9), resource pruning.

**Audio:** cutscene voice acting (`SMPC`, 2026-10-03).

**Cut content checks:** BEACH "cut objective" (not cut, 2026-10-03), MINEMSHA's stray rock `k2 03` (2026-11-25).

**Exe and mod:**
- Defender debug build: `0.BIN` is junk, but `ECCO.ELF` has full symbols; 812 Jaws functions named (2026-11-25).
- Text-format levels load in-game (2026-11-25). Closed by the user as not practical.
- The mod overlay leaking into render-to-texture passes: fixed by drawing in `Present` (2026-11-25, user-confirmed).

**Engine history (2026-11-26):** Sentinels `EXTR`, header/footer dating, the Defender DC vs PS2 comparison, the `jts` = Tamás Jutasi match, *Wacky Races* and *Contra* (not GWB), the May 1999 builds (GWB 2.1.1.6), the "2007 Xbox Ecco" (emulation, not GWB), scratch-folder cleanup, `RefsDecomp.java` and `pvr_decode.py` moved into `scripts/`.

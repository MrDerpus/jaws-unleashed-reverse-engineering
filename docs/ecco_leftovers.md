# Ecco the Dolphin leftovers in Jaws Unleashed

**In short:** *Jaws Unleashed* was built from the code of Appaloosa's *Ecco the Dolphin: Defender of the Future* (2000), not just from its engine. It came through the code of the cancelled sequel *Sentinels of the Universe* (2001).

Jaws keeps:
- the whole engine;
- 62 of Ecco's game classes, mostly effects;
- a few old Ecco features that are compiled in but never used, such as Ecco's ball-shaped fish schools, which we got working again.

None of what makes Ecco *Ecco* survived: no dolphin, sonar, air meter or Ecco levels.

This doc also covers older Ecco material (cut Defender levels and a cut shark attack) and what Appaloosa did around and after Jaws. The engine's history is in `docs/gwb_lineage.md`.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/ecco_leftovers_old_2026-11-27.md`.

---

## Contents

1. [Verdict: Jaws was built from Ecco's code](#1-verdict-jaws-was-built-from-eccos-code)
2. [What came over](#2-what-came-over)
3. [Fish schools and splashes from the *Sole Predator* screenshots](#3-fish-schools-and-splashes-from-the-sole-predator-screenshots)
4. [`MLHalRaj` fish schools restored in Jaws](#4-mlhalraj-fish-schools-restored-in-jaws)
5. [How Jaws reused and changed Ecco code](#5-how-jaws-reused-and-changed-ecco-code)
6. [The 62 classes](#6-the-62-classes)
7. [How this was measured](#7-how-this-was-measured)
8. [Cut Defender levels in the Feb 2000 prototype](#8-cut-defender-levels-in-the-feb-2000-prototype)
9. [Cut shark grab attack (May 1999)](#9-cut-shark-grab-attack-may-1999)
10. [Appaloosa Mermaid tech demo (2001)](#10-appaloosa-mermaid-tech-demo-2001)
11. [Cancelled Appaloosa projects and the *Smurfs* video](#11-cancelled-appaloosa-projects-and-the-smurfs-video)
12. [After Appaloosa: Twofish.hu](#12-after-appaloosa-twofishhu)
13. [Open questions](#13-open-questions)

---

## 1. Verdict: Jaws was built from Ecco's code

**Supported:** *Sole Predator* / *Jaws Unleashed* was built from *Ecco: Defender of the Future*'s codebase. A game started fresh on the bare engine wouldn't contain Ecco game code. `Jaws.exe` has some that is no use in a shark game.

**The evidence:**
- **Dead Ecco gameplay is compiled in.** Ring swimming (`NARingAct`), fish schools (`MLHalRaj`) and splashes (`TRSplash`) are in the program and never placed in any Jaws level. They came along with their source files.
- **Ecco code was edited in place.** `NAWhirl2000` lost exactly one field, `m_noecco`, which became `m_noshark`.
- **Names were kept and reused.** `DDGameState` is still one node per level, with all 18 Ecco fields replaced. `TRActor` is the same.
- **Ecco and Jaws classes share source files.** Jaws's man-o'-war classes are built on Ecco's jellyfish code.

**Spot check:**
- `Jaws.exe` has no "Ecco" string, and none of `EccoGame`, `DolphCtrl`, `TRWorld`, `m_SonarMap`, `m_eccoarea` or `m_noecco`.
- Its two "ECCO" hits are Italian dialogue: "ECCOLO!" = "there he is!".
- The surviving names (`DDGameState`, `DDMedusaAct`, `DDFieldAct`, `MLHalRaj`, `MLMadarRaj`, `TRActor`, `DDThrow`, `NATestAct`) are all there. Their virtual functions pair up one-to-one with Ecco's (`~/Projects/ECCO/re/func_pairs.tsv`).

**The route: through *Sentinels*.** The cancelled sequel *Sentinels of the Universe* (Feb 2001) shares 13 brick, 28 action and 3 property classes with Jaws that Defender doesn't have.
- These include the whole skeleton system, Jaws's fish school `MLHalRaj3`, `NAGenerator`, `NARubberSkeleton`, `MLEnemy` and `NAHair`.
- Only 6 classes are in Defender and Jaws but missing from Sentinels: `GDMultiTexture`, `NAPredatorModel`, `NAModelFade`, `NASubdivide`, `StoreInput`, `GDPropExtRenderSet`.
- Per the user, Jaws was made after Sentinels was cancelled. So the cancelled sequel's code became the base for Jaws. Details: `docs/gwb_lineage.md`.

**Not settled:**
- Was the whole Ecco project copied and mostly deleted, or were chosen source folders imported? Only 14 of 933 `DD`/`TR` classes remain. Both would leave the same traces.
- Were there other Appaloosa projects in between, from 2001 to 2006? Unchecked.

---

## 2. What came over

Jaws keeps three different kinds of Ecco-era code:

1. **The engine** (`GD*` classes, 107 shared). One library block in both programs. Some classes were dropped and some added, but it's the same engine.
2. **Ecco's game code** (`DD`, `TR`, `NA`, `ML`, `P` prefixes): **62 of Ecco's ~2,385 classes**. Jaws kept them in their original source files and added new Jaws classes beside them. These are the real leftovers.
3. **Names reused for new code.** A few classes kept their Ecco name but were rewritten: `DDGameState`, `MLEnemy`, `TRActor`, `PS2Shadow`.

**Of the 62 game classes:**
- **About 32 are placed in Jaws levels.** They are mostly general effects that Jaws uses on purpose: fades, flares, vertex waves, lightning, explosions, turn-to-target.
- **The other 30 are never placed.** That's where the real Ecco leftovers are.

---

## 3. Fish schools and splashes from the *Sole Predator* screenshots

**The user's observation** (from beta screenshots; not examined in the project):
- Schools of fish swim in **ball shapes**, like Defender's.
- **Splashes and particles appear when breaching**, like Defender's.

**The matching Ecco classes:**
- Fish schools: `MLHalRaj` (*halraj* = fish school). Compiled into `Jaws.exe`; never placed in any PC or PS2 level.
- Splashes: `TRSplash`, never placed, and `NAParticle2000`, placed only twice, both in KATATAMA.

**The user's theory:** these are *Sole Predator* leftovers. They were live while the game was *Sole Predator* and dropped later.

**Checked: it fits.** The shipped game replaced both with newer classes, and the old ones had been edited before being dropped.

### Fish schools

- **The shipped schools are `MLHalRaj3`.** In-game they're long columns of one fish type.
  - Placed 121 times on PC (137 on PS2).
  - With `MLHalRaj3Catch` (121, the bite and blood hookup) and `MLHalRaj3Reference` (296 copies).
- **`MLHalRaj3` came from *Sentinels*, not Jaws.** It isn't in Defender, but it is placed once in Sentinels' `420_HangCaverns`.
- **It's a rewrite, not a rename.** 31 fields, none shared with Ecco's class:

  | | Ecco's `MLHalRaj` | `MLHalRaj3` |
  |---|---|---|
  | Shape | Box volume (`boxx/y/z`), clusters (`ccount`) | Group size and depth (`m_groupsize`, `m_groupsizez`), side ratio (`m_sideratio`) |
  | Movement | Follows a leader (`maxleader`) | A wave (`m_waveamp`, `m_wavefreq`) |
  | The player | Flees Ecco (`ecconear`) | Fears the shark (`m_enemy`, `m_feardist`, `m_fearspeed`) |
  | Other | — | Health; light and colour by depth |

- The "3" implies an `MLHalRaj2`, which is in neither program.
- More Jaws-only fish classes: `MSHalraj` (10 placed, with attack fields), `MSPathFish`, `MSGeneralFish`, `MSFishGenerator`.
- **The old `MLHalRaj` was edited before it was dropped.** In `Jaws.exe` it has 25 fields: Defender's 23 plus `mincolor` and `maxcolor`. It still has `ecconear`, the distance to Ecco. The colour fields were added in *Sentinels*.

### Splashes

- **The shipped splashes are `NAWaterSplashAct`**, which isn't in Ecco. Placed 867 times on PC.
- **`TRSplash` lost its three sound fields** (`m_Sound1`–`3`) in *Sentinels*, and then was never placed.

**What those three sound slots held in Ecco** (checked in all 48 Ecco levels):
- Of 105 `TRSplash`es, exactly **one per level** (in 11 levels) has its sounds set: the player's splash. The others are silent.
- The three slots always point to `_eccosounds\esik1.wav`, `esik2.wav` and `esik3.wav`, in that order. *Esik* is Hungarian for "falls".
- In Ecco, by ear (user): breaching gives a splash on leaving the water, bubbling when the air meter refills, and another splash on landing. *Esik* fits the landing splash best.
- Which file is which sound isn't matched yet. Ecco's sound banks (`SFX/*.SAB`) extract without names.
- Jaws has no air meter, and removed all three slots.

**Conclusion:** both effects in the screenshots match Ecco classes that were **changed, then replaced** by newer classes. That supports the theory that they were in use during development. Nothing dates the swap.

**Not yet checked:** does any dangling script target or deleted node ID point at an old `MLHalRaj` or `TRSplash`?

---

## 4. `MLHalRaj` fish schools restored in Jaws

**In short:** Ecco's old fish school runs in the shipped `Jaws.exe` unchanged. It worked first try (user-confirmed, 2026-10-21). 10,000 fish run with no frame drop.

**Build and play:**

```bash
python3 scripts/build_fishball_test.py --deploy FISHBALL
```

Then press F9 in-game and pick FISHBALL. It puts three schools of WRACK's clownfish in front of the start point of the blank FISH level.

### What it looks like

- Not a true ball. One leader wanders, and the others hold random positions around it. That gives the swirling clumps of Defender, the Mermaid demo and the beta screenshots, not Jaws's long columns.
- **Scaled up** (user requests): version 2 had about 3× the fish. Version 3 had 50×: **3,000 + 5,000 + 2,000 = 10,000 fish, with no frame drop** (user-tested). The fish count has no limit in the code.

### Old schools vs shipped schools

The level also holds two stock Jaws schools, for comparison.

| | Ecco's `MLHalRaj` | Jaws's `MLHalRaj3` |
|---|---|---|
| Fish | Real 3D models | Flat sprites (`GD3dSprite` subclass, one material) |
| Placed as | An action on an ordinary brick | A template brick plus `MLHalRaj3Reference` copies |
| Can be eaten | No | Yes (`NABiteTarget` + `MLHalRaj3Catch`) |
| Flees from | Objects in its `felid` list | `HalRiaszto` ("fish alarmer", 26265), a child of the shark |

Because `MLHalRaj3` draws sprites, a clownfish version of it can't be made. The beta screenshots' 3D-looking ball schools fit the old class.

### How to place one

- **No `CLAS` edit is needed.** Every level's action list already names `MLHalRaj`, at FISH index `0x143`. The class word is `0x02144143`.
- PROP IDs in FISH: `0x08000984` + field index.
- **Layout,** copied from Ecco's 120NORTH (node 6354):
  1. a `GDStdBrick` carrying the action;
  2. then an empty `GDStdBrick`;
  3. then the fish model.

  All three need `m_nFlags` `0x12`.

### How the code works

Jaws `MLHalRaj` vtable `0x7DD0D4`.

**Start-up** (`0x4E9A80`):
- takes the brick's child, or grandchild, as the fish model;
- hides it;
- sets up arrays for every fish.

**Each tick** (`0x4EA3E0`):
- Fish 0 leads at `maxspeed`. It picks a new random heading every `ccount` to `ccount + ccountrnd` ticks.
- The leader turns back when it leaves the sphere `mrange`, or the box `boxx/y/z` when `mrange` is 0.
- Every other fish steers to the leader's position plus its own random offset.
  - x and y: within ±`frange`/2.
  - z: from 0 to −`rangez`, or ±`frange`/2 when `rangez` = −1.
- Speed is `maxspeed` × (1 − random × `maxspeedmulrnd`), turning at `rotaccel`. Farther than `maxleader` from the leader, a fish uses `fast`.
- Objects in the **`felid`** list that come closer than `ecconear` make fish flee, turning at `escaccel`. Ecco left `felid` empty.
- **`mrange`, `maxleader` and `ecconear` are squared distances.**
- Fish swim along +Z.

**Drawing** (`0x4E9FF0`):
- draws the model once per fish;
- shades each fish from `mincolor` to `maxcolor` by its angle to the camera.

**Not used by Jaws:** `fp`, `eatscale`, `damage`, `animspeed`, `animspeedrnd` (Ecco's eating and animation fields). `zaj` (sound) is only looked up. So the fish can't be eaten and don't animate.

### Values used

Ecco's 120NORTH has 97 schools, using:

| Field | Ecco's range |
|---|---|
| `mnum` | 3–19 |
| `mrange` | 2–40 |
| `frange` | 2–20 |
| `rangez` | −1 to −10 |
| `maxspeed` | 0.2–0.3 |
| `fast` | 0.3–0.6 |
| `rotaccel` | 0.005 |
| `escaccel` | 0.009 |
| `ccount` | 30, with random 30 |
| `maxleader` | 100 |
| `ecconear` | 50 |

For the clownfish:
- **Size:** distances roughly doubled. The clownfish is WRACK `GMDL 1361` → `GMAT 739` → `GTEX 219`, at scale 7.5, about 1.1 units long. Ecco's fish03 is about 0.65.
- **Fleeing:** the shark (`SHARRRK` 26116) in `felid`, with `ecconear` 400.
- **Colour:** `mincolor` / `maxcolor` = 0.6 / 1.0.
- **Rendering:** the shipped clownfish's render settings (`0x860`, channels `0x3F`).

---

## 5. How Jaws reused and changed Ecco code

### The leftovers sit inside their original source files

- In Ecco's program, the surviving classes sit mixed with Ecco-only classes of the same prefix. For example, `MLHalRaj` and `MLMadarRaj` sit next to `MLGriff`.
- In `Jaws.exe` they're mixed with new Jaws classes of the same prefix, not gathered in one leftover block.
- The `GD*` engine forms its own block (`0x68D070`–`0x7141E0`).
- That's what copying source folders into a new project and carrying on working in them would produce.

### Jaws built new things on them

**Jellyfish:**
- In Ecco, `DDFieldAct` and `DDMedusaAct` always come as a pair, in levels with `gomba` ("mushroom") objects.
- In OPEN_NW the same pair appears once: `DDFieldAct` on node `MedusaField`, `DDMedusaAct` on the model `gomba`.
- Jaws's own man-o'-war classes follow them in the program (`MBMedusaFieldRef` `0x4C56F0`, `MBManowar`, `MBManowarRef`) and in the level.
- Both Ecco classes kept all their fields.

**Bird flock:**
- `MLMadarRaj` (*madárraj* = bird flock) runs once per level in 6 Jaws levels. In TOWN it's on node `MadarCsorda`, "bird herd".
- Jaws added `MLMadarRajRef`, which places flock copies (20 in total). Its code follows `MLMadarRaj` directly in the program.

### Some were trimmed

- `NAWhirl2000` lost `m_noecco`, replaced by `m_noshark`. This is the only change made in the Jaws era.
- `TRSplash` lost its three sound slots, and `MLHalRaj` gained two colours. Both happened in *Sentinels*.
- `NAParticle2000` lost its colour and water-check fields.
- Full list: §6.

### Some only kept the name

| Class | In Ecco | In Jaws |
|---|---|---|
| `DDGameState` | 18 game-state fields (`m_eccoarea`, `m_air`, `m_bossdefeated`, …); one node in 13 of 48 levels | None of those fields; still one node per level, in 18 levels |
| `MLEnemy` | An **action** with movement and health fields; never placed | A **brick**, placed 725 times; 2 of 6 field names left |
| `TRActor` | 808 placed, 7 fields (`m_healthmax`, `m_SonarMap`, …) | 1 of 7 fields; never placed |
| `PS2Shadow` | 259 placed | 5 of 11 fields; placed in the **PC** ARMADA and WRACK |

**`DDGameState` was rewritten twice:**
1. Sentinels cut Ecco's 18 fields to 3: `m_fustemit`, `m_monocam`, `m_sidecam`.
2. Jaws replaced those with 5: `m_angry`, `m_csonakdied` (boat died), `m_darabnum` (piece count), `m_enemyrange`, `m_koteldied` (rope died).

**`MLEnemy`:** Ecco never placed it, and in Jaws it's a brick instead of an action. So it's a Jaws class reusing an unused Ecco name, not Ecco content.

### The engine changed too

| | Classes |
|---|---|
| Ecco has, Jaws doesn't | the `GDPrim*` collision family, `GDWait`, `GDRandom`, `GDAlarm`, `GDGameTime`, `GDWorldBlock`, … |
| Jaws adds | `GDExtendedLight`, `GDRelocator`, `GDRoom`/`GDPortal`, `GDSoundEvent3D`, `GDTile`/`GDTileRef`, `GDMsgSend`/`GDMsgReceive` |

### The dolphin controller

Ecco's player controller (`DolphCtrl`) and sonar are not in `Jaws.exe`. We decompiled them from Ecco's PS2 program and rebuilt them in the mod (Shift+F2). That was mainly a test of our engine knowledge. See `docs/ecco_dolphin_controller.md`.

---

## 6. The 62 classes

**Key:**
- **Counts** are placed instances (nodes + actions).
- **"Ecco fields kept"** = Ecco field names still in `Jaws.exe`. "–" = the class has no fields of its own.
- Field names come from reflection strings. They show which data survived, not how much the code changed.

**Hungarian names (best guesses):** *madárraj* = bird flock, *halraj* = fish school, *medúza* = jellyfish, *lebeg* = float/hover, *gomba* = mushroom, *csorda* = herd.

### Placed in Jaws levels (32 classes)

| Class | Ecco base | Ecco fields kept in Jaws | Jaws PC | Jaws PS2 | Ecco | Jaws PC levels | Jaws.exe GetClassName |
|---|---|---|---|---|---|---|---|
| `MLEnemy` | GDAct | 2/6 | 725 | 494 | 0 | TITLE:74, OPEN_NW:65, DEEPSEA2:64, OPEN_S:50 +15 more | `0x4ca930` |
| `NAModelFade` | GDAct | 2/3 | 714 | 592 | 453 | OPEN_NW:58, OPEN_S:57, OPEN_NE:52, BEACH:48 +14 more | `0x58a190` |
| `NAVertexWave` | GDAct | 12/13 | 240 | 171 | 1308 | DOCKS:55, FISH:54, MINEMSHA:38, START:28 +5 more | `0x5d5110` |
| `NAFlare` | NAVirtualModel | 31/33 | 211 | 190 | 1552 | CHASE:16, DOCKS:16, TITLE:14, ARMADA:13 +15 more | `0x582fa0` |
| `NAModModAct` | GDAct | all 7 | 185 | 173 | 1452 | START:27, OPEN_NW:21, ARMADA:18, FISH:15 +11 more | `0x5d2770` |
| `PRotExplosion` | GDAct | – | 141 | 113 | 10 | DEEPSEA2:45, WRACK:15, DOCKS:14, KATATAMA:10 +14 more | `0x6419a0` |
| `NAFade` | NAVirtualModel | all 4 | 136 | 88 | 20 | AQUARIUM:17, DEEPSEA2:16, KATATAMA:15, WRACK:14 +13 more | `0x5896e0` |
| `NAHideBehind` | GDAct | all 1 | 119 | 14 | 220 | OPEN_S:35, OPEN_NE:21, OPEN_NW:21, ARMADA:14 +3 more | `0x56e270` |
| `NADetachAct` | GDAct | all 25 | 88 | 60 | 66 | DEEPSEA2:11, KATATAMA:9, ARMADA:7, OPEN_NE:7 +13 more | `0x564390` |
| `PMove` | GDAct | 8/9 | 82 | 34 | 60 | DEEPSEA2:18, TOWN:13, TITLE:9, CHASE:7 +10 more | `0x640280` |
| `DDLissaAct` | GDAct | all 6 | 71 | 63 | 41 | DEEPSEA:60, OPEN_NE:5, AQUARIUM:1, ARMADA:1 +4 more | `0x485ff0` |
| `MLTurnToTarget` | GDAct | all 2 | 63 | 58 | 52 | START:9, OPEN_NW:7, ARMADA:6, FISH:5 +11 more | `0x4e0580` |
| `NAPredatorModel` | GDModel | 11/15 | 58 | 63 | 503 | ARMADA:4, BEACH:4, GAUNTLET:4, MINEMSHA:4 +14 more | `0x5e9a40` |
| `DDLibegAct` | GDAct | all 7 | 57 | 59 | 471 | OPEN_NW:8, START:7, OPEN_NE:6, DEEPSEA2:5 +12 more | `0x486700` |
| `NAColorize` | GDAct | all 17 | 40 | 45 | 1990 | START:4, TITLE:3, AQUARIUM:2, ARMADA:2 +15 more | `0x5d43c0` |
| `TRMultiReference` | GDReference | all 3 | 37 | 37 | 136 | GAUNTLET:29, START:8 | `0x68a820` |
| `NAWhirl2000` | GDPath | 10/11 | 30 | 29 | 192 | START:21, DEEPSEA:7, KATATAMA:1, WRACK:1 | `0x63afd0` |
| `NALightning` | NAVirtualModel | 6/9 | 29 | 23 | 0 | BEACH:4, DOCKS:4, TOWN:4, CHASE:3 +11 more | `0x585b00` |
| `NAEdgeFade` | GDAct | all 1 | 26 | 29 | 3542 | BEACH:5, START:3, ARMADA:2, GAUNTLET:2 +14 more | `0x5d3490` |
| `DDGameState` | GDBrick | 0/18 | 18 | 20 | 13 | AQUARIUM:1, ARMADA:1, BEACH:1, BEACHPST:1 +14 more | `0x484610` |
| `NALensReflection` | NAVirtualModel | – | 14 | 14 | 16 | DOCKS:2, AQUARIUM:1, ARMADA:1, BEACH:1 +9 more | `0x584eb0` |
| `NAGlowAct` | GDAct | all 17 | 10 | 10 | 600 | DOCKS:8, BEACH:1, BEACHPST:1 | `0x57e270` |
| `DDWaveAct` | GDAct | all 10 | 8 | 8 | 682 | DOCKS:8 | `0x689600` |
| `MLMadarRaj` | GDAct | all 11 | 6 | 4 | 55 | FISH:1, MINEMSHA:1, OPEN_NE:1, OPEN_NW:1 +2 more | `0x4cf370` |
| `PModelAlphaChain` | GDAct | all 4 | 6 | 6 | 188 | TITLE:6 | `0x63f560` |
| `TRJellyCtrl` | TRMultiLODAct | all 11 | 4 | 4 | 32 | GAUNTLET:2, START:2 | `0x68aca0` |
| `NAParticle2000` | NAVirtualModel | 59/63 | 2 | 2 | 549 | KATATAMA:2 | `0x55b100` |
| `PS2Shadow` | GDModel | 5/11 | 2 | 0 | 259 | ARMADA:1, WRACK:1 | – |
| `DDFieldAct` | GDAct | all 13 | 1 | 0 | 17 | OPEN_NW:1 | `0x4c2520` |
| `DDMedusaAct` | GDCompMorph | all 16 | 1 | 0 | 17 | OPEN_NW:1 | `0x4c4760` |
| `NAFov` | GDAct | all 1 | 1 | 1 | 5 | START:1 | `0x5668b0` |
| `StoreInput` | GDAct | all 4 | 1 | 1 | 0 | WRACK:1 | `0x7116b0` |

### In the Jaws class registry but never placed in a Jaws level (30 classes)

| Class | Ecco base | Ecco fields kept in Jaws | Ecco instances |
|---|---|---|---|
| `TRActor` | GDActor | 1/7 | 808 |
| `MLHalRaj` | GDAct | all 23 (+2 added by *Sentinels*, 2001: `mincolor`, `maxcolor`) | 459 |
| `NARingAct` | GDAct | all 28 | 446 |
| `TRSplash` | GDAct | 27/30 | 128 |
| `MLParticle` | GD3dSprite | all 39 | 122 |
| `PCheckJoy` | GDAct | – | 91 |
| `NASplineMoveAct` | GDAct | all 17 | 87 |
| `NAWhirlBubblesAct` | GDAct | all 3 | 72 |
| `MLModelParticle` | GDModel | all 25 | 49 |
| `NAActivator` | GDAct | all 7 | 31 |
| `MLEnvSkeletonModel` | GDSkeletonModel | all 4 | 8 |
| `NAGlobalResources` | GDAct | all 1 | 2 |
| `NAShoreWave` | GDAct | all 7 | 2 |
| `MLColorize` | GDAct | all 13 | 1 |
| `MLOldParticle` | GD3dSprite | all 36 | 1 |
| `DDThrow` | GDAct | 18/19 | 0 |
| `MLCameraAct` | GDAct | all 7 | 0 |
| `MLScreenFadeModel` | NAVirtualModel | all 1 | 0 |
| `MLSzro` | GDAct | all 3 | 0 |
| `NADestructorClonerAct` | GDAct | all 3 | 0 |
| `NAExplosion` | GDBrick | – | 0 |
| `NAGlow` | NAVirtualModel | – | 0 |
| `NARing` | NAVirtualModel | – | 0 |
| `NAShowVect` | NAVirtualModel | – | 0 |
| `NASubdivide` | GDAct | all 3 | 0 |
| `NATestAct` | GDAct | – | 0 |
| `NAVirtualModel` | GDModel | all 1 | 0 |
| `TRLODAct` | GDAct | 4/5 | 0 |
| `TRMultiLODAct` | TRLODAct | all 1 | 0 |
| `TRSurf` | GDAct | – | 0 |

### Fields dropped on the way to Jaws

| Class | Kept | Ecco fields missing from Jaws.exe |
|---|---|---|
| `DDGameState` | 0/18 | `m_tempdoor`, `m_csapzarva`, `m_nirflags`, `m_nwlevel`, `m_finred`, `m_bossdefeated`, `m_hamon`, `m_air`, `m_fustemit`, `m_alert`, `m_beuszik`, `m_eccoarea`, `m_tempresig`, `m_tempfanatic`, `m_tempboss`, `m_flags`, `m_firstdialact`, `m_sidecam` |
| `DDThrow` | 18/19 | `m_turn` |
| `MLEnemy` | 2/6 | `m_rBaseAccel`, `m_rBaseRotAccel`, `m_rDrag`, `m_nHitPoint` |
| `NAFlare` | 31/33 | `m_raycolor`, `m_fixedsizepower` |
| `NALightning` | 6/9 | `m_VertNum`, `m_uVTile`, `m_segmentrnd` |
| `NAModelFade` | 2/3 | `m_alphalist` |
| `NAParticle2000` | 59/63 | `m_checkwater`, `m_red`, `m_green`, `m_blue` |
| `NAPredatorModel` | 11/15 | `m_buffersizelog2`, `m_blur`, `m_nodither`, `m_usecammtx` |
| `NAVertexWave` | 12/13 | `m_vertexsnap` |
| `NAWhirl2000` | 10/11 | `m_noecco` |
| `PMove` | 8/9 | `m_Loop` |
| `PS2Shadow` | 5/11 | `m_TailBoneNum`, `m_Action2`, `m_Contur1`, `m_Contur2`, `m_Contur3`, `m_Contur4` |
| `TRActor` | 1/7 | `m_healthmax`, `m_healthCnt`, `m_idSidePath`, `m_impulse`, `m_RebornDist`, `m_SonarMap` |
| `TRLODAct` | 4/5 | `m_SpriteID` |
| `TRSplash` | 27/30 | `m_Sound1`, `m_Sound2`, `m_Sound3` |

---

## 7. How this was measured

1. **Which classes.** Ecco's PS2 program has full class names (RTTI) for all 2,385 of its classes. 169 also exist in Jaws, as a string in `Jaws.exe` or in a level's class list. 107 are engine classes; the other 62 are listed above.
2. **Where they're used.** `CLAS` lists every class in every level, used or not, so it says nothing about use. Use is counted from placed nodes and actions, by class ID (the rule in `docs/brtr_editing.md`). Counted in all 20 PC levels, 22 PS2 levels and 48 Ecco levels.
3. **Whether the code came along.** For each class: how many of its Ecco field names still exist in `Jaws.exe`. All of them = it came over intact. None = only the name survived.
4. **Where the code sits.** Each class's `GetClassName` function lives in its own source file, so its address shows the link order. Compared in both programs.

**Scripts and data** (in `~/Projects/ECCO/re/`):
- `class_usage.py`: instances per level, for GDW and GDE files.
- `leftover_classes.py` → `leftover_classes.tsv`.
- `class_layout.py` → `class_layout.tsv`.
- `usage_jaws_pc.tsv`, `usage_jaws_ps2.tsv`, `usage_ecco.tsv`: every class.

---

## 8. Cut Defender levels in the Feb 2000 prototype

The *Defender* Dreamcast prototype of 17 February 2000 has a level-select list (`LEVELS.TXT`, 37 entries). It also has **three levels that are in no later build**: not in the April 2000 prototype, the PAL master or the US master. The prototype itself is described in `docs/gwb_lineage.md` §5.

| Name in the list | File | Size | What it is |
|---|---|---|---|
| Top Middle Low Lakes | `160_TOPMIDLOW.GDE` | 9.5 MB | A full level: ~590 placed models, ~330 lights, 70 sounds, 89 collision regions |
| Pumping Station 1 | `241_PUMP.GDE` | 12.4 MB | A full level: ~1,600 placed models, ~140 glows, 63 bubble generators. The shipped game keeps "Pumping Station 2/3" as `242_Pump`/`243_Pump`. |
| HWG Movie | `HWGM.GDE` | 12.2 MB | An in-engine cutscene for the Hanging Water Generator: a movie resource, 7 animated skeletons, mountain and grass textures |

**Also in the prototype:**
- `FOCI.GDE`, an early small version of the shipped `470_FOCI`.
- `002_DEMO.GDE`, gone by release.

**Not tested:** whether the prototype can load these from its level select, in an emulator.

---

## 9. Cut shark grab attack (May 1999)

**In short:** in the May 1999 *Defender* E3 demo, **sharks grab Ecco in their jaws and drag him**. By the 2000 build the attack is gone, but Ecco's controller still handles being dragged.

This comes from reading the decompiled 1999 program; it wasn't run in an emulator. Method: `docs/gwb_lineage.md` §4.

### How it worked

- **`TRSharkTank`** is a full shark controller in 1999. It is placed 5 times in the 1999 Reef level. It has:
  - a start position, heading and pitch, and a model;
  - three states: cruise (with random wandering), turn around (when blocked), and attack.

  In 2000 the same class is only a list of five shark IDs.
- **The attack:**
  1. The shark turns toward Ecco (within ±30°, closer than 80 or 120 units) and lunges.
  2. It sends Ecco **`DAMG` 30** (damage) and fires a linked action.
  3. While it holds him, every frame it sends **`DRAG`** or **`PULL`** with the position of one bone, probably the jaw.
  4. It also sends `STOP`, whose meaning isn't known.
- `Shark_1` sends the same four messages.
- The receiver is the dolphin controller's message handler, in `Ctrl.cpp` (`0x8C0455BC`).

### What survived

- In the 2000 program nothing sends `DRAG` or `PULL`, but **`DolphCtrl::EccoMessage` still handles both**. A leftover of the cut attack.
- Jaws's dolphin code has neither.

### Evidence

- `TRSharkTank` is in `Octhelp.cpp`; its registry name is `SharkTank`.
- It holds Ecco in attack sub-state 2 (`DRAG`) or higher (`PULL`). The bone is at offset `+0x1E0` in the model's bone array.
- `SharkTrap` (`Sharktrp.cpp`) only sends `DAMG`. Not read in detail.
- The decompiled text stays local, outside the repo: `~/Projects/ECCO/ecco1999_decomp/` (`sharktank_1999.c`, `shark_files_1999.c`).

### Open

- What does `STOP` do?
- How does the handler move Ecco on `DRAG` and `PULL`?
- What are the bone names?
- `SharkTrap` in detail.

---

## 10. Appaloosa Mermaid tech demo (2001)

**In short:** two videos dated 2001-01-05 show an Appaloosa mermaid game demo made after *Defender*. Its character isn't the Jaws mermaid. Only Ecco's jellyfish code links it to Jaws. The editor already had a mermaid class by mid-2000.

### The videos

Supplied by the user: "Appaloosa Mermaid techdemo, 2001.01.05", 41.6 s and 52.0 s. Kept in the user's Downloads, not the repo.

- **The mermaid:** a slim, pale-blue humanoid **with legs**, black hair and see-through fins on the feet.
  - She is **not** the Jaws mermaid, who has a green fish tail, human skin and blonde hair (`docs/mission_system.md` "The Gauntlet's live mermaid").
  - No model is shared.
- **Video 1, no HUD:** she swims through rocky canyons past tight fish schools. A large armoured, spiny fish appears with a blue ring around it.
- **Video 2, a playable prototype with a full HUD:**
  - an extra-lives counter and a round radar;
  - a target-name bar reading **"GIANT MEDUSA"**, later **"SNAKE FIGHTER"**;
  - glowing jellyfish-like orbs she fights, and a spiny snake creature.

### Links to Jaws and Ecco

- *Medusa* is Hungarian *medúza*, "jellyfish". Ecco's jellyfish code (§5) is still in both Jaws programs.
- The ball-shaped fish schools look like Ecco's `MLHalRaj`.
- So the demo most likely ran on the same engine and Ecco-based code.
- **Nothing of its own survives:** no "Giant Medusa", "Snake Fighter" or mermaid text is in `Jaws.exe`, the PS2 program or the Ecco files.

**The editor knew a mermaid class by mid-2000.**
- The US *Defender* master (June/July 2000) lists `MBMermaid` in its class registry.
- Alongside it: `MBMissile`, `MBCameraAct`, `MBLovedek` (*lövedék* = projectile), `MLCamAct`, `MLSmooth`, `NAHair` and `DDPaintBall`.
- None is placed, apart from one `DDPaintBall`.
- So the mermaid project existed in the editor about six months before the videos, and the demo was very likely built with it. The missile and projectile classes fit a mermaid fighting a "Giant Medusa".
- It may be the first use of the `MB` prefix that Jaws's mission classes use. `MBLovedek` reaches Jaws; `MBMermaid` doesn't.
- The earlier PAL master and the Feb/Apr 2000 prototypes don't have these classes.

**Stray "MermaidR" bytes:**
- The pelican skeleton (WRACK 1198, TITLE 894, OPEN_S 2476, and PS2 copies) has the text `MermaidR` in unused slots of its weight table, which hold leftover memory.
- The pelican was probably exported while a "MermaidR…" object was loaded, most likely the Jaws Gauntlet mermaid's rig.
- Nothing dates it to the demo.

---

## 11. Cancelled Appaloosa projects and the *Smurfs* video

Per the user, Appaloosa had at least three cancelled projects besides *Sentinels*:

| Project | What's known | What we have |
|---|---|---|
| **Mermaid tech demo** | Reused *Defender* assets and showed new features | Two videos (§10); `MBMermaid` in the US Defender master |
| **Parrot demo** | A planned first-person game, maybe a shooter; never left the design stage | Nothing |
| ***Smurfs*** (©2002) | An early but polished-looking PS2 build; cancelled | A 15.5-minute video in the user's Downloads |

No files of any of them are public.

### The *Smurfs* video

"Appaloosa Smurfs ©2002", 15 min 29 s, 1080p. Frames were sampled every 20 s; the audio wasn't reviewed.

- **Platform: PlayStation 2.** It shows PS2 button symbols and a 4:3 picture.
- **A developer menu, not a retail one:** "THE SMURFS" over the village, with **ANIM VIEWER**, **CHARACTERS** and **LEVELS**.
- **Anim viewer:**
  - Smurfs: Papa Smurf, Handy, Smurfette, Brainy, Harmony, Hefty, Farmer Smurf.
  - Clips: Neutral, Idle, Idle 2, Walk, Run, Jump, Throw, Hello, Kick, "Do it!", Climb, Duck.
  - So the characters share one set of clips, as Jaws's humans do. That's not proof of the same system.
- **Gameplay:**
  - Third-person. Papa Smurf leads a party of followers, and a portrait shows the selected helper.
  - Helpers react with speech bubbles.
  - Puzzles: a boulder needing a number of Smurfs to push, a water wheel to repair, a caged Smurf, a Smurf in a bubble.
  - A mushroom counter for collectibles.
  - Enemies: spiders, and a green dragon boss in a lava cave.
- **Levels seen:** the Smurf village, a forest and river trail, giant toadstools, a lava cave.

**Link to GWB: none visible.** Nothing on screen ties it to the editor or the Defender/Jaws engine. It fits in time and platform with the *Defender* PS2 port (2001–2002). Whether it used GWB stays unknown without files.

### The sparkles

**The user's observation:** the yellow-and-white sparkles in *Smurfs* look like the ones in Jaws when the shark head-butts a diving cage.

**In *Smurfs*** (11:21–11:24): a gift-bomb blows up a boulder, with rock chunks and small four-pointed yellow/white stars.

**In Jaws:**
- The cage effect is the node **`CageHitEffect`** (KATATAMA 3347/3424, under the cage frames).
- It's an `NAParticle2004` emitter using texture **`0x1DA`**: a 64×64 white starburst with four long rays and thin diagonal ones, tinted yellow by the emitter.

**Compared against every Ecco build:**

| Build | Textures checked | Best match | Score |
|---|---|---|---|
| *Defender* PS2 | 4,310 | The `csillag` ("star") sprites: `csillag-feher` (white), `csillag-sarga` (yellow), … | 0.90–0.93 |
| *Sentinels* (Feb 2001) | 1,808 | `piros01.tga`, `FeherCsillanas.tga` ("white sparkle") | 0.90 |
| *Defender* PAL Dreamcast | 5,413 | `iszkred`, `iszkblue` | 0.89 |

- An identical image would score about 0.99, so **no Ecco build has an exact copy**. The Jaws sparkle was drawn after February 2001: in the *Smurfs* era or later.
- The *style* is older. Defender's Dreamcast version already has thin-rayed starbursts, and its PS2 version adds the four-pointed star set.
- Jaws's emitter class, `NAParticle2004`, is newer than *Smurfs*. It follows the year-named rewrite pattern of `NAParticle2000` and `NAWater2004`.

**Reading:** yellow and white star sparkles were Appaloosa's house style from *Defender* on. The look plausibly runs Defender → *Smurfs* → Jaws. The video is too low-detail to identify the *Smurfs* texture, so this is consistent with carry-over, not proof.

**Tools and files:**
- Dreamcast textures are decoded with `scripts/pvr_decode.py`.
- Comparison images: `particle_compare/` in the project folder, local only.

---

## 12. After Appaloosa: Twofish.hu

**In short:** Appaloosa closed after Jaws. The same Budapest team carried on under a new company, Twofish.hu. Their first game, *EdgeRacers*, was finished but never released. Their later *SmartyAnts* (2010) probably used the Torque engine. So Game World Builder ended with either Jaws or *EdgeRacers*. We don't know which.

### What happened to the company

Source: the user's question in an audio interview with Ed Annunziata, creator of Ecco.

- Appaloosa was **not** renamed. It shut down, along with bonus.com.
- Annunziata founded **Twofish Inc.** (US) with Lee Crawford, who had worked on Sega's Dreamcast online service.
- His condition was that all his Hungarian colleagues join. They all did.
- For legal reasons they were employed by **Twofish.hu** in Budapest. Twofish Inc. owned it fully.
- Twofish Inc. was later sold to **Live Gamer**.
- Annunziata swapped his shares for the Budapest studio, *EdgeRacers*, and "the technology we made".
- He stayed on as the only American at Twofish, which went on to make games for several parent companies.

His view: the people stayed the same; "Novotrade", "Appaloosa" and "Twofish" are only legal names.

Annunziata did not work on Defender, Sentinels or Jaws. He is now making an Ecco remaster at A&R Atelier, with many of the original Novotrade/Appaloosa developers.

### *EdgeRacers* (unreleased)

- A car racing game. Wrecked cars heal over time.
- You can jump out of a broken car and into another one.
- It was finished, then shelved. No reason was given.
- **Engine: unknown.** It was made by the Jaws team, after Jaws and before *SmartyAnts*. That makes it the most likely game to use a later version of GWB. It could equally have used new Twofish technology.
- A game file would settle it at once: GWB files start with `GDED BINARY FORMAT, VERSION …`.

**Pictures.** These come from the studio's portfolio page `studio.twofish.hu/index.php/portfolio/edgeracers/`. The site's certificate has expired. The user's copies are in `download-check/edge-racers/`. Keep them local; they don't go in the repo.

| Files | What they are |
|---|---|
| `car_render_wide_01`–`09` | Studio renders of single cars. Not from the game. |
| `ill_edgeracers_legal` | Title art with the "FE EDGERACERS" logo. Not from the game. |
| `ill_edgeracers_screenshot_01`–`04` | Real in-game shots, with no HUD. |

The four in-game shots show:
- 8–10 cars with bold paint jobs.
- A village square with a church tower.
- A castle on a hill, with a green light beam from the sky.
- A stadium speedway with made-up sponsor boards.
- Cars flying through the air and upside down.

They look like PS2 or Wii-era graphics. Nothing in them points to a particular engine.

All the image files were saved in March 2014, when the website was built. That is not when the game was made.

### *SmartyAnts* (2010)

- Made by Twofish for Smarty Ants, Inc. (Burlingame, California), with a Korean partner.
- It was played online. The installers only download the game; they contain no game data.
- The game's download servers are gone, and the user couldn't find the files on the Wayback Machine.
- **Engine: probably Torque**, a licensed engine from GarageGames. The installer was built in a folder named `c:\Torque\anttools\`.
- This is likely, not proven, because we have only seen the installers.

#### Evidence: the two installers

Both were unpacked without running them. The user also ran the Windows one under Proton.

**Windows `installer.exe`** (57 MB):
- "SmartyAnts Installer" 1.0.0.1, © 2010 SmartyAnts Inc., company string "Twofish".
- Built `Dec 5 2010 18:32:32` with Visual Studio 2005 and MFC.
- Debug path: `c:\Torque\anttools\release\installer.pdb`.
- Code-signed by "Smarty Ants, Inc.", Burlingame, California (Thawte).
- Contents: Twofish's own archive format (`CHHD` header, `CHFE` entries). It holds only Microsoft's DirectX installer.
- The archive header holds `0x20041020`. That reads like a date, as in GWB's format stamps, but it's only suggestive.
- All messages are in English and Hungarian.
- It checks for Windows (up to Windows 7) and Direct3D 9.
- It then downloads `launcher.exe`, `updater.exe`, `SmartyAnts.start.pack`, `dx.pack` and `contentState.txt`. The sources are `s3.amazonaws.com/SA_boot/` and `smartyants.com.nefficient.co.kr/SA_boot/`.
- It registers `.smartyants` files, which is how the website started the game.
- Under Proton it stops at "Downloading SmartyAnts Launcher… [1003]" because the servers are gone.

**Mac `SmartyAnts.zip`** (280 KB, dated October–November 2010):
- A small Java program, package `hu.twofish.app.loadapp`.
- It downloads `SmartyAnts-Launcher.jar` from `s3.amazonaws.com/SA_boot` and runs `hu.twofish.app.prolod.GuiMain`.
- Built with Java 1.6.0_21. It supports Windows, Mac and Linux.

Files to look for if they ever surface: `docs/open_problems.md` §9 "Other titles".

---

## 13. Open questions

- **Did the kept classes' code change?** Ecco and Jaws functions are paired in `~/Projects/ECCO/re/func_pairs.tsv`. Example: `DDMedusaAct` slot `0x74` = Jaws `0x4C51A0`, the same logic with different offsets. `jaws_labels.tsv` there suggests names for those Jaws functions.
- **Can the 30 never-placed classes be reached at all?** For example, spawned by name. Or are they dead code?
- **The cancelled projects:** were the Mermaid demo and *Smurfs* made with GWB? Did Jaws's cage sparkle come from *Smurfs*? Both need files that aren't public. See `docs/open_problems.md` §9 "Other titles".
- **What engine did *EdgeRacers* use?** See "After Appaloosa".

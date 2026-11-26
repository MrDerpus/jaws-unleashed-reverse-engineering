# Ecco the Dolphin leftovers in Jaws Unleashed

*Written 2026-10-12 from the Ecco reverse-engineering work in `~/Projects/ECCO/re/` (Ecco PS2 executable
`SLUS_203.94`, analysed in Ghidra). Both games are by Appaloosa, the Hungarian studio behind Game World
Builder (GWB). The engine lineage itself is in `docs/GDW_FORMAT.md` "Engine lineage".*

**Short answer:** Jaws keeps three different kinds of Ecco-era code, and only the first is "engine":

1. **The GWB engine (`GD*` classes).** Linked as one library block in both executables. It evolved between
   the games (classes dropped and added) but it is the same engine.
2. **Ecco's own game-code modules (`DD`, `TR`, `NA`, `ML`, `P` prefixes).** In Ecco these hold gameplay and
   effects side by side. Jaws carried a hand-picked subset of these source modules forward, kept them in
   the same modules, and added new Jaws classes next to them. These are the real leftovers.
3. **Names reused for new code.** A few classes kept their Ecco name but were rewritten (`DDGameState`,
   `MLEnemy`, `TRActor`, `PS2Shadow`).

So there is no separate "engine template" layer of game classes. The survivors are Ecco game code that the
team kept working in.

---

## Verdict: Jaws was built from Ecco's codebase (reviewed 2026-10-12)

Reviewed in the Jaws project. Spot-checked against `Jaws.exe`: it has no "Ecco" string and none of
`EccoGame`, `DolphCtrl`, `TRWorld`, `m_SonarMap`, `m_eccoarea` or `m_noecco`. (Its two "ECCO" hits are
Italian dialogue, "ECCOLO!" = "there he is!".) The surviving names it does have (`DDGameState`,
`DDMedusaAct`, `DDFieldAct`, `MLHalRaj`, `MLMadarRaj`, `TRActor`, `DDThrow`, `NATestAct`) are all present,
and `func_pairs.tsv` pairs their virtual functions with Ecco's one-to-one. The link-order and instance
counts above were not re-run.

**Supported:** *Sole Predator / Jaws Unleashed was built from Ecco: Defender of the Future's codebase, not
only from its engine.* A project started fresh on the bare GWB engine would not contain Ecco game code, and
some of what's in `Jaws.exe` has no use in a shark game:

- **Dead Ecco gameplay is compiled in:** ring-swimming (`NARingAct`), fish schools (`MLHalRaj`) and splashes
  (`TRSplash`) are in the exe and never placed in any Jaws level. They came along with their source files.
- **Ecco code was edited in place:** `NAWhirl2000` lost exactly one field, `m_noecco`, which became `m_noshark` (field tables, 2026-11-25).
- **Names were kept and reused:** `DDGameState` is still one node per level, with all 18 Ecco fields
  replaced; `TRActor` is the same story.
- **Ecco and Jaws classes share source modules** (link order), and Jaws's man-o'-war classes are built on
  Ecco's jellyfish code (`DDFieldAct`/`DDMedusaAct`).

**Not settled:**
- **Whole copy or chosen modules?** Copying the entire Ecco project and deleting most of it (14 of 933
  `DD`/`TR` classes remain) would leave the same traces as importing selected source folders.
- **Direct or through another project? Partly answered 2026-11-25: through the *Sentinels* code line.**
  Ecco shipped in 2000 and Jaws in 2006. Appaloosa's cancelled Defender sequel *Ecco the Dolphin: Sentinels
  of the Universe* (Dreamcast dev-kit builds, Feb 2001, `GDED` 2.3.2.1) was checked against both. 13 brick
  classes, 28 action classes and 3 property classes are in Sentinels and Jaws but **not** in Defender. They
  include the whole skeleton system (`XBone`, `XSkeletonModel`, `XAnimation`, …), Jaws's fish school
  `MLHalRaj3` (placed once in Sentinels' `420_HangCaverns`), `NAGenerator`, `NARubberSkeleton`, `MLEnemy`
  and `NAHair`. So the code Jaws started from had already been through Sentinels' development, not just
  Defender's. Per the user, Jaws was made after Sentinels was cancelled, which fits: the cancelled
  sequel's code became the base for Jaws. Only 2 brick, 3 action and 1 property class are in Defender and Jaws but missing from
  Sentinels (`GDMultiTexture`, `NAPredatorModel`; `NAModelFade`, `NASubdivide`, `StoreInput`;
  `GDPropExtRenderSet`), which fits Sentinels' class tables being a slimmer, newer branch. Whether further
  Appaloosa projects sat between 2001 and 2006 is still unchecked. Data and method: `docs/GDW_FORMAT.md`
  "Format versions across Appaloosa builds".

**How much came over:** the whole engine (107 shared `GD*` classes), but only 62 of Ecco's ~2,385 classes
on the game side. About 32 of those are placed in Jaws levels, mostly general effects and behaviours
(fades, flares, vertex waves, lightning, explosions, turn-to-target) that Jaws uses on purpose. The other
30 are never placed, and that's where the real Ecco leftovers are. None of what makes Ecco *Ecco* came
over: the dolphin controller, sonar, air meter, game world and levels are all gone.

**Sole Predator beta screenshots (user observation, 2026-10-12; the screenshots are the user's and haven't
been examined in the project):**
- Schools of fish swimming in **ball shapes**, like Defender's fish schools. Matching class: `MLHalRaj`
  (Halraj = fish school), compiled into `Jaws.exe`, never placed in any PC or PS2 Jaws level.
- **Splash effects and particles when breaching** the water surface, like Defender's. Matching classes:
  `TRSplash` (never placed in Jaws) and `NAParticle2000` (placed only twice, both in KATATAMA).

**User's theory:** these classes aren't only Ecco carry-over but **Sole Predator leftovers**. They were live
in the game while it was Sole Predator and dropped later, around the move to Jaws Unleashed.

**Checked 2026-10-12: the shipped game replaced both with new Jaws-only classes, and the old fish-school
class was worked on in Jaws before being replaced.**

- **Shipped fish schools are `MLHalRaj3`**, which isn't in *Defender of the Future* (not in its RTTI, not in
  any of the 48 Defender levels). **Correction 2026-11-25:** it *is* in the cancelled sequel *Ecco the Dolphin:
  Sentinels of the Universe* (Feb 2001, `GDED` 2.3.2.1), placed once in `420_HangCaverns`, so the rewrite was
  done for Sentinels, not for Jaws (`docs/GDW_FORMAT.md` "Format versions across Appaloosa builds"). In the shipped game they're long columns of one fish type (user observation). It's placed 121
  times in the PC levels (137 PS2), alongside `MLHalRaj3Catch` (121, `m_TargetID`/`m_BloodID`: the
  bite/blood hookup) and `MLHalRaj3Reference` (296 instanced copies). It's a rewrite, not a renamed
  `MLHalRaj`: 31 fields, all new `m_` names, none shared with the Ecco class. Ecco's has a box volume
  (`boxx/y/z`), clusters (`ccount`) and leader-following (`maxleader`); `MLHalRaj3` has group size and
  depth (`m_groupsize`, `m_groupsizez`), a side ratio (`m_sideratio`), a wave (`m_waveamp`, `m_wavefreq`),
  fear of the shark (`m_enemy`, `m_feardist`, `m_fearspeed`), health, and light/colour by depth. A group
  size plus a side ratio fits elongated columns rather than balls, but the shipped values haven't been read
  out. The "3" implies a `MLHalRaj2`, which is in neither executable. Further Jaws-only fish classes:
  `MSHalraj` (10 placements, with attack fields: `m_attackspeed`, `m_bAttack`, `m_damage`), `MSPathFish`,
  `MSGeneralFish`, `MSFishGenerator`.
- **The old `MLHalRaj` was edited before Jaws.** In `Jaws.exe` it has **25 fields: Defender's 23 plus two
  new ones, `mincolor` and `maxcolor`** (from `scripts/dump_class_fields.py`; Defender's field list has no
  colour fields). It still has `ecconear` (distance to Ecco). **Corrected 2026-11-25:** the colour fields
  were already added in *Sentinels of the Universe* (Feb 2001), which also introduced `MLHalRaj3`; Jaws
  inherited both and placed only `MLHalRaj3`. Same for `TRSplash`'s lost sound fields (gone in Sentinels).
- **Shipped splashes are `NAWaterSplashAct`**, which also isn't in Ecco, placed 867 times across the PC
  levels. `TRSplash` lost its three sound fields (`m_Sound1`–`m_Sound3`) between Ecco and Jaws, then ended
  up never placed.
- **What those three sound slots held in Ecco (checked 2026-10-12 in all 48 Ecco levels):** of 105
  `TRSplash` instances, exactly **one per level** (in 11 levels) has its sounds set: the player's splash.
  The other splashes are silent. In every case the three slots point at three `GDSound` nodes playing
  `_eccosounds\esik1.wav`, `esik2.wav` and `esik3.wav`, always in that order (e.g. 120NORTH: action 2732 →
  nodes 2734/2737/2739). *Esik* is Hungarian for "falls". By ear in Ecco (user), breaching gives a splash
  on leaving the water, a bubbling sound when the air meter is low and refilling (it can play together with
  the first), and a different splash on landing back in the water. The `esik` name fits the landing splash
  best. Which of the three files is which sound, and whether the air-refill bubbles come from `TRSplash` at
  all or from the dolphin controller's air code, hasn't been checked: Ecco's sound banks (`SFX/*.SAB`) are
  extracted without names, so the files still need matching up by `GSFX` ID or by ear. Jaws, which has no
  air meter, removed all three slots.

So both effects in the beta screenshots match Ecco classes that were **modified in the Jaws codebase and
then superseded by new Jaws classes**. That supports the theory: they were in use during development
(Sole Predator era) and replaced later, not dragged along untouched. It doesn't date the swap: nothing in
the data says whether it happened at the rename to Jaws or at some other point in development. Not yet
checked: whether any dangling `GDControl` target or deleted node ID points at an
`MLHalRaj`/`TRSplash` instance.

**Correction to the `MLEnemy` row below:** Ecco never placed it (0 instances), and in Jaws it's a brick
instead of an action, so it's a Jaws class reusing an unused Ecco name, not Ecco content.

### `MLHalRaj` fish schools restored in Jaws (2026-10-21, user-confirmed working first try)

The old Ecco fish school runs in the shipped `Jaws.exe` unchanged. `scripts/build_fishball_test.py
[OUT] [--deploy NAME]` puts three schools of WRACK's clownfish in front of the spawn of the blank FISH
base (`levels/custom_fish/FISH_blank_base.GDW`) → `edited_levels/FISHBALL.GDW`, loaded with the mod's F9.

**Shape:** not a true ball. One leader wanders and the rest hold random offsets from it, which gives the
swirling clumps of Defender, the Mermaid demo and the Sole Predator beta screenshots, not Jaws's long
`MLHalRaj3` columns. **`MLHalRaj2`** (implied by the "3") is in neither exe, so it can't be restored. User's
theory: it was the school of the Mermaid demo and early Sole Predator (fits the dates, unverifiable).

**Placing it, no `CLAS` edit needed:** every level's `ACCM` list already names `MLHalRaj` (it's the whole
engine registry; FISH index `0x143`), and the action loader `0x68ED80` only uses the class ID's low 12 bits
(remapped through the file's list), so the class word is `0x02144143` (middle bits = index + 1, as in
`MLMadarRaj` `0x0214C14B`). PROP IDs in FISH: `0x08000984` + field index (`mnum` … `maxcolor`, order in the
table below).

**Layout (Ecco 120NORTH node 6354, kept as is):** `GDStdBrick` carrying the `ACTN` → empty `GDStdBrick`
→ fish `GDModel` (Ecco: `fish03.GDM` `GDMovingModel` with a `GDMorphAnim`). All three need `m_nFlags` `0x12`.

**Code (Jaws `MLHalRaj` vtable `0x7DD0D4`, props value = wrapper offset + 4):**
- Init `0x4E9A80`: takes the brick's first child and, if that has a child, the grandchild as the model;
  hides both (`0x100`) and allocates per-fish arrays (`mnum` × matrix, state, offset, vertex colours).
- Tick `0x4EA3E0`: fish 0 leads at `maxspeed`, picks a new random heading every
  `ccount`…`ccount+ccountrnd` ticks, and turns back when outside the sphere `mrange` (or the box
  `boxx/y/z` when `mrange` = 0). Fish *i* steers to the leader's matrix × its random offset
  (x, y in ±`frange`/2; z in 0…−`rangez`, or ±`frange`/2 when `rangez` = −1), at
  `maxspeed` × (1 − rnd × `maxspeedmulrnd`), turning at `rotaccel`; farther than `maxleader` it uses
  `fast`. Objects in **`felid`** (an ID list; Ecco left it empty) closer than `ecconear` make a fish flee,
  turning at `escaccel`. **`mrange`, `maxleader` and `ecconear` are squared distances.** Fish swim along +Z.
- Draw `0x4E9FF0`: renders the model once per fish (grandchild case: fish matrix × the model's own local
  transform, so scale/orientation go on the model node), shading each fish's vertex colours from
  `mincolor` to `maxcolor` by its angle to the camera (the two fields added in *Sentinels*, 2001).
- `fp`, `eatscale`, `damage`, `animspeed`, `animspeedrnd` are not read by the Jaws code (Ecco's eating and
  morph-animation fields), and `zaj` (sound) is only looked up. The fish can't be eaten and the static
  clownfish doesn't animate.

**Values used** (Ecco 120NORTH's 97 schools use `mnum` 3–19, `mrange` 2–40, `frange` 2–20, `rangez` −1 to
−10, `maxspeed` 0.2–0.3, `fast` 0.3–0.6, `rotaccel` 0.005, `escaccel` 0.009, `ccount` 30/30,
`maxleader` 100, `ecconear` 50, `felid` empty): distances roughly doubled for the clownfish (WRACK
`GMDL 1361` → `GMAT 739` → `GTEX 219`, at WRACK's scale 7.5, ≈ 1.1 units long; Ecco's fish03 ≈ 0.65), the
shark (`SHARRRK` 26116) in `felid` with `ecconear` 400, `mincolor`/`maxcolor` 0.6/1.0, and the shipped
clownfish's render settings (`m_RenderSetting` `0x860`, `m_ChannelSetting` `0x3F`).

**Scaled up (user requests, same day):** v2 ~3× the fish and 2× the spread (`mnum` 60/100/40, `mrange`
400/900/100, `frange` 16/24/8); v3 **50× the fish: 3,000 / 5,000 / 2,000 = 10,000 fish, no frame drop at all
(user-tested)**. `mnum` has no cap in the code (all per-fish arrays are heap-allocated from it).

**Side by side with the shipped schools:** the level also holds two stock Jaws schools (FISH templates
`Piros-Feher Hal Sprite` 23022 and `Zebra Hal Sprite` 22980, copied as they are, each placed by a copy of
FISH's `MLHalRaj3Reference` 34098). Differences found on the way:
- **`MLHalRaj3` is a `GD3dSprite` subclass:** Jaws's schools are flat sprite fish (one material, e.g.
  `GMAT 969`), not meshes, so a clownfish `MLHalRaj3` can't be made. `MLHalRaj` draws real 3D models. The
  beta screenshots' 3D-looking ball schools fit the old class.
- `MLHalRaj3` is a **brick** placed as a top-level template plus `MLHalRaj3Reference` nodes (`m_Ref` =
  template, own `m_fishnum`, `m_speed`, `m_moverange`, `m_groupsize`/`z`, `m_enemy`, `m_feardist`,
  `m_size`, `m_health`); `MLHalRaj` is an **action** on an ordinary brick.
- The Jaws fish are **edible** (each template carries an `NABiteTarget` and an `MLHalRaj3Catch` action);
  the Ecco ones aren't.
- Jaws schools flee from **`HalRiaszto`** (26265, "fish alarmer"), a child brick of the shark, with
  `m_feardist` 5 (15 on the template).

---

## How this was measured

- **Which classes:** Ecco's executable has full GCC RTTI, giving all 2,385 of its class names. 169 of them
  also exist in Jaws (as a string in `Jaws.exe` or in the level class registry). 107 are `GD*` engine
  classes; the other **62** are game-side and listed below.
- **Where they're used:** `CLAS` lists every registered class in every level, used or not, so it says
  nothing about use. Usage = `CHBR` nodes / `ACTN` blocks whose class ID's low 12 bits index the class in
  `BRCM` / `ACCM` (the rule in `docs/brtr_editing.md`). Counted in all 20 PC GDWs, the 22 PS2 GDEs and all
  48 Ecco GDEs. The parser reproduces the documented FISH lookups (`0x02F` GDModel, `0x06E` NAGarden,
  `0x039` GDControl, `0x128` MSHHSharkGen).
- **Whether the code came along:** for each class, how many of its Ecco reflected field names
  (`m_...`, from Ecco's field registrations) still exist as strings in `Jaws.exe`. All kept = the class
  came over essentially intact. None kept = only the name survived.
- **Where the code sits:** a GDED class's `GetClassName` stub (`mov eax, <name>; ret`) lives in the class's
  own source file, so its address shows link order. Compared in both executables.

Scripts and full data (in `~/Projects/ECCO/re/`): `class_usage.py` (per-level instance counter, works on
GDW and GDE), `leftover_classes.py` → `leftover_classes.tsv`, `class_layout.py` → `class_layout.tsv`,
`usage_jaws_pc.tsv` / `usage_jaws_ps2.tsv` / `usage_ecco.tsv` (every class, not just these).

---

## Evidence

**Only a small, chosen part of Ecco's game code came over.** Ecco has 933 `DD*`/`TR*` classes; 14 are in
Jaws. `Jaws.exe` has no "Ecco" string, none of Ecco's top-level classes (`EccoGame`, `DolphCtrl`,
`DolphConfig`, `TRWorld`) and none of its level names. Its dolphin strings are Jaws's own
(`MSDolphinSightseeingMission`, "Dolphin Frenzy").

**The survivors sit inside their original modules, in both games.** In Ecco's executable they are mixed
with Ecco-only classes of the same prefix (`NAModelFade NAFov` sit next to `NATeleportEcco NACamShow`;
`MLHalRaj MLMadarRaj` next to `MLGriff`). In `Jaws.exe` they are mixed with new Jaws classes of the same
prefix, not gathered in one leftover block, while the `GD*` engine forms its own block (`0x68D070`–
`0x7141E0`, with Jaws-only GD classes interleaved). A team that copied source folders into the new project
and kept working in them would produce exactly this.

**Jaws built on some of them.** New Jaws classes are linked right after the Ecco code they extend, and
placed next to it in the levels:

- **Jellyfish.** In Ecco, `DDFieldAct` and `DDMedusaAct` always come as a pair (same count in all 8 levels
  that use them), and those levels contain `gomba` ("mushroom") objects. In OPEN_NW the same pair appears
  once: `DDFieldAct` on node `MedusaField`, `DDMedusaAct` on the GDModel `gomba`. Jaws's own man-o'-war
  classes follow them in the exe (`MBMedusaFieldRef` `0x4C56F0`, `MBManowar`, `MBManowarRef`) and in the
  level (`MBManowar` on `ManOWar Root`, `MBMedusaFieldRef 1` under `JellydroidRaiser`). Both Ecco classes
  kept all their fields.
- **Bird flock.** `MLMadarRaj` ("bird flock", Ecco: 10 levels) runs once per level in 6 Jaws levels (TOWN:
  on node `MadarCsorda`, "bird herd"). Jaws added `MLMadarRajRef`, a reference brick (`0x100`-byte
  `GDReference` subclass) that places flock instances (`Madarraj`, `Madarraj 1`, ...: 20 in total). Its
  code follows `MLMadarRaj` directly in the exe.

**Some were trimmed** (dated 2026-11-25 against *Sentinels*: `TRSplash` and `MLHalRaj` were changed in Sentinels already; only `NAWhirl2000`'s change is Jaws-era). `NAWhirl2000` lost exactly one field, `m_noecco`, replaced by `m_noshark`. `TRSplash` lost its three
sound slots, `NAParticle2000` its colour and water-check fields (see the table at the end).

**Some only kept the name.**

| Class | Ecco | Jaws |
|---|---|---|
| `DDGameState` | 18 Ecco game-state fields (`m_eccoarea`, `m_air`, `m_bossdefeated`, `m_hamon`, `m_finred`, ...); one node in 13 of the 48 levels | none of those fields; still one node per level in 18 levels (TOWN: node `GameState`) |
| `MLEnemy` | an **action** (`ACCM`) with movement/health fields (`m_rBaseAccel`, `m_rDrag`, `m_nHitPoint`, ...), never placed | a **brick** (`BRCM`) placed 725 times (e.g. `ManOWar Root`); 2 of 6 field names left |
| `TRActor` | 808 placements, 7 fields (`m_healthmax`, `m_SonarMap`, ...) | 1 of 7 fields; never placed |
| `PS2Shadow` | 259 placements | 5 of 11 fields; placed in the **PC** ARMADA and WRACK |

Field names come from reflection strings, so this shows which *data* survived, not how much of each
method body changed.

**The engine changed too.** Ecco has `GD` classes Jaws doesn't (`GDPrim*` primitive collision family,
`GDWait`, `GDRandom`, `GDAlarm`, `GDGameTime`, `GDWorldBlock`, ...). Jaws adds others (`GDExtendedLight`,
`GDRelocator`, `GDRoom`/`GDPortal`, `GDSoundEvent3D`, `GDTile`/`GDTileRef`, `GDMsgSend`/`GDMsgReceive`).

---

## The 62 classes

Counts are placed instances (nodes + actions). "Ecco fields kept" = Ecco field names still present in
`Jaws.exe`; "–" = the class has no reflected fields of its own. Hungarian name glosses are best guesses:
Madárraj = bird flock, Halraj = fish school, Medúza = jellyfish, Lebeg = float/hover, gomba = mushroom,
Csorda = herd.

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

## Cut Defender levels in the Feb 2000 prototype (2026-11-26)

The *Defender of the Future* Dreamcast prototype of 17 February 2000 (Hidden Palace release; `MK-0000 V0.800` office sample disc, GWB 2.1.12.1; see `docs/GDW_FORMAT.md`) has a level-select list `LEVELS.TXT` (2000-02-16, 37 entries, `START.TXT` = `000_Title.gde`) and three levels that are in no later build (not in the April 2000 prototype, the PAL master or the US master):

| List name | File | Size | Content |
|---|---|---|---|
| Top Middle Low Lakes | `160_TOPMIDLOW.GDE` (2000-02-17) | 9.5 MB | full level: 1,171 `GMDL`, 922 `GMAT`, 514 `GTEX`, 89 `MREG` collision regions, 69 `GSFX`, 2 skeletons; ~590 placed models, ~330 lights, 70 sounds, 61 `TRMacroModel` |
| Pumping Station 1 | `241_PUMP.GDE` (2000-02-17) | 12.4 MB | full level: 315 `GMDL`, 189 `MREG`, 3 skeletons, 74 `GSFX`; ~1,600 placed models, ~140 `NAGlowAct`, 63 bubble generators; textures shared with the shipped pumping stations (`PSVenti`, `monitoroldal`, `iriszpupilla…`). The shipped game keeps "Pumping Station 2/3" as `242_Pump`/`243_Pump` |
| HWG Movie | `HWGM.GDE` (2000-02-15) | 12.2 MB | in-engine cutscene for the Hanging Water Generator: a `GMOV` (movie) resource, 7 skeletons with `GDSkeletonAnim`, 523 `GMDL`, 49 `NAVertexWave`, landscape textures (`hegy…` = mountain, `fualap` = grass base) |

Also in the prototype: `FOCI.GDE` (2000-01-24, 1.7 MB, 34 meshes), an early small form of the shipped `470_FOCI` (which the US master expanded again), and `002_DEMO.GDE` (also in the April build, gone at release). Not checked in-game; whether the prototype can load them from its level select wasn't tested. Counts come from the `RSRC` walk and `gded_lineage.py placed` (heuristic).

## Appaloosa Mermaid tech demo (2001-01-05)

*Added 2026-10-20.* Two videos the user supplied, titled "Appaloosa Mermaid techdemo, 2001.01.05" (41.6 s and
52.0 s, 480p; kept outside the repo in the user's Downloads). Per the user, the demo came after Ecco: Defender
of the Future (2000). Seen from frames pulled with ffmpeg (no audio reviewed):

- **The mermaid** is a slim, pale-blue humanoid **with legs**, black hair and translucent fin-like flippers on
  the feet. She is **not** the Jaws mermaid (green fish tail, human skin, blonde hair; see
  `docs/mission_system.md` "The Gauntlet's live mermaid"). No model is shared.
- **Video 1** (no HUD): she swims through rocky canyons past tight fish schools; a large armoured, spiny fish
  appears with a blue ring effect around it.
- **Video 2** (playable prototype with a full HUD): counters with an extra-lives count (top left), a round
  radar (top right), a target-name bar reading **"GIANT MEDUSA"** and later **"SNAKE FIGHTER"**, glowing
  jellyfish-like orbs she fights, and a spiny snake creature.

**Link to the code:** *medusa* is Hungarian *medúza*, "jellyfish". The jellyfish code from Ecco
(`DDMedusaAct`/`DDFieldAct`, see "Jellyfish" above) is still in both Jaws exes, next to Jaws's own
`MBMedusaFieldRef`. Together with the ball-shaped fish schools (like Ecco's `MLHalRaj`), this suggests the
demo ran on the same Appaloosa engine and Ecco-derived code, between Ecco (2000) and Sole Predator / Jaws.
**What doesn't survive:** no "Giant Medusa", "Snake Fighter" or mermaid text is in `Jaws.exe`, the PS2
`SLUS_210.62` or the Ecco files in `~/Projects/ECCO`. The demo's own content (character, enemies, HUD) left
no trace found in Jaws.

**Correction (2026-11-26): the editor knew a mermaid class by mid-2000.** The US *Defender* Dreamcast master
(`MK-51033 V1.000`, 2000-06/07; `docs/GDW_FORMAT.md` "European vs US Dreamcast masters") lists **`MBMermaid`**
in its levels' class registry, together with `MBMissile`, `MBCameraAct`, `MBLovedek` (*lövedék* = projectile),
`MLCamAct`, `MLSmooth`, `NAHair` and `DDPaintBall`. None of them is placed in Defender (except one
`DDPaintBall`); they're listed because the editor build that exported the US files had them registered. So the
older statement "Ecco's files contain no mermaid at all" holds for content, not for the class registry. Reading
(inference): the mermaid project existed in Game World Builder about six months before the demo videos (dated
2001-01-05), so the demo was very likely built with GWB; the missile/projectile classes fit a demo where the
mermaid fights a "Giant Medusa" and a "Snake Fighter". It may also be the first use of the `MB` prefix that
Jaws' mission classes use: `MBLovedek` reaches Jaws, `MBMermaid` doesn't (it's in neither Sentinels nor Jaws).
The PAL master (May 2000) and the Feb/Apr 2000 prototypes don't have these classes.

**Stray "MermaidR" bytes (not demo evidence):** the pelican skeleton (`SKEL` with clips `Pelican_*`, 262
vertices; WRACK 1198, TITLE 894, OPEN_S 2476, plus PS2 OPEN_S/TITLE/WRACK/OPEN_NE) has the text `MermaidR` in
the unused slots of its `WGHT` table, which hold leftover memory. The pelican was likely exported in a tool
session that also had a "MermaidR…" object loaded, most plausibly the Jaws Gauntlet mermaid's rig. Nothing
dates it to the demo.

## Cancelled Appaloosa projects (user information, 2026-11-26)

Per the user, Appaloosa had at least three cancelled projects besides *Sentinels of the Universe*:

| Project | What's known | Evidence on hand |
|---|---|---|
| **Mermaid tech demo** | Reused assets from *Defender of the Future* and showcased new features; no public build exists | two videos dated 2001-01-05 (section above); `MBMermaid` in the US Defender master's class registry (mid-2000) |
| **Parrot demo** | Planned as a first-person, possibly shooter-type game; per the user it never left the design stage | none (no files expected) |
| **Smurfs** (©2002) | Video of an early but very polished-looking build exists; cancelled, no public build | a 15.5-minute 1080p video in the user's Downloads ("Appaloosa Smurfs ©2002"); see "Smurfs video (2002)" below |

## After Appaloosa: Twofish and *SmartyAnts* (2010) (checked 2026-11-26)

Per the user, after Appaloosa shut down its people founded **Twofish**, which kept making games, so Game World Builder / Diesel Power might have lived on. The user found two *SmartyAnts* installers (Wayback Machine downloads, in `download-check/`); both were unpacked read-only, nothing run except the Windows installer by the user under Proton:

- **Windows `installer.exe`** (57 MB, "SmartyAnts Installer" 1.0.0.1, © 2010 SmartyAnts Inc., built `Dec 5 2010 18:32:32`, company string "Twofish"). The payload (a gzip resource) is Twofish's own archive format (`CHHD` header, `CHFE` entries; header value `0x20041020`, which reads like a YYYYMMDD stamp, cf. GWB's format stamps; suggestive only) holding nothing but Microsoft's DirectX redistributable (64 cabinets, 2005–2007). Every message is in English and Hungarian. It checks the CPU and Windows version (knows up to Windows 7; Proton's default Windows 10 gives "Unknown Windows OS", Proton 3.7 reporting Windows 7 SP1 passes) and Direct3D 9 (`Direct3DCreate9`, `d3dx9_`), then downloads `launcher.exe`, `updater.exe`, `SmartyAnts.start.pack`, `dx.pack`, `contentState.txt` and a manifest from `http://s3.amazonaws.com/SA_boot/` or `http://smartyants.com.nefficient.co.kr/SA_boot/`. Options `-variant`/`-var`, `-dir`, `-nolaunch`; string `krus` (likely Korean/US variants); writes `installer.log`. Under Proton it stops at "Downloading SmartyAnts Launcher… [1003]" (servers gone).
- **Mac `SmartyAnts.zip`** (280 KB, app bundle dated 2010-10-26/11-08): a Java bootstrapper `loadapp.jar`, package `hu.twofish.app.loadapp` (bundle id `hu.twofish.app.loadapp.MainFrame`). It downloads `SmartyAnts-Launcher.jar` from `http://s3.amazonaws.com/SA_boot` with variant `macus` (also `mactest`) and runs `hu.twofish.app.prolod.GuiMain`; it handles Windows, Mac and Linux.

- **Build details of the Windows installer:** debug-symbol path **`c:\Torque\anttools\release\installer.pdb`**; Visual Studio 2005 (linker 8.0, Rich header build 50727), MFC; PE timestamp 2010-12-05 17:32:52 UTC. Code-signed by **"Smarty Ants, Inc.", Burlingame, California, US** (Thawte Code Signing CA - G2). Registers the file type `.smartyants` and the web content type `application/smartyants` ("Play SmartyAnts"; i.e. the website started the game by handing the browser a `.smartyants` file), settings under `Software\<company>\<product>\Params`.
- **Build details of the Mac launcher:** `Created-By: 1.6.0_21 (Sun Microsystems Inc.)`, classes compiled for Java 5 (class version 49); installs under the user's home `Library`.

**Result:** Twofish (Hungarian, `hu.twofish`) built *SmartyAnts* for the US company Smarty Ants, Inc. (Burlingame, CA; Korean partner site `smartyants.co.kr`), delivered online-only through launchers; the game data was never in the installers, and the user couldn't find the server files on the Wayback Machine. **The engine was probably GarageGames' Torque, not Diesel Power:** the SmartyAnts tools (`anttools`) were built inside a `c:\Torque\` tree, which fits the Direct3D 9 renderer and the Mac/Linux support (both Torque traits) and the 2010 date. So the Appaloosa → Twofish line most likely switched to a licensed engine after Jaws, and Diesel Power / Game World Builder may have ended with Jaws (2006). Not proven (only the installers were seen, not the game); GWB use inside *SmartyAnts* is now unlikely rather than unknown. URLs to try if they ever surface: `docs/open_problems.md` lineage item 8.

## Smurfs video (2002) (reviewed 2026-11-26)

Video "Appaloosa Smurfs ©2002" (15 min 29 s, 1080p, uploader's caption "Cancelled Project · All Rights Reserved"; kept in the user's Downloads, not in the repo). Frames were sampled every 20 s plus every second of the first minute (ffmpeg contact sheets; audio not reviewed).

- **Platform: PlayStation 2.** Menus show PS2 button glyphs (△ back, ✕ select, d-pad arrows); 4:3 picture.
- **Developer front end, not a retail menu:** "THE SMURFS" title over the village with the options **ANIM VIEWER**, **CHARACTERS**, **LEVELS**.
- **Anim viewer:** "SMURF: … / ANIMATION: …" with ◀/▶ = Smurf, ▲/▼ = animation. Characters: Papa Smurf, Handy, Smurfette, Brainy, Harmony, Hefty, Farmer Smurf. Clips: Neutral, Idle, Idle 2, Walk, Run, Jump, Throw, Hello, Kick, "Do it!", Climb, Duck. So skinned characters with a shared clip set (as in Jaws, where humans share `GlobalSkeletonAnim`'s clips; not proof of the same system).
- **Gameplay:** third-person, Papa Smurf leads a party of followers; a portrait in the bottom-right corner shows the selected helper (Harmony with trumpet, Farmer, Smurfette, a gift-box icon for Jokey). Helpers react with speech/thought bubbles ("Hey!", a gear icon near a broken water wheel). Puzzles: a sparkling boulder with a number over it (how many Smurfs are needed to push it), a water wheel to repair, a caged Smurf, a Smurf trapped in a pink bubble. A mushroom counter top right (12 → 21 → 31 → 37) = collectibles. Enemies: spiders; a green dragon boss in a lava cave.
- **Levels seen:** Smurf village (mushroom houses, well, vegetable garden), forest/river trail with rocks and spider webs, giant toadstool platforms, a lava cave.

**Sparkle particles (user observation, checked 2026-11-26).** The user noticed that the yellow-and-white sparkles in *Smurfs* look like those in Jaws when the shark head-butts a diving cage. In *Smurfs* (11:21–11:24 in the video), a gift-bomb blows up a boulder: grey rock chunks plus a spray of small four-pointed yellow/white star sparks. In Jaws the cage effect is the node **`CageHitEffect`** (KATATAMA nodes 3347/3424, children of the cage frames `Cage Keret`/`Cage Keret 1`). It is an `NAParticle2004` emitter (`m_` field `0x080010CE` = `GMAT 0x5A5`) whose texture is **`0x1DA`**: a 64×64 white starburst (four long rays plus thin diagonal rays) stored in the alpha channel and tinted yellow by the emitter's colour keys (RGBA ≈ (1.00, 0.96, 0.16) → (0.94, 0.80, 0.31)). Comparison with *Defender* PS2 (all 4,310 decodable 32–128 px textures, correlation against the Jaws alpha):
- best matches are Defender's **`csillag` ("star") sprites**: `csillag.tga`, `csillag-feher` (white), `csillag-sarga` (yellow), `-piros`/`-kek`/`-zold` (32×32, 16-bit), score 0.90–0.93; also `sarga_flare` (yellow flare), `fehercsillanas` (white sparkle);
- no exact copy (an identical image would score ~0.99). So the Jaws sparkle is a newer, larger redraw of the same four-pointed-star sparkle idea, not Defender's file.
- *Sentinels* (Feb 2001, 1,808 Dreamcast PVR textures, decoded with a scratch PVR decoder) and *Defender* PAL Dreamcast (5,413 textures) checked the same way: best Sentinels matches `piros01.tga` (64×64 many-rayed starburst, 0.905) and `Textures\Resources\Effects\FeherCsillanas.tga` ("white sparkle", 64×64, 0.90); best Dreamcast Defender match `iszkred`/`iszkblue` (0.89). The `csillag-*` star set is PS2-only (Defender PS2 gallery level). **No exact copy in any Ecco build**, so the exact Jaws sparkle image was made after Feb 2001 (Smurfs-era or later). The *style* is older: Defender Dreamcast already has thin-rayed starbursts like it (`kekcsillog` blue sparkle, `eff3`, `fenyudvar2` light halo, `piros01`), Defender PS2 adds the four-pointed `csillag` set. Dreamcast textures are PVR images (twiddled, VQ and small-VQ, optionally mipmapped; in a mipmapped VQ texture the full-size index block starts after the codebook + the smaller levels, 1 + Σ(s/2)² bytes, and is followed by 10 padding bytes; small VQ uses a shorter codebook); decoded with `scripts/pvr_decode.py`. Comparison images (not in the repo; extracted assets): `particle_compare/` in the project folder.

Reading: yellow/white star sparkles were already Appaloosa's house style in *Defender* (2000–2002); *Smurfs* (2002) sits between, so the look plausibly runs Defender → Smurfs → Jaws, but the video's resolution doesn't allow the *Smurfs* texture to be identified, and Jaws's emitter class is the newer `NAParticle2004` (cf. Defender's `NAParticle2000`, the year-named rewrite convention also seen in `NAWater2004`), so the system that draws it in Jaws postdates *Smurfs*. Not proof of carry-over from *Smurfs* specifically; consistent with it.

**Link to the GWB lineage: none visible.** Nothing on screen (fonts, HUD layout, effects, water) is distinctive enough to tie it to Game World Builder or the Defender/Jaws engine; there's no debug overlay or file name. What fits: Appaloosa, 2002, PS2, the same period and platform as the *Defender* PS2 port (2001–2002), when the engine evidently had a PS2 branch. Whether *Smurfs* used GWB stays unknown without game files.

## Open questions

- Whether the kept classes' method bodies changed. Ecco and Jaws virtual functions are paired in
  `~/Projects/ECCO/re/func_pairs.tsv` (e.g. `DDMedusaAct` slot `0x74` = Jaws `0x4C51A0`: same logic, other
  offsets), and `jaws_labels.tsv` there has suggested names for those Jaws functions.
- ~~What Jaws's rewritten `DDGameState` holds now~~ **Answered 2026-11-25:** 5 fields `m_angry`, `m_csonakdied` (boat died), `m_darabnum` (piece count), `m_enemyrange`, `m_koteldied` (rope died). It was rewritten twice: Sentinels cut Ecco's 18 fields to 3 (`m_fustemit`, `m_monocam`, `m_sidecam`), then Jaws replaced those.
- Whether the 30 never-placed classes are reachable from code at all (spawned by name, or dead).
- Cancelled projects: whether the Mermaid demo and *Smurfs* were GWB titles, and whether Jaws's cage sparkle (`0x1DA`) came from *Smurfs*; both need files that aren't public (`docs/open_problems.md` lineage item 8).

---

## Moved from CLAUDE.md (2026-11-25)

The text below was moved word for word from the root `CLAUDE.md`. It is newer than earlier sections of this file where they disagree.

**Ecco code in Jaws (2026-10-12):** beyond the shared engine (107 `GD*` classes), `Jaws.exe` carries 62 of Ecco's game-side classes (`DD`/`TR`/`NA`/`ML`/`P`), from Ecco PS2 RTTI. About 32 are placed in Jaws levels, mostly general effects (`NAModelFade`, `NAFlare`, `NAVertexWave`, `NALightning`…). The other 30 are never placed, including Ecco gameplay like `NARingAct` (rings) and `MLHalRaj` (fish schools). `NAWhirl2000`'s `m_noecco` became `m_noshark`, and `DDGameState` kept its name with all 18 Ecco fields replaced. **Verdict: Jaws was built from Ecco: Defender's codebase, not only its engine.** Whether that was a whole-project copy or chosen modules is not settled; it came through the code line of the cancelled sequel *Sentinels of the Universe* (2001), which already has `MLHalRaj3` and the skeleton classes (2026-11-25, "Verdict"). No dolphin, sonar or Ecco level code survived. **Sole Predator beta screenshots (user observation)** show Defender-style ball-shaped fish schools and breach splash/particle effects. The matching classes are `MLHalRaj` and `TRSplash`, both compiled in and never placed (plus `NAParticle2000`, placed only twice, both in KATATAMA). User's theory: these are Sole Predator-era leftovers, used during development and dropped later. **Checked 2026-10-12, supports it:** the shipped game uses newer classes instead (`MLHalRaj3` turned out to date from *Sentinels*, 2001, not Jaws). Fish schools are `MLHalRaj3` (121 placed + 296 references, plus `MLHalRaj3Catch`): a 31-field rewrite with group size, side ratio and wave fields, shown in-game as long columns of one fish type. The "3" implies a `MLHalRaj2` that exists in neither exe. Splashes are `NAWaterSplashAct` (867). **`MLHalRaj` restored (2026-10-21, user-confirmed working first try):** `scripts/build_fishball_test.py --deploy FISHBALL` places 3 schools of WRACK clownfish in the blank FISH base (F9 → FISHBALL). No `CLAS` edit: `ACCM` already lists it (class `0x02144143`, PROPs `0x08000984` + field index); Ecco layout brick+`ACTN` → empty brick → fish model, all `m_nFlags` `0x12`; `mrange`/`maxleader`/`ecconear` are squared distances; `felid` = flee list (shark). `MLHalRaj2` exists in neither exe. 10,000 fish (3 schools at 50×) run with no frame drop (user-tested). The level also has 2 stock Jaws schools for comparison: shipped `MLHalRaj3` is a **sprite** brick (`GD3dSprite`, template + `MLHalRaj3Reference`, edible, flees `HalRiaszto` 26265 under the shark), not a 3D-mesh action. Details: `docs/ecco_leftovers.md` "`MLHalRaj` fish schools restored". **Ecco's player controller decompiled (2026-10-21, step 1 of an Ecco-in-Jaws port, read-only):** `TRActor` + **`DolphCtrl`** action (34 KB; tick `0x19E270` = 29 KB, states 0–6: idle/brake, swim, charge, jump, tail-walk, 180° turn, circling) + `DolphConfig` brick (119 tuning fields, the `SharkConfig` counterpart); calls ~147 unmatched engine functions; not in `Jaws.exe`, so a port = C++ rewrite in the mod. Dolphin clip table (10 frame ranges of `Ecco.gdm`'s 319-frame pool) recovered. Sources `~/Projects/ECCO/re/dolphctrl/`; write-up and port options: `docs/ecco_dolphin_controller.md`. **Sonar decompiled (2026-10-21), now in the mod as visual + sound (Shift+F2 row below, user-confirmed):** trigger `FUN_001ABBE8` (button bit 4, underwater, cooldown `m_rSonarFrequency`, costs `m_rSonarAirNeed` air, a second press within 15 ticks = magnet sonar; holding only re-arms the cooldown), visuals `NASonarAct`/`NASonarConeAct` (hidden cone/wave meshes on the dolphin actor, head-bone placed, grow and fade), effect = message `0xE` to touched objects' `m_OnSonar` receivers; all sonar classes are absent from `Jaws.exe`. Details: `docs/ecco_dolphin_controller.md` "Step 3". Both old Ecco classes were **edited, then abandoned**: `MLHalRaj` gained `mincolor`/`maxcolor` (25 fields vs Ecco's 23, still including `ecconear`), and `TRSplash` lost its 3 sound fields; **both edits already happened in *Sentinels of the Universe* (2001), not in Jaws** (2026-11-25, `docs/lineage_field_diff.txt`). In Ecco only the player's splash (one per level) sets those 3 slots, always to `_eccosounds\esik1/2/3.wav` (*esik* = "falls"); which in-game sound each file is hasn't been matched yet. When the swap happened isn't dated. Details: `docs/ecco_leftovers.md` "Verdict".

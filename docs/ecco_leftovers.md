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
- **Ecco code was edited in place:** `NAWhirl2000` lost exactly one field, `m_noecco`.
- **Names were kept and reused:** `DDGameState` is still one node per level, with all 18 Ecco fields
  replaced; `TRActor` is the same story.
- **Ecco and Jaws classes share source modules** (link order), and Jaws's man-o'-war classes are built on
  Ecco's jellyfish code (`DDFieldAct`/`DDMedusaAct`).

**Not settled:**
- **Whole copy or chosen modules?** Copying the entire Ecco project and deleting most of it (14 of 933
  `DD`/`TR` classes remain) would leave the same traces as importing selected source folders.
- **Direct or through another project?** Ecco shipped in 2000 and Jaws in 2006. If another Appaloosa game
  used this code in between, the Ecco code could have reached Jaws through it. No other Appaloosa title has
  been checked.

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

- **Shipped fish schools are `MLHalRaj3`**, which isn't in Ecco (not in its RTTI, not in any of the 48 Ecco
  levels). In the shipped game they're long columns of one fish type (user observation). It's placed 121
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
- **The old `MLHalRaj` was edited for Jaws.** In `Jaws.exe` it has **25 fields: Ecco's 23 plus two new
  ones, `mincolor` and `maxcolor`** (from `scripts/dump_class_fields.py`; Ecco's field list has no colour
  fields). It still has `ecconear` (distance to Ecco). So someone added a colour tint to Ecco's fish school
  in the Jaws codebase, and the class was later replaced by `MLHalRaj3` and left unplaced. That's the same
  edited-then-abandoned pattern as `TRSplash`.
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

**Some were trimmed for Jaws.** `NAWhirl2000` lost exactly one field, `m_noecco`. `TRSplash` lost its three
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
| `MLHalRaj` | GDAct | all 23 (+2 added in Jaws: `mincolor`, `maxcolor`) | 459 |
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

## Open questions

- Whether the kept classes' method bodies changed. Ecco and Jaws virtual functions are paired in
  `~/Projects/ECCO/re/func_pairs.tsv` (e.g. `DDMedusaAct` slot `0x74` = Jaws `0x4C51A0`: same logic, other
  offsets), and `jaws_labels.tsv` there has suggested names for those Jaws functions.
- What Jaws's rewritten `DDGameState` holds now (its Jaws field list, via `scripts/dump_class_fields.py`).
- Whether the 30 never-placed classes are reachable from code at all (spawned by name, or dead).

# Audio leads: unused sounds, checked one by one

**In short:** every sound file was traced from what plays it back to the sample. 373 of 4,050 files are never requested. Checked by ear and by waveform, those come down to **48 recordings no player ever hears**.

The interesting ones:
- **Brody's two cut lines** from the tutorial's rope fight (START 470/471);
- **the squid boss's** attack, pain and death sounds, never wired to the fight;
- **the boss orca's** threat and alarm calls;
- **a TOWN alarm bell** with nothing to ring it;
- **DEEPSEA's** conveyor-belt and servo sounds, plus a generator run-down sound.

Most other "unused" sounds are copies of sounds that play elsewhere, or raw masters.

The story dialogue isn't here: it's in 49 captioned `SMPC` samples (`docs/cutscene_dialogue.md`). Formats and the playback chain: `docs/audio_format.md`. Cut content summary: `docs/cut_content.md`.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/audio_leads_old_2026-11-27.md`.

---

## Contents

1. [Unused-audio audit](#1-unused-audio-audit)
2. [Recording check](#2-recording-check)
3. [START: Brody's cut rope-fight lines](#3-start-brodys-cut-rope-fight-lines)
4. [START: the rest of the `Movie` bank](#4-start-the-rest-of-the-movie-bank)
5. [DEEPSEA2: the squid boss](#5-deepsea2-the-squid-boss)
6. [AQUARIUM: the boss orca](#6-aquarium-the-boss-orca)
7. [TOWN: alarm bell](#7-town-alarm-bell)
8. [TOWN: fireworks](#8-town-fireworks)
9. [DEEPSEA: mine sounds; DEEPSEA2: generator](#9-deepsea-mine-sounds-deepsea2-generator)
10. [The first lead: long SFX samples](#10-the-first-lead-long-sfx-samples)
11. [Old mistakes](#11-old-mistakes)

---

## 1. Unused-audio audit

```bash
python3 scripts/audit_audio.py [NAME ...]      # read-only
```

- Checks every file in `audio/<NAME>/` against the chain: `Group.Name` request → sound bank → `GSFX` → sample.
- Writes `audio/audio_audit.csv` and `audio/audio_audit.txt`. The chain and status meanings are in the script's docstring.

**First run (2026-10-15), 19 levels with audio:**
- 4,050 files;
- **3,677 used**;
- **373 unrequested**;
- none without a bank or trigger.

**Unrequested names, by how many levels have them:**

| Spread | Names |
|---|---|
| 12–18 levels | `Camera.AboveWater`, `Camera.UnderWater` (surface-crossing sounds), `Jaws.ImpactGlass/Wood/Metal/WindowUnbreak`, `Jaws.GrabBody`, `SeaSeeker.Fire`, `HumanFemale.Panic`, `HHShark.Attack` |
| 6–8 levels | `ElectricFence.Ambient/Szikrazas`, `Seal.SplashIn/SplashOut`, `Boat.WaterSplash`, `SeaSeeker.Engine`, `Dolphin.Alarm/Attack`, `Submarine.Ambient` |
| One level | DEEPSEA2 `Squid.Hurt/Die/Attack` (§5); START `Movie.VoiceBrody3/4` and other `Movie.*` (§3, §4); TOWN 388 `MovieTown1.VoiceCrew2` (an alternate take); BEACHPST `Truck.*`, `TeeniePartyMusic.Ambient`, `Waterslide.WaterStart`; DEEPSEA `Mine.Servo01–03` (§9); WRACK `Movie.WoodCreak1–3`, `Movie.BoatSplash01/02` |

**Limits:**
- "Unrequested" = no string or typed `GSFX` reference found. It doesn't prove silence; the exe could reach a bank entry another way (not seen so far).
- "Used" = something *can* ask for it. Whether that object or action ever runs needs `dump_gdcontrol.py` or a play test.

---

## 2. Recording check

Added 2026-11-23. `audit_audio.py` also compares the 16-bit PCM of every unrequested file with every used one (exact match).
- New CSV columns: `recording` (`plays_elsewhere` / `unheard`) and `copy_of`.
- `audio_audit.txt` lists unheard files first.

**Result for the 373 unrequested files:**
- **194 play elsewhere**, under another name or in another level. Example: START `Movie.HumanMaleFear` = `Human.Cry`.
- **179 are never heard.** They are **48 distinct recordings**:

| Group | Recordings |
|---|---|
| Shared, unheard in every level | `Camera.AboveWater` (18 levels), `Jaws.ImpactGlass` (18), `Jaws.ImpactWood` (18), `SeaSeeker.Fire` (15), `HumanFemale.Panic` (2 takes, 13), `Seal.SplashIn/SplashOut` (8), `Dolphin.Alarm` (6), `Dolphin.Attack` (2 takes, 6), `Stingray.Bite` (3 takes, 4), `SmallSub.Crash` (3), `Buoy.Bell`, `Button.Esc` |
| Bosses and creatures | DEEPSEA2 `Squid.Attack` (2), `Squid.Hurt` (2), `Squid.Die`; START `Movie.SquidHurt` (close to `Squid.Attack`, not identical); AQUARIUM `Orca.Alarm`, `Orca.Threatening` |
| Level-specific | TOWN `Bell.Alarm` (2), `TownFirework.FireWork`; DEEPSEA `Mine.Servo01–03`, `Mine.EngineFutoszalag`; DEEPSEA2 `Generator.Slow`; AQUARIUM `HotDogStand.Bounce` (2); WRACK `JeepEngine.Engine` (3), `Movie.BoatSplash01/02`, `Movie.Explosion03`; DOCKS `Movie.FishingBoatEngine` |
| Cutscene voice and leftovers | START `Movie.VoiceBrody3/4`, `Movie.FootstepsGuard`, `Movie.EngineSeaSeeker`, one `Movie.EngineOldBoat` copy; TOWN `MovieTown1.VoiceCrew2` (alternate take) |

The same limits apply: "used" means the name can be requested, not that the requester runs.

**Exact matching needed an extractor fix** (2026-11-23):
- `rip_smpb.py` started the PCM 4 bytes late (`sec_hdr + 20` instead of `+ 16`).
- So every `SMPB` `.wav` lacked its first 2 samples and ended with 2 zero samples (the loop fields). Inaudible, but byte-exact comparisons between `GSMP` and `SMPB` copies failed.
- `rip_smpc.py` had the same mistake.
- Both were fixed the same day; all 1,128 + 49 files re-extracted. Copies now hash-match.

---

## 3. START: Brody's cut rope-fight lines

**In short:** samples 470 and 471 are Brody's lines from the cut tutorial ending, where the shark is hooked to the Aurora and fights the rope (`docs/cut_content.md` §3). They're never played on PC or PS2.

**The lines** (user-transcribed 2026-11-23):

| Sample | Name | Length | Line |
|---|---|---|---|
| 470 | `Movie.VoiceBrody3` | 2.43 s | *"Gottem! Hold tight, he's gonna try and break free!"* |
| 471 | `Movie.VoiceBrody4` | 5.19 s | *"Oh my God it's a Great White! Make sure he's fully restrained and let's get him to the research center ASAP."* |

Files: `audio/START/START_id0470_*.wav`, `…0471_*.wav`.

- **Same voice actor** as the shipped lines 1 and 2 (user-confirmed by listening).
- **Plain `GSMP`, not `SMPC`:** no caption was ever attached. The shipped lines 1/2 (460/461) are captioned `SMPC`.
- **Unique:** the PCM matches no other sample in any level. DEEPSEA2's `Movie.VoiceBrody3` is a different, captioned line; each level has its own `Movie` bank, so names collide.

**Never played, PC and PS2:**
- PC `START.GDW` and PS2 `START2.GDE`: `VoiceBrody1/2` occur 3 times each (bank + sound-event action), `3/4` only once (bank).
- PS2 `START.GDE` has all four once.
- No `GDSoundEvent` names them.
- The cutscene's sound actions (209–227, on `AuroraComesMovie`/`Sounds` 208) have no ID gaps, and its controls' empty steps are all-zero (no leftover targets).

**Above/underwater:** `VoiceBrody3/4` have the same `GSFX` in both the above- and underwater lists. The cutscene's `VoiceBrody1/2` are above-water only. That fits lines meant for a playable fight, where the camera can be below the surface.

**Cutscene timing:**
- `AuroraComesMovie` (198) plays `VoiceBrody1` at tick 0 and `VoiceBrody2` at 170 (both Scene01).
- The movie ends at tick 1000. Scene04 (from about 725) only switches the camera, with no sound.
- Lines 3 and 4 (~228 ticks) would fit there, but nothing proves they were meant to.

**Signal check:**
- Both are speech: strong voicing, 68 % / 47 % voiced frames. 471 is two phrases with a ~1 s pause.
- Median pitch ~220 Hz against 117–159 Hz for Brody's used lines (175 Hz for his shout *"There it is!"*). That's excited delivery; a crude autocorrelation estimate.

---

## 4. START: the rest of the `Movie` bank

**In short:** START's other unused `Movie` sounds are mostly copies of stock sounds staged for cutscenes. Only two are unique: guard footsteps and a SeaSeeker engine.

**The bank:**
- Node `SndMovie 5` (16800), 28 names.
- It serves two shipped cutscenes:
  - the tutorial ending `AuroraComesMovie` (198, actions 214–227);
  - **`DeathOfShawMovie`** (543, actions 559–565): the death of Shaw's son, a diver (`ShawsSonKilledEvent`). Started by root action 8 `DeathOfShaw_MovieStarterNDestroyer`. Shipped, not cut; it's not about Shaw himself.

**Order and empty slots:**
- Names 0–9 (`BigShipComing` … `VoiceBrody2`) look like the first batch.
- `SquidHurt` has a much later `GSFX` ID (2176, against 1510–1538).
- `SquiIdle` and `Bubbles` are empty slots (no `GSFX`).

**Copies of sounds that play elsewhere:**

| START sample | Same as | How found |
|---|---|---|
| `SplashOut3` / `SPlashOut4` (468/469) | Shared `Jaws.SplashOut` | Exact |
| `JawsGrowl2` (459) | Shared `Jaws.Growl` (also WRACK `Movie.JawsGrowl02`) | Exact |
| `FerryEngineIdle` (455) | TOWN `Ferry.Engine` | Exact |
| `HumanMaleFear` (456) | `Human.Cry`, the generic NPC scream heard in most levels (START sample 399; the user had heard it in START) | Waveform, small lag |
| `SpearGun` (465) | `SpearGun.Fire` (divers' spear gun) | Waveform |
| `EngineOldBoat` (478/479) | `OldMotorBoatEngine.Engine` above/under water | Waveform |
| `SquidHurt` (639) | Close to DEEPSEA2 `Squid.Attack` (correlation 0.985; unused there too) | Waveform |

The waveform matches were found before the extractor fix (§2), when exact hashing still missed them.

**Truly unique and never played:**
- `FootstepsGuard` (457, 1.15 s): an NPC walking on wood. The user listened 2026-11-23: never heard in-game.
- `EngineSeaSeeker` (477, 1.23 s, underwater only).
- Brody's two lines (§3).

**Also START-only and unrequested in the same bank:** `SpearGun`, `FootstepsGuard`, `HumanMaleFear`, `FerryEngineIdle`, `EngineOldBoat`, `EngineSeaSeeker`, `SplashOut3/4`, `JawsGrowl2`, `SquidHurt`. A cutscene's worth of effects, probably for an older or longer version of the ending (compare the old Brody clips `MBrody_AuroraComesMovie` / `GrabHarpoonMovie`, `docs/cut_content.md`).

---

## 5. DEEPSEA2: the squid boss

**In short:** the squid boss's attack, pain and death sounds were recorded and banked but never connected to the fight. In-game, the squid is heard only in the entrance cutscene (user-confirmed 2026-11-23).

**The bank:** `SndSquid` (17940), group `Squid`, underwater only.

| Name | Samples | Status |
|---|---|---|
| `Idle` | 573–575 | Used |
| `Attack` | 569, 571 | Never requested |
| `Hurt` | 570, 572 | Never requested |
| `Die` | 576 | Never requested |

No identical copy plays anywhere. START `Movie.SquidHurt` (639) is a near-copy of 571, also unused.

**Who plays `Squid.Idle`:**
- Only two `GDSoundEvent3DB` nodes in the **entrance cutscene**: `TheSquidEntrance_Movie` → `szkvidhangok` ("squid sounds") → `szkvidordit` ("squid roar") and `csapvegighuz` ("tentacle drags along").
- They sit at the cutscene origin (0, −210, −57), about 90 units from the boss model (26, −248, 23), near the room's centre. So the sound comes from the room, not from the squid.
- Nothing in the fight or the defeat movie requests a `Squid.*` sound.

**Why the boss can't play them:**
- `BossSquid` (3841, `MLEnemy`) runs `NASquidBoss` (3842). Its 11 fields: `m_roomcenter`, `m_roomradius`, `m_armrange`, `m_cutscene`, `m_tentacleids`, `m_torntentacle`, `m_armrubberskeletons`, `m_mouthid`, `m_headid`, `m_eyeids`, `m_armswingdelay`. No sound field.
- The class's strings in the exe are field and clip names only.
- Creature AIs build `<prefix>.Idle/Hurt/Die` from their first clip name (see the audit docstring). The reef squids give `LittleSquid`, the boss rig `BossSquidBody`. No `Squid_…` rig exists.

---

## 6. AQUARIUM: the boss orca

**In short:** the boss orca's `Threatening` and `Alarm` calls were recorded and banked on PC and PS2 but never played (user-confirmed: not heard in the fight, 2026-11-23).

**The bank:** `Orca`, AQUARIUM only, underwater only. 9 entries:

| Name | Samples | Requested? |
|---|---|---|
| `Hurt` | 559, 560, 562 | Yes |
| `Idle` | 561, 563, 564 | Yes |
| `Die` | 805 | Yes |
| `Threatening` | 565 (2.11 s) | **No** |
| `Alarm` | 566 (1.22 s) | **No** |

**Who requests what:**
- The boss orca's class **`MSOrca`** requests `Orca.Die`/`Hurt`/`Idle` (strings `0x8A55D0`–`0x8A55E8`, next to its fields and `BOSS_ORCA_*` state names; a second `Orca.Die` at `0x8A48ED`).
- Nothing requests `Threatening` or `Alarm`: no exe string, no property or action in the level, and the generated `%s.Idle/Hurt/Die` names don't cover them.
- None of the `BOSS_ORCA_*` states (open-mouth swim, supercharge, grab, tail whip, dizzy) has a sound of its own.

**Unique recordings:** 565 and 566 match none of the other orca, cutscene (`MovieEnd.OrcaLastGrowl` 800, `OrcaFlesh` 801) or AQUARIUM samples (best correlation ≤ 0.07).

**They fit a pattern:**
- Other creature banks carry the same extra names. The hammerhead's AI does request `HHShark.Alarm` (exe `0x8A5204`), while `HHShark.Attack`, `Dolphin.Attack` and some `Dolphin.Alarm` entries are banked and unrequested.
- So sound design delivered a full set per creature (idle, hurt, die, attack or threatening, alarm), and `MSOrca`'s code plays only three.

**PS2 is the same:** `AQUA2.GDE` has the identical name list (`Hurt Hurt Idle Hurt Idle Idle Threatening Alarm Die`); `SLUS_210.62` requests only `Orca.Die/Hurt/Idle`.

### OPEN_S orcas (the user's suggestion)

- OPEN_S has the open-ocean orcas of SC26 Orca Revenge:
  - template `OrcaNB Root` (49054, `MLEnemy`; info text "Orcas will hunt for Jaws…");
  - spawned by `OrcaGen` (5320, an `MSHHSharkGen` generator) under the area `OrcaRaiser` (5316).
- **Their AI is `MSNarwhal`** (action 49055; fields `m_SwimOnSurface`, `m_Angry`). It requests `Narwhal.Die`/`Hurt`/`Idle` (exe `0x8A5958`–`0x8A5974`, code near `0x50C472`), not `Orca.*`.
- **No level has a `Narwhal` bank**, and OPEN_S has no `Orca` bank either (its `Orca2Engine` is Quint's boat).
- So `Threatening`/`Alarm` can't play there, and the open-ocean orcas' own requests find nothing: they should be silent apart from generic hit and splash effects. **Worth an ear check.**
- Same in PS2 `OPEN_S.GDE`. The only other `OrcaNB` copy is in TITLE (menu).
- Every `Orca.Die` request in the exe (`0x4FE305`, `0x4FEE1B`, `0x519940`, static descriptor `0x51D200`) is in boss-orca code or static sound descriptors.

---

## 7. TOWN: alarm bell

**In short:** an alarm bell recorded for Blood on the Beach, banked on PC and PS2, with nothing that could ring it. The user listened (2026-11-23): never heard in-game. It sounds like a hand bell of the kind on a boat or rung by lifeguards to warn swimmers. A shark alert would fit the stage, but that's an impression, not data.

**The bank:** `SndBell` (node 16374), group `Bell`, one name `Alarm`.

| Sample | Version | Length | Sound |
|---|---|---|---|
| 431 | Above water | 2.13 s | Bright metallic ringing, strongest partials ~3.6 and 4.3 kHz |
| 432 | Underwater | 3.75 s | A separately made muffled version, energy ~250–300 Hz |

Both are unique recordings.

**TOWN only:**
- No other PC level has a `SndBell` bank.
- Its neighbours in the node list (`SndElectricFence`, `SndBarrelExplosion`, `SndWood`, `SndHelicopter`, 4 IDs apart) are shared banks that TOWN uses. `Bell` is the only TOWN-specific one in that run.

**Nothing could play it:**
- No property or action in TOWN names `Bell.Alarm`.
- The exe has no `Bell` string, so it can't build the name either.
- No object in TOWN is named after a bell (Hungarian *harang*), church or fire station. Other "bell" hits are the field name `m_alphabell`.

**PS2 `TOWN.GDE` is the same:** the bank is there, nothing requests it.

---

## 8. TOWN: fireworks

**In short:** the unused `FireWork` sample is the raw master of the firework sound that does play. Not a lost sound.

**The bank:** `TownFirework`, three 9.55 s takes of one recording.

| Sample | Name | Played by |
|---|---|---|
| 110 | `FireWork` | Nothing |
| 111 | `FireWorkNrom` (sic) | Action 1187 `FireWorkNorm` in the intro cutscene's `controls` → `sound cont1`, tick 140 |
| 112 | `FireWorkHalfNorm` | Sound object `Firework` 1117 |

**How they relate:**
- 112 = 111 × 0.63 (correlation 1.0000). "Norm" = normalised; 111 peaks at full scale.
- 110 correlates 0.93 with them. It's quieter with more dynamic range (1 s RMS 961–3251 against 3534–6372): the master they were normalised and compressed from.

**The show itself was cut down** (also in `docs/cut_content.md`):
- The intro cutscene's `firework 1` / `firework 2` controls (on `NemElpusztuloActionok` 1172) each fire 7 bursts across 7 emitters.
- Only `firework1 ref` (1375) and `firework1 ref 1` (1374) survive, both references to the template `continuous firework gun` (1307), at about (3000, 0, 120) by the barges.
- **Nodes 1368–1373 and 1378 are deleted.** (1357/1361/1365/1377 in that range are action IDs, not gaps.) 1369–1373 are the five targets the controls still list.
- **PS2 `TOWN.GDE` is the same** (two refs, the same three takes), so the trim predates both builds.
- The sound wasn't affected: one 9.55 s firework bed covers the show either way.

---

## 9. DEEPSEA: mine sounds; DEEPSEA2: generator

### DEEPSEA bank `Mine` (underwater only)

**Used:** `AmbientMine`, `AmbientMineNoise01/02`, `AmbientKupola` (*kupola* = dome), `EngineBigDrill`, `Kifuj` (blow out), `Sziszeg` (hiss), `Spark`, `Stream`, `GozKifuj` (steam blow-out), `EngineCrusher`.
- `EngineCrusher` is the rock crusher `Rock_Crusher`. Its drill head `furofej_rc` and turbine `turbina_rc` rotate via `JTSRotAct`/`ANRotate`.

**Never requested** (all unique recordings):

| Name | Sample | Length |
|---|---|---|
| `EngineFutoszalag` (*futószalag* = conveyor belt) | 168 | 5.02 s |
| `Servo01` / `02` / `03` | 170–172 | 1.1–1.5 s |

**The conveyor belt:**
- DEEPSEA places 42 `futoszalag` pieces, all plain top-level `GDModel`s with no actions: nothing moves them and no sound object is near them. DEEPSEA2 has 3 more.
- The belt was built as static scenery, so its engine loop had nothing to attach to.

**The servos:** no object in DEEPSEA is named after a servo, robot or arm mechanism, and nothing requests the names. What they were for isn't recorded.

### DEEPSEA2 bank `Generator`

| Name | Sample | Played by |
|---|---|---|
| `Engine` | 511 | Loop on `generator` / `generator 1` |
| `Slow` | 512 (1.39 s) | **Nothing** |
| `Stop` | 513 | `genleall` (*generátor leáll* = "generator stops") |

When the generator is destroyed, the script starts `genleall` 20 ticks later. There's no step for `Slow`, so the planned run-down sound between running and stopped was skipped.

**PS2 is the same:** `DEEPSEA.GDE` has `EngineFutoszalag` and `Servo01–03` once each, unrequested; `DEEPSEA2.GDE` likewise for `Slow`.

---

## 10. The first lead: long SFX samples

**Closed.** Found 2026-07-29, before the dialogue was located. The idea: `GSMP` category 2 (sound effects) samples are usually under 5 s, so long, level-unique, `GSFX`-triggered ones might be the missing story dialogue.

**It was the wrong place to look.** The dialogue turned out to be in `SMPC` samples, which the old extractors skipped (2026-10-03, `docs/cutscene_dialogue.md`).

**The candidates, for the record:**

| File | Length | Result |
|---|---|---|
| `BEACH_id0590`, `BEACHPST_id0579` | 44.58 s | A song on the beach radio, not dialogue (user listened 2026-07-29). Diegetic music is filed as category 2; category 3 seems to be background music. |
| `BEACH_id0476` | 16.44 s | Not checked |
| `WRACK_id0416` | 14.16 s | Not checked |
| `WRACK_id0427`, `TOWN_id0540` | 10.70 s | Not checked |
| `TOWN_id0541` | 10.31 s | Not checked |
| `KATATAMA_id0288` | 10.00 s | Not checked |
| `DEEPSEA_id0166`, `DEEPSEA2_id0564` | 9.98 s | Not checked |
| `WRACK_id0230` | 9.91 s | Not checked |
| `DEEPSEA_id0163` | 9.58 s | Not checked |
| `TOWN_id0109`–`0112` | 7.12–9.55 s | 110–112 are the firework takes (§8). 109 not checked. |
| `DEEPSEA_id0489`, `DEEPSEA2_id0516` | 8.02 s | Not checked |
| `DOCKS_id0301` | 7.43 s | Not checked |
| `DEEPSEA2_id0599` | 7.24 s | Not checked |
| `AQUARIUM_id0681` | 7.08 s | Not checked |

All are `GSFX`-triggered (checked on `BEACH_id0590`) and already in `audio/<LEVEL>/`.

---

## 11. Old mistakes

| Old claim | Now |
|---|---|
| Long category-2 samples may be the story dialogue | The dialogue is in `SMPC` samples (§10) |
| `TOWN_id0109`–`0112` (4 consecutive IDs) are likely a recorded conversation | 110–112 are the three firework takes (§8) |
| START 470/471 are maybe Brody lines, unverified | User-transcribed: the cut rope-fight lines (§3) |
| `SMPB`/`SMPC` `.wav` files are exact | They lacked 2 samples until the 2026-11-23 fix (§2) |

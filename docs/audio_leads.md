# Audio Leads — Possible Story Dialogue

> **Superseded 2026-10-03:** the story dialogue was found, as 49 captioned `SMPC` voice samples, which the old extractors skipped. See `docs/cutscene_dialogue.md`. The cat2 "long sample" candidates below were the wrong place to look.

> Moved here from `CLAUDE.md` on 2026-10-02 to keep that file under its size limit. Text is verbatim.

## Lead: long-duration `GSMP` cat2 "SFX" samples may be the missing story dialogue (found 2026-07-29, unconfirmed — needs a human to listen)

Regular `GSMP` category 2 (SFX) samples are documented as "typically <5s." Scanning actual extracted durations across all 20 GDWs turns up a small set of outliers, all confirmed **actively referenced by a `GSFX` trigger** (checked `BEACH_id0590`, not dangling data) — durations and per-level uniqueness (not duplicated across many GDWs like the shared ambient pool is) make them poor fits for footsteps/splashes/explosions and good fits for spoken dialogue:

| File | Duration | Note |
|---|---|---|
| ~~`BEACH_id0590`, `BEACHPST_id0579`~~ | ~~44.58s~~ | **RULED OUT (2026-07-29, user confirmed by listening): this is a song playing diegetically on the beach (radio/boombox source), not dialogue.** Duration/GSFX-triggered alone is not sufficient evidence of speech — diegetic music cues are also filed under cat2 rather than cat3 (cat3 appears to be reserved for non-diegetic background/loop music). Downgrades confidence in the rest of this list; still worth checking but expect more music/ambient false positives, not just dialogue. |
| `BEACH_id0476` | 16.44s | |
| `WRACK_id0416` | 14.16s | |
| `WRACK_id0427`, `TOWN_id0540` | 10.70s | |
| `TOWN_id0541` | 10.31s | |
| `KATATAMA_id0288` | 10.00s | |
| `DEEPSEA_id0166`, `DEEPSEA2_id0564` | 9.98s | |
| `WRACK_id0230` | 9.91s | |
| `DEEPSEA_id0163` | 9.58s | |
| `TOWN_id0109`, `id0110`, `id0111`, `id0112` | 7.12s, 9.55s, 9.55s, 9.55s | **4 consecutive resource IDs**, a strong signature for a short recorded back-and-forth exchange (sequential lines authored/exported together) |
| `DEEPSEA_id0489`, `DEEPSEA2_id0516` | 8.02s | |
| `DOCKS_id0301` | 7.43s | |
| `DEEPSEA2_id0599` | 7.24s | |
| `AQUARIUM_id0681` | 7.08s | |

These files already exist in `audio/<LEVEL>/` right now (no re-extraction needed) — this project has no audio playback/transcription tool available, so this is an unconfirmed lead, not a verified finding. **Next step: a human listens to the `TOWN_id0109`–`id0112` sequence** (now the best remaining candidate — 4 consecutive resource IDs still looks like the strongest structural signature for a short recorded exchange) and works down the rest of the list, and confirms/denies each as spoken dialogue vs. diegetic music/ambience.

## Unused-audio audit (2026-10-15)

`python3 scripts/audit_audio.py [NAME ...]` (read-only) checks every extracted file in `audio/<NAME>/` against the playback chain `Group.Name` request → sound bank → `GSFX` → sample, and writes `audio/audio_audit.csv` + `audio/audio_audit.txt`. Format of the chain and the status meanings are in the script's docstring and `CLAUDE.md` "Unused-audio audit".

First run over 19 levels with audio: 4,050 files, **3,677 used, 373 unrequested**, none without a bank or trigger. Unrequested names, by number of levels:

- **Shared, in 12–18 levels:** `Camera.AboveWater`, `Camera.UnderWater` (surface-crossing sounds), `Jaws.ImpactGlass/Wood/Metal/WindowUnbreak`, `Jaws.GrabBody`, `SeaSeeker.Fire`, `HumanFemale.Panic`, `HHShark.Attack`.
- **6–8 levels:** `ElectricFence.Ambient/Szikrazas`, `Seal.SplashIn/SplashOut`, `Boat.WaterSplash`, `SeaSeeker.Engine`, `Dolphin.Alarm/Attack`, `Submarine.Ambient`.
- **Level-specific leads:** DEEPSEA2 `Squid.Hurt/Die/Attack` (only `Squid.Idle` is requested, by two sound objects; the exe's one `Squid` string is the class name); **START `Movie.VoiceBrody3/4`** (samples 470/471, 2.4 s and 5.2 s, uncaptioned; START's captioned Brody lines 1/2 are played by actions 214/215; possibly from the cut Aurora rope ending, unverified, needs listening); START's other `Movie.*` cutscene sounds (`EngineSeaSeeker`, `SquidHurt`, `JawsGrowl2`…); TOWN 388 `MovieTown1.VoiceCrew2` (already known unused); BEACHPST `Truck.*`, `TeeniePartyMusic.Ambient`, `Waterslide.WaterStart`; DEEPSEA `Mine.Servo01–03`; WRACK `Movie.WoodCreak1–3`, `Movie.BoatSplash01/02`.

Caveats: "unrequested" means no string or typed `GSFX` reference was found, not that the sound was proven silent; the exe could still reach a bank entry another way (not seen so far). "Used" means something can ask for it; whether that object or action ever runs needs `dump_gdcontrol.py` or a play test.

### START `Movie.VoiceBrody3/4` checked (2026-11-23)

- **Samples:** 470 (`Movie.VoiceBrody3`, 2.43 s) and 471 (`Movie.VoiceBrody4`, 5.19 s), `audio/START/START_id0470_*.wav` / `…0471_*.wav`. Plain `GSMP`, not `SMPC`: no caption was ever attached, unlike lines 1/2 (460/461, `SMPC`, captioned).
- **Distinct recordings:** PCM matches no other sample in any level. DEEPSEA2's `Movie.VoiceBrody3` is a different, captioned line (each level has its own `Movie` bank, so names collide).
- **Never played, PC and PS2:** in PC `START.GDW` and PS2 `START2.GDE`, `VoiceBrody1/2` occur 3× (bank + sound-event action), `3/4` once (bank only); PS2 `START.GDE` has all four once. No `GDSoundEvent` action names them; the cutscene's sound actions (209–227 on `AuroraComesMovie`/`Sounds` 208) run without ID gaps, and its controls' empty steps are all-zero (no leftover targets).
- **Cutscene timing:** `AuroraComesMovie` (198) plays `VoiceBrody1` at tick 0 and `VoiceBrody2` at 170 (both Scene01); the movie ends at tick 1000; Scene04 (from ≈725) only switches camera, no sound. Lines 3+4 (≈228 ticks) would fit there, but nothing proves it.
- **Signal check:** both are speech (strong harmonic voicing, 68% / 47% voiced frames; 471 is two phrases with a ~1 s pause). Median pitch ≈220 Hz vs Brody's used lines 117–159 Hz (his shout `There it is!` 175 Hz): either yelled delivery or a different speaker. Crude autocorrelation estimate.
- **Same bank, also START-only and unrequested:** `Movie.SpearGun`, `FootstepsGuard`, `HumanMaleFear`, `FerryEngineIdle`, `EngineOldBoat` (aw+uw), `EngineSeaSeeker`, `SplashOut3/4`, `JawsGrowl2`, `SquidHurt`: a cutscene's worth of unused effects, probably an older or longer version of the ending (cf. the old Brody `MBrody_AuroraComesMovie`/`GrabHarpoonMovie` clips, `cut_content.md`).
- **Content (user-transcribed 2026-11-23):** 470 *"Gottem! Hold tight, he's gonna try and break free!"*; 471 *"Oh my God it's a Great White! Make sure he's fully restrained and let's get him to the research center ASAP."* **These are the cut rope fight's lines** (hook → tug-of-war → capture), see `cut_content.md`. Same voice actor as the shipped lines 1/2 (user-confirmed by listening); the higher pitch is excited delivery.

### START's other unused `Movie` sounds checked (2026-11-23)

START's `Movie` bank is node `SndMovie 5` (16800), 28 names. It serves two shipped cutscenes: the tutorial ending `AuroraComesMovie` (198, actions 214–227) and **`DeathOfShawMovie`** (543, actions 559–565), which is **shipped**: the death of Shaw's son, a diver (`ShawsSonKilledEvent`), started by root action 8 `DeathOfShaw_MovieStarterNDestroyer` (not Shaw himself, and not cut).

- **Above/underwater:** `VoiceBrody3/4` have the same `GSFX` in both the above- and underwater lists, while the cutscene's `VoiceBrody1/2` are above-water only. That fits lines meant for a playable fight where the camera can be under the surface.
- **Order / empty slots:** names 0–9 (`BigShipComing` … `VoiceBrody2`) look like the first batch; `SquidHurt` has a far later `GSFX` id (2176 vs 1510–1538); `SquiIdle` and `Bubbles` are empty slots (no `GSFX`).
- **Copies of stock sounds (not unique):** `SplashOut3`/`SPlashOut4` (468/469) = the shared `Jaws.SplashOut` samples; `JawsGrowl2` (459) = shared `Jaws.Growl` (also WRACK `Movie.JawsGrowl02`); `FerryEngineIdle` (455) = TOWN `Ferry.Engine`.
- **More copies, found by waveform match with small lags (exact hashing missed them, see the `rip_smpb.py` offset below):** `HumanMaleFear` 456 = `Human.Cry`, the generic NPC scream played in gameplay in most levels (START sample 399; the user had heard it in START); `SpearGun` 465 = `SpearGun.Fire` (divers' spear gun, used); `EngineOldBoat` 478/479 = `OldMotorBoatEngine.Engine` aw/uw (used); `SquidHurt` 639 ≈ DEEPSEA2 `Squid.Attack` (corr 0.985; unrequested there too).
- **Truly unique and never played:** only `FootstepsGuard` 457 (1.15 s; user listened 2026-11-23: an NPC walking on a wooden surface, never heard in-game, judged unused) and `EngineSeaSeeker` 477 (underwater only, 1.23 s), plus `VoiceBrody3/4` (470/471, no copy anywhere). So the bank's unused entries are mostly stock sounds staged for cutscenes; the real cut-content leftovers are Brody's two rope-fight lines.
- **Extractor offset (found 2026-11-23):** `scripts/rip_smpb.py` starts the PCM 4 bytes late (`audio_start = sec_hdr + 20`; should be `+ 16`): every SMPB `.wav` lacks its first 2 samples and ends with 2 zero samples (the trailing loop fields). Inaudible, but byte-exact comparisons between GSMP and SMPB copies failed. **Fixed the same day** in both `rip_smpb.py` and `rip_smpc.py` (same mistake), all 1,128 + 49 files re-extracted; copies now hash-match.

### Recording check: which unrequested sounds are really never heard (2026-11-23)

`audit_audio.py` now also compares the 16-bit PCM of every non-used file with every used one (exact match; possible since the `rip_smpb.py`/`rip_smpc.py` fix). New CSV columns `recording` (`plays_elsewhere` / `unheard`) and `copy_of`; `audio_audit.txt` lists unheard files first. Result: of the 373 unrequested files, **194 play elsewhere** under another name or level (e.g. START `Movie.HumanMaleFear` = `Human.Cry`, `Movie.SpearGun` = `SpearGun.Fire`), **179 are unheard**, which are **48 distinct recordings**:

- **Shared, unheard in every level:** `Camera.AboveWater` (18 levels), `Jaws.ImpactGlass` (18), `Jaws.ImpactWood` (18), `SeaSeeker.Fire` (15), `HumanFemale.Panic` (2 takes, 13), `Seal.SplashIn/SplashOut` (8), `Dolphin.Alarm` (6), `Dolphin.Attack` (2 takes, 6), `Stingray.Bite` (3 takes, 4), `SmallSub.Crash` (3), `Buoy.Bell`, `Button.Esc`.
- **Bosses and creatures:** DEEPSEA2 squid `Squid.Attack` (2), `Squid.Hurt` (2), `Squid.Die`, plus START `Movie.SquidHurt` (≈ `Squid.Attack`, not byte-identical); AQUARIUM `Orca.Alarm`, `Orca.Threatening`.
- **Level-specific:** TOWN `Bell.Alarm` (2, checked 2026-11-23, see below), `TownFirework.FireWork` (checked 2026-11-23: the unprocessed master of the used firework sound, see below); DEEPSEA `Mine.Servo01–03`, `Mine.EngineFutoszalag` (*futószalag* = conveyor belt), DEEPSEA2 `Generator.Slow`; AQUARIUM `HotDogStand.Bounce` (2); WRACK `JeepEngine.Engine` (3), `Movie.BoatSplash01/02`, `Movie.Explosion03`; DOCKS `Movie.FishingBoatEngine`.
- **Cut-scene voice and leftovers:** START `Movie.VoiceBrody3/4` (rope fight), `Movie.FootstepsGuard`, `Movie.EngineSeaSeeker`, one `Movie.EngineOldBoat` copy; TOWN `MovieTown1.VoiceCrew2` (alternate take).

Same limits as before: "used" means the name can be requested, not that the requester ever runs.

### DEEPSEA2 squid sounds checked (2026-11-23)

- **Bank `SndSquid` (17940), group `Squid`, underwater only:** `Idle` ×3 (samples 573–575, used), `Attack` ×2 (569, 571), `Hurt` ×2 (570, 572), `Die` (576), all never requested and no identical copy plays anywhere (START `Movie.SquidHurt` 639 is a near-copy of 571, also unused).
- **User-confirmed 2026-11-23:** a squid sound plays in the opening in-game cutscene. That's `Squid.Idle`: its two sound objects sit at the cutscene origin (0, −210, −57), about 90 units from the boss model (26, −248, 23), near the room centre, so it comes from the room, not attached to the squid.
- **Who plays `Squid.Idle`:** only two `GDSoundEvent3DB` nodes in the **entrance cutscene** (`TheSquidEntrance_Movie` → `szkvidhangok` "squid sounds": `szkvidordit` "squid roar", `csapvegighuz` "tentacle drags along"). Nothing in the fight or the defeat movie requests a `Squid.*` sound.
- **The boss can't request them:** `BossSquid` (3841, `MLEnemy`) runs `NASquidBoss` (3842) whose 11 fields are `m_roomcenter`, `m_roomradius`, `m_armrange`, `m_cutscene`, `m_tentacleids`, `m_torntentacle`, `m_armrubberskeletons`, `m_mouthid`, `m_headid`, `m_eyeids`, `m_armswingdelay`: no sound field, and the class's exe strings are field and clip names only (no sound names).
- **Generated names don't reach them either:** the exe's creature AIs build `<prefix>.Idle/Hurt/Die` from the first clip name (see the audit docstring); the reef squids give `LittleSquid`, the boss rig `BossSquidBody`. No `Squid_…` rig exists.
- **Conclusion:** the boss's attack, pain and death sounds were recorded and banked but never wired to the fight, which therefore has no squid voice beyond the entrance cutscene. **User-confirmed in-game 2026-11-23:** the Attack/Hurt/Die samples are never heard.

### TOWN fireworks checked (2026-11-23)

- **Bank `TownFirework`, three 9.55 s takes of one recording:** `FireWork` (110, unrequested), `FireWorkNrom` (111, sic; played by action 1187 `FireWorkNorm` in the intro cutscene's `controls` → `sound cont1`, tick 140), `FireWorkHalfNorm` (112, played by sound object `Firework` 1117).
- **What the unused one is:** 111 and 112 are the same samples at different gain (112 = 111 × 0.63, corr 1.0000; "Norm" = normalised, peaks at full scale). 110 correlates 0.93 with them and is quieter with more dynamic range (1 s RMS 961–3251 vs 3534–6372): the **raw master** they were normalised and compressed from. Not a lost sound; it never needed to play.
- **The show itself was cut down (already in `cut_content.md`):** the intro cutscene's `firework 1`/`firework 2` controls (on `NemElpusztuloActionok` 1172) each fire 7 bursts across 7 emitters; only `firework1 ref` (1375) and `firework1 ref 1` (1374) survive, both references to the template `continuous firework gun` (1307), at ≈(3000, 0, 120) by the barges. Node IDs **1368–1373 and 1378 are deleted** (1357/1361/1365/1377 in the same range are action IDs, not gaps); 1369–1373 are the five targets the controls still list. **PS2 `TOWN.GDE` is the same** (two refs, same three firework takes), so the trim predates both builds. The sound wasn't affected: one 9.55 s firework bed covers the show either way.

### TOWN `Bell.Alarm` checked (2026-11-23)

- **Bank `SndBell` (node 16374, group `Bell`, one name `Alarm`)**: sample 431 above water (2.13 s, bright metallic ringing, strongest partials ~3.6 and 4.3 kHz) and 432 under water (3.75 s, a separately made muffled version, energy ~250–300 Hz). Both unique recordings, never requested.
- **TOWN only:** no other PC level has a `SndBell` bank. Its neighbours in the node list (`SndElectricFence`, `SndBarrelExplosion`, `SndWood`, `SndHelicopter`, each 4 IDs apart) are shared banks that other levels have too and TOWN uses; `Bell` is the only TOWN-specific one in that run.
- **Nothing could play it:** no PROP or action in TOWN names `Bell.Alarm`; the exe holds no `Bell` string, so it can't build the name either (its run-time names are creature `%s.Idle/Hurt/Die`); no object in TOWN is named after a bell (Hungarian *harang*), church or fire station (the other `bell` hits are the `m_alphabell` field name).
- **PS2 `TOWN.GDE` is the same:** the `SndBell` bank is there, nothing requests `Bell.*`.
- **Conclusion:** an alarm bell recorded for Blood on the Beach, banked in both versions and never hooked up. Which object or moment it was meant for isn't recorded anywhere in the data. **User listened (2026-11-23):** definitely never heard in-game; it sounds like a hand bell of the kind on a boat or rung by lifeguards to warn swimmers (a beach shark alert would fit the stage, but that's an impression, not data).

### AQUARIUM orca sounds checked (2026-11-23)

- **Bank `Orca` (AQUARIUM only, underwater only), 9 entries:** `Hurt` ×3 (559, 560, 562), `Idle` ×3 (561, 563, 564), `Threatening` (565, 2.11 s), `Alarm` (566, 1.22 s), `Die` (805). The boss orca's exe class **`MSOrca`** requests `Orca.Die`/`Orca.Hurt`/`Orca.Idle` (strings at `0x8A55D0`–`0x8A55E8`, next to its fields and the `BOSS_ORCA_*` state names; a second `Orca.Die` request sits at `0x8A48ED`). Nothing requests `Threatening` or `Alarm`: no exe string, no PROP or action in the level, and the generated `%s.Idle/Hurt/Die` names don't cover them.
- **Unique recordings:** 565 and 566 match none of the other orca, cutscene (`MovieEnd.OrcaLastGrowl` 800, `OrcaFlesh` 801) or AQUARIUM samples (best normalised cross-correlation ≤ 0.07).
- **They fit the creature template:** other creature banks carry the same extra names, and the hammerhead's AI does request its `HHShark.Alarm` (exe `0x8A5204`), while `HHShark.Attack`, `Dolphin.Attack` and some `Dolphin.Alarm` entries are likewise banked and unrequested. So sound design delivered a full set per creature (idle, hurt, die, attack/threatening, alarm); `MSOrca`'s code only plays three of them. `Threatening` is the orca's only such name; none of its `BOSS_ORCA_*` states (open-mouth swim, supercharge, grab, tail whip, dizzy) has a sound of its own.
- **PS2 is the same:** `AQUA2.GDE` has the identical name list (`Hurt Hurt Idle Hurt Idle Idle Threatening Alarm Die`) and `SLUS_210.62` requests only `Orca.Die/Hurt/Idle`.
- **Conclusion:** the boss orca's threat and alarm calls were recorded and banked in both versions but never played. **User-confirmed 2026-11-23:** not heard in the boss fight.
- **OPEN_S checked (user's suggestion):** OPEN_S has the open-ocean orcas of SC26 Orca Revenge: template `OrcaNB Root` (49054, `MLEnemy`, info text "Orcas will hunt for Jaws…"), spawned by `OrcaGen` (5320, an `MSHHSharkGen` generator) under the area `OrcaRaiser` (5316). Their AI is **`MSNarwhal`** (action 49055, fields `m_SwimOnSurface`, `m_Angry`), which requests `Narwhal.Die`/`Hurt`/`Idle` (exe `0x8A5958`–`0x8A5974`, code near `0x50C472`), not `Orca.*`. **No level has a `Narwhal` sound bank** and OPEN_S has no `Orca` bank either (its only orca bank is `Orca2Engine`, Quint's boat). So `Threatening`/`Alarm` can't play there, and the open-ocean orcas' own idle/hurt/die requests find nothing: they should be voiceless apart from generic hit/splash effects (worth an ear check). Same in PS2 `OPEN_S.GDE`. The only other `OrcaNB` copy is in TITLE (menu). All `Orca.Die` requests in the exe (`0x4FE305`, `0x4FEE1B`, `0x519940`, static descriptor `0x51D200`) sit in boss-orca code or static sound descriptors.

### DEEPSEA mine sounds and DEEPSEA2 generator checked (2026-11-23)

- **DEEPSEA bank `Mine` (underwater only):** used = `AmbientMine`, `AmbientMineNoise01/02`, `AmbientKupola` (*kupola* = dome), `EngineBigDrill`, `Kifuj` (blow out), `Sziszeg` (hiss), `Spark`, `Stream`, `GozKifuj` (steam blow-out), `EngineCrusher` (the rock crusher `Rock_Crusher`, whose drill head `furofej_rc` and turbine `turbina_rc` rotate via `JTSRotAct`/`ANRotate`). **Never requested:** `EngineFutoszalag` (168, 5.02 s, *futószalag* = conveyor belt) and `Servo01/02/03` (170–172, 1.1–1.5 s). All four are unique recordings.
- **Conveyor belt:** DEEPSEA places 42 `futoszalag` pieces, all plain top-level `GDModel`s with no actions (nothing moves them, no sound object near them); DEEPSEA2 has 3 more. The belt was built as static scenery, so its engine loop had nothing to attach to.
- **Servos:** no object in DEEPSEA is named after a servo, robot or arm mechanism, and nothing requests the names; what they were for isn't recorded.
- **DEEPSEA2 bank `Generator`:** `Engine` (511, loop on `generator`/`generator 1`), `Slow` (512, 1.39 s, never requested), `Stop` (513, played by `genleall` = *generátor leáll*, "generator stops"). When the generator is destroyed, the script starts `genleall` 20 ticks later; there is no step for `Slow`, so the planned run-down sound between running and stopped was skipped.
- **PS2 is the same:** `DEEPSEA.GDE` has the bank names once each (`EngineFutoszalag`, `Servo01–03`) and nothing requests them; `DEEPSEA2.GDE` likewise for `Slow`.


# Audio formats: GSMP, SMPB, SMPC, GSFX, unused-audio audit, WMV movies

Moved word for word from the root `CLAUDE.md` on 2026-11-25 to keep that file short. Where this disagrees with older docs, this text is the newer one.

## Audio System

Two audio chunk types are fully extracted. All scripts output to `audio/`.

### GSMP (Game Sample) — `scripts/rip_gsmp.py`

> **Note (2026-10-03):** `scripts/rip_gsmp.py` is not present in the repo (only its output in `audio/` and the sibling `rip_smpb.py` exist). The format below is enough to rewrite it.
Raw PCM audio blocks. Header (24 bytes after the 8-byte chunk header):

```
[uint32 sample_id][uint32 flags][uint32 hash][uint32 category][uint32 sample_rate][uint32 byte_count]
```

Audio data (signed 16-bit PCM mono) follows immediately. Flags vary by GDW package but a consistent bit pattern holds across all levels:

| flags bit | meaning |
|---|---|
| base (0x01 or 0x81) | raw PCM audio block |
| base \| 0x20 | SMPB-type block (see below) |
| 0x44 | GSFX property block — NOT audio (contains volume float 0.8 + GSMP ID reference) |

Category field values: `2` (SFX), `3` (music, long loops), `6` (ambient). Music tracks (cat3) are 2–3.5 minutes at 22050 Hz; SFX and ambient are typically <5s at 11025 Hz.

**Level music, decoded 2026-10-04 (`scripts/gdw_music.py`):** a sound bank node with group name `Music` (`PROP 0x08001939`; FISH node `SndMusic`) names four tracks (`0x0800193A`): `Calm_aw` (calm, above water), `Calm_uw` (calm, underwater), `Susp`, `Act`, with a parallel `['GSFX'][id]` list (`0x0800193B`) → GSFX → one GSMP each. FISH's are **16-bit stereo** 22,050 Hz, 117.1 s each, all exactly the same length (likely synced layers). The PCM is followed by **`[uint32 loop start frame][uint32 loop end frame]`** (music: 0 and frames − 1; SFX: 0, 0; 2 extra zero bytes when the byte count is ≡ 2 mod 4). Rebuilding a stock music block from its PCM is byte-identical. Replacing all four with test tones works in-game (user-confirmed 2026-10-04: calm above/under switch; suspense and action audible once made loud and harsh, since they're mixed in as layers, in stock FISH/OPEN_NE with test tones). **Engine side (2026-10-04, `Jaws.exe`):** the four tracks are **layers played together** and mixed by volume. The sound player `FUN_006fbc60` maps a `Music.<track>` name to slot 0–3 (`Calm_aw`, `Calm_uw`, `Susp`, `Act`, strings at `0x8BB7C8/C0/B8/B4`) and keeps per-slot handles/volumes at `+0xF814`/`+0xF824`; `FUN_006fbfb0` = SetMusicVolumes(float[4]) (via the audio object's vtable `0x7FB138` slot `+0x100`, method `0x715C50`). The music director is `FUN_004982e0` (vtable `0x7D8E24`, slot `+0x48`): calm layer from the underwater flag `DAT_008b2e7c`, suspense/action targets from a 4×4 float table (`+0x44`) row picked by a state number at `+0x4C` (0–2), faded per tick. What sets that state is not traced yet (the class is not named; candidates `GDPlayMusic`/`GDPropMusic`).

Output filename: `{STEM}_id{id:04d}_cat{cat}_{rate}hz_{dur:.2f}s.wav`

**Extracted: ~2873 files across all 20 GDWs.**

### GSMP+SMPB (Embedded Sample Block) — `scripts/rip_smpb.py`
A variant of GSMP where the `hash` and `category` fields are replaced by an `OBPR` sub-chunk. These blocks are identified by `data[pos+16:pos+20] == b'OBPR'`.

Structure:
```
GSMP [block_size]
  [uint32 sample_id]
  [uint32 flags]
  OBPR [size=20]
    PROP [size=12]
      prop_id=0x04000030  value="SMPB" (type tag)
  [secondary header 16 bytes: magic, field, sample_rate, byte_count]
  [raw PCM audio: byte_count bytes, signed 16-bit mono]
  [uint32 loop start][uint32 loop end] (+2 pad bytes when byte_count % 4 == 2), as plain GSMP
```

The "category" field read at the standard offset is actually the OBPR size (20), not a real category. Sample rate and byte count come from the secondary header at `pos + 16 + 8 + obpr_size`. **Corrected 2026-11-23:** the header is 16 bytes, not 20; the old "pad" word was the first 2 PCM samples, so `rip_smpb.py` (and `rip_smpc.py`, same mistake on its caption header) started 2 samples late. Both fixed (verified: after the PCM exactly the 8 loop bytes, or 10 with padding, remain in every block) and all 1,128 SMPB + 49 SMPC files re-extracted; SMPB copies now match their plain-GSMP twins byte for byte.

**Content:** NPC voice lines (short barks/reactions, 0.3–7s — durations and skeleton clip names like `BeingDevouredLegs`, `PanicRun`, `FrightenedRun`, `StandCheer3x` suggest crowd-panic/reaction audio, not full mission dialogue).

**Correction (2026-07-29) — these are NOT unused/cut content.** Previous docs claimed SMPB samples were "present but not triggered." This is wrong. Every SMPB sample is wired to a `GSFX` trigger block exactly like regular gameplay SFX — verified exhaustively on `START.GDW`: all 70/70 extracted SMPB sample IDs are referenced by a `GSFX` block's embedded sample-reference field (as are all 214/214 of that GDW's regular raw-PCM `GSMP` samples; only 3 of 287 total GSFX references in the file are dangling). See the `GSFX` decode note below — the old "unused" label was never verified against actual trigger data, just guessed from the format looking unusual.

Output filename: `{STEM}_smpb_id{id:04d}_{rate}hz_{dur:.2f}s.wav`

**Extracted: 1128 files across all GDWs.**

### GSFX — Sound Effect Trigger Blocks (decoded 2026-07-29)

`GSFX` is a real, distinct top-level RSRC tag (not literally a `GSMP` flags variant as earlier docs implied — that was an artifact of naive byte-pattern scanning landing mid-block). Fixed 68-byte payload, standard `[tag][uint32 size][payload]` framing (`size` = payload-only, consistent with the rest of the format):

```
GSFX [uint32 size=68]
  [uint32 event/instance id]
  [uint32 flags = 0x21]
  OBPR [uint32 obpr_size = 0]
  [40 bytes, mostly zero — one float32 near offset+20, observed range 0.8–1.0, likely playback volume]
  [uint32 = 1]
  ['GSMP' 4-byte ASCII type discriminator — same embedded-tag-as-marker pattern as PROP 0x08001873's 'GMDL']
  [uint32 referenced_sample_id]   ← the GSMP/SMPB sample_id this event plays
```
This is the actual sound-trigger layer sitting between gameplay/AI logic and the raw audio resources: every `GSFX` block's `referenced_sample_id` was confirmed to resolve to either a regular `GSMP` sample or an `SMPB` sample (never both), never dangling except 3/287 stragglers in the one file checked. Use this to determine whether *any* given audio resource ID is actually triggered in-game, and (with more work — not yet done) to trace which gameplay object/quest fires it, by locating the `GSFX` block's containing `GMOA`/`GSQD`/`CHBR` context.

### GSMP+SMPC — cutscene dialogue with captions (FOUND 2026-10-03) — `scripts/rip_smpc.py`

**The in-engine cutscene voice acting is in `GSMP` blocks of a third variant, `SMPC` ("sample with caption")**, each carrying its own subtitle text. **49 lines in 12 GDWs** (Mayor Vaughn, Brody, Shaw, Cruz, Ruddock, Martin, Horace, reporter, fishermen, crew), extracted to `audio/<NAME>/<NAME>_smpc_*.wav` plus a transcript, `audio/<NAME>/<NAME>_captions.txt`. `rip_smpb.py` had silently skipped them (odd-sized `OBPR`, extra caption header). Cutscenes play sounds by `Group.Name` (e.g. `Movie2.Mayor3`), either through a sound-event action that a control starts (`ACTN` `0x0201C01B`, `PROP 0x08001936`) or through a sound object node that a control adds (class `0x0100E00D`, `PROP 0x0800192B`). A sound-bank node (`PROP 0x08001939` group, `0x0800193A` names, `0x0800193B/C` `GSFX` lists) maps names to `GSFX` triggers and then to samples. **One line is unused:** TOWN 388, an alternate take of the crew's "Something's happening out at the pond" by a different voice actor (user-identified). Full format, naming chain and the 49-line catalogue: **`docs/cutscene_dialogue.md`**. The older cat2 "long samples" lead (`docs/audio_leads.md`) is superseded.

### Unused-audio audit — `scripts/audit_audio.py` (2026-10-15)

Read-only. Sounds are only ever played by name: a request for `Group.Name` (hardcoded in `Jaws.exe`, ~200 names, or a level PROP string: `0x0800192B` sound object, `0x08001920`/`0x08001936` sound-event actions, or any other PROP holding a bank name) → sound bank (`0x08001939` group, `0x0800193A` names, repeated names = random variants, `0x0800193B`/`0x0800193C` = above/under-water `GSFX` lists) → `GSFX` → sample. The script walks that chain backwards for every file in `audio/<NAME>/` and writes `audio/audio_audit.csv` (status, bank names, who requests it: exe string VA or level node/action) and `audio/audio_audit.txt` (the non-used list). Statuses: `used`, `unrequested` (in a bank, nothing asks for the name: likely unused), `no_bank`, `no_gsfx`. First run: **3,677 used, 373 unrequested, 0 no_bank, 0 no_gsfx** (every sample has a trigger and a bank). **Recording check (2026-11-23):** columns `recording`/`copy_of` compare PCM exactly; 194 of the 373 are copies of recordings used elsewhere, **179 files = 48 distinct recordings are never heard** (list in `docs/audio_leads.md` "Recording check"). Correctly flags the known unused TOWN 388. **Corrected 2026-11-23:** the exe does build some names: three creature-AI init functions (`0x508380`, near `0x512F3D`, `0x514F46`) cut the creature's first clip name at `_` (`Mermaid_Swim` → `Mermaid`) and sprintf `%s.Idle`/`%s.Hurt`/`%s.Die`. Checked: no unrequested bank name matches a skeleton prefix in its level, so the results stand. Limits: a request only proves the sound *can* be asked for (the requesting object may never run), and "unrequested" is unconfirmed until heard or checked in Ghidra. Notable unrequested: shared `Camera.AboveWater/UnderWater`, `Jaws.ImpactWood/Metal/Glass/WindowUnbreak`, `Jaws.GrabBody`, `HumanFemale.Panic`, `HHShark.Attack` (12–18 levels each); DEEPSEA `Mine.EngineFutoszalag`/`Servo01–03` (conveyor belts are 42 static models with no actions, no servo object; PS2 same) and DEEPSEA2 `Generator.Slow` (destroy script goes straight to `Stop`), checked 2026-11-23; AQUARIUM `Orca.Threatening/Alarm` (565/566, unique; boss class `MSOrca` only requests Die/Hurt/Idle, PS2 same; user: not heard in the boss fight; OPEN_S's Orca Revenge orcas run `MSNarwhal` AI, which requests `Narwhal.*`, and no level has a `Narwhal` or OPEN_S an `Orca` bank, so they're voiceless; checked 2026-11-23); TOWN `Bell.Alarm` (TOWN-only bank, never requested PC/PS2, user: sounds like a boat/lifeguard warning bell); DEEPSEA2 `Squid.Hurt/Die/Attack` (boss is real, only `Squid.Idle` is requested, and only by the entrance cutscene's sound objects `szkvidordit`/`csapvegighuz`; checked 2026-11-23: `NASquidBoss` has no sound fields or sound strings, the reef squids build `LittleSquid.*` and the boss rig's clips are `BossSquidBody_*`, so nothing ever requests the `Squid` group's Attack/Hurt/Die: recorded, never wired up; user-confirmed not heard in-game); START `Movie.VoiceBrody3/4` (samples 470/471, uncaptioned plain `GSMP`, unique recordings, never played on PC or PS2; user-transcribed 2026-11-23: 470 "Gottem! Hold tight, he's gonna try and break free!", 471 "Oh my God it's a Great White! Make sure he's fully restrained and let's get him to the research center ASAP" = **the cut Aurora rope fight's dialogue** (hook, then capture); the bank's other 10 unrequested names are mostly copies of stock gameplay sounds (`HumanMaleFear` = `Human.Cry`, `SpearGun` = `SpearGun.Fire`, engines, splashes, growl; `SquidHurt` ≈ DEEPSEA2 `Squid.Attack`), only `FootstepsGuard` (footsteps on wood, user: never heard in-game, unused) and `EngineSeaSeeker` are unique; (`rip_smpb.py`/`rip_smpc.py` read PCM 2 samples late; fixed and re-extracted 2026-11-23, copies now hash-match); content needs listening; checked 2026-11-23, `docs/audio_leads.md` "START `Movie.VoiceBrody3/4` checked"). Details: `docs/audio_leads.md` "Unused-audio audit".

### WMV Cutscene Videos — `audio/wmv/`
Pre-rendered cutscenes in Windows Media Video format, stored in `movie/` in the game install directory. Audio extracted via ffmpeg to `audio/wmv/`. All files are WMA2 stereo 48000 Hz. Notable files:

| File | Duration | Content |
|---|---|---|
| `INTRO.WMV` | 43s | Game intro cinematic |
| `SHARK.WMV` | 79s | Shark story intro |
| `OUTSCENE.WMV` | 53s | Outro sequence |
| `PSYCHO.WMV` | 157s | Psycho mode cinematic |
| `JAWSC4/7/8/9/10/11.WMV` | 37–188s | Unlockable 1975 Jaws film clips |
| `FLUX.WMV` | 27s | Cross-promo trailer for *Æon Flux* (2005 Majesco-published PS2/Xbox game), viewable from the Jaws Unleashed main menu (user-confirmed 2026-08-02). Not Jaws content — publisher cross-promotion. Not referenced by name anywhere in `Jaws.exe` or any GDW — presumably hardcoded into a menu trailer-list, not data-driven. |
| `INF.WMV` | 63s | Cross-promo trailer for *Infected* (2005 Majesco-published PSP game), viewable from the Jaws Unleashed main menu (user-confirmed 2026-08-02). Not Jaws content — publisher cross-promotion. Same wiring caveats as `FLUX.WMV` above. |

**How movies are requested (2026-10-16):** the exe plays `movie\<name>.WMV` through DirectShow (`FUN_007221E0`) and holds none of the names. They come from `PROP 0x080005E6` on movie-play actions in the levels: TITLE `INTRO`/`SHARK` (`PC MPEG Demo 1 Loader`), `Movie Scene 1–6` = `JAWSC4/10/7/11/8/9`, `Trailers Page 0` `FLUX`/`PSYCHO`/`INF`, CHASE `OUTSCENE` (`MPGPlay 3_pc`). All 12 requests match the 12 shipped files, so nothing requested is missing. The `JAWSC` numbering gaps (1–3, 5, 6) aren't referenced anywhere; possibly the film's scene/chapter numbers, unverified, not evidence of cut content. Details: `docs/exe_analysis.md` "Movie playback".

**Source for the two previously-undocumented files above (2026-08-02):** `game_binary/unins000.exe` + `unins000.dat` (the original Inno Setup uninstaller pair, added to `game_binary/` by the user) contain a complete installer file manifest — confirmed our 20 extracted `.GDW` files exactly match the shipped set (nothing missing/extra), and surfaced `FLUX.WMV`/`INF.WMV` as shipped `movie\` files not previously in this table. Their audio (`audio/wmv/FLUX.wav`, `INF.wav`) was already extracted, just unlabeled/uncatalogued until now.

### ~~Missing: In-Game Cutscene Voice Acting~~ — found (2026-10-03)

Resolved: see "GSMP+SMPC" above and `docs/cutscene_dialogue.md`. The pre-rendered WMV cinematics have their own audio (`audio/wmv/`); the in-engine `NACutScene` sequences use the `SMPC` voice lines.

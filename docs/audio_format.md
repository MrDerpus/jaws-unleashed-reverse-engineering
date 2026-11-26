# Audio formats

**In short:** game sounds are `GSMP` blocks of raw 16-bit PCM. Two variants carry voice: `SMPB` (short barks) and `SMPC` (cutscene dialogue with captions). `GSFX` blocks link a trigger to a sample. Sounds are always requested by name (`Group.Name`) through sound-bank nodes. Level music is four layers mixed by volume. The pre-rendered movies are separate `.WMV` files.

Related docs: `docs/cutscene_dialogue.md` (the 49 dialogue lines), `docs/audio_leads.md` (unused-audio findings).

Rewritten for readability on 2026-11-27. Old version: `docs/archive/audio_format_old_2026-11-27.md`.

---

## Contents

1. [Plain samples (GSMP)](#1-plain-samples-gsmp)
2. [Level music](#2-level-music)
3. [Voice barks (SMPB)](#3-voice-barks-smpb)
4. [Triggers (GSFX)](#4-triggers-gsfx)
5. [Cutscene dialogue (SMPC)](#5-cutscene-dialogue-smpc)
6. [How a sound gets played](#6-how-a-sound-gets-played)
7. [Unused-audio audit](#7-unused-audio-audit)
8. [WMV movies](#8-wmv-movies)
9. [Old mistakes](#9-old-mistakes)

---

## 1. Plain samples (GSMP)

**Layout**, after the 8-byte chunk header:

```
[uint32 sample_id][uint32 flags][uint32 hash][uint32 category][uint32 sample_rate][uint32 byte_count]
[PCM: byte_count bytes, signed 16-bit]
[uint32 loop start frame][uint32 loop end frame]   (+2 zero bytes when byte_count % 4 == 2)
```

**Category:**

| Value | Kind | Typical |
|---|---|---|
| 2 | Sound effects | Under 5 s, 11,025 Hz |
| 3 | Music | 2–3.5 min loops, 22,050 Hz |
| 6 | Ambient | Under 5 s, 11,025 Hz |

**Flags:**
- `0x01` or `0x81`: a plain sample.
- The same with `| 0x20`: an `SMPB` sample (§3).

**Loop points:** music loops from 0 to frames − 1; sound effects have 0, 0.

**Extraction:**
- About 2,873 files across all 20 levels, in `audio/<NAME>/`.
- Names: `{STEM}_id{id:04d}_cat{cat}_{rate}hz_{dur:.2f}s.wav`.
- The extractor `scripts/rip_gsmp.py` is missing from the repo; only its output exists. The layout above is enough to rewrite it.

---

## 2. Level music

**In short:** each level has four music tracks that play together as layers. The game fades them in and out by volume.

| Track | When it's loud |
|---|---|
| `Calm_aw` | Calm, above water |
| `Calm_uw` | Calm, underwater |
| `Susp` | Suspense |
| `Act` | Action |

**In the level file:**
- A sound-bank node with group name `Music` (`PROP 0x08001939`; FISH's is `SndMusic`).
- Its track names: `PROP 0x0800193A`.
- A matching list of `['GSFX'][id]` (`PROP 0x0800193B`), each pointing to one sample.

**FISH's tracks:** 16-bit stereo, 22,050 Hz, all exactly 117.1 s, so they stay in sync.

**Replacing music works.**
- Tool: `scripts/gdw_music.py IN OUT none|DIR`.
- Rebuilding a stock music block from its PCM gives identical bytes.
- Tested with test tones in FISH and OPEN_NE (user-confirmed 2026-10-04): calm switches above and below water. Suspense and action were only audible once made loud and harsh, because they're mixed in as layers.

### In the game code

- The sound player `0x6FBC60` maps `Music.<track>` to slots 0–3. Strings at `0x8BB7C8`/`C0`/`B8`/`B4`.
- Per-slot handles and volumes: `+0xF814` / `+0xF824`.
- Set volumes: `0x6FBFB0` (float[4]), through the audio object's vtable `0x7FB138` slot `+0x100` (`0x715C50`).
- **The music director** is `0x4982E0` (vtable `0x7D8E24`, slot `+0x48`):
  - the calm layer follows the underwater flag `0x8B2E7C`;
  - suspense and action come from a 4×4 float table (`+0x44`), with the row picked by a state number at `+0x4C` (0–2);
  - volumes fade each tick.
- **Open:** what sets that state number. The class isn't named; candidates are `GDPlayMusic` and `GDPropMusic`.

---

## 3. Voice barks (SMPB)

**In short:** short NPC voice reactions, 0.3–7 s: panic, screams, cheers. They are all used.

**Layout:** like `GSMP`, but the hash and category are replaced by an `OBPR` sub-chunk.

```
GSMP [block_size]
  [uint32 sample_id]
  [uint32 flags]
  OBPR [size=20]
    PROP [size=12]  prop_id=0x04000030  value="SMPB"
  [16-byte header: magic, field, sample_rate, byte_count]
  [PCM: byte_count bytes, signed 16-bit mono]
  [uint32 loop start][uint32 loop end]   (+2 pad bytes when byte_count % 4 == 2)
```

- Recognise one by `data[pos+16:pos+20] == b'OBPR'`.
- The second header sits at `pos + 16 + 8 + obpr_size`.

**Extraction:**
- `scripts/rip_smpb.py`, 1,128 files.
- Names: `{STEM}_smpb_id{id:04d}_{rate}hz_{dur:.2f}s.wav`.
- SMPB copies match their plain-GSMP twins byte for byte.

---

## 4. Triggers (GSFX)

**In short:** a `GSFX` block links one sound event to one sample. It's the layer between game logic and the audio.

**Layout:** a top-level `RSRC` resource with a fixed 68-byte payload.

```
GSFX [uint32 size=68]
  [uint32 event id]
  [uint32 flags = 0x21]
  OBPR [uint32 size = 0]
  [40 bytes, mostly zero; one float near +20, 0.8–1.0, probably volume]
  [uint32 = 1]
  ['GSMP']
  [uint32 sample_id]      ← the sample this event plays
```

- The `'GSMP'` tag is a type marker, like `'GMDL'` in mesh references.
- **Checked on START:** every sample (all 214 plain, all 70 SMPB) has a `GSFX`. Only 3 of 287 `GSFX` references dangle.

---

## 5. Cutscene dialogue (SMPC)

**In short:** the in-engine cutscene voice acting is a third `GSMP` variant, `SMPC` ("sample with caption"). Each block carries its own subtitle.

- **49 lines in 12 levels.** Speakers: Mayor Vaughn, Brody, Shaw, Cruz, Ruddock, Martin, Horace, a reporter, fishermen and crew.
- Extracted by `scripts/rip_smpc.py` to `audio/<NAME>/<NAME>_smpc_*.wav`, with a transcript in `audio/<NAME>/<NAME>_captions.txt`.
- `rip_smpb.py` used to skip them: odd-sized `OBPR` and an extra caption header.
- **One line is unused:** TOWN 388, a different voice actor's take of the crew's "Something's happening out at the pond" (user-identified).

Full format, the naming chain and the 49-line list: `docs/cutscene_dialogue.md`.

---

## 6. How a sound gets played

Sounds are only ever played by name. The chain:

1. **A request for `Group.Name`.** It comes from either:
   - `Jaws.exe`, about 200 hardcoded names; or
   - a level property: `0x0800192B` (sound object), `0x08001920` or `0x08001936` (sound-event actions), or any other property holding a bank name.
2. **A sound bank** in the level:
   - `0x08001939` = group;
   - `0x0800193A` = names (a repeated name = random variants);
   - `0x0800193B` / `0x0800193C` = the above-water / underwater `GSFX` lists.
3. **The `GSFX`** (§4).
4. **The sample.**

**Cutscenes** use the same chain, e.g. `Movie2.Mayor3`. The name comes from:
- a sound-event action started by a control (`ACTN` `0x0201C01B`, `PROP 0x08001936`); or
- a sound-object node added by a control (class `0x0100E00D`, `PROP 0x0800192B`).

**Names the exe builds:** three creature-AI setup functions (`0x508380`, near `0x512F3D`, `0x514F46`) cut the creature's first clip name at `_` (`Mermaid_Swim` → `Mermaid`) and add `.Idle`, `.Hurt` or `.Die`.

---

## 7. Unused-audio audit

**In short:** `scripts/audit_audio.py` walks the chain in §6 backwards for every extracted file. Every sample has a trigger and a bank, but **373 files are never requested**. After removing copies, **48 distinct recordings are never heard**.

### The script

- Read-only.
- Writes:
  - `audio/audio_audit.csv`: status, bank names, and who requests it (exe address or level node/action);
  - `audio/audio_audit.txt`: the unused list.
- **Statuses:**

  | Status | Meaning | Count |
  |---|---|---|
  | `used` | Something requests it | 3,677 |
  | `unrequested` | In a bank, but nothing asks for the name | 373 |
  | `no_bank` | No bank | 0 |
  | `no_gsfx` | No trigger | 0 |

- **Recording check (2026-11-23):** the `recording` and `copy_of` columns compare PCM exactly.
  - 194 of the 373 are copies of recordings used elsewhere.
  - **179 files = 48 distinct recordings are never heard.** List: `docs/audio_leads.md` "Recording check".
- The built names from §6 were checked: no unrequested bank name matches a skeleton prefix in its level, so the results stand.

**Limits:**
- A request only proves the sound *can* be asked for. The object asking may never run.
- "Unrequested" is unconfirmed until heard, or checked in Ghidra.

### Notable unrequested sounds

| Sound | Level | What's known |
|---|---|---|
| `Camera.AboveWater` / `UnderWater`, `Jaws.ImpactWood` / `Metal` / `Glass` / `WindowUnbreak`, `Jaws.GrabBody`, `HumanFemale.Panic`, `HHShark.Attack` | 12–18 levels each | Shared pool |
| `Mine.EngineFutoszalag`, `Servo01–03` | DEEPSEA | The conveyor belts are 42 static models with no actions and no servo object. Same on PS2. |
| `Generator.Slow` | DEEPSEA2 | The destroy script goes straight to `Stop` |
| `Orca.Threatening` / `Alarm` (565/566) | AQUARIUM | The boss class `MSOrca` only requests Die/Hurt/Idle; same on PS2. User: not heard in the fight. |
| `Bell.Alarm` | TOWN | TOWN-only bank, never requested on PC or PS2. User: sounds like a warning bell. |
| `Squid.Hurt` / `Die` / `Attack` | DEEPSEA2 | Recorded, never wired up (below) |
| `Movie.VoiceBrody3` / `4` (470/471) | START | **The cut Aurora rope fight's dialogue** (below) |

**Orca Revenge's orcas are voiceless.** In OPEN_S they run `MSNarwhal` AI, which requests `Narwhal.*`. No level has a `Narwhal` bank, and OPEN_S has no `Orca` bank.

**The squid boss:**
- It's real, but only `Squid.Idle` is requested, and only by the entrance cutscene's sound objects (`szkvidordit`, `csapvegighuz`).
- `NASquidBoss` has no sound fields or strings.
- The reef squids build `LittleSquid.*`, and the boss's clips are `BossSquidBody_*`.
- So nothing requests the boss's Attack/Hurt/Die. User-confirmed not heard in-game.

**START's Brody lines:**
- Samples 470 and 471: plain `GSMP`, no caption, unique recordings, never played on PC or PS2.
- Transcribed by the user (2026-11-23):
  - 470: "Gottem! Hold tight, he's gonna try and break free!"
  - 471: "Oh my God it's a Great White! Make sure he's fully restrained and let's get him to the research center ASAP"
- That's the hook and the capture of the cut rope fight (`docs/cut_content.md` §3).
- The same bank has 10 more unrequested names. Most are copies of stock sounds:
  - `HumanMaleFear` = `Human.Cry`, `SpearGun` = `SpearGun.Fire`, engines, splashes, a growl;
  - `SquidHurt` ≈ DEEPSEA2 `Squid.Attack`.
- Only two are unique:
  - `FootstepsGuard` (footsteps on wood; user: never heard, unused);
  - `EngineSeaSeeker`.

Details: `docs/audio_leads.md` "Unused-audio audit" and "START `Movie.VoiceBrody3/4` checked".

---

## 8. WMV movies

**In short:** the pre-rendered cutscenes are `.WMV` files in the install's `movie/` folder. All 12 requested names match the 12 shipped files, so nothing is missing.

Their audio is extracted with ffmpeg to `audio/wmv/` (WMA2 stereo, 48,000 Hz).

| File | Length | Content |
|---|---|---|
| `INTRO.WMV` | 43 s | Game intro |
| `SHARK.WMV` | 79 s | Shark story intro |
| `OUTSCENE.WMV` | 53 s | Ending |
| `PSYCHO.WMV` | 157 s | Psycho mode |
| `JAWSC4/7/8/9/10/11.WMV` | 37–188 s | Unlockable clips from the 1975 film |
| `FLUX.WMV` | 27 s | Trailer for *Æon Flux* (Majesco, 2005), from the main menu |
| `INF.WMV` | 63 s | Trailer for *Infected* (Majesco, 2005, PSP), from the main menu |

### How movies are requested

- The exe plays `movie\<name>.WMV` through DirectShow (`0x7221E0`) and holds none of the names.
- The names come from `PROP 0x080005E6` on movie-play actions in the levels:

  | Level | Action | Movies |
  |---|---|---|
  | TITLE | `PC MPEG Demo 1 Loader` | `INTRO`, `SHARK` |
  | TITLE | `Movie Scene 1–6` | `JAWSC4/10/7/11/8/9` |
  | TITLE | `Trailers Page 0` | `FLUX`, `PSYCHO`, `INF` |
  | CHASE | `MPGPlay 3_pc` | `OUTSCENE` |

- The missing `JAWSC` numbers (1–3, 5, 6) aren't referenced anywhere. Maybe the film's chapter numbers; unverified, not evidence of cut content.
- Details: `docs/exe_analysis.md` "Movie playback".
- On Linux the movies need GE-Proton; Valve's Proton has no WMV2/WMA2 decoder for non-Steam games (`CLAUDE.md`).

### Evidence

- The installer manifest in `game_binary/unins000.exe` + `unins000.dat` (Inno Setup) lists every shipped file. It matches our 20 level files exactly and lists `FLUX.WMV` and `INF.WMV`.
- Both trailers user-confirmed on the main menu, 2026-08-02.

---

## 9. Old mistakes

| Old claim | Now |
|---|---|
| SMPB voice samples are "present but never triggered" | All are wired to `GSFX` triggers (checked on START, 2026-07-29). It was a guess from the unusual format. |
| `GSFX` is a flag variant of `GSMP` | A separate resource type; the old reading came from byte scans landing mid-block |
| The SMPB/SMPC second header is 20 bytes | 16 bytes. The extra "pad" word was the first 2 PCM samples, so files started 2 samples late. Fixed and re-extracted 2026-11-23. |
| The in-engine cutscene voice acting is missing | Found 2026-10-03: the `SMPC` blocks (§5). The long category-2 samples lead in `docs/audio_leads.md` is superseded. |

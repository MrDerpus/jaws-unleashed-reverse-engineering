# Cutscene dialogue: captioned voice lines (`SMPC`)

**In short:** the in-engine cutscene voice acting is stored in sound samples of a third kind, **`SMPC`** ("sample with caption"), which carry their subtitle text inside the block.
- **49 lines in 12 levels**, all extracted with their captions.
- 48 are played by the game.
- 1 is an unused alternate take (TOWN 388).
- Found 2026-10-03. The user listened to the TOWN lines and confirmed real voice acting; the rest weren't checked one by one.

Two more unused Brody lines (START 470/471) are plain samples without captions, so they're not among the 49 (§4).

Rewritten for readability on 2026-11-27. Old version: `docs/archive/cutscene_dialogue_old_2026-11-27.md`.

---

## Contents

1. [Extracting them](#1-extracting-them)
2. [Block layout](#2-block-layout)
3. [How cutscenes name and play sounds](#3-how-cutscenes-name-and-play-sounds)
4. [Unused lines](#4-unused-lines)
5. [Catalogue (all 49)](#5-catalogue-all-49)
6. [Related](#6-related)

---

## 1. Extracting them

```bash
python3 scripts/rip_smpc.py [NAME ...]
```

- Audio: `audio/<NAME>/<NAME>_smpc_id<id>_<rate>hz_<dur>s.wav`.
- Transcript per level: `audio/<NAME>/<NAME>_captions.txt`.

**Why they were missed for so long:** `rip_smpb.py` only handles the `SMPB` layout. `SMPC` blocks failed its checks silently, because:
- the caption makes the `OBPR` block an odd size (not 4-aligned);
- the sample header has an extra caption section.

---

## 2. Block layout

```
GSMP [size]
  [u32 sample_id][u32 flags = 0x21]
  OBPR [n]                          n not 4-aligned; the next field starts after padding to 4
    PROP [..] [u32 0x04000025] 'SMPC' [u32 len][caption, NUL-padded]
  [u32 0x013131B1][u32 0x22]        0x20 = has caption (plain samples have 0x02)
  [u32 len][caption, padded to 4]   the same text again
  [u32 duration_ms][u32 sample_rate][u32 byte_count]
  [byte_count bytes: signed 16-bit mono PCM]
  [8 bytes: loop start, loop end]
```

- The PCM starts right after `byte_count`; there's no pad word (corrected 2026-11-23).
- Every line seen is 11,025 Hz.
- Other sample kinds (`GSMP`, `SMPB`): `docs/audio_format.md`.

---

## 3. How cutscenes name and play sounds

**1. A cutscene asks for a sound by name, `Group.Name`** (e.g. `Movie2.Mayor3`), in one of two ways:
- a **sound-event action** (`ACTN` class `0x0201C01B`, name in `PROP 0x08001936`) that a `GDControl` **starts** (step `0x1`);
- a **sound object node** (class `0x0100E00D`, name in `PROP 0x0800192B`) that a `GDControl` **adds** (step `0x4`). Example: DEEPSEA2's `shawvo` plays `ShawMovie.VoiceShaw1` 120 ticks into Mr Shaw's entrance movie.

**2. A sound bank node** in `BRTR` resolves the name (e.g. `SndMovie2` under the cutscene's container):

| PROP | Holds |
|---|---|
| `0x08001939` | Group name |
| `0x0800193A` | List of sound names |
| `0x0800193B` / `0x0800193C` | Two parallel lists of `['GSFX'][id]`: probably above-water and underwater versions (cf. `GDSoundEventScope.m_AW_Resource`/`m_UW_Resource`). The second is often empty. |

**3. The `GSFX` trigger's** last field is the **sample ID**.

`rip_smpc.py` resolves every line's name this way (49 of 49).

**Note:** a name appearing nowhere else in the file means nothing by itself. Ordinary sounds such as `Music.Calm_aw` are only named in their bank and their event.

---

## 4. Unused lines

### TOWN 388, `MovieTown1.VoiceCrew2`

- The same line as 387 (*"Something's happening out at the pond. Mr. Mayor, we must leave!…"*), recorded by a **different voice actor in a calmer tone** (user-identified by listening).
- Its name appears only in the `MovieTown1/2/3` banks' name lists. No sound event or sound object uses it, so the game never plays it.
- The cutscene plays 387 at tick 10, then the mayor's *"OH MY GOD!"* (`VoiceMajor3`) at tick 250.
- All the other 48 lines are used.

### START 470 / 471, `Movie.VoiceBrody3` / `VoiceBrody4`

Found 2026-11-23. Plain `GSMP` samples with no caption, so never set up as subtitled dialogue. Same voice actor as the shipped Brody lines 1 and 2. User-transcribed:

| Sample | Length | Line |
|---|---|---|
| 470 | 2.43 s | *"Gottem! Hold tight, he's gonna try and break free!"* |
| 471 | 5.19 s | *"Oh my God it's a Great White! Make sure he's fully restrained and let's get him to the research center ASAP."* |

- They're the dialogue of the cut Aurora rope fight at the end of the tutorial:
  - 470 when the harpoon hooks the shark and the tug-of-war starts;
  - 471 for the capture once the shark is reeled in (`NAAuroraRope.m_finalmovie`).
- Never played on PC or PS2.
- Details: `docs/audio_leads.md` §3, `docs/cut_content.md` §3.

---

## 5. Catalogue (all 49)

Grouped by level, in story order. Captions are copied exactly, including the game's typos and capitals.

### START: 1 The Arrival (plus the side-challenge intro `MovieSM12`)

| Sample | Sound name | Seconds | Caption |
|---|---|---|---|
| 460 | `Movie.VoiceBrody1` | 4.92 | That distress call on the police band said the shark sightings were in this area.  Everyone keep an eye out. |
| 461 | `Movie.VoiceBrody2` | 0.72 | There it is! |
| 704 | `MovieSM12.VoiceMartin` | 12.82 | IN THE RECENT MONTHS, THE UNEXPECTED INCREASE IN AMITY'S SHARK POPULATION HAS HAD A DRASTIC EFFECT ON THE LOCAL SEAL POPULATION. NORMALLY AT THIS TIME OF YEAR, SEALS CAN BE VIEWED IN LARGE NUMBERS BY THE PUBLIC HERE, BUT THIS YEAR IS DIFFERENT. |

### AQUARIUM: 2 The Break Out

| Sample | Sound name | Seconds | Caption |
|---|---|---|---|
| 790 | `Movie.VoiceMajor1` | 7.32 | For the first time ever, Amity has its own Great White shark on display for the tourists. This is going to draw crowds in record numbers! |
| 791 | `Movie.VoiceBrody2` | 4.81 | Mayor, Our research tank can hold the shark but we are NOT prepared to display him in the show room tank. |
| 792 | `Movie.VoiceMajor3` | 3.73 | Nonsense!  The word has already spread.  Give the people what they want, Brody. |
| 793 | `Movie.VoiceShaw4` | 6.59 | Mr. Mayor, I understand you captured a shark by the Cove.  Is that him?   My son was killed by a shark there. |
| 794 | `Movie.VoiceShaw5` | 4.24 | Damn thing ripped right through the cage.  I demand you kill that creature immediately! |
| 795 | `MovieEnd.VoiceMajor1b` | 9.56 | There is no real threat to the safety of vacationers or the citizens of Amity. I assure you that we are doing everything within our power to deal with this issue. |
| 796 | `MovieEnd.VoiceBrody2b` | 6.92 | THE MAYOR IS ABSOLUTELY CORRECT. THE THREAT IS MINIMAL AND WE'LL SOON HAVE THE SHARK TRACKED AND CAPTURED WITH THE USE OF OUR AURORA II RESEARCH VESSEL. |
| 797 | `MovieEnd.VoiceShaw3b` | 12.28 | Say what you want, but Mr. Mayor, we have too much invested to be careless.  Until the beast is captured or better yet, killed.  My employees will be on alert.  And Brody, you better get to him before I do, if you want him alive. |

### BEACH: 3 The Dead of Night

| Sample | Sound name | Seconds | Caption |
|---|---|---|---|
| 479 | `Movie.VoiceMajor1` | 15.51 | LISTEN BRODY, I DON'T KNOW WHAT THEY TAUGHT YOU IN THOSE INSTITUTIONS WHERE YOU STUDIED, BUT YOU'RE BEGINNING TO SOUND LIKE YOUR DAD, CRYING WOLF.  ENVIRONPLUS IS BRINGING IN MILLIONS TO OUR COMMUNITY.  THE MACHINES STAY!  THE AMITY SHARK TOURNAMENT BEGINS TOMORROW AND ODDS ARE THEY WILL CATCH THE SHARK BEFORE ANYTHING ELSE HAPPENS. |
| 480 | `Movie.VoiceBrody2` | 12.70 | MAYOR, OUR RESEARCH CLEARLY INDICATES THAT THE SUBSONIC FREQUENCIES USED BY SHAW'S UNDERWATER SEASEEKER MACHINES ARE HAVING A DRAMATIC EFFECT ON THE LOCAL SHARK POPULATION.  IT'S CAUSING THEM TO APPROACH HUMAN SETTLEMENTS AND TO BECOME INCREASINGLY MORE VIOLENT. |

### DOCKS: 4 Hunted

| Sample | Sound name | Seconds | Caption |
|---|---|---|---|
| 416 | `Movie.Fisherman1` | 1.53 | WHAT'S GOIN' ON WITH ALL THE SEARCH LIGHTS. |
| 417 | `Movie.Fisherman2` | 5.57 | DON'T KNOW, SOME CORPORATE GUY IS NERVOUS.  BUT THIS SHOULD BE AN EASY  COMPETITION.  SLUDGY WATER SHOULD SLOW 'EM ALL DOWN. |
| 418 | `Movie.Fisherman3` | 1.75 | THINK WE'LL CATCH THAT BIG ONE FROM THE AQUARIUM? |
| 419 | `Movie.Fisherman4` | 2.95 | DON'T SEE WHY NOT.  WE GOT THE RIGHT BAIT AND THE NET'S BIG ENOUGH! |

### KATATAMA: 5 Predator in the Bay

| Sample | Sound name | Seconds | Caption |
|---|---|---|---|
| 451 | `MovieBurningShip.Cruz1` | 6.37 | LISTEN, YER IN OVER YER HEAD!  IF WE HADN'T ARRIVED, YOU'D BE A BLEEDING STUMP OF SHARK BAIT RIGHT ABOUT NOW. |
| 452 | `MovieBurningShip.Brody2` | 1.14 | Who the hell are you!? |
| 453 | `MovieBurningShip.Cruz3` | 8.09 | The man dat saved yer life!  I was hired by the CEO of that disaster down there, to take out YOUR shark. |
| 454 | `MovieBurningShip.Brody4` | 6.94 | IT'S NOT MINE!  AND YOUR CEO IS RESPONSIBLE!  WE HAVE GOT TO SHUT DOWN THE SEASEEKERS OR THINGS ARE JUST GOING TO GET WORSE! |
| 455 | `MovieBurningShip.Cruz5` | 14.83 | I DON'T CARE WHO'S RESPONSIBLE.  MAYOR'S PUT OUT A NEW REWARD.  I'M GONNA CASH IN ON THAT, PLUS COLLECT A HEFTY LUMP OF CASH FROM ENVIRONPLUS.  AND WITHOUT YER BOAT, YOU WON'T BE IN MY WAY.  HA HAAA. |

### ARMADA: 6 The Angry Armada

| Sample | Sound name | Seconds | Caption |
|---|---|---|---|
| 127 | `Movie.VoiceFM1` | 2.01 | GOOD, WE'RE THE FIRST CREW OUT. |
| 135 | `Movie.VoiceFM2` | 1.82 | YEAH, THAT REWARD'S AS GOOD AS OURS. |
| 136 | `Movie.VoiceFM3` | 3.86 | YOU GOT THAT GEAR READY?  I DON'T WANNA END UP LIKE THAT SCIENCE GUY, BRODY. |
| 137 | `Movie.VoiceFM4` | 2.80 | Yeah... Oh shit, there it is! |

### WRACK: 7 A Taste for Blood

| Sample | Sound name | Seconds | Caption |
|---|---|---|---|
| 307 | `Movie.Horace1` | 20.96 | I'M GOING TO GET ME SOME FISH... SMOKIN' DEAD SHARK FISH. BUY MESELF A NEW SHRIMPIN' BOAT OR SOMETHIN' WHEN I GET THAT REWARD! |
| 308 | `Movie.Horace2` | 2.07 | Ahh shit! |
| 423 | `Movie2.Horace2` | 14.81 | PEOPLE DYING... SHOWING UP WITH THEIR BODILY ORGANS RIPPED OUT. YOU SEE IT ALL DAY LONG ON TV. WHY I WOULDN'T FRET ABOUT IT. IT'S NATURAL, JUST LIKE GAS. |
| 424 | `Movie2.Reporter1` | 5.07 | Mayor Vaughn, will the recent shark attacks cause you to consider canceling the Amity 4th of July festivities? |
| 425 | `Movie2.Mayor3` | 24.52 | AS I HAVE STATED TO YOU EARLIER, THE SHARK THREAT TO AMITY IS IN FACT, HIGHLY OVER RATED. THE BEACHES ARE COMPLETELY SAFE FOR YOU TO ENJOY AND THIS YEAR'S INDEPENDENCE DAY CELEBRATION IS GOING TO BE ONE TO REMEMBER FOR GENERATIONS TO COME. WHY, I PLAN TO KICK OFF THE FIRE WORKS MYSELF. I LOOK FORWARD TO SEEING ALL OF YOU DOWN AT THE BEACH FOR SOME NICE BAR-B-Q COOKING AND FRIENDLY PATRIOTIC SMILES! |
| 426 | `Movie2.Reporter4` | 3.16 | Thank you Mr. Mayor. We are all looking forward to seeing you on the 4th, too! |

### DEEPSEA2: 9 The Facility

| Sample | Sound name | Seconds | Caption |
|---|---|---|---|
| 460 | `Movie.VoiceSurvivor` | 8.97 | MR. MAYOR, I SAW THE WHOLE COMPLEX EXPLODE WITH THE SHARK INSIDE! MR. SHAW SACRIFICED HIMSELF TO KILL THE BEAST AND I'M LUCKY I MADE IT OUT IN ONE PIECE! |
| 461 | `Movie.VoiceMajor2` | 8.46 | I truly appreciate your bravery in the light of such overwhelming danger.   The good news now is that the shark is finally dead. |
| 462 | `Movie.VoiceBrody3` | 9.45 | I WOULD NOT BE SO SURE OF THAT! WE CAN'T BE CERTAIN THAT THERE IS NO REMAINING THREAT TO THE PUBLIC. MAYOR, I'M TELLING YOU, YOU BETTER PUT THE 4TH OF JULY CELEBRATION ON HOLD. IT'S JUST TOO DANGEROUS. |
| 463 | `Movie.VoiceRuddock5` | 8.97 | HATE TO SAY IT, BUT HE MAY BE RIGHT.  I'VE SEEN FIRST-HAND WHAT THIS SHARK'S CAPABLE OF, AND I'M GONNA CONTINUE TO HUNT HIM DOWN UNTIL I'M CERTAIN HE'S DEAD. |
| 464 | `Movie.VoiceMajor6` | 5.91 | UHH HUH, YEAH!   WELL I'M NOT GOING TO SHUT DOWN THE FESTIVITIES BECAUSE YOU BOYS THINK A SHARK CAN SURVIVE AN EXPLOSION LIKE THAT. |
| 465 | `ShawMovie.VoiceShaw1` | 2.98 | MY SON!  NOW MY WORK!   I'LL KILL YOU MYSELF! |

### TOWN: 10 Blood on the Beach

| Sample | Sound name | Seconds | Caption |
|---|---|---|---|
| 387 | `MovieTown1.VoiceCrew1` | 5.40 | Something's happening out at the pond. Mr. Mayor, we must leave! Things are getting... Oh shit, look at the size of that thing! |
| 388 | `MovieTown1.VoiceCrew2` | 6.18 | Something's happening out at the pond. Mr. Mayor, we must leave! Things are getting... Oh shit, look at the size of that thing! **(unused alternate take)** |
| 389 | `MovieTown1.VoiceMajor3` | 1.80 | OH MY GOD!  THIS CAN'T BE HAPPENING! |
| 390 | `MovieTown3.Cruz` | 5.40 | YEP, IT LIVED AWRIGHT.  WELL, I GOT SOMETHIN' FOR 'EM.  YOU COMIN' BRODY? |
| 391 | `MovieTown3.Brody` | 3.65 | I HAVE ELECTRONIC TRACKING EQUIPMENT WE CAN USE.  I'LL GET MY SUPPLIES AND CATCH UP WITH YOU. |

### CHASE: 11 The Final Chase

| Sample | Sound name | Seconds | Caption |
|---|---|---|---|
| 191 | `Movie1.Voice_Cruz` | 2.76 | BRODY, SEEMS LIKE YER TRACER WORKED. |
| 193 | `Movie2.Voice_Cruz` | 4.96 | HOW YER LIKE MY NEW BOAT, YER BASTARD!  OPEN UP THE THROTTLE.  CLOSE IN ON 'EM! |
| 227 | `Movie1.Voice_Brody` | 3.97 | WE'RE ON OUR WAY. TRY AND CORNER HIM AND WE'LL FIRE DOWN ON HIM FROM THE HELICOPTER. |

### OPEN_S: Open Ocean South, side-challenge movie `MovieSM2`

| Sample | Sound name | Seconds | Caption |
|---|---|---|---|
| 463 | `MovieSM2.VoiceMartin1` | 6.33 | MY GOD. IT'S A GREAT WHITE! HE'S TRYING TO CATCH THOSE SEALS! POOR LITTLE GUYS. LET'S TRY TO HELP THEM OUT. |

### OPEN_NE: Open Ocean East, side-challenge movies `MovieSM6`/`MovieSM7`

| Sample | Sound name | Seconds | Caption |
|---|---|---|---|
| 600 | `MovieSM7.VocieReporter` | 10.88 | LADIES AND GENTLEMEN, TODAY'S TERROR CHALLENGE IS FOR EACH ONE OF YOU  LOVELY CONTESTANTS TO JUMP OFF THE CLIFF AND INTO THE SHARK-INFESTED WATERS BELOW. DON'T WORRY THOUGH, WE WILL ATTACH A STRONG ROPE TO YOU! |
| 607 | `MovieSM6.Help` | 2.79 | Help me!   God help me! |

---

## 6. Related

- **WRACK's mayor interview** (`MAyorSpeakContainer`, camera `cin7_cam`, built just outside the playable area) has a caption switch, `MayorFeliratKiBeKapcsolgato`. Its two targets (IDs 422, 423) were deleted. Probably separate caption overlays, made redundant once captions came from the samples. Found by the dangling-reference survey (`docs/cut_content.md`).
- **The earlier "long category-2 samples" lead** (`docs/audio_leads.md` §10) was the wrong place to look; this is where the dialogue was.
- **Level ↔ stage mapping** used here follows the corrected table in `CLAUDE.md` (BEACH = 3, DOCKS = 4, TOWN = 10).

# Cutscene Dialogue — Captioned Voice Lines (`SMPC`)

**Found 2026-10-03.** The in-engine cutscene voice acting, long listed as "not found", is stored in `GSMP` sample blocks of a third variant, **`SMPC`** ("sample with caption"), which carries its subtitle text inside the block. **49 lines in 12 GDWs**, extracted with **`python3 scripts/rip_smpc.py [NAME ...]`** to `audio/<NAME>/<NAME>_smpc_id<id>_<rate>hz_<dur>s.wav`, plus a transcript per level, `audio/<NAME>/<NAME>_captions.txt`. The user listened to the TOWN takes and confirmed real voice acting (2026-10-03); the rest weren't individually checked yet.

Why it was missed: `rip_smpb.py` only handles the `SMPB` layout. `SMPC` blocks have a non-4-aligned `OBPR` (the caption makes it odd-sized) and an extra caption section in the sample header, so they failed its checks silently.

## Block layout

```
GSMP [size]
  [u32 sample_id][u32 flags = 0x21]
  OBPR [n]                         n not 4-aligned; the next field starts after padding to 4
    PROP [..] [u32 0x04000025] 'SMPC' [u32 len][caption, NUL-padded]
  [u32 0x013131B1][u32 0x22]       0x20 = has caption (plain samples have 0x02)
  [u32 len][caption, padded to 4]  same text again
  [u32 duration_ms][u32 sample_rate][u32 byte_count][u32 pad]
  [byte_count bytes: signed 16-bit mono PCM, 11025 Hz in every case seen]
```

## How cutscenes name and play sounds

1. **By name, `Group.Name`** (e.g. `Movie2.Mayor3`), in one of two ways:
   - a **sound-event action** (`ACTN` class `0x0201C01B`, name in `PROP 0x08001936`) that a `GDControl` **starts** (`0x1` step), or
   - a **sound object node** (class `0x0100E00D`, name in `PROP 0x0800192B`) that a `GDControl` **adds** (`0x4` step). Example: DEEPSEA2's `shawvo` plays `ShawMovie.VoiceShaw1` 120 ticks into Mr Shaw's entrance movie.
2. **Sound bank** node in `BRTR` (e.g. `SndMovie2` under the cutscene's container): `PROP 0x08001939` = group name, `0x0800193A` = list of sound names, `0x0800193B` / `0x0800193C` = two parallel lists of `['GSFX'][id]` (probably above-water / below-water variants, cf. `GDSoundEventScope.m_AW_Resource/m_UW_Resource`; the second is often empty).
3. **`GSFX`** trigger → its last field is the **sample ID** (see `CLAUDE.md` Audio System, `GSFX`).

`rip_smpc.py` resolves every line's name this way (49/49). A name being absent from the rest of the file means nothing by itself: ordinary sounds such as `Music.Calm_aw` are only named in their bank and their event.

## Unused line

**TOWN 388, `MovieTown1.VoiceCrew2`:** the same line as 387 ("Something's happening out at the pond. Mr. Mayor, we must leave!…"), recorded by a **different voice actor in a calmer tone** (user-identified by listening). Its name appears only in the `MovieTown1/2/3` bank name lists; no sound event or sound object references it, so the game never plays it. The cutscene plays 387 at tick 10, then the mayor's "OH MY GOD!" (`VoiceMajor3`) at 250. All other 48 lines are referenced. See also `docs/cut_content.md`.

## Catalogue (all 49)

Levels: AQUARIUM = M02 The Break Out, ARMADA = M06 The Angry Armada, BEACH = M10 Blood on the Beach, CHASE = M11 The Final Chase, DEEPSEA2 = M08 The Deep / M09 The Facility, DOCKS = M10 (Docks), KATATAMA = M05 Predator in the Bay, OPEN_NE = Open Ocean East (`MovieSM6`/`MovieSM7` side-mission movies), OPEN_S = Open Ocean South (`MovieSM2` side-mission movie), START = M01 Tutorial (+ a `MovieSM12` side-mission intro), TOWN = M10 (Town), WRACK = M07 A Taste for Blood.

| GDW | Sample | Sound name | Seconds | Caption |
|---|---|---|---|---|
| AQUARIUM | 790 | `Movie.VoiceMajor1` | 7.32 | For the first time ever, Amity has its own Great White shark on display for the tourists. This is going to draw crowds in record numbers! |
| AQUARIUM | 791 | `Movie.VoiceBrody2` | 4.81 | Mayor, Our research tank can hold the shark but we are NOT prepared to display him in the show room tank. |
| AQUARIUM | 792 | `Movie.VoiceMajor3` | 3.73 | Nonsense!  The word has already spread.  Give the people what they want, Brody. |
| AQUARIUM | 793 | `Movie.VoiceShaw4` | 6.59 | Mr. Mayor, I understand you captured a shark by the Cove.  Is that him?   My son was killed by a shark there. |
| AQUARIUM | 794 | `Movie.VoiceShaw5` | 4.24 | Damn thing ripped right through the cage.  I demand you kill that creature immediately! |
| AQUARIUM | 795 | `MovieEnd.VoiceMajor1b` | 9.56 | There is no real threat to the safety of vacationers or the citizens of Amity. I assure you that we are doing everything within our power to deal with this issue. |
| AQUARIUM | 796 | `MovieEnd.VoiceBrody2b` | 6.92 | THE MAYOR IS ABSOLUTELY CORRECT. THE THREAT IS MINIMAL AND WE'LL SOON HAVE THE SHARK TRACKED AND CAPTURED WITH THE USE OF OUR AURORA II RESEARCH VESSEL. |
| AQUARIUM | 797 | `MovieEnd.VoiceShaw3b` | 12.28 | Say what you want, but Mr. Mayor, we have too much invested to be careless.  Until the beast is captured or better yet, killed.  My employees will be on alert.  And Brody, you better get to him before I do, if you want him alive. |
| ARMADA | 127 | `Movie.VoiceFM1` | 2.01 | GOOD, WE'RE THE FIRST CREW OUT. |
| ARMADA | 135 | `Movie.VoiceFM2` | 1.82 | YEAH, THAT REWARD'S AS GOOD AS OURS. |
| ARMADA | 136 | `Movie.VoiceFM3` | 3.86 | YOU GOT THAT GEAR READY?  I DON'T WANNA END UP LIKE THAT SCIENCE GUY, BRODY. |
| ARMADA | 137 | `Movie.VoiceFM4` | 2.80 | Yeah... Oh shit, there it is! |
| BEACH | 479 | `Movie.VoiceMajor1` | 15.51 | LISTEN BRODY, I DON'T KNOW WHAT THEY TAUGHT YOU IN THOSE INSTITUTIONS WHERE YOU STUDIED, BUT YOU'RE BEGINNING TO SOUND LIKE YOUR DAD, CRYING WOLF.  ENVIRONPLUS IS BRINGING IN MILLIONS TO OUR COMMUNITY.  THE MACHINES STAY!  THE AMITY SHARK TOURNAMENT BEGINS TOMORROW AND ODDS ARE THEY WILL CATCH THE SHARK BEFORE ANYTHING ELSE HAPPENS. |
| BEACH | 480 | `Movie.VoiceBrody2` | 12.70 | MAYOR, OUR RESEARCH CLEARLY INDICATES THAT THE SUBSONIC FREQUENCIES USED BY SHAW'S UNDERWATER SEASEEKER MACHINES ARE HAVING A DRAMATIC EFFECT ON THE LOCAL SHARK POPULATION.  IT'S CAUSING THEM TO APPROACH HUMAN SETTLEMENTS AND TO BECOME INCREASINGLY MORE VIOLENT. |
| CHASE | 191 | `Movie1.Voice_Cruz` | 2.76 | BRODY, SEEMS LIKE YER TRACER WORKED. |
| CHASE | 193 | `Movie2.Voice_Cruz` | 4.96 | HOW YER LIKE MY NEW BOAT, YER BASTARD!  OPEN UP THE THROTTLE.  CLOSE IN ON 'EM! |
| CHASE | 227 | `Movie1.Voice_Brody` | 3.97 | WE'RE ON OUR WAY. TRY AND CORNER HIM AND WE'LL FIRE DOWN ON HIM FROM THE HELICOPTER. |
| DEEPSEA2 | 460 | `Movie.VoiceSurvivor` | 8.97 | MR. MAYOR, I SAW THE WHOLE COMPLEX EXPLODE WITH THE SHARK INSIDE! MR. SHAW SACRIFICED HIMSELF TO KILL THE BEAST AND I'M LUCKY I MADE IT OUT IN ONE PIECE! |
| DEEPSEA2 | 461 | `Movie.VoiceMajor2` | 8.46 | I truly appreciate your bravery in the light of such overwhelming danger.   The good news now is that the shark is finally dead. |
| DEEPSEA2 | 462 | `Movie.VoiceBrody3` | 9.45 | I WOULD NOT BE SO SURE OF THAT! WE CAN'T BE CERTAIN THAT THERE IS NO REMAINING THREAT TO THE PUBLIC. MAYOR, I'M TELLING YOU, YOU BETTER PUT THE 4TH OF JULY CELEBRATION ON HOLD. IT'S JUST TOO DANGEROUS. |
| DEEPSEA2 | 463 | `Movie.VoiceRuddock5` | 8.97 | HATE TO SAY IT, BUT HE MAY BE RIGHT.  I'VE SEEN FIRST-HAND WHAT THIS SHARK'S CAPABLE OF, AND I'M GONNA CONTINUE TO HUNT HIM DOWN UNTIL I'M CERTAIN HE'S DEAD. |
| DEEPSEA2 | 464 | `Movie.VoiceMajor6` | 5.91 | UHH HUH, YEAH!   WELL I'M NOT GOING TO SHUT DOWN THE FESTIVITIES BECAUSE YOU BOYS THINK A SHARK CAN SURVIVE AN EXPLOSION LIKE THAT. |
| DEEPSEA2 | 465 | `ShawMovie.VoiceShaw1` | 2.98 | MY SON!  NOW MY WORK!   I'LL KILL YOU MYSELF! |
| DOCKS | 416 | `Movie.Fisherman1` | 1.53 | WHAT'S GOIN' ON WITH ALL THE SEARCH LIGHTS. |
| DOCKS | 417 | `Movie.Fisherman2` | 5.57 | DON'T KNOW, SOME CORPORATE GUY IS NERVOUS.  BUT THIS SHOULD BE AN EASY  COMPETITION.  SLUDGY WATER SHOULD SLOW 'EM ALL DOWN. |
| DOCKS | 418 | `Movie.Fisherman3` | 1.75 | THINK WE'LL CATCH THAT BIG ONE FROM THE AQUARIUM? |
| DOCKS | 419 | `Movie.Fisherman4` | 2.95 | DON'T SEE WHY NOT.  WE GOT THE RIGHT BAIT AND THE NET'S BIG ENOUGH! |
| KATATAMA | 451 | `MovieBurningShip.Cruz1` | 6.37 | LISTEN, YER IN OVER YER HEAD!  IF WE HADN'T ARRIVED, YOU'D BE A BLEEDING STUMP OF SHARK BAIT RIGHT ABOUT NOW. |
| KATATAMA | 452 | `MovieBurningShip.Brody2` | 1.14 | Who the hell are you!? |
| KATATAMA | 453 | `MovieBurningShip.Cruz3` | 8.09 | The man dat saved yer life!  I was hired by the CEO of that disaster down there, to take out YOUR shark. |
| KATATAMA | 454 | `MovieBurningShip.Brody4` | 6.94 | IT'S NOT MINE!  AND YOUR CEO IS RESPONSIBLE!  WE HAVE GOT TO SHUT DOWN THE SEASEEKERS OR THINGS ARE JUST GOING TO GET WORSE! |
| KATATAMA | 455 | `MovieBurningShip.Cruz5` | 14.83 | I DON'T CARE WHO'S RESPONSIBLE.  MAYOR'S PUT OUT A NEW REWARD.  I'M GONNA CASH IN ON THAT, PLUS COLLECT A HEFTY LUMP OF CASH FROM ENVIRONPLUS.  AND WITHOUT YER BOAT, YOU WON'T BE IN MY WAY.  HA HAAA. |
| OPEN_NE | 600 | `MovieSM7.VocieReporter` | 10.88 | LADIES AND GENTLEMEN, TODAY'S TERROR CHALLENGE IS FOR EACH ONE OF YOU  LOVELY CONTESTANTS TO JUMP OFF THE CLIFF AND INTO THE SHARK-INFESTED WATERS BELOW. DON'T WORRY THOUGH, WE WILL ATTACH A STRONG ROPE TO YOU! |
| OPEN_NE | 607 | `MovieSM6.Help` | 2.79 | Help me!   God help me! |
| OPEN_S | 463 | `MovieSM2.VoiceMartin1` | 6.33 | MY GOD. IT'S A GREAT WHITE! HE'S TRYING TO CATCH THOSE SEALS! POOR LITTLE GUYS. LET'S TRY TO HELP THEM OUT. |
| START | 460 | `Movie.VoiceBrody1` | 4.92 | That distress call on the police band said the shark sightings were in this area.  Everyone keep an eye out. |
| START | 461 | `Movie.VoiceBrody2` | 0.72 | There it is! |
| START | 704 | `MovieSM12.VoiceMartin` | 12.82 | IN THE RECENT MONTHS, THE UNEXPECTED INCREASE IN AMITY'S SHARK POPULATION HAS HAD A DRASTIC EFFECT ON THE LOCAL SEAL POPULATION. NORMALLY AT THIS TIME OF YEAR, SEALS CAN BE VIEWED IN LARGE NUMBERS BY THE PUBLIC HERE, BUT THIS YEAR IS DIFFERENT. |
| TOWN | 387 | `MovieTown1.VoiceCrew1` | 5.40 | Something's happening out at the pond. Mr. Mayor, we must leave! Things are getting... Oh shit, look at the size of that thing! |
| TOWN | 388 | `MovieTown1.VoiceCrew2` | 6.18 | Something's happening out at the pond. Mr. Mayor, we must leave! Things are getting... Oh shit, look at the size of that thing! **(unused alternate take)** |
| TOWN | 389 | `MovieTown1.VoiceMajor3` | 1.80 | OH MY GOD!  THIS CAN'T BE HAPPENING! |
| TOWN | 390 | `MovieTown3.Cruz` | 5.40 | YEP, IT LIVED AWRIGHT.  WELL, I GOT SOMETHIN' FOR 'EM.  YOU COMIN' BRODY? |
| TOWN | 391 | `MovieTown3.Brody` | 3.65 | I HAVE ELECTRONIC TRACKING EQUIPMENT WE CAN USE.  I'LL GET MY SUPPLIES AND CATCH UP WITH YOU. |
| WRACK | 307 | `Movie.Horace1` | 20.96 | I'M GOING TO GET ME SOME FISH... SMOKIN' DEAD SHARK FISH. BUY MESELF A NEW SHRIMPIN' BOAT OR SOMETHIN' WHEN I GET THAT REWARD! |
| WRACK | 308 | `Movie.Horace2` | 2.07 | Ahh shit! |
| WRACK | 423 | `Movie2.Horace2` | 14.81 | PEOPLE DYING... SHOWING UP WITH THEIR BODILY ORGANS RIPPED OUT. YOU SEE IT ALL DAY LONG ON TV. WHY I WOULDN'T FRET ABOUT IT. IT'S NATURAL, JUST LIKE GAS. |
| WRACK | 424 | `Movie2.Reporter1` | 5.07 | Mayor Vaughn, will the recent shark attacks cause you to consider canceling the Amity 4th of July festivities? |
| WRACK | 425 | `Movie2.Mayor3` | 24.52 | AS I HAVE STATED TO YOU EARLIER, THE SHARK THREAT TO AMITY IS IN FACT, HIGHLY OVER RATED. THE BEACHES ARE COMPLETELY SAFE FOR YOU TO ENJOY AND THIS YEAR'S INDEPENDENCE DAY CELEBRATION IS GOING TO BE ONE TO REMEMBER FOR GENERATIONS TO COME. WHY, I PLAN TO KICK OFF THE FIRE WORKS MYSELF. I LOOK FORWARD TO SEEING ALL OF YOU DOWN AT THE BEACH FOR SOME NICE BAR-B-Q COOKING AND FRIENDLY PATRIOTIC SMILES! |
| WRACK | 426 | `Movie2.Reporter4` | 3.16 | Thank you Mr. Mayor. We are all looking forward to seeing you on the 4th, too! |

## Related

- WRACK's mayor-interview cutscene (`MAyorSpeakContainer`, camera `cin7_cam`, built just outside the playable area) also has a caption switch, `MayorFeliratKiBeKapcsolgato`, whose two target objects (IDs 422, 423) were deleted. Presumably separate caption overlays, made redundant once captions came from the samples. Found through the dangling-reference survey (`docs/cut_content.md`).
- The earlier "long `GSMP` cat2 samples" lead (`docs/audio_leads.md`) is superseded by this.

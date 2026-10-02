# Audio Leads — Possible Story Dialogue

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

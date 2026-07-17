# PS2 Dataset Inventory

Documents the full PS2 release data provided at `GAME_GDWs/ps2/`, which supersedes the earlier single-file `_FISH.GDE`-only state (see `class_registry.md` / `CLAUDE.md`'s "PS2 Version Data" section for the original single-file findings, which still stand).

---

## Directory Layout

```
GAME_GDWs/ps2/DATA/*.GDE      -- all 20 level archives (PC-equivalent names, .GDE extension)
                                  plus two with NO PC equivalent: AQUA2.GDE, START2.GDE
GAME_GDWs/ps2/SLUS_210.62      -- PS2 main executable (ELF32, MIPS, stripped, 5,969,728 bytes)
GAME_GDWs/ps2/SYSTEM.CNF       -- boot config
GAME_GDWs/ps2/IOP/*.IRX,.IMG   -- PS2 IOP driver modules (audio/pad/memcard) -- not game content
GAME_GDWs/ps2/STRDATA/*.MIC    -- streaming audio/video containers, one per level -- not decoded
GAME_GDWs/ps2/FILES.LST        -- plain file manifest
```

`SYSTEM.CNF` contents:
```
BOOT2 = cdrom0:\SLUS_210.62;1
VER = 1.02
VMODE = NTSC
```

## SLUS_210.62 — Executable Details

```
ELF32, MIPS, 2's complement little-endian, statically linked, stripped
Entry point: 0x100008
Flags: 0x20924001 -- noreorder, 5900, eabi64, mips3
Built: April 2006 (file timestamp)
```

The `5900`/`eabi64`/`mips3` flags confirm this targets the PS2 Emotion Engine (R5900), not a generic MIPS R3000 despite `readelf`'s generic machine-type label. "Stripped" means no function/variable symbol table survives — only embedded string literals and the engine's own runtime class/field reflection strings (used for save/serialization, not debug info) are readable. See `ps2_disassembly_notes.md`.

Built roughly six months before PC's `Jaws.exe` (October 2006) — this age gap explains several content differences documented in `ps2_cut_content_findings.md`.

## Per-File Sizes (`DATA/*.GDE`)

| File | Size | | File | Size |
|---|---|---|---|---|
| AQUA2.GDE | 23.2 MB | | KATATAMA.GDE | 26.3 MB |
| AQUARIUM.GDE | 24.3 MB | | MINEMSHA.GDE | 17.7 MB |
| ARMADA.GDE | 24.4 MB | | OPEN_NE.GDE | 45.7 MB |
| BEACH.GDE | 24.6 MB | | OPEN_NW.GDE | 45.2 MB |
| BEACHPST.GDE | 20.0 MB | | OPEN_S.GDE | 51.8 MB |
| CHASE.GDE | 17.4 MB | | START.GDE | 26.6 MB |
| DEEPSEA.GDE | 23.4 MB | | START2.GDE | 27.0 MB |
| DEEPSEA2.GDE | 25.6 MB | | TITLE.GDE | 52.8 MB |
| DOCKS.GDE | 19.8 MB | | TITLE0.GDE | 1.8 MB |
| FISH.GDE | 16.7 MB | | TOWN.GDE | 24.4 MB |
| GAUNTLET.GDE | 13.4 MB | | WRACK.GDE | 24.4 MB |

All are much smaller than their PC counterparts (e.g. `FISH.GDE` 16.7 MB vs `FISH.GDW` 131 MB), consistent with PS2-resolution/PS2-budget assets rather than missing content — same conclusion already reached for the single-file `_FISH.GDE` case.

## Open Question: `AQUA2.GDE` and `START2.GDE`

Both are structurally complete, valid GDED archives — same chunk layout as `AQUARIUM.GDE`/`START.GDE` (`FSIZ`/`VERS`/`EXBY`/`GNRL`/`WDIM`/`RSPR`/`CLAS`/`RSRC`/`BNCH`/`BRTR`/`SCRT`/`SKIP`/`FDIR`/`ENDF`), not truncated or corrupt fragments. Their `CLAS` chunk size (248,939 bytes) matches every other PS2 GDE exactly, and their `WDIM` world-bounds floats are the same shared constant seen across the whole PS2 build.

No PC GDW has an equivalent second file for Aquarium or Start/Tutorial. The closest PC analogue is the `BEACH.GDW` / `BEACHPST.GDW` pairing (pre/post-mission-state variants of one level) — `AQUA2`/`START2` may be the same kind of "alternate state" pairing for two more levels that got collapsed back into a single file by the time of the PC build. **Not yet confirmed** — would need a name/BRTR diff against `AQUARIUM.GDE`/`START.GDE` to verify.

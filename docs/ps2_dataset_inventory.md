# PS2 files: what we have

**In short:** the full PS2 release is in `GAME_GDWs/ps2/`: 22 level files (`.GDE`) and the game program `SLUS_210.62`. The levels match the PC's, plus two extra files, `AQUA2` and `START2`, which hold parts of the aquarium and tutorial levels. Everything is much smaller than on PC (lower-resolution assets, not missing content).

Formats: `docs/ps2_asset_extraction.md`. What the exe tells us: `docs/ps2_cut_content_findings.md`.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/ps2_dataset_inventory_old_2026-11-27.md`.

---

## Folder layout

| Path | What |
|---|---|
| `GAME_GDWs/ps2/DATA/*.GDE` | 22 level files: the PC's 20 names plus `AQUA2` and `START2` |
| `GAME_GDWs/ps2/SLUS_210.62` | The game program |
| `GAME_GDWs/ps2/SYSTEM.CNF` | Boot settings |
| `GAME_GDWs/ps2/IOP/*.IRX`, `*.IMG` | PS2 driver modules (audio, pad, memory card). Not game content. |
| `GAME_GDWs/ps2/STRDATA/*.MIC` | Streamed audio/video, one per level. Not decoded; searched for text (`docs/ps2_cut_content_findings.md`). |
| `GAME_GDWs/ps2/FILES.LST` | Plain file list |

`SYSTEM.CNF`:

```
BOOT2 = cdrom0:\SLUS_210.62;1
VER = 1.02
VMODE = NTSC
```

---

## The program: `SLUS_210.62`

```
ELF32, MIPS, little-endian, statically linked, stripped
Size: 5,969,728 bytes
Entry point: 0x100008
Flags: 0x20924001 (noreorder, 5900, eabi64, mips3)
File date: April 2006
```

- The `5900`/`eabi64` flags mean the PS2's main processor (Emotion Engine, R5900).
- **Stripped:** no symbol table. Only string literals and the engine's own reflection strings (class and field names) are readable.
- File-dated about six months before the PC's `Jaws.exe` (October 2006).
- Disassembly setup: `docs/ps2_disassembly_notes.md`.

---

## Level file sizes

| File | Size | File | Size |
|---|---|---|---|
| AQUA2 | 23.2 MB | KATATAMA | 26.3 MB |
| AQUARIUM | 24.3 MB | MINEMSHA | 17.7 MB |
| ARMADA | 24.4 MB | OPEN_NE | 45.7 MB |
| BEACH | 24.6 MB | OPEN_NW | 45.2 MB |
| BEACHPST | 20.0 MB | OPEN_S | 51.8 MB |
| CHASE | 17.4 MB | START | 26.6 MB |
| DEEPSEA | 23.4 MB | START2 | 27.0 MB |
| DEEPSEA2 | 25.6 MB | TITLE | 52.8 MB |
| DOCKS | 19.8 MB | TITLE0 | 1.8 MB |
| FISH | 16.7 MB | TOWN | 24.4 MB |
| GAUNTLET | 13.4 MB | WRACK | 24.4 MB |

All far smaller than on PC (FISH: 16.7 MB against 131 MB).

---

## `AQUA2` and `START2`

**Both are complete, valid level files**, not fragments:
- the same chunk list as the others (`FSIZ VERS EXBY GNRL WDIM RSPR CLAS RSRC BNCH BRTR SCRT SKIP FDIR ENDF`);
- the same `CLAS` size as every PS2 file (248,939 bytes);
- the same `WDIM` world bounds as the rest of the PS2 build.

**The PC has no second file** for these two levels. On PS2 each level is split in two:
- **`START2`** holds the tutorial's ending: the Aurora cutscene, the four rocks and the HUD sprites (`docs/cut_content.md` §3).
- **`AQUA2`** seems to hold the orca boss's part of the aquarium; it has the boss's own copy of a name the PC level also has (`docs/cut_content.md`). Not fully compared.

Probably a split for the PS2's smaller memory, similar in shape to the PC's `BEACH` / `BEACHPST` pair. A full name and `BRTR` comparison against `AQUARIUM`/`START` wasn't done.

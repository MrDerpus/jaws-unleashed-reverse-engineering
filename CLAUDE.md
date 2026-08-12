# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a reverse engineering project for *Jaws Unleashed* (PC version, 2006, developed by Appaloosa Interactive). The goal is to parse and extract assets from the game's `.GDW` archive format — textures, meshes, animations, serialized gameplay objects — and eventually reconstruct scenes in Blender. The game runs on Linux via Wine/Proton. The PC version uses **DirectX 8** (`d3d8.dll`), not DX9 and not the PS2 VIF/GIF rendering pipeline.

## Running Scripts

All scripts live in `scripts/` and are standalone Python files. Run from the project root or from within `scripts/` depending on the script's hardcoded `INPUT_FILE` paths (some use relative paths like `'../GAME_GDWs/FISH.GDW'`, others use `'FISH.GDW'` meaning they expect to be run from `GAME_GDWs/`).

```bash
# From project root
python3 scripts/rip_textures.py

# Scripts that reference FISH.GDW directly need to run from GAME_GDWs/
cd GAME_GDWs && python3 ../scripts/object_parser.py
```

**Dependency:** `Pillow` for image output (`pip install Pillow`). No other dependencies beyond stdlib.

**Typical script workflow:**
1. Edit `NAME` / `name` variable at top of script to target a different `.GDW`
2. Run script — outputs go to a directory specified by `OUTPUT_DIR` in the script
3. Results are `.png`, `.raw`, or `.txt` files

**Run a script across all GDWs at once:**
```bash
# rip_gtex.py uses NAME (uppercase) and runs from project root
for name in AQUARIUM ARMADA BEACH BEACHPST CHASE DEEPSEA2 DEEPSEA DOCKS FISH GAUNTLET KATATAMA MINEMSHA OPEN_NE OPEN_NW OPEN_S START TITLE0 TITLE TOWN WRACK; do
    python3 -c "
import re; from pathlib import Path
script = Path('scripts/rip_gtex.py').read_text()
script = re.sub(r\"^NAME = .*\$\", \"NAME = '$name'\", script, flags=re.MULTILINE)
exec(compile(script, 'rip_gtex.py', 'exec'))
"
done

# rip_textures.py uses name (lowercase) and must run from scripts/ (uses ../GAME_GDWs/ path)
cd scripts
for name in AQUARIUM ARMADA BEACH BEACHPST CHASE DEEPSEA2 DEEPSEA DOCKS FISH GAUNTLET KATATAMA MINEMSHA OPEN_NE OPEN_NW OPEN_S START TITLE0 TITLE TOWN WRACK; do
    python3 -c "
import re; from pathlib import Path
script = Path('rip_textures.py').read_text()
script = re.sub(r\"^name = .*\$\", \"name = '$name'\", script, flags=re.MULTILINE)
exec(compile(script, 'rip_textures.py', 'exec'))
"
done
cd ..
```

## GDW Archive Format

`.GDW` files are chunk-based binary containers (little-endian).

**File header:** A 44-byte plain-text preamble before the first chunk:
```
GDED BINARY FORMAT, VERSION 2.6.3.16.\r\n\r\n\x00\x00\x00
```
Chunks start at byte offset 44 (0x2C).

**Chunk structure:**
```
[4-byte FOURCC tag][uint32 size][payload]
```

Chunks may contain nested subchunks. Known top-level chunks (in order as they appear):

| Chunk | Offset (FISH.GDW) | Size | Description |
|---|---|---|---|
| `FSIZ` | 0x2C | 4 | File size metadata |
| `VERS` | 0x38 | 13 | Version string |
| `EXBY` | 0x50 | 10 | Unknown — small header block |
| `GNRL` | 0x64 | 8 | General archive data (8-byte placeholder in FISH.GDW) |
| `WDIM` | 0x74 | 40 | World dimension bounds (~5000×2000×5000) |
| `RSPR` | 0xA4 | 0 | Unknown — always empty in FISH.GDW |
| `CLAS` | 0xAC | ~250 KB | Class/reflection database |
| `RSRC` | 0x3D43C | ~111 MB | Packed resource payloads (contains GMDL, GTEXT, GTEX, GSMP, etc.) |
| `BRTR` | 0x6A42B40 | ~5.4 MB | **Scene graph / resource tree** — see Scene System section |
| `SCRT` | 0x6F77FC8 | 12,576 | **Screen/overlay object tree** — see note below. Not scripting, not obfuscated. |
| `SKIP` | 0x6F7B0F0 | 264 | **Sector-alignment padding** — payload is all `0xFF` bytes, sized so the following `FDIR` starts on a 512-byte file-offset boundary. See note below. |
| `FDIR` | 0x6F7B200 | 40 | File directory footer |
| `ENDF` | 0x6F7B230 | 0 | Archive terminator |

Each chunk (including nested ones) is padded to a 4-byte boundary before the next tag begins — account for this when walking the chain, or offsets will drift.

**FDIR chunk structure** (32-byte entries, 8-byte header) — corrected 2026-07-17, FDIR is a real offset index, not just names:
```
Header: [uint32 magic/build-date][uint32 entry_count]
Entry:  [uint32 offset][uint32 size][24 bytes name, null-padded]
```
FDIR names are sub-archive identifiers, not individual asset names (e.g. `FISH00`, `TITLE00`–`TITLE0F`, `AQUARI00`). Each entry's `offset`/`size` point at a second, complete, independently-embedded `GDED BINARY FORMAT...` archive concatenated after the primary archive's `ENDF` (see note below) — verified on `FISH.GDW`: entry `FISH00` decodes to `offset=0x6F7B400, size=14415320`, which exactly matches that archive's real start and satisfies `offset+size == EOF`. **Any edit that grows a chunk before this offset (e.g. appending to `RSRC` or `BRTR`) must patch this field by the same delta**, or the game will seek to the wrong place for the second archive. Individual textures/meshes have no stored names in FDIR; they are identified by their numeric resource ID.

**Note on the second embedded archive (found 2026-07-15, mechanics decoded 2026-07-17):** every GDW's declared `ENDF` is not the true end of the file — a second, complete, independent `GDED BINARY FORMAT...` archive (own preamble, own `VERS/EXBY/GNRL/WDIM/RSPR/CLAS/RSRC/BRTR` chain) is concatenated immediately after, padded to reach it with `0xFF` bytes just like `SKIP`. This second archive has **no `FSIZ`, `SCRT`, `SKIP`, `FDIR`, or `ENDF` of its own** — it just ends at true EOF right after its own `BRTR`. Confirmed on `OPEN_S.GDW` (11 such embedded sub-archives) to be **bundled loading-screen scenes** for level transitions (e.g. one named `OPEN_S00`/`LevelLoaderKAT`, holding progress-bar/hint-text UI objects for transitioning to `KATATAMA.GDW`) — not terrain, not cut content. Bounded story levels carry one small (~14MB) embedded archive (mostly a shared/duplicate stub); open zones carry many more, proportional to how many destinations they connect to. `FISH.GDW`'s own second archive has a ~14MB `RSRC` and a tiny (~6KB) `BRTR` (a handful of `CHBR` nodes), consistent with a small loading-screen scene but not independently re-verified by node name.

**Note on PROP-level alignment (found 2026-07-17):** the "padded to a 4-byte boundary before the next tag" rule (see below) also applies **inside** `PRPS` payloads, i.e. individual `PROP` entries are each individually 4-byte-aligned, not just top-level GDW chunks. Missing this causes a full parse desync when decoding a `CHBR` node's property list by hand — probably a general rule for all nested tag sequences in this format (TSET/TANG/VERT sub-chunks not re-verified against it, but suspected to hold there too).

**Note on `SCRT` (corrected 2026-07-08 — do not trust earlier "obfuscated scripting chunk" claim):** There are two `SCRT`-tagged byte sequences in `FISH.GDW`. The one previously documented at offset `0x1105ECC` **inside** `RSRC` is a **false-positive tag match** — its "size" field decodes to over 1 billion, which is impossible, meaning it is not a real chunk header at all, just a coincidental 4-byte pattern inside unrelated binary/compressed data (the printable-ASCII-but-noise bytes seen there are not obfuscated script code, they're just whatever data happens to sit next to the coincidental match). The **real** `SCRT` chunk is a normal **top-level** chunk (sibling of `BRTR`/`FDIR`, not nested in `RSRC`) at `0x6F77FC8`, and it is **not obfuscated** — it uses the same plain `PRPS`/`CHBR`/`PROP` tree format as `BRTR` (see Scene / Object System section). Its root node is named `"Screen"` and its 20 `CHBR` children are named render/overlay targets: `Whale, GDScreen 3-7, CrowdScreenek, WaterSurface, TransparencyAbove/Below/Blur, ReflectionAbove/Below/Blur, ScreenWater/Above/Below, MotionBlur, ZZZ, XXX`. This is a small **screen-space post-processing overlay tree** (water surface reflection/refraction targets, transparency layers, motion blur, crowd billboard, a "Whale" screen effect) tied to the `GDScreen`/`GDOverlay`/`GDForceOverlay` engine classes seen in `CLAS` — not a scripting/gameplay-logic chunk. It reuses the same object-name property (`0x080017D8`) as `BRTR` CHBR nodes, plus a second, still-undocumented property range (`0x08001980`–`0x08001993`) specific to these screen objects. The PS2 `_FISH.GDE` file has the equivalent chunk (also top-level, 8,772 bytes, 14 `CHBR` children) but its nodes use a different but parallel ID range (`0x08001957`–`0x0800196A`) and have no name property set — see PS2 Version Data section.

**Note on `SKIP` (decoded 2026-07-08):** `SKIP` is sector-alignment padding, nothing more. Its payload is entirely `0xFF` bytes, and its size is always exactly what's needed so the byte offset immediately after it (where `FDIR` begins) lands on a multiple of 512. Confirmed across FISH, TOWN, START, AQUARIUM, TITLE0 (PC) and `_FISH.GDE` (PS2) — sizes vary per file (20–428 bytes) because `SCRT` ends at a different arbitrary offset each time, but the post-`SKIP` offset is always `% 512 == 0` in every case checked. No further structure to parse.

## Texture System (GTEXT)

Textures use the `GTEXT` marker. Confirmed header layout:

| Offset | Field |
|---|---|
| `+0x00` | `GTEXT` signature |
| `+0x04` | block size (uint32) |
| `+0x08` | texture ID |
| `+0x18` | width (uint32) |
| `+0x1C` | height (uint32) |
| `+0x20` | bits-per-pixel (uint32) |
| `+0x24` | `TGAN0` marker (5 bytes) + 7 unknown bytes |
| `+0x30` | standard 18-byte TGA 1.0 header (ID len, cmap fields, x/y origin, width, height, bpp, descriptor — all confirmed to redundantly match the fields already read at `+0x18`/`+0x1C`/`+0x20` above) |
| `+0x42` | **pixel payload start** (corrected 2026-07-29, was wrongly documented/coded as `+0x54`) |

**Correction (2026-07-29):** pixel data actually starts at `+0x42`, immediately after the 18-byte TGA header — not `+0x54` as previously documented and implemented in `rip_textures.py`. The `+0x54` figure conflated the real 18-byte TGA header with a **trailing** TGA 2.0 footer (`[8 zero offset bytes]["TRUEVISION-XFILE.\0"]`, 26 bytes total, of which 18 land inside the declared `block_size` and the remaining 8 spill into the start of the next block's raw bytes — harmless for parsing since block boundaries are found by string search, but fatal if used to compute the pixel read offset). Reading from `+0x54` skipped the first 18 bytes of real pixel data and read 18 bytes of footer garbage at the end instead — a non-integer-pixel shift that produced a diagonally-sheared/wrapped image. Verified structurally across all 242 real GTEXT blocks in `FISH.GDW` (width/height/bpp fields inside the TGA header at `+0x3C`/`+0x3E`/`+0x40` match the values already read at `+0x18`/`+0x1C`/`+0x20` in 242/242 cases) and visually (a "Sole Predator" promotional title-screen texture that sheared/wrapped under the old offset extracts cleanly at `+0x42`).

Payload size formula is unchanged: `payload_size = block_size - 0x54` (this already yields the correct total pixel byte count — `block_size` accounts for the 66-byte real header plus payload plus the 18 trailing footer bytes it includes; only the **start offset** was wrong, not the length).

Supported pixel formats: `32` (RGBA32, but see byte-order correction below), `24` (RGB24, stored as BGR — swap channels on read), and `8` (indexed/CLUT — decoded 2026-07-29, see below). Textures are stored upside-down (origin at bottom-left, as is common in OpenGL/DirectX conventions); `rip_textures.py` applies `FLIP_VERTICAL` by default. Unknown BPP values are dumped as `.raw` files in `textures/<LEVEL>/gtext/`.

**8bpp indexed/CLUT format (decoded 2026-07-29):** payload = `[768-byte palette: 256 entries × 3 bytes RGB][width×height index bytes, one per pixel]`. Confirmed on the only 2 real 8bpp GTEXT blocks found across all 20 GDWs (`TITLE.GDW` tex_id `0x139` and `GAUNTLET.GDW` tex_id `0x18b`, both 64×64, same shared UI icon — a small vehicle/silhouette thumbnail): file size in both cases is exactly `768 + width*height` bytes, and both palettes happen to be an identical linear inverted grayscale ramp (`palette[i] = (255-i, 255-i, 255-i)`). Decodes cleanly via palette lookup. `rip_textures.py` now handles this (`idx8.png` output suffix). Of the 59 `.raw` dumps that previously sat in `textures/*/gtext/`, only these 2 were real textures — the other 57 were confirmed false-positive `GTEXT` string matches inside unrelated binary data (byte-for-byte checked: they're legitimate `GMAT` material sub-chunks — readable tags like `SHIN`/`SILL`/`TRAN`/`COLS` and plausible float values sit right in the dump — that a coincidental 5-byte `"GTEXT"` pattern match landed inside of; nonsensical multi-billion-pixel declared dimensions and "texture IDs" that decode as ASCII tag fragments like `REFL`/`GTEX` gave it away). The source data is untouched in the `.GDW` files; only the wrongly-produced output files were deleted (2026-07-29) — none remain on disk. Note this is a distinct, separate finding from `docs/GDW_FORMAT.md`'s "CLUT textures extract as scrambled garbage" note, which is about 24/32bpp textures that looked wrong under the old pixel-offset/byte-order bugs (now separately annotated/corrected there) — not about this genuinely-indexed 8bpp format.

**Byte-order correction (2026-07-29):** 32bpp GTEXT pixel data is **not** straight RGBA — like GTEX (see below), it's native little-endian `D3DFMT_A8R8G8B8`, byte order **B, G, R, A**. The previous "RGBA32, no swap" assumption produced a systematic R/B channel swap (subtle blue tint on naturally warm-toned textures — e.g. a kelp/seaweed texture rendered blue-teal instead of its correct green/brown). `rip_textures.py` now reads 32bpp with PIL raw mode `'BGRA'`, matching the already-correct 24bpp `'BGR'` handling. This bug was masked until the `+0x42` offset fix above was applied, since the pre-existing pixel-shift corruption made channel-order errors hard to distinguish from general noise.

**Output filename format:** `texture_<seq:04>_id<tex_id:08x>_<W>x<H>_<rgba32|rgb24>.png` — output to `textures/<LEVEL>/gtext/`.

**Primary texture extraction script:** `scripts/rip_textures.py` — set the `name` variable to the GDW filename stem (e.g. `'FISH'`). Must be run from within `scripts/` (uses `../GAME_GDWs/` relative path).

**Extracted: 4,923 total GTEXT textures across all 20 GDWs** (TITLE0 has 0; others range 176–357). Re-extracted 2026-07-29 after the offset/byte-order fixes above (was 4,673 — the extra 248 are blocks that previously came up short on the final length check due to the offset bug and were silently dropped, not new content) and again after the 8bpp indexed/CLUT decode below (+2: the only 2 real 8bpp blocks in the whole dataset, `TITLE.GDW` and `GAUNTLET.GDW`, previously fell into the unsupported-BPP `.raw` path instead of being counted as extracted).

## Texture System (GTEX)

A second, newer texture system uses a 4-byte `GTEX` tag (not `GTEXT`). These are sprite/overlay textures meant to be composited in layers by the engine. Script: `scripts/rip_gtex.py`.

**GTEX block structure:**
```
[GTEX][uint32 block_size][payload]
```
**GTEX payload structure:**
```
[uint32 texture_id][uint32 flags][...optional OBPR/PROP sub-blocks...][uint32 width][uint32 height][uint32 bpp][TGAN]
```
- First uint32 of payload = engine texture ID (used to bind textures to materials)
- Width/height/BPP are always the 3 uint32s immediately before the `TGAN` sub-chunk
- Some blocks contain an `OBPR` section with a `PROP` chunk holding a type tag (`TEXB`, `TEXH`, `TEXD`) — meaning of these tags is not yet known
- TGAN payload layout (corrected 2026-07-29): `[4-byte size-prefix, value = tgan_size-4][18-byte standard TGA 1.0 header][pixel data][optional 26-byte trailing TGA 2.0 footer: 8 zero offset bytes + "TRUEVISION-XFILE.\0"]`. The header is a **fixed 22 bytes** (4 + 18) — pixel data always starts at `tgan_pos + 8 + 22`. Do not derive the header size as `tgan_size - pixel_size`: `tgan_size` sometimes includes the trailing 26-byte footer and sometimes doesn't (both observed in `FISH.GDW`), so that formula intermittently included the footer as if it were leading header bytes, skipping real pixel data and reading footer garbage instead — a non-integer-pixel shift producing shifted/wrapped image content. Verified structurally across 90/90 sampled GTEX blocks in `FISH.GDW` (width/height/bpp fields inside the 18-byte TGA header match the values already read outside TGAN).

**Output filename format:** `gtex_<seq:04>_id<tex_id:08x>_<W>x<H>_<rgba32|rgb24>.png`

**Confirmed pixel formats (from GDW analysis + game binary `game_binary/Jaws.exe`):**
- Game uses DirectX 8, `D3DFMT_A8R8G8B8` for 32bpp textures
- **24bpp:** native BGR byte order (`byte[0]=B, byte[1]=G, byte[2]=R`) — swap channels on read. TGA `image_descriptor=0x00`. **Corrected 2026-07-29** (previously documented/coded as "R, B, G, swap G↔B" — wrong; the file is straight BGR, same convention as GTEXT's 24bpp path).
- **32bpp:** native BGRA byte order (`byte[0]=B, byte[1]=G, byte[2]=R, byte[3]=A`). TGA `image_descriptor=0x08` (8 alpha bits). **Corrected 2026-07-29** (previously documented/coded as "ARGB, byte[0]=A..." — wrong. `D3DFMT_A8R8G8B8` names bit significance MSB→LSB, not little-endian file byte order, which is actually B,G,R,A). The old ARGB assumption produced a visible R/G channel swap; the old GTEXT "straight RGBA" assumption on the same underlying format produced a subtler R/B swap (blue tint on warm-toned textures). Verified by rendering a seaweed/kelp texture: renders as implausible blue-teal under the old byte order, correct green/brown under BGRA. Both issues were masked until the TGAN pixel-offset fix above was applied.
- **Chroma key:** CYAN `#00FFFF` (D3D DWORD `0xFF00FFFF`, confirmed at VA `0x725427` in binary). Background pixels where R<20, G>235, B>235 become fully transparent. (Chroma detection must read R/G/B from the corrected BGRA byte positions above — the old ARGB-based detection was checking the wrong bytes.)
- All textures stored bottom-up; apply `FLIP_TOP_BOTTOM` on extract.
- 32bpp GTEX without TGAN are metadata/reference blocks (no pixel data) — skip them.
- 32bpp GTEX with `descriptor=0x00` and all-zero pixels are runtime render targets filled by the engine — correct to export as blank.

**Other TGAN format tags seen in binary dispatch:** `TGAF`, `DXTF`, `ZIPN`, `ZIPT`. Tags like `DXTF`/`ZIPN`/`ZIPT` that appear inside `.GDW` files are false-positive byte matches inside unrelated compressed/binary data — not real texture blocks. (Note: `ZIPN` **is** a real, legitimate tag on the PS2 side, marking native PS2 GS pixel data — not compression, despite the name — see PS2 Version Data section for the fully-decoded format. Its occurrences inside PC `.GDW` files are coincidental matches, not PS2-format texture blocks smuggled into the PC archive.)

**Extracted: 2,787 total GTEX textures across all 20 GDWs** (via `scripts/rip_gtex.py`). Re-extracted 2026-07-29 after the offset/byte-order fixes above (was ~1,660 — the dynamic `tgan_size - pixel_size` header-offset formula previously pushed many blocks' pixel-read window past the end of their real data, causing a silent short-read skip; the fixed offset recovers those).

## Texture Database — `textures/texture_db.json`

The game uses a **global texture ID space** shared across all GDWs. When a level loads, the engine pulls textures from multiple GDW files simultaneously. A single texture ID may appear in several GDWs (redundant copies).

**Key findings (from exhaustive scan of all 20 GDWs):**
- **1,049 unique texture IDs** in the range 1–4146 (sparse — 3,097 gaps)
- **7,710 total database entries** (IDs duplicated across GDWs counted separately)
- **911 IDs** appear in multiple GDWs (shared textures — water caustics, creature skins, common materials)
- **138 IDs** are unique to a single GDW (level-specific content)
- **65 IDs** are referenced by mesh TSET chunks but stored nowhere — these are runtime render targets (reflections, shadow maps) created by the engine at startup; no pixel data exists for them

**Database schema** (`textures/texture_db.json`):
```json
{
  "<texture_id>": [
    { "gdw": "AQUARIUM", "file": "textures/AQUARIUM/gtext/texture_0042_id0000002a_256x256_rgb24.png",
      "w": 256, "h": 256, "bpp": 24, "src": "GTEXT" },
    ...
  ]
}
```
Each entry gives the first GDW where the ID was found, plus its extracted filename. IDs shared across GDWs have multiple entries.

**Rebuild the database** (after re-extracting textures):
```bash
python3 scripts/build_texture_db.py
```

**Correction (2026-07-30) — texture IDs are not always genuinely shared content across GDWs; true collisions happen.** The "911 IDs appear in multiple GDWs" figure above was previously assumed to mean redundant copies of the *same* image per ID (consistent with the shared global asset pool described elsewhere in this doc). Spot-checking texture ID `0x2E9` (745) — encountered while cataloguing the Amity Island overview map, see below — found it resolves to **three unrelated images** in three different GDWs: `BEACH.GDW` (a Spanish-language "ability unlocked" tutorial popup, 640×480), `OPEN_NW.GDW` (a "The Underwater Caves / Loading..." splash screen, 1024×512), and `OPEN_NE.GDW` (the world map, 512×256, see below) — different dimensions in every case, confirming these are not the same asset re-embedded, just a coincidental ID collision. Not yet re-audited across the other 910 multi-GDW IDs, so treat "shared across GDWs" as **unverified same-content** for any given ID until spot-checked, not a guarantee.

**World/stage-select map texture, catalogued 2026-07-30:** `OPEN_NE.GDW`'s `gtex_0123_id000002e9_512x256_rgba32.png` is the in-game Amity Island overview map, shown when the player presses `^MAP^` (see the `MAP OF AMITY ISLAND` strings in `game_binary/Jaws.exe`, already noted in `docs/mission_system.md`'s location string table). This is normal, fully shipped UI content, not cut — flagging only because the ID collision above means the same texture ID elsewhere is a red herring, and because this specific file became relevant to the BEACH cut-objective investigation below (the map's painted illustration of the interior near BEACH shows a distinct rounded landform and a lighter, stream-like break in the canopy leading to it from the coast — independent, suggestive-but-not-conclusive visual corroboration of that theory, since this is a painted overview graphic, not literal terrain data).

## Geometry Pipeline — `scripts/rip_meshes.py`

Mesh extraction is **working** across all 20 GDWs. **11,948 total `.obj` files** extracted to `models/<NAME>/`.

| GDW | Meshes | GDW | Meshes |
|---|---|---|---|
| AQUARIUM | 1,161 | OPEN_NE | 1,100 |
| START | 1,115 | KATATAMA | 923 |
| OPEN_S | 1,009 | OPEN_NW | 798 |
| BEACH | 765 | TOWN | 696 |
| ARMADA | 666 | DEEPSEA2 | 660 |
| DOCKS | 465 | BEACHPST | 460 |
| MINEMSHA | 386 | FISH | 384 |
| WRACK | 344 | DEEPSEA | 366 |
| CHASE | 244 | GAUNTLET | 261 |
| TITLE | 145 | TITLE0 | 0 |

### GMDL Chunk Hierarchy

```
GMDL  [variable size]
  [12-byte sub-header: mesh_id, count, hash]
  MATR  [52]       material colour properties
  MATS  [20]       material set
  GMAT              material definitions (GMAT1, GMAT2 sub-entries)
  TSET  [variable] texture channel assignments — see format below
  TANG  [variable] triangle data container
    VIND            uint16 triangle list index buffer
    TNOR            per-triangle normals
    TFLG            per-triangle flags
  VERT  [variable] vertex data container
    POSI            float32 XYZ positions  (12 bytes/vert)
    NORM            float32 XYZ normals    (12 bytes/vert)
    UVUV            float32 UV coords      (8 bytes/vert — one UV pair per vertex)
  VCOL              vertex colours         (16 bytes/vert — RGBA float32)
```

**Key layout notes:**
- TANG and VERT are **container chunks** — they each begin with a **uint32 count header** (triangle count or vertex count), followed immediately by their sub-chunks. Do not try to parse sub-chunks at the GMDL level; descend into the TANG/VERT payload first, skip 4 bytes, then scan for VIND/POSI/etc.
- Index buffer is a **triangle list** (groups of 3 uint16 indices per triangle, alternating winding for quads)
- `max(VIND indices)` must be `< POSI count` — use this to validate meshes and skip false positives
- V coordinate should be flipped (`1.0 - v`) when writing OBJ for standard UV convention
- GMDL blocks with no POSI/VIND, or where max index ≥ vert count, are skipped

### TSET Format

```
TSET [uint32 payload_size]
  [uint32 N]           ← number of texture layers (1–6+ seen)
  [N × 20-byte layer records]
```

Each layer record (5 × uint32):
```
[layer_idx][val_A][val_B][val_C][val_D]
```
- `layer_idx` = 0-based layer index (matches record position)
- `val_A`–`val_D` contain texture IDs from the global ID space; non-zero values reference textures
- For `layer_idx=0`: val_A and val_C are often 0 (no previous layer); val_B and val_D are the primary texture IDs
- For `layer_idx>0`: all four values may contain texture IDs (previous and current layer textures)
- Block size formula: `(1 + N×5) × 4` bytes

Texture IDs from TSET are resolved using `textures/texture_db.json`. Up to 663 unique texture IDs referenced per level; ~65 per level are runtime render targets with no stored data.

**Dead end — do not revisit:** The region at `0x6FB887C` in `FISH.GDW` was conclusively ruled out as geometry by `scripts/vertex_stride_tester.py`.

### GMAT Material Sub-Chunks

Each `GMAT` block contains a full material definition as a sequence of small named sub-chunks (all confirmed via sliding-window scan of RSRC). Every sub-chunk follows the standard `[4-byte tag][uint32 size][payload]` format:

| Tag | Size | Description |
|---|---|---|
| `TEXP` | 12 | Texture expression — `[uint32 layer_idx][uint32 GTEX_ref]` binding to a GTEX texture slot |
| `REFL` | 8 | Reflection map — 2 floats (intensity, falloff) |
| `BUMP` | 8 | Bump map — 2 floats |
| `COLS` | 48 | Diffuse colour — 12 floats (4 × RGBA for multiple colour slots) |
| `SHIN` | 8 | Shininess — 2 floats (specular power, specular intensity) |
| `SILL` | 4 | Silhouette/rim intensity — 1 float |
| `TRAN` | 4 | Transparency — 1 uint32 (0 = opaque) |
| `BIAS` | 4 | Polygon offset bias — 1 float |
| `TIAS` | 4 | Texture image alpha scale — 1 float |
| `STAF` | 4 | Shadow/stencil flag — 1 uint32 |
| `SLIF` | 4 | Slice/clip flag — 1 uint32 |
| `CHRO` | 4 | Chroma key flag — 1 uint32 |
| `SMOO` | 4 | Smoothing — 1 uint32 |
| `TWOS` | 4 | Two-sided rendering — 1 uint32 |
| `CLAM` | 4 | Texture clamping mode — 1 uint32 |
| `COLT` | 4 | Colour tint flag — 1 uint32 |
| `FLAG` | 4 | Material flags — 1 uint32 |
| `TXAN` | 8 | Texture animation — 2 uint32s |
| `MTOP` | 4 | Material opacity flag — 1 uint32 |

These appear as 434 instances each (one per GMAT block in FISH.GDW). The `TEXP` sub-chunk is the key link to textures — it maps a material layer to a GTEX texture block by ID, providing the visual appearance of the mesh surface.

## RSRC Internal Layout

The `RSRC` chunk payload does **not** start immediately with a chunk tag. It begins with a **12-byte binary sub-header** (content unknown), then the first resource block. Resource blocks are not a flat `[tag][size]` chain at the top level — they use a mix of 4-byte and 5-byte marker strings depending on type. Use marker-search (byte-pattern `find`) rather than size-hopping to locate specific block types.

**RSRC payload structure:**
```
[12 bytes sub-header]
[GTEX blocks]          ← texture resources (GTEX format, 4-byte tag)
[GTEXT blocks]         ← texture resources (GTEXT format, 5-char marker)
[GSMP / SMPB blocks]   ← audio samples
[GSFX blocks]          ← sound effect property blocks
[GMAT / material sub-chunk blocks]  ← full material database
[SKEL / BONE / ROTS / ANIM blocks]  ← skeletal animation data
[GMDL blocks]          ← mesh geometry (res IDs 0x745–0xFFFFFFFF)
[MREG blocks]          ← collision/BVH regions (0x69CBB80 onward)
[GMOA / GSQD blocks]   ← AI behavior sequences
```

**Complete list of discovered RSRC chunk tags** (confirmed by sliding-window scan of FISH.GDW RSRC, 2025-06-29):

| Tag | Count (FISH) | Description |
|---|---|---|
| `GMDL` | 459 total | Mesh geometry (see Geometry Pipeline section) |
| `GSFX` | ~20,000 | Sound effect property blocks — `flags=0x44` variant of GSMP; contains volume float + GSMP sample ID reference. NOT audio PCM. |
| `GMAT` | ~41,000 | Material definition blocks |
| `GTEX` | ~15,000 | Texture blocks (GTEX format) |
| `GSMP` | ~10,000 | Audio sample blocks |
| `SKEL` | 30 | **Skeletal animation data, fully decoded** — see Skeletal Animation section |
| `TRAN` | 1,152 | Transform property sub-chunk (4-byte, transparency/transform value) |
| `MREG` | 123 | **Collision mesh region** — see Collision / BVH System section |
| `MTOB` | 718 | 4×3 float32 transform matrix (48 bytes, `[col0 col1 col2 translation]`) |
| `ROTS` | 718 | Rotation keyframe array — float32 quaternion/matrix data for animation |
| `CHLD` | 548 | Child node container — holds MTOB + ROTS sub-chunks |
| `GSQD` | 485 | Game Sequence Data — AI behavior zone definition; see AI System section |
| `GMOA` | 485 | Game Model Object Animation — top-level AI/behavior container |
| `BROT` | 140 | Bone rotation track — contains MTOB |
| `BONE` | 30 | Individual bone definition — contains MTOB (rest pose transform) |
| `WGHT` | 30 | **Vertex weights** for skeletal skinning |
| `ANIM` | 10 | Animation name dictionary — maps animation IDs to string names |

## Collision / BVH System — MREG / BREG / STRI

Each `MREG` block pairs a visual GMDL mesh with a **Bounding Volume Hierarchy (BVH)** for physics/collision. There are **123 MREG blocks** in FISH.GDW (region IDs 0x943–0x9EB, file offsets 0x69CBB80–0x6A329EC within RSRC).

### MREG Block Layout

```
MREG [uint32 size]
  [uint32 region_id]       ← unique region ID (2371–2539 in FISH.GDW)
  [uint32 unknown = 1]
  [uint32 "GMDL" type tag] ← ASCII 0x4C444D47, type discriminator (not a chunk)
  [uint32 mesh_res_id]     ← resource ID of the paired GMDL mesh
  [uint32 flags = 0xFFFFFFFF]
  PERF [4]                 ← float32 LOD/performance hint (always 0.25 in FISH.GDW)
  BREG [variable]          ← BVH node array
  STRI [variable]          ← BVH traversal index list
```

### BREG — BVH Node Array

```
BREG [uint32 size]
  [uint32 node_count]           ← number of BVH nodes (139–199 in FISH.GDW)
  [node_count × 24 bytes]       ← one AABB per node
    [float32 minX minY minZ]    ← bounding box minimum corner
    [float32 maxX maxY maxZ]    ← bounding box maximum corner
```

Node 0 is always the root AABB (enclosing the entire mesh). Subsequent nodes subdivide the space recursively. The vertex extents of the paired GMDL mesh match the root BREG AABB exactly (verified for multiple MREGs).

### STRI — BVH Traversal Indices

```
STRI [uint32 size]
  [uint32 index_count]
  [index_count × uint32]   ← BVH node traversal order or child-pair indices
```

### MREG ↔ BRTR Relationship

Of the 123 MREG blocks in FISH.GDW:
- **118 mesh_res_ids** match GMDL meshes that are **also placed as visual instances in BRTR** — rocks (`szikla`), sandy shore tiles (`Homokos`), foundation meshes, etc. each have both a visual BRTR placement AND a collision MREG.
- **5 mesh_res_ids** have MREG collision data but **no BRTR visual instance** — collision-only geometry not rendered.

The `mesh_res_id` in MREG matches the **first uint32 of the 12-byte GMDL sub-header** (same linkage as PROP `0x08001873` in BRTR). GMDL mesh indices for the MREG-referenced meshes in FISH.GDW span approximately idx 23–262.

## Skeletal Animation System — SKEL / BONE / WGHT / ROTS / ANIM

**Fully decoded (2026-07-17).** Each `SKEL` block is one complete skeleton (one per skinned character/creature mesh) — bind-pose reference mesh, per-vertex bone weights, a recursive bone hierarchy, and (if the skeleton has named clips) a shared quaternion keyframe pool sliced by an animation dictionary. **Correction:** earlier docs listed `SKEL` count as 3,030 — the real count is **30** (an accidental doubling of the true figure; it now matches the `BONE`/`WGHT` counts below, all of which describe the same 30 skeletons). `ROTS`/`MTOB`/`CHLD`/`BROT` counts below are likewise per-bone-node totals across all 30 skeletons, not top-level RSRC entries.

Extractor: `scripts/rip_skeletons.py` (run from project root, set `NAME` to the target GDW stem) → `skeletons/<NAME>/skel_<id>.json` (one file per skeleton: bind mesh, weights, full bone tree with per-bone rotation keyframes, named clips) + `_summary.json`. Verified clean on `FISH.GDW`: 30/30 skeletons parsed with zero false positives; spot-checked 729 quaternions across all skeletons — 728 are unit-length to within 1%, all named-clip frame ranges fall within their skeleton's shared frame-pool bounds.

### Known chunk types

| Tag | Count (FISH) | Description |
|---|---|---|
| `SKEL` | 30 | Skeleton container — one per skinned character/creature mesh, 54 KB–1 MB each |
| `BONE` | 30 | Root bone of each skeleton's hierarchy — a recursive container (see below), not a single leaf |
| `WGHT` | 30 | Per-vertex bone skinning weight table, one per skeleton — fully decoded, see below |
| `VERT`/`NORM` | 30 each | Bind-pose reference mesh (positions + normals) embedded in each `SKEL`, sized to match that skeleton's `WGHT` vertex count |
| `ANIM` | ≤30 (optional per-skeleton) | Named animation-clip dictionary — present only on skeletons with authored clips (e.g. shark: 73 clips; many prop/creature skeletons have 0) |
| `MTOB` | 718 total (one per bone node, all skeletons) | 4×3 float32 bind-pose local transform, 48 bytes: column-major layout matching PROP `0x080017DA` (3×3 basis + translation) |
| `TRAN` | one per bone node | 3× float32 small local offset alongside each `MTOB` — role unconfirmed, values near-zero in samples checked |
| `ROTS` | one per bone node | Per-bone stream of unit quaternions (`x,y,z,w`, 16 bytes each), one frame per shared skeleton-wide frame pool — **this is the actual keyframe animation data** |
| `CHLD` / `BROT` | 548 / 140 total | Child bone-node containers — same grammar as `BONE`'s payload (`MTOB`+`TRAN`+`ROTS`+further children); no observed semantic difference between the two tags, both just nest another bone |

### WGHT — Vertex Skinning Weights (decoded)

No header — straight array of fixed 32-byte records, one per bind-pose mesh vertex (vertex count comes from the sibling `VERT` block):

```
WGHT [uint32 size]     ← size == vertex_count * 32, no leading count/header field
  per vertex (32 bytes):
    [4 × int32 bone_index]   ← -1 marks an unused influence slot
    [4 × float32 weight]     ← only meaningful where the paired bone_index != -1;
                                the weight slot for an unused (-1) index holds
                                leftover/garbage data (often 1.0) and must be
                                masked out, not summed
```
Verified on FISH.GDW's 40-bone shark skeleton (2,384 verts): masked weights sum to 1.0 for all 2,384 vertices; raw (unmasked) sums are wrong for any vertex with fewer than 4 real influences.

### BONE / CHLD / BROT — Recursive Bone Hierarchy (decoded)

`BONE` is not a single bone leaf — it's the **root of the entire skeleton tree**, and its declared size spans everything from the root bone's own data through every nested child, all the way to the end of the `SKEL` payload. `CHLD` and `BROT` are children using the identical node grammar (interchangeable, no semantic split found — a branching bone with two children just uses one of each tag at that level):

```
BONE | CHLD | BROT  [uint32 size]        ← one bone node
  MTOB [48]   ← bind-pose local transform: 3×3 basis (col-major) + translation
  TRAN [12]   ← 3 floats, small local offset, unconfirmed role
  ROTS [N×16] ← N unit quaternions (x,y,z,w), one per frame of this skeleton's
                shared pool (every bone in a skeleton has the same N)
  [zero or more CHLD/BROT children, same grammar, recursing]
```
Verified on the shark skeleton: 40 `MTOB` nodes total (root + 39 nested), tree depth up to 17, every `ROTS` stream exactly 1,516 frames long (matching the `ANIM` dictionary's frame-pool bounds below), all sampled quaternions unit-length.

### ANIM — Animation Name Dictionary + Frame Ranges (decoded)

Present only on skeletons with named clips (e.g. shark: 73 clips; most creature/prop skeletons: 0, animating only via the bind pose / external drivers). All bones in a skeleton share **one contiguous quaternion pool**; `ANIM` slices it into named clips:

```
ANIM [uint32 size]
  [uint32 clip_count]
  [uint32 unknown]                          ← not yet decoded
  clip_count × {
    [uint32 name_len]                       ← includes NUL terminator
    [name_len bytes, NUL-terminated ASCII]  ← padded to 4-byte alignment
  }
  clip_count × [uint32 start_frame]         ← index into the shared ROTS pool
  clip_count × [uint32 end_frame]           ← inclusive
```
Frame 0 of the pool is the shared bind/rest frame and falls outside every named clip (shark's clips start at frame 1). Verified: `end_frame` of the last clip equals the shared pool's final frame index (1,515, for a 1,516-frame pool) on the shark skeleton.

**Confirmed animation names from FISH.GDW's shark skeleton (73 total):** `Shark_GW_BodyBomb2`, `Shark_GW_BodySlam_Left/Right`, `Shark_GW_Devour01/02`, `Shark_GW_NyammogA/B/C/D` + `_nagy`/`_kicsi_*` size variants (`nyammog` = munching/biting motion in Hungarian), `Shark_GW_TailWhip_Left/Right_*`, `Shark_GW_Swallow_A/B/Begin/C/End`, `Shark_GW_Landwalk*`, `Shark_GW_DeathSpinCW_Begin/Spin`, `Shark_GW_ThrowLeftDown/Up`, `Shark_GW_ThrowRightDown/Up`, and more (full list in `skeletons/FISH/skel_01766.json`).

**NPC human animations** (seen as skeleton names on smaller skeletons, not yet cross-referenced clip-by-clip): `BeingDevouredLegs_A01/02/03`, `FrightenedRun`, `GetOut`, `GrThrow`, `Harpoon`, `icRun`, `Run2x`, `Walk2x`, `FatWalk2x`, `PanicRun`, `SharkAvoid2x`, `StandCheer3x`, `StandClap4x`

### Still open

- The undecoded blob (tens of KB, varies per skeleton) between the 12-byte `SKEL` header and the `VERT` block — not yet identified; a morph/blendshape delta table is one hypothesis (unconfirmed) given how many named clips are jaw/mouth animations, but the blob's byte count doesn't cleanly divide by the bind-mesh vertex count.
- `TRAN`'s exact role (near-zero in every sample checked so far).
- Cross-referencing `ANIM` clip names to the `XAnimation`/`XAnimationSet`/`XAnimationNames` CLAS classes and to skeleton *instances* placed in `BRTR` (i.e. which placed `XSkeletonModel` node plays which `SKEL` block).
- Blender armature + animation import (mesh-only import already exists — see `scenes/import_fish_blender.py` — but it has no skinning/bone data wired in yet).

## AI / Behavior Sequence System — GMOA / GSQD

The AI zone and behavior sequence system occupies the tail of RSRC (0x6A329F4 onward in FISH.GDW).

```
GMOA [uint32 size]     ← Game Model Object Animation — top-level container
  [uint32 gmoa_id]
  [uint32 count]
  [uint32 magic]
  SQDR [8]             ← Sequence Director — contains reference to one GSQD by ID
  GSQD [variable]      ← Game Sequence Data — one AI behavior zone
    [uint32 zone_id]
    [uint32 count]
    [uint32 magic]
    GSEQ [variable]    ← Game Sequence — named behavior (e.g. "repul" = repulsion zone)
    [uint32 MREG-type tag]
    [uint32 mreg_region_id]  ← references an MREG spatial region
  MOIL [variable]      ← unknown — large integer/float table (~66 KB)
```

`GSQD` zones define where AI behaviors (attraction, repulsion, patrol) apply spatially by referencing an `MREG` region. The "repul" name seen in FISH.GDW designates zones where certain creatures are repelled. `MOIL` content is not yet decoded.

## Scene / Object System — BRTR Chunk

**The `BRTR` chunk IS the pre-built scene graph.** It contains all placed object instances with full world-space transforms, mesh references, vertex colour data, and AABBs — the complete level layout as authored by the developers.

### BRTR Internal Structure

```
BRTR [uint32 size]
  [4-byte magic: 0x01025024][uint32 root_count=1]
  PRPS [root "World" object]     ← root scene node, pos=(0,0,0), name="World"
  CHBR [uint32 size]             ← child branch node (one per placed object)
    [uint32 magic: 0x0107402F]
    [uint32 node_id]             ← sequential ID, range 66–35137 in FISH.GDW
    PRPS [uint32 size]
      PROP ...                   ← all object properties (see below)
  CHBR ...
```

FISH.GDW BRTR stats:
- **2782 CHBR nodes** — all have names and world transforms
- **1161 nodes** have resolvable mesh references → geometry placed in the level
- **908 nodes** have baked vertex colour data (baked lighting)
- **1621 nodes** are non-mesh objects: waypoints, AI markers, particle systems, audio sources, triggers

### Known PROP IDs (BRTR / PRPS context)

| ID | Meaning | Payload |
|---|---|---|
| `0x080017D8` | Object name | uint32 length + UTF-8 string |
| `0x080017D9` | Object flags | uint32 |
| `0x080017DA` | World transform | 12 float32s — column-major 4×3 (see below) |
| `0x080017DB` | Unknown flag | uint32 |
| `0x080017DC` | Unknown flag | uint32 |
| `0x080017DD` | Unknown flag | uint32 |
| `0x080017DE` | Unknown flag | uint32 |
| `0x080017DF` | AABB bounds | 6 float32s: minX minY minZ maxX maxY maxZ — **world space** |
| `0x080017E3` | Unknown | uint32 |
| `0x080017E4` | Unknown | uint32 |
| `0x08001873` | Mesh reference | 8 bytes: `[uint32 "GMDL" tag][uint32 mesh_resource_id]` |
| `0x08001874` | Unknown | uint32 |
| `0x08001875` | Object type flags | uint32 (e.g. `0x1000009`) |
| `0x08001876` | Unknown flags | uint32 |
| `0x08001877` | Unknown | uint32 |
| `0x08001878` | Unknown | uint32 |
| `0x08001879` | Colour scale | 4 float32s (RGBA multiplier, usually 1.0) |
| `0x0800187A` | Per-vertex colour data | uint32 vert_count + vert_count × 16 bytes (RGBA float32 per vert) — **baked lighting** |
| `0x0800187B` | Unknown | uint32 |
| `0x080003C7` | Child node ID list | uint32 count + count × uint32 node_ids |

**Mesh reference clarification:** PROP `0x08001873` first uint32 is literally the ASCII tag `GMDL` (= `0x4C444D47`) stored as a type discriminator, not an "unknown" field. Second uint32 = mesh resource ID matching the first uint32 of the GMDL 12-byte sub-header.

### Transform Format (PROP `0x080017DA`)

Stored as **12 float32s in column-major 4×3 layout**:

```
xf[0..2]  = X-basis vector (column 0)
xf[3..5]  = Y-basis vector (column 1)
xf[6..8]  = Z-basis vector (column 2)
xf[9..11] = Translation (TX, TY, TZ)
```

To transform a local vertex `(x, y, z)` to world space:
```python
wx = xf[0]*x + xf[3]*y + xf[6]*z + xf[9]
wy = xf[1]*x + xf[4]*y + xf[7]*z + xf[10]
wz = xf[2]*x + xf[5]*y + xf[8]*z + xf[11]
```

Column vector lengths encode uniform or non-uniform scale. Verified correct: computed world AABBs match stored PROP `0x080017DF` values to within floating-point precision (error = 0.0).

### Mesh–Object Linkage

PROP `0x08001873` second uint32 = mesh resource ID. This matches the **first uint32 of the 12-byte GMDL sub-header** (the mesh's resource ID). Use this to link a CHBR scene object to its GMDL geometry.

The sequential OBJ file index (`FISH_mesh_XXXX.obj`) corresponds to the order GMDL blocks are encountered during a linear scan of the GDW — not the resource ID directly. `rip_brtr_scene.py` builds the `resource_id → mesh_idx` mapping at runtime.

### Scene Layout — FISH.GDW

Coordinate system is DirectX Y-up (Y = height). World extents: X −120 to 2499, Y −229 to 2305, Z −4584 to 32.

Two spatial clusters:
- **Pier/dock** at world origin (~0, 0, 0): dock planks (`deska`), columns (`oszlop`), breakable posts, shops, buildings
- **Underwater tutorial area** at ~(1600–2500, −50 to +50, −3600 to −4600): rocks (`szikla`), wrecks (`wrack`), skull (`koponya`), alpha overlays (`interalph`), mansions (`mansionC`)

Notable placed objects in FISH.GDW: `GWside` (great white shark model), `WhaleCarcass Body`, `MartinWalker` (NPC), `mansionC` (×2 underwater buildings), `CorkScrewEffect`, `PredatorEffectNONPS2`.

**Static terrain is IN BRTR** — confirmed 2025-06-29. All terrain and environment geometry is placed as regular BRTR mesh instances with full world transforms. There is no separate BSP, heightmap, or hidden terrain container.

| BRTR Object Name Pattern | World Z range | Description |
|---|---|---|
| `Homokos_PartSzakasz_B03..B23` | −3908 to −4331 | Sandy shore tiles — main seafloor in tutorial area |
| `Homokos_Alpha_Szakasz_…` | ~−4100 | Shore tiles with alpha transparency |
| `szikla elem`, `szikla a`, `szikla a04/a05` | −3760 to −4534 | Rock formations (~908 tris each) |
| `Plane01` (×7), `Plane02` | −4004 to −4429 | Water surface / seafloor flat planes |
| `plane16` (×6) | ~−4100 | Small path/floor tile sections |
| `alap01`, `alapkieg` | ~−3904 | Terrain foundation / base layer mesh |
| `Kotelszakito_szikla` | ~−4534 | "Rope-breaking rock" — gameplay obstacle near pier |
| `molo04`, `molo05`, `molo_also`, `molo_felso` | ~0 | Main dock structure (lower/upper sections) |
| `kis_halaszhajo` | ~0 | Small fishing boat prop near pier |
| `seascooter-optimalized` | ~0 | Seascooter vehicle prop near pier |
| `HammerHead Headpart/Tailpart` | ~−4050 | Hammerhead shark mesh (creature) |

### Object Naming Convention — Hungarian

Content was authored at Appaloosa Interactive (formerly Novotrade, Budapest). Object names are in Hungarian:

| Hungarian | English |
|---|---|
| `szikla` | rock |
| `deska` | plank/board |
| `oszlop` | column/pillar |
| `koponya` | skull |
| `wrack` | wreck (English loanword) |
| `Torheto_pozna` | breakable post |
| `pierstores` | pier structure container |
| `fa` | tree |
| `fenyo` | pine tree |
| `feny` | light |
| `torzs` | trunk |
| `molo` | pier/dock |
| `molo_also` | lower dock section |
| `molo_felso` | upper dock section |
| `csonak` | boat |
| `korlat` | railing |
| `csolezaro` | boat barrier/blocker (seen in DEEPSEA.GDW) |
| `homokos` | sandy (terrain tile type) |
| `PartSzakasz` | shore/beach section |
| `alap` | base/foundation |
| `alapkieg` | foundation extension/supplement |
| `Kotelszakito` | rope-breaking (named gameplay obstacle) |
| `kis_halaszhajo` | small fishing boat |

## Scene Extraction Pipeline

### `scripts/rip_brtr_scene.py` — primary scene extractor

Run from the project root:
```bash
python3 scripts/rip_brtr_scene.py
```

Outputs to `scenes/`:
- `FISH_brtr.obj` — merged world-space geometry (15 MB), one OBJ group per placed object
- `FISH_brtr.json` — manifest of all 1161 instances, each with:
  - `node_id`, `name`, `mesh_id`, `mesh_idx` (index into `models/FISH/FISH_mesh_XXXX.obj`)
  - `xf` — full 12-float transform matrix
  - `pos` — world-space translation
  - `tris`, `vcols` (vertex colour count)

To change target GDW, edit `NAME = 'FISH'` at the top of the script.

**Known bug — false-positive `BRTR` tag match on some GDWs (found 2026-07-30, not yet patched into the script):** both `rip_brtr_scene.py` and `resolve_brtr_hierarchy.py` locate the `BRTR` chunk with a naive `data.find(b'BRTR')`, which on some files lands on a coincidental 4-byte `"BRTR"` match inside `RSRC` binary data instead of the real top-level chunk (same class of bug as the old `SCRT` false-positive — see that note above). Symptom: a nonsense declared size (e.g. `1,414,161,505`) and, in `resolve_brtr_hierarchy.py`, an `AssertionError: expected root PRPS at start of BRTR`. Confirmed affected: `KATATAMA.GDW` (previously documented, see M05 correction note below), `BEACH.GDW`, `BEACHPST.GDW`, `START.GDW` — likely more, not yet swept across all 20.
**Fix:** scan every `BRTR` occurrence, keep only candidates where `magic==0x01025024` (4 bytes after the size field), `root_count==1`, and the next tag is `PRPS`, then take the **largest** matching size — the real top-level scene chunk is always much bigger than the small embedded loading-screen sub-archives' own `BRTR` (see the "second embedded archive" note above), which also pass the magic/root_count/PRPS check but are a fraction of the size.
```python
candidates = []
pos = 0
while True:
    idx = data.find(b'BRTR', pos)
    if idx == -1: break
    sz = u32(data, idx+4)
    if idx+16 <= len(data) and u32(data, idx+8) == 0x01025024 and u32(data, idx+12) == 1 and data[idx+16:idx+20] == b'PRPS':
        candidates.append((sz, idx))
    pos = idx + 4
brtr_sz, brtr_pos = max(candidates)
```
Verified real offsets found this way: `BEACH.GDW` @ `0x6F93BA0` (size 6,648,364), `BEACHPST.GDW` @ `0x67CB268` (size 5,278,588), `START.GDW` @ `0x85E1298` (size 9,945,376). **TODO: patch both scripts with this fix properly** and re-sweep all 20 GDWs — any existing `*_brtr.json`/`*_resolved_hierarchy.json` for an affected file that predates this note may be wrong or incomplete.

### `scenes/import_fish_blender.py` — Blender import script

Paste into Blender's Scripting workspace and run. Imports each unique mesh from `models/FISH/` once (shared mesh data), then places 1161 instances with proper Blender object transforms. Objects are sorted into named collections (Player, Characters, Buildings, Rocks, Flora, Dock, Terrain, Collision, etc.).

**Coordinate conversion** — game (DirectX Y-up, left-handed) → Blender (Z-up, right-handed):

```
Blender X =  game X
Blender Y = -game Z
Blender Z =  game Y
```

As a matrix applied to the game's 4×3 world transform:
```python
# CONV @ game_matrix @ CONV_INV
CONV = Matrix([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]])
```

Mesh OBJs are imported with `-Z forward / Y up` (standard Blender Y-up OBJ convention), then `CONV @ M @ CONV_INV` is applied as the Blender world matrix.

**Viewport settings to apply after import:**
- Clip End: 20,000 (level spans ~4600 units)
- Scale: scene unit scale = 0.01 (game units are centimetre-scale)

### Live BRTR Editing — confirmed working (2026-07-16/17)

Beyond static extraction, `BRTR` can be **hand-edited and reloaded** by the actual game with predictable results — validated through a live edit-and-test loop against a running Proton install (backup-and-swap into the Steam install's `data/` directory; game re-reads a level's `.GDW` from disk on stage re-entry, no full process restart needed between edits).

**To cleanly relocate a placed static (non-physics) object**, patch two `PROP`s together, shifted by the same delta:
- `0x080017DA` (world transform) — the object's new position/orientation.
- `0x080017DF` (AABB) — **must** be updated to match, or the object's own AABB goes stale relative to its new transform. A stale AABB causes intermittent disappearing/culling *and* missing collision at the new location (both rendering and collision queries appear to use this AABB as a broad-phase spatial gate). With both fields kept in sync, relocation is clean: renders correctly, has correct collision, no fall/pop-in artifact. No `MREG` edit needed for objects without their own dedicated collision region.
- Editing the transform alone (leaving the AABB stale) is the most common mistake and produces exactly this failure mode — confirmed by direct A/B test on a large static mesh (`torzs`, a ship hull).

**Physics-eligible objects behave differently and this is correct, not a bug.** A physics/buoyant object (confirmed on `WhaleCarcass Body`, a boss-encounter rig) will visibly "drop" and resettle after an edit, *even for a pure horizontal move that doesn't touch Y*. This isn't an artifact of the edit pipeline — the shipped `Y` value in `BRTR` is simply the exact resting height the original level designers hand-placed for that specific `(X,Z)`; any edit that changes the effective location without also recomputing the true resting `Y` for the new spot leaves real gravity/buoyancy to visibly correct it. Static (non-physics) objects showed zero fall/drop when moved, confirming this is object-type-specific, not a general side effect of BRTR edits.

**Parent-child transform composition (see PROP `0x080017DA` note above) matters for reasoning about "where things are"**, not just for editing — a nested node's raw local-transform reading is frequently a red herring (e.g. reads near `(0,0,0)` regardless of true location) unless composed through the full ancestor chain via `scripts/resolve_brtr_hierarchy.py`. Learned the hard way while trying to locate objects by raw position during this experiment.

Full narrative (including several dead-end fixes tried and ruled out, and the discovery that `FISH.GDW`'s BRTR content is actually the SC17 "Mine All Mine" side-challenge instance) is preserved in memory; see also `mod/README.md`'s "XYZ Overlay Accuracy" section for a related but distinct investigation into reading live player position for this same purpose.

### Custom map feasibility (2026-07-17) — resource injection works, brand-new node insertion doesn't

Explored growing the archive itself (not just in-place editing) toward the goal of importing custom content. Two techniques are **confirmed working in-game**:

1. **Injecting a new resource.** Duplicate an existing `GMDL` block verbatim, patch only its mesh-ID field, append it to the end of `RSRC`'s payload (right before `BRTR`), and fix up `RSRC`'s size field, `FSIZ`, `SKIP` (recompute so `FDIR` stays 512-aligned — see `SKIP` note above), and the `FDIR` archive-2 offset entry (see FDIR note above) by the same inserted-byte delta. Repointing an existing `BRTR` node's `PROP 0x08001873` to the new resource ID renders it correctly — the game's resource loader does discover data appended into `RSRC` after original build time.
2. **Repointing/relocating existing nodes**, including **nested** ones. For a nested node, relocating to an arbitrary world position requires composing through the parent's transform (`new_local = parent_M⁻¹ @ (target_world − parent_translation)`, i.e. invert the parent's 3×3 rotation+scale basis), not just adding a translation delta — a plain delta only works for depth-0 (unparented) nodes. AABB shifts by the plain **world-space** delta regardless of nesting depth.

**Not working, unresolved:** appending a brand-new `CHBR` sibling node to `BRTR` itself (same size-field-cascade technique as above, applied to `BRTR` instead of `RSRC`) does not render in-game — tried 3 ways (out-of-range node_id, in-range node_id, and a verbatim byte-clone of a real working node with only mesh-ref/transform/AABB patched), all failing identically with no crash and no render, despite every build independently re-verified as structurally sound. Leading theory: some precomputed spatial/streaming index or node membership list, built at level-authoring time and not touched by these edits, gates which nodes the engine even considers loading — but this isn't confirmed, and a weak counter-signal (new node was placed well inside an already-densely-populated, currently-streaming cluster) argues against simple region-based gating. Static analysis is exhausted here; next step would be runtime instrumentation of the game via the `mod/` d3d8 proxy to directly observe `BRTR` node processing during level load. Full narrative in memory (`project_custom_map_feasibility`).

### Cut Objective — BEACH/BEACHPST Submarine + Blocking Boulders (found 2026-07-30)

User-reported anomaly: an underwater "drone" sits motionless under the bridge in `BEACH.GDW`/`BEACHPST.GDW` and never activates (unlike other similar drones elsewhere in the level, which move and chase the player), yet still drains player hunger on proximity. Investigation, prompted by the user recalling that `START.GDW` (M01 Tutorial) has a submarine which, when destroyed, blows up a boulder blocking the path and opens the next area:

**`TKSub` — a fully code-complete miniature attack submarine class**, found in the shared `CLAS` reflection registry (present in every GDW, so class presence alone doesn't prove a specific level uses it): `m_faster`/`m_slower` (speed), `m_maxyturn`/`m_turnaccel` (turning), `m_crab` (strafe), `m_libegamp` (hover/bob amplitude — "lebegő" = Hungarian "floating"), `m_MaxScooter`/`m_MaxDiver`/`m_MaxTorpedo` (damage thresholds by weapon type), `m_ShotPosID`/`m_ShotPos2ID` (torpedo firing points), `m_DiverID`/`m_DiverPosID` (carries a pilot diver), `m_RudderID` (destructible rudder), `m_BubblesID`/`m_DustID` (engine FX), `m_PropExplID` (propeller blows off on death), `m_ExplID`/`m_ExplActID`/`m_CompleteID`/`m_marker` (death sequence). It's referenced by a single resource-ID field (not a spawn list) from `MSScooter`, alongside `m_ScooterID` (player's seascooter), `m_RomboloID` ("Rombolo" = Hungarian for Destroyer ship), and **`m_TesztID`** ("Teszt" = Hungarian for "Test") — a field literally named "Test ID" sitting next to the sub reference is a strong signal this Scooter/Sub/Rombolo/Teszt group was a dev-time vehicle-mount test harness, not something uniformly finished across every level that references it. No CHBR node named "Sub"/"TKSub"/"submarine" exists anywhere in BEACH's or START's static `BRTR` scene graph — these vehicles are almost certainly mounted/spawned by that single ID reference at runtime (hardcoded mission C++), not individually art-named like a static prop, so the specific stuck instance can't be pinned down by name search.

**The mechanic is proven working in `START.GDW`.** A tight cluster at world pos ~`(535.6, -12.5, 23.5)`: `TunnelBlockingDust`/`TunnelBlockingRockDust` (literally "tunnel blocking rock dust"), `TunnelRoom` (the gated room, 17 units away), `FromStart2` (checkpoint marker), and a `LastSeaSeekerMissionBrick` mission trigger nesting `KoVizbeEsik` ("rock falls into water", Hungarian) and `TitokzatosKod` ("mysterious code"). `Szikla1 127` — one of ~200 generic numbered boulder props scattered through the level — sits directly on the dust marker and is almost certainly the actual blocking rock.

**`BEACH.GDW` has a matching, explicitly-named blocking-boulder group that never opens.** Searching for meshes placed in groups of exactly 3 near the bridge (bridge center ≈ `(-220, 20, 280)`, see `BridgeShooters`/`Bridge Spot` nodes) found:
```
Level3_elzarokovek   ("Level3 Blocking Rocks" — BEACH is internally named "Level3")
├── Elzaroko01  world (-343.5, -17.4, 338.6)
├── Elzaroko02  world (-342.4,  -2.9, 342.0)
└── Elzaroko03  world (-342.4, -15.2, 350.1)
```
"Elzáró" = Hungarian for "blocking/sealing/shutting off" — an explicitly-named, dedicated barrier group, ~140 units past the bridge. Each rock's mesh is ~16 units long (`models/BEACH/BEACH_mesh_0395.obj`) — a real boulder, not decoration. Right next to them (4 units) sits `Kizaro_Lap_Kozepes` ("Excluding Plate, Medium") — an invisible collision-blocker plate, the same mesh (`mesh_id 2394`) used elsewhere in the level as `LowTideBarrier`: a visual wall of 3 rocks *plus* an invisible hard collision stop, together forming a deliberate, reinforced dead end. The underwater canyon (built from 64 `Fal_alapkeszlet` modular wall-kit pieces, the same canyon the bridge crosses) continues for 200+ more units past the rocks, up to a rock breaching the surface around `Z≈570` — i.e. there's substantial, fully-built map geometry sealed behind this barrier, not a dead-end stub.

**BEACH vs. BEACHPST (the post-mission-state variant of this level) are byte-identical for this group** — same 3 rock positions, same structure (only the mesh_id numbering differs: 2557 vs 2506, consistent with per-file mesh-index renumbering of the same asset, not a state change). If this were a working "destroy to progress" objective, the post-mission variant should show the rocks already cleared. It doesn't — strong evidence this objective was never completed/wired up before shipping, in either mission state.

**Working theory (data-supported, not proven):** the inert submarine under the BEACH bridge and the permanently-sealed `Elzaroko` boulders are two halves of one abandoned objective — a "destroy the sub → blast open the canyon → reach the next area" sequence, mechanically proven to exist and work via the equivalent `TunnelBlockingDust` setup in `START.GDW`, that never got fully wired together in `BEACH`/`BEACHPST` before shipping. The exact causal trigger (sub kill → rock destruction) is almost certainly hardcoded in `Jaws.exe`'s mission C++, not data-driven, so it isn't provable from GDW data alone. No transition marker (`ToDocks`/`ToTown`-style) was found to confirm where the sealed canyon was meant to lead — worth checking `DOCKS.GDW`/`TOWN.GDW` for a matching `FromBeach`-style marker. Next step to go further: runtime instrumentation via the `mod/` d3d8 proxy to watch the sub and the `Elzaroko`/`Kizaro_Lap_Kozepes` objects live in-game.

**Independent visual corroboration, found 2026-07-30 (user-provided, user is the sole known extractor of this asset):** the in-game Amity Island overview map (`OPEN_NE.GDW`'s `gtex_0123_id000002e9_512x256_rgba32.png` — see the Texture Database section above; this is normal shipped UI content, not cut, only the *area it depicts* is in question) independently shows a distinct, rounded, lighter-toned landform in the island's interior, roughly inland from the BEACH coastal cove, connected to that cove by a visibly lighter, meandering break in the tree-canopy texture consistent with an artist's rendering of a stream. This lines up geographically with the sealed canyon's direction of travel and its terminus at the literal edge of BEACH's built geometry (see above). Caveat: this is a painted overview illustration, not literal terrain data — it's suggestive corroboration from an independent source, not proof by itself. The stronger evidence remains the GDW-side findings above.

## Class Namespace Conventions

The engine uses a prefix-based class registry:

| Prefix | Domain |
|---|---|
| `GD` | Generic engine / rendering (GDModel, GDLight, GDFog) |
| `NA` | Gameplay / shark systems (NAPredator, NABiteTarget, NAWayPoint) |
| `MB` | Mission / boat systems (MBMissionBrick) |
| `MS` | Menu / spawn / scenario (MSMissionGenerator, MSKatatamaMission) |
| `ML` | Lighting / effects |
| `mc` | Mesh collections (mcMeshCollection) |
| `X` | Skeleton / bone (XSkeletonModel, XBone) |
| `AN` | Action nodes / scripted behaviours (ANSideMission21, ANSharkMsg) |
| `BG` | Background / persistent mission state (BGSetMissionCompleted) |

## Game Content — Mission & Mode List

Source: `context.txt` (authoritative in-game list).

**Story Missions (11 total):**

| ID | Stage | Title |
|---|---|---|
| M01 | 1 | Tutorial *(also known as "The Arrival", set in Open Ocean)* |
| M02 | 2 | The Break Out |
| M03 | 3 | The Dead of Night |
| M04 | 4 | Hunted |
| M05 | 5 | Predator in the Bay |
| M06 | 6 | The Angry Armada |
| M07 | 7 | A Taste for Blood |
| M08 | 8 | The Deep |
| M09 | 9 | The Facility |
| M10 | 10 | Blood on the Beach |
| M11 | 11 | The Final Chase |

**Side Challenges (32 total):**

| ID | Title | ID | Title |
|---|---|---|---|
| SC01 | Barrels of Fun | SC17 | Mine All Mine |
| SC02 | Seal Whip | SC18 | Return to Sender |
| SC03 | Bay Patrol Blood Bath | SC19 | Get Mr. Stripes |
| SC04 | Dolphin Sightseeing Junket | SC20 | Losing Your Head |
| SC05 | Dog Gone | SC21 | Scavenge |
| SC06 | Flip the Bird | SC22 | The Gauntlet |
| SC07 | Reality TV | SC23 | Manic Maze |
| SC08 | Row Your Boat | SC24 | Catamaran Jam |
| SC09 | Sheebang! | SC25 | Oh Puppy |
| SC10 | The Bends | SC26 | Orca Revenge |
| SC11 | The Best Laid Plans | SC27 | Shark Frenzy |
| SC12 | Trouble and Strife | SC28 | Dolphin Frenzy |
| SC13 | To Kill a Killer | SC29 | Thar She Blows |
| SC14 | Undertow | SC30 | Deep Chase |
| SC15 | Up a Creek | SC31 | Lights Out |
| SC16 | Head Rush | SC32 | Swim for Life |

All 32 side challenges have been mapped to their implementation classes. Complete mapping in `docs/mission_system.md`. Summary:

| Class | SC# | | Class | SC# |
|---|---|---|---|---|
| `BarrelsOfFunMission` | SC01 | | `ANSideMission21` | SC20 |
| `SealWhipMission` | SC02 | | `ANSideMission22` | SC21 |
| `BayPatrolBloodBathMission` | SC03 | | `TheGauntletMission` | SC22 |
| `MSDolphinSightseeingMission` | SC04 | | `BGSideMission24` | SC23 |
| `MSDogGoneMission` | SC05 | | `ANSideMission25` + `MSKatatamaMission` | SC24 |
| `FlipTheBirdMission` | SC06 | | `OhPuppyMission` | SC25 |
| `BGSideMission8` | SC07 | | `MBSideMissionAQ` | SC26 |
| `BGSideMission9` | SC08 | | `FrenzyMission` | SC27+28 |
| `MBSideMission10` | SC09 | | `ANSideMission33` | SC29 |
| `TheBendsMission` | SC10 | | *(none found)* | SC30 |
| `MBSideMission12` | SC11 | | `BGSideMission31` | SC31 |
| `TroubleAndStrifeMission` | SC12 | | *(none found)* | SC32 |
| `MSKillKillerMission` | SC13 | | `OrcaExplorationMission` | M02 or cut |
| `ANSideMission15` | SC14 | | `KillthemallMission` | **CUT** |
| `UpACreekMission` | SC15 | | `MSHatchMission` | **CUT** "Down the Hatch" |
| `MBSideMission17` | SC16 | | | |
| `MSMineAllMineMission` | SC17 | | | |
| `BGSideMission19` | SC18 | | | |
| `GetMrStripMission` | SC19 | | | |

### GDW File — Mission Mapping

Source: `context.txt` (PS2 strategy guide) and direct observation. The three Open Ocean GDWs are free-play zones — each contains multiple story and side challenge areas. Story missions that are not accessible from Open Ocean after completion (`M09`, `M11`) have no confirmed GDW of their own.

| GDW | Mission / Area | In-game location name |
|---|---|---|
| `AQUARIUM` | M02 — The Break Out | South Shore Aquarium |
| `ARMADA` | M06 — The Angry Armada | Bridgeport Sound |
| `BEACH` | M10 — Blood on the Beach | Amity Town Beach / The Pond |
| `BEACHPST` | M10 — Blood on the Beach (post-mission state variant) | Amity Town Beach (post) |
| `CHASE` | M11 — The Final Chase | *(not revisitable from Open Ocean)* |
| `DEEPSEA` / `DEEPSEA2` | M08 — The Deep (two sub-areas) | ENVIRONPLUS Mining Site |
| `DOCKS` | M10 — Blood on the Beach *(probable)* | Amity Public Docks |
| `FISH` | Fisherman's Isle *(non-story area)* — **not the M05 mission space, see correction below** | Old South Beach Piers / Fisherman's Isle |
| `GAUNTLET` | SC10 + SC22 — The Bends & The Gauntlet | The Underwater Caves *(non-story area, Open Ocean: West)* |
| `KATATAMA` | **M05 — Predator in the Bay (confirmed 2026-07-15, corrected from FISH.GDW)** | Avril Bay — oil platforms, shipyard, power generator |
| `MINEMSHA` | **Grand Occasus Canals (identified 2026-08-12)** — SC15 Up a Creek | Named after the real Menemsha harbour on Martha's Vineyard from the 1975 film; BRTR contains 50 numbered `canal01`–`canal50` segments + 35 `canal_f01`–`canal_f35` variants + `fog canal 1/2/3` volumes — a fully-built dedicated canal level, not shared with `OPEN_NW` (which lists "Grand Occasus Canals" as accessible but has no such object set of its own) |
| `OPEN_NE` | Open Ocean: East free-play zone | Bridgeport Sound, Amity Town Beach, Coast Guard HQ, South Amity Cliffs, Cable Junction, Crater Pass, Brody's House, Eastside Homes |
| `OPEN_NW` | Open Ocean: West free-play zone | Grand Occasus Harbor, Grand Occasus Canals, Water Ski Park, The Underwater Caves, ENVIRONPLUS Mining Site, North Amity Keys, Amity Swamp |
| `OPEN_S` | Open Ocean: South free-play zone | Red Reef Valley, Seal Island, Misty Ridge, South Shore Aquarium, South Beach Cove, Old South Beach Piers, Fisherman's Isle |
| `START` | M01 — The Arrival (Tutorial) | Red Reef Valley / The Arrival *(Open Ocean: South)* |
| `TITLE` / `TITLE0` | Main menu / title screen | *(TITLE0 has 0 meshes)* |
| `TOWN` | M10 — Blood on the Beach *(probable)* | Amity Town / town area |
| `WRACK` | M07 — A Taste for Blood | Misty Ridge *(Southeast island, Open Ocean: East/South boundary)* |

**Correction (2026-07-15) — M05 is in `KATATAMA.GDW`, not `FISH.GDW`:** Extracting `KATATAMA.GDW`'s BRTR scene (`scripts/rip_brtr_scene.py`, `NAME='KATATAMA'` → `scenes/KATATAMA_brtr.json`/`.obj`) surfaced `DrillingPlatform 1/2/3` (with `autogun_uw_laser_gun`, `Laser Autogun Root`, `OilRig LOD`), `PowerPlant 1` + `Ventillator`, `OilTank`/`OilTank_Darab*` debris, the `cutter_FIN_V2_opt_FIN_JAV_tores` Coast Guard Cutter (intact/`_rombolt`-destroyed variants), and `AURORA_LO0` — i.e. the complete Avril Bay mission set from the M05 walkthrough (3 oil platforms, shipyard power generator with two feed columns, Coast Guard Cutter, Aurora II). `FISH.GDW`'s BRTR, by contrast, contains none of this — it's pier/dock structures, beach houses, and tourist NPCs (Fisherman's Isle content only), confirming it is not the M05 mission space despite the earlier mapping. `KATATAMA.GDW`'s BRTR chunk has a corrupt/implausible size field (reads as ~1.3GB against a 151MB file) — the parser still recovers usable data by reading until EOF rather than trusting the size, but treat the KATATAMA scene extraction as unverified for completeness (some tail content past the corruption point may be missing).

**Checked for cut content in KATATAMA (2026-07-15), none found:** exactly 3 `DrillingPlatform` groups exist (matches shipped "three in all"); the 35/923 GMDL mesh indices never placed by BRTR are small props and `_normal`/`_serult` damage-state variants (destruction-mechanic assets swapped in by code, not orphaned level geometry); `StageWreckQuest` (M05's quest class — confirmed via `m_scubadivers` field matching the shark-cage divers) and `MSKatatamaMission` (single `m_PreyID` field, likely an unrelated side-mission hunt target) showed no unused/dead fields comparable to the confirmed cut missions below. This doesn't rule out a cut area — nested BRTR parent transforms aren't resolved to world space yet (see Parent-child hierarchy open problem), so a spatial gap-hunt across the full level hasn't been done.

**Correction (2026-08-12) — `MINEMSHA.GDW` is Grand Occasus Canals (SC15 Up a Creek), not an unknown location:** user-supplied identification, verified against BRTR content — see table row above. This also resolves part of the cut Hot Pursuit mission investigation (see Cut Content section, which has the full merged writeup — "Pursuit" and "Jet Ski Mission" were the same mission, official title "Hot Pursuit"): that mission's leftover objects (`JetskiChase`, `jetski_mountpoint`/`_a`, `jetskipath`, `ccjetski`) are concentrated almost exclusively in `MINEMSHA.GDW` (vs. the usual all-20-GDWs shared-asset-pool pattern), and `StagePursuitQuest2`'s gate fields — previously unexplained for an open-water chase — make much more sense as canal lock/sluice gates. A second, independent site was also found in `OPEN_NE.GDW`: a bare `HOTPURSUIT` anchor marker sitting near the `Brody's House` map location, which in-game has no house actually built at it. `Lighthouse02` lives in `OPEN_NE.GDW` too but ~4,270 units from that marker, not adjacent — so the "near the lighthouse" mission-goal framing still doesn't fully reconcile with either site. Not fully resolved; see `docs/mission_system.md` and `docs/ps2_cut_content_findings.md` for the full writeup.

### Named In-Game Locations — Mission Cross-Reference

| In-game name | Mission | Open Ocean zone |
|---|---|---|
| Red Reef Valley / The Arrival | M01 Tutorial | Open Ocean: South |
| South Shore Aquarium | M02 The Break Out | Open Ocean: South |
| South Beach Cove | M03 The Dead of Night | Open Ocean: South |
| Grand Occasus Harbor | M04 Hunted | Open Ocean: West |
| Old South Beach Piers / Avril Bay | M05 Predator in the Bay | Open Ocean: South |
| Bridgeport Sound | M06 The Angry Armada | Open Ocean: East |
| Misty Ridge | M07 A Taste for Blood | Open Ocean: East (SE boundary) |
| ENVIRONPLUS Mining Site | M08 The Deep | Open Ocean: West (North) |
| The Facility | M09 The Facility | *(inside M08 area; not revisitable)* |
| Amity Town Beach / The Pond / Amity Public Docks | M10 Blood on the Beach | Open Ocean: East |
| *(open ocean)* | M11 The Final Chase | *(not revisitable)* |
| Fisherman's Isle | SC17 Mine All Mine | Open Ocean: South *(non-story)* |
| Grand Occasus Canals | SC15 Up a Creek | Open Ocean: West *(non-story)* — dedicated GDW is `MINEMSHA.GDW` (see GDW File — Mission Mapping table above) |
| The Underwater Caves | SC10 The Bends + SC22 The Gauntlet | Open Ocean: West *(non-story)* |
| North Amity Keys | SC23 Manic Maze | Open Ocean: West (far North) |

### Shared Assets Across GDWs

The engine bundles a **common asset pool into every GDW** — meshes, textures, and props accessible from any level are duplicated into all 20 archives rather than stored in a separate global file. This is why 911/1049 unique texture IDs appear in multiple GDWs.

**Identifying true cut/unused content:** An asset appearing in all GDWs does not mean it was used in all levels or that it is cut content. The BRTR scene graph controls what is actually placed — an asset is only active in a level if a CHBR node references it via PROP `0x08001873`. To determine whether a shared asset is used vs. unused in a given level, check its mesh resource ID against the BRTR instance list for that GDW.

**Example — "Free the Shark" signs:** These assets appear in all 20 GDWs (shared pool) but are intentional level dressing used only in `AQUARIUM.GDW` (M02 — The Break Out), where Jaws escapes from an aquarium and protesters with signs are set dressing outside the facility. Their presence in other GDWs is engine bundling, not cut content.

### Cut Content — Missions and Areas

Identified by searching `game_binary/Jaws.exe` for strings and class names not present in the shipped game. All findings below are from the PC binary.

**Cut missions:**

| Name | Evidence | Notes |
|---|---|---|
| **Down the Hatch** | `MSHatchMission` class; string `" -, Down the Hatch (unused!)"` in stage select list; objective text `SWALLOW %d COLLECTABLES WITHIN %d SECONDS.` | Side challenge where Jaws must swallow a set number of spawned collectables before the timer expires. Three difficulty levels via `m_EasyNum`/`m_MediumNum`/`m_HardNum` and matching time limits. Uses the shark's built-in swallow animation (same mechanic as shipped SC22 The Gauntlet, which uses `COLLECT %d TIRES`; "Down the Hatch" is the simpler, earlier version — no ships or seekers, just eat-items-in-time). Not instantiated in any GDW's BRTR; cut before level placement. |
| **Hot Pursuit** *(cut story stage, not side content — corrected 2026-08-12, was catalogued as two separate entries "Jet Ski Mission" + "Pursuit")* | Official title confirmed via PS2 exe (`SLUS_210.62`) stage-name string table, sitting between "Blood on the Beach" (M10) and "The Final Chase" (M11). Implemented by `StagePursuitQuest`/`StagePursuitQuest2`/`...QuestEvent` (`m_JetSkiIDList`, `m_JetSkiBossIDList`, `m_GateIDList`/`m_GateOpenPosIDList`/`m_GateClosePosIDList`/`m_GateOpenerIDList`, `m_OnBossFight`, `m_PursuitLostDist`). **Confirmed a cut STORY mission, not a cut side challenge, on two independent grounds:** (1) its classes use the `Stage*Quest` naming convention shared by every other real story mission (`Stage0Quest`, `StageBeachQuest`, `StageDeepSeaQuest`, etc.) — completely distinct from the side-challenge naming grammar (`...Mission`, `ANSideMission#`, `BGSideMission#`, `MBSideMission#`); (2) it sits interspersed directly in the numbered M01–M11 sequence in the PS2 stage list, not grouped with the free-roam zone/side-area names clustered at that list's tail. Likely occupied one of `MSStageSelect`'s 7 unused stage slots (18 total, 11 shipped), probably as M11, pushing the shipped "The Final Chase" mission down a slot. Goal text: *"Locate the jet skiers near the lighthouse and stop them from reaching the home of Amity Police Chief Candy Wilson."* Failure: *"The jet skiers have escaped!"* Plus a typo'd duplicate objective line, `"Destroy all the jets kis!"`, sitting next to the correct `"Destroy all the jet skis!"`. **Note: Candy Wilson is not the boss.** `m_JetSkiBossIDList` (a *list*, i.e. tougher enemy jet-ski riders) and `m_OnBossFight` describe a separate boss-fight segment within the chase — Candy Wilson only ever appears in the text as the person/house being protected, never as a combat target. **Real placed content found in two GDWs, not just code stubs:** (1) `MINEMSHA.GDW` (= Grand Occasus Canals, see below) has `JetskiChase`/`jetski 1`/`jetskipath` clustered within ~3 world units of each other at `(-1254, 0, -787)`, plus `jetski_mountpoint`/`ccjetski` unique to this file — and a jet ski with an NPC stuck in A-pose (bind/rest pose) reproducibly spawns at this exact spot in the shipped PC game. (2) `OPEN_NE.GDW` has a bare, dimensionless anchor node literally named `HOTPURSUIT` (world `(612.5, 0, 3626.4)`, no mesh, AABB min==max) sitting ~338 units from the `Brody's House` map-UI marker (world `(929.7, 0, 3508.8)`) — and in-game, that map location has no house built there at all, consistent with a mapped mission-endpoint that was cut before its building was placed. `Lighthouse02` also lives in `OPEN_NE.GDW` but ~4,270 units away, not adjacent — so the "near the lighthouse" framing doesn't fully reconcile with either site yet. Gate fields (previously unexplained for an open-water chase) make sense as canal lock/sluice gates given the Grand Occasus Canals connection. |

**Cut character:**
- **Candy Wilson** — Amity Police Chief. Referenced only in the Hot Pursuit mission text (all five languages, exactly 5 occurrences total — not duplicated per quest class). No class name, scene placement, or mesh anywhere in any of the 20 GDWs, including `MINEMSHA.GDW` itself (confirmed 2026-08-13) — but her house's intended location may be identified: see the `Brody's House` empty-lot finding under Hot Pursuit above. Her mission text sits inside a large shared "mission goals" localization pool used by many missions' briefing screens (unrelated M08/M09 text sits immediately adjacent), so static analysis can't confirm whether `StagePursuitQuest`, `StagePursuitQuest2`, or both reference this specific string at runtime. Note "Brody" itself is a separate, real (non-cut) character elsewhere in the game — an animated skeleton with Aurora/Coast Guard cutscene clips (`MBrody_AuroraComesMovie`, `MBrody_GrabHarpoonMovie`, etc.) tied to `KATATAMA.GDW`'s M05 content — so "Brody's House" as a map label is not itself cut content, it's just sitting empty at the spot the cut mission also anchors a marker to.

**Cut / unused map areas:**

Both names appear in the in-game map location string table (at binary offset `0x490010` and `0x4900C0`) alongside all shipped area names, but are absent from the shipped game and the PS2 strategy guide:

| Name | Position in string table | Notes |
|---|---|---|
| **HIGHLANDS BAY** | Between ENVIRONPLUS MINING SITE and BRIDGEPORT SOUND | Likely Open Ocean: East or a bay area. No GDW filename match. |
| **DOLPHIN PASSAGE** | Between AMITY ISLAND and OLD SOUTH BEACH PIERS | Likely Open Ocean: South. Could relate to dolphin-themed side challenges (SC04, SC28) or be a renamed area. |

**Stage slot evidence:**
The `MSStageSelect` data structure contains fields `m_Stage1ID` through `m_Stage18ID` — 18 stage slots total. The shipped game has 11 story missions. The 7 extra slots (stages 12–18) were likely reserved for cut story missions. Named stage quest classes that do not map to shipped missions: `StagePursuitQuest/2`, `StageDocksQuest` (DOCKS.GDW has its own dedicated quest stage).

**ANSideMission internal numbering gap:**
The five shipped `ANSideMission` classes map to display SC numbers as follows: class 15 → SC14, class 21 → SC20, class 22 → SC21, class 25 → SC24, class 33 → SC29. Classes 15/21/22/25 are all exactly 1 higher than their display number. Class 33 maps to SC29 (offset of 4), meaning **classes 26–32** existed internally but were removed — at least 3 cut side challenges in that range, compressing the display numbers from 25 onward. "Down the Hatch" (`MSHatchMission`) likely occupied one of those removed slots. See `docs/mission_system.md` for the full mapping table.

### "Sole Predator" — original working title

*Sole Predator* was the game's original working title during development at Appaloosa Interactive (formerly Novotrade, Budapest), before Majesco licensed the Jaws IP and agreed to publish the game. The title change happened during production; the shipped build is *Jaws Unleashed*.

The string "Sole Predator" **does appear** in extracted textures as promotional/marketing copy describing the game's boasted features — early promotional assets baked into the build that survived the title change. It is **absent** from mission names, class names, mode names, and script strings — the rename was applied consistently to the code/data namespace but not to all texture assets.

## Audio System

Two audio chunk types are fully extracted. All scripts output to `audio/`.

### GSMP (Game Sample) — `scripts/rip_gsmp.py`
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
  [secondary header 20 bytes: magic, field, sample_rate, byte_count, pad]
  [raw PCM audio: byte_count bytes, signed 16-bit mono]
```

The "category" field read at the standard offset is actually the OBPR size (20), not a real category. Sample rate and byte count come from the secondary header at `pos + 16 + 8 + obpr_size`.

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

### Lead: long-duration `GSMP` cat2 "SFX" samples may be the missing story dialogue (found 2026-07-29, unconfirmed — needs a human to listen)

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

**Source for the two previously-undocumented files above (2026-08-02):** `game_binary/unins000.exe` + `unins000.dat` (the original Inno Setup uninstaller pair, added to `game_binary/` by the user) contain a complete installer file manifest — confirmed our 20 extracted `.GDW` files exactly match the shipped set (nothing missing/extra), and surfaced `FLUX.WMV`/`INF.WMV` as shipped `movie\` files not previously in this table. Their audio (`audio/wmv/FLUX.wav`, `INF.wav`) was already extracted, just unlabeled/uncatalogued until now.

### Missing: In-Game Cutscene Voice Acting
The game has in-game cutscenes driven by the `NACutScene` engine class alongside `MPGPlay` / `StreamPlay` objects. Voice acting heard during these sequences has **still not conclusively been located**, but see the SMPB correction and long-duration `GSMP` lead above (2026-07-29) — SMPB is confirmed in-use (not cut) but appears to be short crowd/reaction barks rather than full dialogue; a short list of unusually long, per-level-unique `GSMP` cat2 samples were flagged as a candidate lead for story dialogue, but the top candidate (`BEACH_id0590`/`BEACHPST_id0579`, 44.58s) was listened to and is a diegetic song (beach radio), not dialogue — so duration + per-level-uniqueness alone is not reliable evidence of speech, and the rest of the list is unconfirmed and now lower-confidence. Ruled out this session: no external audio middleware (checked for FMOD/Miles/Wwise — none present; `fmod` string in the binary is the C runtime `fmod()` math function, a false lead; `DSOUND.dll` is just standard DirectSound) and no separate movie/bank file format (`MPGPlay`'s `m_fname` field and `%s.WMV` format string confirm cutscene video is exclusively the already-extracted WMV files; `GDSoundEventScope`'s `m_AW_Resource`/`m_UW_Resource` fields are Above-Water/Under-Water reverb variants, not an external bank reference). Remaining possible locations:
- Unknown chunk types in RSRC not yet decoded
- `BRTR` non-mesh CHBR nodes with `Audio` prefix names (1621 non-mesh nodes include audio source objects) — not yet cross-referenced against the GSFX sample IDs above
- Possibility that regular (non-cutscene) story dialogue was never voiced at all — only the big pre-rendered WMV cinematics (INTRO/SHARK/OUTSCENE/PSYCHO) got real VO, with in-engine `NACutScene` sequences relying on subtitle text only. Not ruled out.

## PS2 Version Data — `.GDE` Files

`GAME_GDWs/_FISH.GDE` is asset data pulled from the **PlayStation 2 ISO** of Jaws Unleashed — the PS2-side counterpart to the PC `.GDW` files, not a PC development build (an earlier read of this file misidentified it as a small/early PC dev snapshot; corrected after confirming its origin).

**Container format is identical to PC `.GDW`:** same 44-byte preamble (`GDED BINARY FORMAT, VERSION 2.6.3.16.\r\n\r\n\x00\x00\x00`), same top-level chunk-walk (`[4-byte tag][uint32 size][payload]`, each chunk padded to a 4-byte boundary before the next tag). Confirmed top-level chunks in `_FISH.GDE`: `FSIZ, VERS, EXBY, GNRL, WDIM, RSPR, CLAS, RSRC, BNCH, BRTR, SCRT, SKIP, FDIR, ENDF`. Once the PC `.GDW` top-level chunk-walk was corrected (see `SCRT` note above), it turns out the layouts match almost exactly — the PC file has `RSPR`, `SCRT`, and `SKIP` too (they'd been missed because earlier scans stopped enumerating after `BRTR`). The **only** PS2-exclusive top-level chunk is `BNCH` (163 KB — a master name dictionary, see below). `_FISH.GDE` is much smaller than the PC file (16.7MB vs 131MB; RSRC 12MB vs 111MB; BRTR 2.5MB vs 5.4MB), consistent with PS2-resolution/PS2-budget assets rather than missing content.

**Internal resource sub-formats differ from PC and are PS2-native** (Emotion Engine / Graphics Synthesizer, VIF/GIF pipeline — see Project Overview note that the PC build uses DX8 instead of the PS2 pipeline):

- **Textures (`GTEXT`) — FULLY DECODED (2026-07-08), `ZIPN` is not compression:** PS2 `GTEXT` blocks wrap pixel data in an `OBPR`/`PROP` metadata sub-block (prop_id `0x04000030`, type tag `TEXB`) followed by a `ZIPN`-tagged payload. Despite the name, `ZIPN` is **not compressed data** — it's native PlayStation 2 Graphics Synthesizer (GS) pixel storage, the same byte layout the PS2 hardware DMAs directly into VRAM. All 4 formats seen in `_FISH.GDE` were reverse-engineered and visually verified by rendering to PNG (see `scripts/rip_gtext_ps2.py`):
    - **Header layout** after the 5-byte `GTEXT` tag + 3-byte pad (tag offset +8): `[+0x00 uint32 texture_id][+0x04 uint32 unknown-constant][+0x08 OBPR{ PROP{ prop_id=0x04000030, type="TEXB", value } }][+0x24 uint32 datestamp][+0x28 uint32 unknown][+0x2C uint32 width][+0x30 uint32 height][+0x34 uint32 bpp][+0x38 ZIPN tag+size][+0x40 ZIPN sub-header: uint32 remaining_size, uint32 width, uint32 height, uint32 format, uint32 unknown=1][pixel data]`. (Earlier notes had `texture_id` and the unknown field swapped — corrected: the *first* field increments per-texture, 49 unique values confirmed across the file; the second field was a red herring, constant `0xA1` in the first batch sampled.)
    - **Pixel format** = `format field & 0xFFFF`, matching documented PS2 GS `PSM` constants exactly:
      - `0x00` = **PSMCT32**: 4 bytes/pixel, straight RGBA8888, raster order (no swizzle). Verified: decoded a 32×32 sample to a clean UI glyph (letter "N").
      - `0x02` = **PSMCT16**: 2 bytes/pixel, RGBA5551 (bit15=A, bits14-10=R, bits9-5=G, bits4-0=B), little-endian uint16, raster order (no swizzle). Verified: decoded a 64×64 sample to a clean sky/clouds texture, and a 1024×512 sample to a fully legible "Open Ocean - South / Loading..." screen.
      - `0x13` = **PSMT8**: 8-bit palettized. Payload = `[256-entry palette][W×H index bytes]`. Palette is RGBA (4 bytes/entry, 1024 bytes total) when the format field's bit 16 (`0x10000`) is clear, or RGB-only (3 bytes/entry, 768 bytes total, alpha implicitly 255) when that bit is set. **Index bytes are GS-swizzled**, not raster order — see `unswizzle8()` in the script for the standard public PS2 8-bit-texture de-swizzle algorithm (block/column/byte decomposition). Verified on both palette variants: decoded to clean circular UI reticle icons.
    - **False positives:** 6 of the 55 raw `GTEXT` string matches in `_FISH.GDE` are not real chunks — coincidental substring matches where `"GTEXT"` appears as the tail of an unrelated field immediately followed by `REFL`/`BUMP` (GMAT material sub-chunks). Detectable because `data[base+8:base+12] != b'OBPR'`. 49 of 55 matches are real textures.
    - **Extraction script:** `scripts/rip_gtext_ps2.py` — set `name` to the `.GDE` filename stem. Outputs to `textures/<NAME>_PS2/gtext/`. Ran clean on `_FISH.GDE`: 49/49 extracted, 0 failures.
- **Meshes (`GMDL`) — DECODED (2026-07-08), numerically validated:** PS2 `GMDL` blocks use an extended chunk hierarchy with extra wrapper tags (`MTYP`, `MATS`, `SSET`) not present in the PC format, and a **triangle-strip** index format instead of the PC's triangle-list `VIND`. Dedicated extractor: `scripts/rip_meshes_ps2.py` — extracted 293 real meshes from `_FISH.GDE` (vs. 3 with the naive PC-format parser). Chunk order: `GMDL[12-byte sub-header] → MTYP(4) → MATS(12, contains a literal "GMAT" ASCII value as a type discriminator, same self-referencing-value pattern as `BRTR`'s `PROP 0x08001873`, not a real nested chunk) → SSET(92, undecoded) → STRP → STTA(undecoded) → VERT[container: uint32 vertex_count, then POSS → NORM → UVUV]`.
  - **`VERT`/`POSS`/`NORM`/`UVUV`:** `VERT` is a container exactly like the PC format (leading `uint32` vertex count, then sub-chunks). `NORM` (unit-length float32 XYZ, verified) and `UVUV` (float32 UV pairs, verified) are byte-identical in format to PC. **`POSS`** (PC's equivalent is `POSI`) is different: **quantized**, not flat float32. Layout: `[float32 scale][N × (int16 x, int16 y, int16 z, int16 w)]` — real position = `int16_component * scale`. The `w` component observed as only `0` or `INT16_MIN` in samples — likely a flag/pad field, not position data, unconfirmed. Verified by decoding and checking values are small/bounded/symmetric (consistent with local mesh-space coords), not by rendering.
  - **`STRP` (triangle strip + flags) — the index buffer:** `[uint32 count][count × uint16 entries]`. Each entry: bit 15 = flag, bits 0–14 = vertex index, **except** the sentinel value `0x7FFF` (all 15 index bits set) which marks a **strip break** — split the entry stream into sub-strips at every `0x7FFF`. Real per-texture vertex indices within a sub-strip are sequential in most observed samples (vertex buffer is pre-ordered to match strip traversal), so `STRP` mostly just reconstructs strip boundaries + winding flags rather than arbitrary reordering.
  - **Strip → triangle conversion (numerically verified to 100% on a clean test mesh, 77–100% across 12 diverse meshes):** for sub-strip position `i` (triangle uses vertices `strip[i], strip[i+1], strip[i+2]`), the winding flip decision is `flip = (i % 2 == 0) XOR flag_of(strip[i+2])` — i.e. standard strip winding alternation, XORed with the flag bit of the *newly entering* vertex. Triangles whose 3 positions are collinear/near-identical (cross-product magnitude below a small threshold) are **degenerate strip-connector triangles** and must be dropped, not written to the mesh — real strip export commonly repeats a vertex to "jump" between disconnected strip segments, producing zero-area filler triangles.
  - **Validation method:** computed each candidate triangle's face normal via cross product and compared (dot product) against the average of its 3 vertices' stored `NORM` vectors — a purely numeric check requiring no visual tooling. This caught both the winding rule (mismatches dropped from 30% to 0% once the flag-XOR rule was found) and the degenerate-triangle issue (mismatches were exactly the near-zero-area triangles).
  - **Unresolved:** `SSET` (92 bytes) and `STTA` (96 bytes) sub-chunks are present in every mesh but not decoded — likely per-strip metadata (texture/material assignment per segment, or smoothing groups) given `STTA`'s content looked like a secondary small index table. `POSS`'s `w` component meaning is unconfirmed. `MATS`'s embedded value (e.g. `1034`) likely references a `GMAT` resource ID but the exact linkage isn't confirmed.
- **`SCRT` (screen overlay tree):** present and structurally identical in principle (`PRPS`/`CHBR`/`PROP`, same format as PC — see `SCRT` note in GDW Archive Format section), but the PS2 copy is smaller (8,772 bytes vs PC's 12,576), has 14 `CHBR` children instead of 20, and none of its nodes have the `0x080017D8` name property set (all unnamed) — its property-ID range (`0x08001957`–`0x0800196A`) is shifted from but parallel to the PC's (`0x08001980`–`0x08001993`).
- **`BNCH` (master name dictionary + transform table, decoded 2026-07-08):** PS2-exclusive top-level chunk (163 KB in `_FISH.GDE`; zero occurrences anywhere in PC `FISH.GDW`). Layout: `[8-byte header: uint32 build timestamp (20060316 = 2006-03-16), uint32 secondary size = payload_size-8][~101.8 KB record array][small trailer with 0xFF-filled gaps and a few count fields][~58 KB null-terminated string pool]`.
  - **Record array:** fixed-size **80-byte records** (~1,272 of them) — stride confirmed empirically by periodicity of `[1.0,1.0,1.0,1.0]` marker vec4s (206 occurrences found; dominant gap 80 bytes, all other gaps clean multiples of 80). Working field hypothesis per record: `[vec4 A: scale/color multiplier, often all-0 or all-1][vec4 B, C, D: 3×3 basis/rotation matrix rows][vec4 E: position]` — i.e. a PS2 VU-padded version of the same world-transform concept the PC format stores compactly as 12 floats / 48 bytes (`BRTR` PROP `0x080017DA`), expanded here to 16-byte-aligned vec4 rows (5×16=80 bytes) for VU register loading, plus an extra leading multiplier field the PC layout doesn't have. **Not fully confirmed** — plausible but unverified against known world-space values.
  - **Open question:** record count (~1,272) does not match the string pool's name count (3,495), so the exact correspondence between a transform record and its name is unresolved — likely only a subset of named objects have transforms here (or there's an indirection/index table not yet found).
  - **String pool:** fully decoded. A flat, deduplicated list of **3,495 null-terminated object/entity names** (mesh instances, quest/script markers like `Stage0Quest`/`ch2_intro_moviestarter`, spawn generators like `ShrimpGen1`) — critically, its final 15 entries are the exact same names as `SCRT`'s `"Screen"` overlay tree (`Whale`, `WaterSurface`, `TransparencyAbove/Below/Blur`, `ReflectionAbove/Below/Blur`, `ScreenWater/Above/Below`, `MotionBlur`, `ZZZ`, `XXX`), proving `BNCH` is a **shared name-interning table**: PS2 stores each object name once here and references it by index/offset elsewhere, instead of embedding the string inline per-node like the PC format does (explains why PS2 `SCRT` nodes have no inline name property).

**Status: textures fully decoded and extractable (`scripts/rip_gtext_ps2.py`, 49/49); meshes decoded and extractable (`scripts/rip_meshes_ps2.py`, 293 real meshes, geometry numerically validated); `SCRT` and `BNCH`'s string pool are fully readable; `BNCH`'s transform record array has a confirmed stride but unverified field semantics.** Remaining PS2-track open items: `BNCH`'s numeric-record field semantics and its mapping to the name pool, and the `SSET`/`STTA` `GMDL` sub-chunks (likely per-strip material/smoothing metadata). Worth pursuing further for cross-platform comparison — the PS2 build may preserve different or cut content than the PC build — but treat as a separate reverse-engineering track from the PC `.GDW` pipeline documented above.

## Key Investigation Commands

```bash
# Find texture blocks
grep -oba "GTEXT" GAME_GDWs/FISH.GDW

# Find class/reflection metadata
grep -oba "NABiteTarget" GAME_GDWs/FISH.GDW

# Hex inspect at offset
xxd -s 0x06FB5000 -l 4096 GAME_GDWs/FISH.GDW

# Find DDS texture headers (alternate embedded format)
grep -oba "DDS" GAME_GDWs/FISH.GDW

# Search for a string across all GDWs and the executable
grep -rioab "search_term" GAME_GDWs/ game_binary/
```

## Open Problems

- **Static environment geometry** — ~~terrain not found~~ **RESOLVED (2025-06-29)**: all terrain tiles, rocks, water planes, and dock structures are present in BRTR as named mesh instances (see Scene Layout table). No hidden BSP or heightmap. The water surface at the pier area (Z~0 cluster) may still use runtime geometry — check `Plane01/02` instances.
- ~~**Skeletal animation**~~ **RESOLVED (2026-07-17)**: `SKEL`/`BONE`/`WGHT`/`ROTS`/`BROT`/`MTOB`/`CHLD`/`ANIM` fully decoded — bind mesh, per-vertex weights, recursive bone hierarchy, and per-bone quaternion keyframe streams sliced into named clips by `ANIM`. Extractor `scripts/rip_skeletons.py` verified clean on all 30 of FISH.GDW's skeletons. See Skeletal Animation System section. Still open: the undecoded pre-`VERT` blob, `TRAN`'s role, and Blender armature/animation import (mesh-only import exists, no skinning wired in yet).
- ~~**Parent-child hierarchy**~~ **RESOLVED (2026-07-16)**: nested `CHBR` nodes store transforms LOCAL to their parent, not world space. World position = compose the full ancestor chain (`world = parent_world ∘ local`, standard affine composition: `R_world = R_parent @ R_child`, `T_world = R_parent @ T_child + T_parent`), starting from the root "World" `PRPS` node (which itself carries an identity transform in FISH.GDW). Nesting is physical — a child `CHBR` sits inside its parent's payload after the parent's own `PRPS` block, not merely cross-referenced via `PROP 0x080003C7`. Validated on `FISH.GDW`: resolved node count (2782) exactly matches the known flat-scan `CHBR` tag count; a nested `WhaleCarcass Body` group (raw local pos reads near (0,0,0), a red herring) resolves to world pos `(60, -20, 105)`, exactly matching a separate top-level `Kis_Halaszhajo` (small fishing boat) cluster and a family of ship-sinking FX/audio nodes (`NewEffectShipSinking_above`, `SndShipExplo`, `boat_crash`, etc.) at the same coordinates — confirmed against in-game observation that the whale carcass sits right at the small boat/pier area. Also incidentally confirmed `FISH.GDW`'s BRTR *is* the SC17 "Mine All Mine" side-challenge instance (nodes named `MineAllMine Mission Shark 1-4`, `SideMissionRemainingTimeTextModel`, `You Have X PointS` all resolve to the same world region). Extractor: `scripts/resolve_brtr_hierarchy.py` → `scenes/<NAME>_resolved_hierarchy.json` (per-node name, resolved world_pos, local_pos, mesh_id, parent_id, depth). `rip_brtr_scene.py`'s flat local-position reads remain accurate only for top-level (`depth=0`) nodes; nested-node positions from it should be treated as unresolved/local, not world space, until re-run through the new resolver.
- **In-game cutscene voice acting** — still not conclusively found, but progress 2026-07-29: `GSFX` sound-trigger blocks fully decoded (see Audio System section), proving SMPB samples are NOT unused/cut as previously claimed — all are actively triggered, just appear to be short crowd/reaction barks. A short list of unusually long (7–44s), per-level-unique `GSMP` cat2 "SFX" samples was flagged as a lead, but the top candidate turned out to be a diegetic beach-radio song, not dialogue (user-confirmed by listening) — so this lead is weaker than initially thought; remaining candidates (esp. `TOWN_id0109`–`id0112`, 4 consecutive resource IDs) are still unconfirmed. External audio middleware and a separate movie-bank file format are both ruled out. (Ruled out: `SCRT` — see below, resolved and it's not audio-related.)
- ~~`SCRT` scripting chunk (obfuscated)~~ **RESOLVED (2026-07-08)**: not obfuscated, not scripting. The offset previously cited was a false-positive tag match; the real `SCRT` is a small top-level `PRPS`/`CHBR`/`PROP` tree (same format as `BRTR`) holding named screen-space overlay objects (`GDScreen`, water reflection/transparency layers, motion blur). See the `SCRT` note in the GDW Archive Format section.
- **Unknown PROP IDs** — `0x080017DB`–`0x080017E4`, `0x08001874`–`0x0800187B`, and (new, from `SCRT`) `0x08001980`–`0x08001993` / PS2's `0x08001957`–`0x0800196A` seen on CHBR nodes; most meanings not yet determined (see PROP ID table above for partial decode).
- ~~`SKIP` chunk undecoded~~ **RESOLVED (2026-07-08)**: pure sector-alignment padding (`0xFF`-filled, pads to a 512-byte boundary before `FDIR`). See `SKIP` note in GDW Archive Format section.
- ~~`BNCH` chunk undecoded~~ **MOSTLY RESOLVED (2026-07-08)**: PS2-only master name dictionary (3,495 interned object names in a string pool) plus an 80-byte-stride transform record array (~1,272 records, tentative field layout — unverified). Open: how the ~1,272 transform records map to the 3,495 names. See `BNCH` note in PS2 Version Data section.
- **Texture–mesh linkage** — TSET texture IDs are resolvable via `textures/texture_db.json` (1,049 IDs mapped, 65 are runtime render targets). Blender material assignment (loading PNG files onto mesh UV maps) not yet implemented. TSET layer semantics (exact role of each val_A–val_D per layer) not fully decoded.
- **GMAT `TEXP` ↔ TSET linkage** — `TEXP` sub-chunks inside GMAT reference GTEX texture IDs; TSET records reference the same IDs. The exact relationship between GMAT (material parameters) and TSET (layer assignments) per mesh is not yet mapped.
- **MREG `MOIL` content** — the large (~66 KB) `MOIL` sub-chunk inside `GMOA` blocks is undecoded. May contain AI pathfinding graph data or NPC navigation mesh.
- **Brand-new BRTR node insertion silently fails to render** — see "Custom map feasibility" note above. Resource injection into `RSRC` and repointing/relocating existing `BRTR` nodes both work; appending an entirely new, structurally-valid `CHBR` sibling to `BRTR` does not appear in-game (3/3 attempts, no crash). Cause unknown — candidates are a precomputed spatial/streaming index or a node membership list/count consulted before individual `CHBR` parsing, neither located yet. Next step would be runtime instrumentation via the `mod/` d3d8 proxy rather than further static analysis.
- **BRTR false-positive tag offset affects multiple GDWs beyond KATATAMA** — see the note under `rip_brtr_scene.py` above. Confirmed on `KATATAMA`, `BEACH`, `BEACHPST`, `START`; fix identified (scan for `magic==0x01025024`/`root_count==1`/next-tag `PRPS`, take the largest match) but not yet patched into `rip_brtr_scene.py`/`resolve_brtr_hierarchy.py`, and the other 16 GDWs haven't been swept to check if they're affected too.
- **Cut objective — BEACH/BEACHPST submarine + blocking boulders, not confirmed** — see "Cut Objective" note above. Strong circumstantial evidence (named `Elzaroko`/`Level3_elzarokovek` blocking-rock group + matching invisible barrier, unchanged between BEACH and BEACHPST mission states, a fully-built canyon sealed behind it, and a proven working precedent of the same "destroy something → clear boulder → open room" mechanic in `START.GDW` via `TunnelBlockingDust`) but the causal trigger linking a `TKSub` kill to the boulders' destruction is not present in any GDW's static data — it's presumed hardcoded in `Jaws.exe`. Needs runtime instrumentation (`mod/` d3d8 proxy) to confirm, and `DOCKS.GDW`/`TOWN.GDW` haven't been checked for a matching transition marker on the far side of the sealed canyon.
- **Cut mission — Hot Pursuit, location confirmed across two GDWs but full scope not pinned down** — see Cut Content section above for the full writeup. `MINEMSHA.GDW` (Grand Occasus Canals) has a tightly-clustered jetski chase/spawn/path node group, live-reproducible in the shipped game as a broken A-posing NPC. `OPEN_NE.GDW` independently has a bare `HOTPURSUIT` anchor marker near the `Brody's House` map location, confirmed in-game (2026-08-12) to have no house actually built there. Still open: the mission-goal text's "near the lighthouse" framing doesn't reconcile with either site (`Lighthouse02`, also in `OPEN_NE.GDW`, is ~4,270 units from the `HOTPURSUIT`/`Brody's House` cluster); whether the mission spanned both GDWs as one sequence or represents two different development-time concepts isn't confirmed; the causal/scripted trigger logic is presumed hardcoded in `Jaws.exe`, same caveat as the BEACH submarine finding above.

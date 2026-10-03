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

**Correction (2026-10-03): "GTEXT" is not a tag, and "GTEXT"/"GTEX" are not two texture systems.** Walking `RSRC` as a chunk chain shows every texture is a plain `GTEX` chunk (FISH: 321). "GTEXT" is just the `GTEX` tag followed by the size field, whose low byte is `0x54` (`'T'`) for most 24-bit sizes (e.g. 512×512×3 + 0x54 = `0x000C0054`). The two real variants differ in the payload: **plain** (258 in FISH: `[id][flags 1][stamp 0x0131F253][0][w][h][bpp]` then `TGAN`; what `rip_textures.py` calls GTEXT) and **with an `OBPR`** property block carrying a `TEXB`/`TEXH`/`TEXD` type tag (63 in FISH: `[id][flags 0x21]OBPR…[stamp][0][w][h][bpp]TGAN`; what `rip_gtex.py` handles). The offsets below still hold for the plain variant. Full layout and the generator that writes new textures: `docs/brtr_editing.md` "Custom textures".

Textures use the `GTEXT` marker (see the correction above: this is `GTEX` + size). Confirmed header layout:

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
  MATS  [variable] material list: [uint32 n] + n × ['GMAT' tag][uint32 gmat_resource_id], one per TSET submesh
  GMAT              material definitions (GMAT1, GMAT2 sub-entries)
  TSET  [variable] triangle sets (submeshes): vertex/triangle ranges, one per MATS entry — see format below
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
- **Handedness: the game is DirectX LEFT-handed; OBJ/Blender are right-handed. Exports negate Z and keep the original `VIND` order (2026-10-01; this supersedes the 2026-08-17 winding-swap entry below).** The game's axes are X right, Y up, Z forward. Proof from the data: the shark model's right fin (`Jobb…` = Hungarian "right") sits at local +X, the dorsal fin at +Y, and the head at +Z, which is only "right" in a left-handed system. Writing raw coordinates into a right-handed format **mirrors** everything, and no rotation can undo a mirror. That was the long-parked "levels look flipped/mirrored" bug: the old Blender `CONV` (X=x, Y=−z, Z=y) and Blender's OBJ importer are both rotations (determinant +1). Fix: `rip_meshes.py` and `rip_brtr_scene.py` write `(x, y, −z)` for positions and normals, and faces in **original** `VIND` order. Verified numerically on 2,363 FISH triangles: in Z-mirrored space the original order's cross-product normals agree with the stored `NORM` data 2,307/2,363, and the old b↔c swap agrees 8/2,363 (the 2026-08-17 swap was only right for raw, un-mirrored data). `scenes/import_fish_blender.py` now uses `CONV` = (X=x, Y=z, Z=y), determinant −1, plus a `FLIP_Z` on the local side: `matrix_world = CONV @ game_world @ FLIP_Z`. The scene OBJs import correctly with Blender's **default** OBJ settings (forward −Z, up Y). Manifest `xf`/`pos` values stay in raw game coordinates. All 20 GDWs' `models/` and `scenes/` were regenerated with this. **User-confirmed correct in Blender (2026-10-01).**

### TSET Format — triangle sets, not textures (corrected 2026-10-01)

```
TSET [uint32 payload_size]          payload_size == (1 + N*5) * 4
  [uint32 N]                         number of submeshes (== MATS count on 383/384 FISH meshes)
  N × [set_idx][first_vert][vert_count][first_tri][tri_count]
```
Record `i` covers triangles `first_tri … first_tri+tri_count−1` of the `VIND` list (and vertices `first_vert…`), and is drawn with material `MATS[i]`. The starts are running sums of the counts (e.g. `(0,0,204,0,186)`, `(1,204,24,186,16)`, `(2,228,46,202,36)`), and the `tri_count`s add up to the mesh's triangle total on all 384 FISH meshes.

**Correction:** this section previously described TSET as texture-layer assignments ("val_A–val_D contain texture IDs"). That was wrong: those values are vertex/triangle counts and offsets. Everything built on that reading was based on coincidental ID collisions, including the 2026-08-17 textured scene export (the rock "referencing a black render target, a caustic texture AND a grass decal" was just vertex counts landing on unrelated texture IDs) and the "65 render-target IDs" claim.

**Texture binding (decoded 2026-10-01):** `GMDL.TSET[i]` ↔ `GMDL.MATS[i]` → GMAT resource block (`['GMAT'][size][uint32 id][uint32 flags]['OBPR']…`, elsewhere in RSRC) → its `TEXP` sub-chunk `[uint32 n] + n × ['GTEX' tag][uint32 texture_id]`. The first entry is the base texture; extra entries are further layers (e.g. FISH material 692 has two). Implemented in `scripts/gdw_materials.py`. **Look textures up only in the same GDW**, since IDs collide across GDWs. Same-GDW coverage: FISH 93% of triangles textured, OPEN_S 96%, TOWN 95%. The rest are materials with no TEXP (3–5%), flat render targets (<0.5%), or 74 OPEN_S triangles whose texture isn't stored in that GDW. Verified visually by rendering in Blender: the great white (5 submeshes → textures 72–77, the shark skin atlas), the whale carcass (bloody blue-whale hide), and the FISH pier area (grassy seafloor, wooden piers, painted fishing boat).

### GMAT Material Sub-Chunks

Each `GMAT` block contains a full material definition as a sequence of small named sub-chunks (all confirmed via sliding-window scan of RSRC). Every sub-chunk follows the standard `[4-byte tag][uint32 size][payload]` format:

| Tag | Size | Description |
|---|---|---|
| `TEXP` | 8n+4 | Texture binding — `[uint32 n]` + n × `['GTEX' 4-byte tag][uint32 texture_id]`; first entry = base texture (corrected 2026-10-01, see TSET Format) |
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

### STRI — triangle order (decoded 2026-10-03)

```
STRI [uint32 size]
  [uint32 m]               ← = the mesh's triangle count
  [m × uint32]             ← a permutation of the mesh's triangle indices (VIND order)
```

### BVH layout — fully decoded (2026-10-03, all 123 FISH MREGs)

- `BREG` is a binary tree in **heap order**: node 0 is the root, node k's children are 2k+1 and 2k+2. It has `n = 2L − 1` nodes, where **L = max(1, ⌊triangles ÷ 4⌋) leaves**.
- Leaves are taken in **in-order traversal** (left subtree, then right), and each owns the next run of `STRI`: **4 triangles per leaf**, with the 1–3 leftover triangles (when the count isn't a multiple of 4) going into a single leaf. Where that leaf sits isn't determinable from the data. `obj_to_gmdl.py` avoids the question by padding meshes to a multiple of 4 triangles.
- Every leaf box is the exact AABB of its triangles; every internal box is the exact union of its children. Boxes are in **mesh-local** space, so a node's transform carries them.
- Header flags `0xFFFFFFFF` = "has data" (the loader `FUN_006e3cb0` reads `PERF`/`BREG`/`STRI` only when that field is negative). `PERF` = 0.25 in all FISH MREGs.
- Engine loader: `FUN_006e3cb0` (MREG class vtable `0x7F79A0`; `+0x20` PERF, `+0x24`/`+0x30` box count/array, `+0x28`/`+0x2C` STRI count/array). It stores no leaf ranges, so the query code recomputes them.
- Collision meshes (122/123) also carry per-triangle `TNOR` = **−normalize((B−A) × (C−A))** in raw game coordinates (46,153/46,153 shipped triangles) and `TFLG` (8 bytes per triangle: `[uint32 1][uint16 flags][uint16 n]`; the low 3 flag bits look like per-edge flags, and `0x47` = all set is what the generator writes).
- **Generated collision works in-game** (user-confirmed 2026-10-03): `obj_to_gmdl.py --collision` + a node with a `PRIM` pointing at the new region. See `docs/brtr_editing.md`.

### MREG ↔ BRTR Relationship

Of the 123 MREG blocks in FISH.GDW:
- **118 mesh_res_ids** match GMDL meshes that are **also placed as visual instances in BRTR** — rocks (`szikla`), sandy shore tiles (`Homokos`), foundation meshes, etc. each have both a visual BRTR placement AND a collision MREG.
- **5 mesh_res_ids** have MREG collision data but **no BRTR visual instance** — collision-only geometry not rendered.

The `mesh_res_id` in MREG matches the **first uint32 of the 12-byte GMDL sub-header** (same linkage as PROP `0x08001873` in BRTR). GMDL mesh indices for the MREG-referenced meshes in FISH.GDW span approximately idx 23–262.

## Skeletal Animation System — SKEL / BONE / WGHT / ROTS / ANIM

**Fully decoded (2026-07-17).** Each `SKEL` block is one complete skeleton (one per skinned character/creature mesh) — bind-pose reference mesh, per-vertex bone weights, a recursive bone hierarchy, and (if the skeleton has named clips) a shared quaternion keyframe pool sliced by an animation dictionary. **Correction:** earlier docs listed `SKEL` count as 3,030 — the real count is **30** (an accidental doubling of the true figure; it now matches the `BONE`/`WGHT` counts below, all of which describe the same 30 skeletons). `ROTS`/`MTOB`/`CHLD`/`BROT` counts below are likewise per-bone-node totals across all 30 skeletons, not top-level RSRC entries.

**Skinning math solved and Blender import working (2026-10-03).** Several of the 2026-07-17 readings below were wrong; corrected from `Jaws.exe` and verified numerically: skinning each skeleton's `VERT` mesh with frame 0 reproduces its shipped `GMDL` mesh to float precision (≤ 1.5e-6) for **all 30 FISH skeletons**. **All 20 GDWs re-extracted (2026-10-03): 752 skeletons** (`python3 scripts/rip_skeletons.py NAME`); 740 of the 741 with a placed mesh verified the same way. The exception, START `SKEL 2424`, is a 3-vertex animation placeholder sharing its mesh with `SKEL 2430` (which matches). The other 11 have no scene user and are all one rig: a 25-bone, 275-vertex **low-detail scuba diver** (AQUARIUM `SKEL 2547` ↔ unplaced `GMDL 3653` / `AQUARIUM_mesh_0821`, frame-0 match 5.6e-7) in 11 levels, sharing 10 of 11 textures with the placed `NewScuba` diver (839 verts). Either an unused LOD or the older diver `NewScuba` replaced; not determinable from the data.
- **`BROT` = next sibling, `CHLD` = first child** (bone loader `FUN_006F4F00`: `CHLD` → `+0x38` with this bone as parent, `BROT` → `+0x3C` with this bone's parent). The old extractor nested `BROT` as a child.
- **`MTOB` = inverse rest matrix** (mesh → bone space); the bone's rest pose is `inverse(MTOB)`, where the `VERT` mesh lives. **`TRAN` = local translation** relative to the parent. **`ROTS` = local rotation per frame, transposed:** `local = [R(q)ᵀ | TRAN]` with `R` the standard `(x,y,z,w)` matrix.
- `world = parent_world · local`; `skin = world · MTOB`; `v' = Σ wᵢ skinᵢ v` (pose `FUN_006F5600`, skinning `FUN_006F63F0`). **Frame 0 is the pose baked into the `GMDL` render mesh.**
- Bone indices (WGHT) follow the engine order: root, then each bone's sibling chain before its child (`FUN_006F46D0`/`FUN_006F5140`).
- **The pre-`VERT` blob is decoded:** `[u32 version][u32 frame_count][u32 morph_frame_count if version > 0x13130F1][frame_count × vec3 root-motion deltas][frame_count × vec3 running position if version ≥ 0x1317CBA]`. Optional `MORF` chunk = vertex-animation frames (none in FISH).
- **Model ↔ skeleton link:** the scene node's `PROP 0x080018FF` = `['SKEL'][id]` next to its `0x08001873` mesh (FISH `GWside` → `SKEL 1766` + `GMDL 1890`).
- **Human bodies have no clips of their own:** the 75 human animations live in `GlobalSkeletonAnim` (`SKEL 1770`, a 51-vertex placeholder); all human rigs share its 24-bone layout.
- **Blender:** `blender -b --python scripts/import_skeleton_blender.py -- --name FISH --skel 1766 [--anim-skel 1770] [--save out.blend]` (or run in Blender's text editor with `CONFIG`). Builds armature + textured skinned mesh + one action per clip, with optional root motion; Blender's deformation matches the engine math to 3e-6 (checked over 6 shark clips). Bones are unnamed in the data (`bone_00`…).

Extractor: `scripts/rip_skeletons.py` (run from project root, set `NAME` to the target GDW stem) → `skeletons/<NAME>/skel_<id>.json` (one file per skeleton: bind mesh, weights, full bone tree with per-bone rotation keyframes, named clips) + `_summary.json`. Verified clean on `FISH.GDW`: 30/30 skeletons parsed with zero false positives; spot-checked 729 quaternions across all skeletons — 728 are unit-length to within 1%, all named-clip frame ranges fall within their skeleton's shared frame-pool bounds.

### Known chunk types

| Tag | Count (FISH) | Description |
|---|---|---|
| `SKEL` | 30 | Skeleton container — one per skinned character/creature mesh, 54 KB–1 MB each |
| `BONE` | 30 | Root bone of each skeleton's hierarchy — a recursive container (see below), not a single leaf |
| `WGHT` | 30 | Per-vertex bone skinning weight table, one per skeleton — fully decoded, see below |
| `VERT`/`NORM` | 30 each | Bind-pose reference mesh (positions + normals) embedded in each `SKEL`, sized to match that skeleton's `WGHT` vertex count |
| `ANIM` | ≤30 (optional per-skeleton) | Named animation-clip dictionary — present only on skeletons with authored clips (e.g. shark: 73 clips; many prop/creature skeletons have 0) |
| `MTOB` | 718 total (one per bone node, all skeletons) | **Inverse rest matrix** (mesh → bone space), 4×3 float32 column-major like PROP `0x080017DA` (corrected 2026-10-03; was read as a local transform) |
| `TRAN` | one per bone node | **Local translation** relative to the parent bone (corrected 2026-10-03), typically `(0, length, 0)` |
| `ROTS` | one per bone node | Per-bone stream of unit quaternions (`x,y,z,w`, 16 bytes each), one frame per shared skeleton-wide frame pool — **this is the actual keyframe animation data** |
| `CHLD` / `BROT` | 548 / 140 total | `CHLD` = first child, **`BROT` = next sibling** (shares the current bone's parent). Same payload grammar as `BONE` (corrected 2026-10-03) |

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
  MTOB [48]   ← inverse rest matrix: 3×3 basis (col-major) + translation
  TRAN [12]   ← local translation relative to the parent bone
  ROTS [N×16] ← N unit quaternions (x,y,z,w), one per frame of this skeleton's
                shared pool (every bone in a skeleton has the same N)
  [CHLD = first child, BROT = next sibling (corrected 2026-10-03), same grammar]
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

**NPC human animations** (the 75 clips of `GlobalSkeletonAnim`, `SKEL 1770`, shared by all 24-bone human rigs; corrected 2026-10-03): `BeingDevouredLegs_A01/02/03`, `FrightenedRun`, `GetOut`, `GrThrow`, `Harpoon`, `icRun`, `Run2x`, `Walk2x`, `FatWalk2x`, `PanicRun`, `SharkAvoid2x`, `StandCheer3x`, `StandClap4x`

### Still open

- Bone names (none stored; the importer uses `bone_00`…).
- How the engine binds a body to `GlobalSkeletonAnim`'s clips at runtime (the importer just takes rotations from the clip skeleton and `TRAN` from the body's), and the engine's playback rate (importer assumes 30 fps).
- The second per-frame track's exact role, the `ANIM` header's second word, and `MORF` vertex animation (not seen in FISH).

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
    [uint32 class ID]           ← e.g. 0x0107402F = plain model brick (rocks, props), 0x0106F06E = flora; not a constant magic (2026-10-03, see "Blank base level" in docs/brtr_editing.md)
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
| `0x080017D9` | Object flags (`m_nFlags`) — `0x2` enabled, `0x100` **not rendered** (invisible blockers), `0x10`/`0x40` "active in world" (clearing at runtime removes visibility and collision), `0x20000` suspended, `0x20000000` absolute transform; `0x1` = killed at runtime (see GDControl below) | uint32 |
| `0x080017DA` | World transform | 12 float32s — column-major 4×3 (see below) |
| `0x080017DB` | `m_ExecFilter` (name from reflection table, see note below) | uint32 |
| `0x080017DC` | `m_CameraFilter` | uint32 |
| `0x080017DD` | `m_Viewport` — render-pass mask; `1` = above-water only, `0x20003` = above + underwater (both user-confirmed) | uint32 |
| `0x080017DE` | Unknown flag | uint32 |
| `0x080017DF` | AABB bounds | 6 float32s: minX minY minZ maxX maxY maxZ — **world space** |
| `0x080017E3` | Unknown | uint32 |
| `0x080017E4` | Unknown | uint32 |
| `0x08001873` | Mesh reference | 8 bytes: `[uint32 "GMDL" tag][uint32 mesh_resource_id]` |
| `0x08001874` | `m_DynamicLights` | uint32 |
| `0x08001875` | `m_StaticLights` (e.g. `0x1000009`; `0` on hidden render-layer companions) | uint32 |
| `0x08001876` | `m_RenderSetting` (`0x40000800` walls, `0x820` sand; `0x40000400`/`0x40002400` = hidden companion layer; `0x80000920` = seaweed alpha cut-out, `0x200820` = blended sand overlays) | uint32 |
| `0x08001877` | `m_ExtRenderSetting` | uint32 |
| `0x08001878` | `m_ChannelSetting` | uint32 |
| `0x08001879` | `m_ModelColor` — colour scale | 4 float32s (RGBA multiplier, usually 1.0) |
| `0x0800187A` | Per-vertex colour data | uint32 vert_count + vert_count × 16 bytes (RGBA float32 per vert) — **baked lighting** |
| `0x0800187B` | Unknown | uint32 |
| `0x080003C7` | Child node ID list | uint32 count + count × uint32 node_ids |

**Field names (2026-10-03):** PROP IDs' low bits are each field's global registration index in `Jaws.exe`'s reflection table (`scripts/dump_class_fields.py`), plus a small offset that drifts because the dump misses a few registrations, so names can be read off by neighbourhood. Details in `docs/brtr_editing.md`.

**`PRIM` sub-chunk = collision link (2026-10-03):** a `CHBR` node may carry a `PRIM` chunk after its `PRPS` (class `0x20003002`, its own `PRPS` with `PROP 0x080018D8` = `['MREG' tag][uint32 region_id]`), linking it to its `MREG` collision region. 598 in FISH. `MREG` is mesh-local, so a copied `PRIM` follows the node: an inserted wall carrying its template's `PRIM` blocks the shark at its new position, and one without a `PRIM` can be swum through (both user-confirmed 2026-10-03).

**Mesh reference clarification:** PROP `0x08001873` first uint32 is literally the ASCII tag `GMDL` (= `0x4C444D47`) stored as a type discriminator, not an "unknown" field. Second uint32 = mesh resource ID matching the first uint32 of the GMDL 12-byte sub-header.

**Class-specific PROP IDs (decoded 2026-08-13, `BSCollectibleGameObject`):** in addition to the generic `0x080017Dx`/`0x08001873` engine-wide fields above, individual gameplay classes have their own PROP ID ranges for class-specific fields, found by matching the class's field-name list in `Jaws.exe`'s reflection strings (`BSCollectibleGameObject.m_Template..m_AutoYPlacement....m_AutoY_Offset..m_myid`) against a live node's raw PROP IDs, in declaration order:

| ID | Field | Meaning |
|---|---|---|
| `0x080004A1` | `m_Template` | uint32 — BRTR node ID of this instance's `BSCollectibleGameObjectTemplate` (the shared `"NN - ItemName"` reference/template node — see Collectible System note below) |
| `0x080004A2` | `m_AutoYPlacement` | uint32 (bool) — auto-snap to ground height flag |
| `0x080004A3` | `m_AutoY_Offset` | float32 — vertical offset applied on top of auto-placement |
| `0x080004A4` | `m_myid` | uint32 — per-level sequential instance ID (shared across all collectible categories in that GDW, not per-category — e.g. in `WRACK.GDW`, License Plates use IDs 1–5, Tin Cans 6–9, the Diamond Necklace is 10) |

The sibling class `BSCollectibleGameObjectTemplate` has its own fields (`m_DisplayName`, `m_TypeIndex`, `m_AllCount`, `m_RareItem`, `m_RegenerationMode`, `m_AddOn` — PROP IDs not yet individually mapped) — `m_TypeIndex` is almost certainly the `"NN"` catalog number seen in every template node's name (`"06 - Diamond Necklace"`, `"10 - Trident"`, etc.), `m_AllCount` the total-instances-in-game figure quoted in reward text (e.g. `"45 license plates hidden throughout the story locations"`), and `m_RareItem` a bool distinguishing single one-off finds (Diamond Necklace, Trident, Pirate Ship, Body Bag, Mermaid, Nautilus, Mask — generic `"YOU HAVE FOUND A %s"` reward text) from per-level counted sets (License Plate, Tin Can — dedicated `"...THERE IS %d MORE..."` reward text). See `docs/cut_content.md` ("Cut collectible category — Trident only") for the full category catalog and cut-content finding, and `docs/mission_system.md` for complete detail.

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

**Objects at the world origin (found 2026-10-01, user-observed in-game via F8 teleport to `0 0 0`):** `OPEN_S.GDW` has a starfish (`Starfish02`, at `(0, 0, 0.14)`) and `FISH.GDW` has a small piece of floating wood (best match: `debris1` under `Floater1_Brown`). The starfish was first read as a deliberate origin marker, but it's a **reference template** (6 placed starfish point at it via `PROP 0x080017F0`, see "Reference instancing" below) that also renders at its authored position. Most origin-authored templates (FISH's 72×-referenced buoy template, civilians, fish, weapon models) do *not* appear at the origin in-game, so whether a template renders at its own position is per-object, not a rule. Details in `docs/terrain_and_water_bounds.md`.

### Reference Instancing, Absolute Transforms, and Mission Relocation (decoded 2026-10-01)

Three placement rules beyond plain nesting. All three are implemented in **`scripts/brtr_scene_graph.py`**, which `rip_brtr_scene.py` and `resolve_brtr_hierarchy.py` now share:

1. **Reference instancing: `PROP 0x080017F0` = target node ID** (a base-brick field present on every node, 0 = none). The reference node places a **copy of the target's whole subtree**, with **"replace" semantics**: the copy's root takes the reference node's own world transform, the target's own transform is ignored, and the target's descendants compose beneath it as usual. Evidence: OPEN_S `Starfish01` (authored at y −27.6) and its 10 references. Replace puts every copy at seafloor depth (y −28 to −33), compose would bury them at y −55 to −61, and each reference carries its own random rotation. FISH's pier `molo` (authored at dock height y 3.59) and its 12 references at y 3.4–4.3 agree. References nest (templates containing references, like KATATAMA's `TRef*` grid of `ope*` seafloor clusters). Scale: FISH 130 reference nodes → 1,591 copied nodes; OPEN_S 539 → 37,082. The most-copied template everywhere is the ~140-node `Civilian` NPC rig (21–94× per level).
   - **Templates still exist at their authored spot** (usually the origin). In-game, *some* render there (OPEN_S's origin starfish, a piece of wood at FISH's origin) but most don't (FISH's 72×-referenced buoy template, civilians, fish), so it's per-object. Exports keep them, flagged `is_template`.
2. **Absolute transforms: node flags (`PROP 0x080017D9`, `m_nFlags`) bit `0x20000000`** means the node's transform is **already world space**, and the parent is ignored. This matches the engine's world-matrix updater (`Jaws.exe` `0x696EA0`), which skips parent composition when brick flag `0x20000000` is set. Example: FISH's `fenyo` pine trees and their `Box0N` foliage-card children (flags `0x2000005A`). Composing those through the parent sent them ~7,400 units away. FISH has 738 nodes with the flag (92 of them nested).
3. **Mission relocation: `MSMineAllMineMission.m_WhaleID` (`PROP 0x08000AE5`)** on `MineAllMine Mission Root` (FISH, at (2021, 0, −3827)) positions the whale's top-level node `WhaleCarcass MorePrim` **relative to the mission root** ("compose" semantics: whale world = root world ∘ whale authored local). The whale is moved, not copied. Verified in-game: predicted (2081, −20, −3722), and the user teleported there and landed against the carcass. Sibling fields: `m_SharksID` (`0x08000AE6`, a list of 5 shark node IDs), `m_Easy/Medium/HardSharkNum` (`0x08000AE7–9`, 5/7/10), `m_Easy/Medium/HardWhaleDeadHurt` (`0x08000AEA–C`, 14.0/10.0/6.0). This is the only mission relocation implemented. Other mission classes may link objects the same way and aren't handled yet.

**Known limitation:** OPEN_NE's `LeisureOverlay` template (referenced once, by `LeisureOverlayRef 1`) has crew references authored ~6,000 units from the template origin, so its copy lands off-map (150 placements beyond ±12,000). It's probably a runtime-attached group (e.g. a crew on a moving boat). Not resolved. Copies of multi-variant templates (e.g. `Civilian`, which contains every tourist body type and its LOD meshes) also emit every variant overlapping, where the engine shows one.

### Mesh–Object Linkage

PROP `0x08001873` second uint32 = mesh resource ID. This matches the **first uint32 of the 12-byte GMDL sub-header** (the mesh's resource ID). Use this to link a CHBR scene object to its GMDL geometry.

The sequential OBJ file index (`FISH_mesh_XXXX.obj`) corresponds to the order GMDL blocks are encountered during a linear scan of the GDW — not the resource ID directly. `rip_brtr_scene.py` builds the `resource_id → mesh_idx` mapping at runtime.

### Scene Layout — FISH.GDW

Coordinate system is DirectX Y-up (Y = height). World extents of real (non-template) mesh placements after the 2026-10-01 instancing/composition fix: X −240 to 2917, Y −226 to 3457 (the top is the `NEW_SKY_OPEN` sky dome), Z −4879 to 193.

**Correction (2026-10-01):** this section used to describe "two spatial clusters", with a **pier/dock cluster at the world origin**. That was wrong. The origin "cluster" is **reference templates**: the pier `molo`, breakable posts `Torheto_pozna`, the small fishing boat `Kis_Halaszhajo`, buoys `BolyaDefOpen`, the civilian rig, fish and weapon models, plus the SC17 mission's whale/sharks authored in mission-local coordinates. They're placed in the real play area by reference nodes or the mission root (see "Reference Instancing" below). For example, the 12 real pier copies sit at y 3.4–4.3 around (1810–2006, −4010 to −4110). FISH is essentially **one area**, around (1600–2900, −3600 to −4900), containing the pier/dock, the rocks (`szikla`), wrecks (`wrack`, `torzs`), the skull (`koponya`), alpha overlays (`interalph`), mansions (`mansionC`), the cadillac, and the whale carcass at (2081, −20, −3722).

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

**Textures:** scene OBJs use per-submesh `usemtl` from MATS → GMAT → TEXP with same-GDW textures (see TSET Format), with materials in `scenes/<NAME>_brtr.mtl`.

**Re-extracted 2026-10-01 with the scene-graph fix** (nested composition + absolute-transform flag + reference instancing + whale relocation; see "Reference Instancing…" in the Scene / Object System section). Mesh placements per GDW: AQUARIUM 6,119 · ARMADA 4,429 · BEACH 3,442 · BEACHPST 1,841 · CHASE 730 · DEEPSEA2 3,940 · DEEPSEA 3,917 · DOCKS 3,877 · FISH 1,610 · GAUNTLET 1,201 · KATATAMA 6,152 · MINEMSHA 3,765 · OPEN_NE 9,940 · OPEN_NW 11,251 · OPEN_S 16,234 · START 6,273 · TITLE0 0 · TITLE 226 · TOWN 7,789 · WRACK 2,256. Zero bad-geometry skips. `scenes/` grew from 632 MB to 3.3 GB. Manifest (`<NAME>_brtr.json`) entries now carry a **world** `xf`/`pos` plus `depth`, `via_ref` (reference node that placed this copy, or null), `is_template`, and `relocated_by`. OBJ object names get `@ref<id>` for copies and a `TEMPLATE__` prefix for template spots. `<NAME>_resolved_hierarchy.json` entries gained `absolute_xf`, `ref_target`, `is_template`, and `relocated_world_pos`.

`OPEN_S`/`OPEN_NE`/`OPEN_NW` are the three largest scenes by a wide margin, consistent with being the big free-roam Open Ocean zones; `TITLE0` remains an 8-node menu stub with zero placed mesh instances, matching its already-documented 0-mesh status elsewhere in this file.

Re-extraction command (same loop pattern as the `rip_gtex.py`/`rip_textures.py` all-GDW loops earlier in this file, run from project root):
```bash
for name in AQUARIUM ARMADA BEACH BEACHPST CHASE DEEPSEA2 DEEPSEA DOCKS FISH GAUNTLET KATATAMA MINEMSHA OPEN_NE OPEN_NW OPEN_S START TITLE0 TITLE TOWN WRACK; do
    python3 -c "
import re; from pathlib import Path
script = Path('scripts/rip_brtr_scene.py').read_text()
script = re.sub(r\"^NAME\s*=.*\$\", \"NAME = '$name'\", script, flags=re.MULTILINE)
exec(compile(script, 'rip_brtr_scene.py', 'exec'))
"
done
```

**Locating `BRTR`:** a naive `data.find(b'BRTR')` lands on a coincidental match inside `RSRC` in 8 GDWs (`BEACH`, `BEACHPST`, `KATATAMA`, `OPEN_S`, `START`, `TITLE`, `TITLE0`, `WRACK`). Both scene scripts use this instead: keep candidates with the right magic, root count and `PRPS`, then take the **largest** (embedded loading-screen sub-archives have their own, smaller `BRTR`).
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

### `scenes/import_fish_blender.py` — Blender import script

Paste into Blender's Scripting workspace and run. Imports each unique mesh from `models/FISH/` once (shared mesh data), then places 1161 instances with proper Blender object transforms. Objects are sorted into named collections (Player, Characters, Buildings, Rocks, Flora, Dock, Terrain, Collision, etc.).

**Coordinate conversion** (current, user-confirmed 2026-10-01): `matrix_world = CONV @ game_world @ FLIP_Z`, with `CONV` = (Blender X = game X, Y = game Z, Z = game Y), determinant −1, because the game is left-handed. See the handedness entry under GMDL Chunk Hierarchy. The script parses our OBJ files directly (`mesh.from_pydata`), not through Blender's OBJ importer, so no importer axis conversion is involved. Set `NAME` at the top to import any GDW.

**Viewport settings to apply after import:**
- Clip End: 20,000 (level spans ~4600 units)
- Scale: scene unit scale = 0.01 (game units are centimetre-scale)

### Live BRTR Editing and Custom Maps — rules (full narrative in `docs/brtr_editing.md`)

**Level-editing tool index (2026-10-03, all in `scripts/`, run from there):**

| Script | Does |
|---|---|
| `blender_export_scene.py` | runs **in Blender**: exports collection `JAWS` (meshes, transforms, images, material blend/culling settings) to `blender_export/` + `manifest.json` |
| `build_scene.py BASE OUT EXPORT_DIR [--deploy NAME]` | one-command build: textures + materials + meshes + collision + nodes, verified, optionally deployed (then F10 in-game) |
| `strip_level.py IN OUT [--keep-class/--keep-name/--keep-id]` | blank base: removes scenery, keeps gameplay layer, protects referenced nodes |
| `obj_to_gmdl.py IN OUT model.obj [ID] [--gmat --scale --collision]` | single OBJ → `GMDL` (+ generated `MREG`) appended to `RSRC`; library for `build_scene.py` |
| `insert_brtr_node.py IN OUT` | append node clones (edit `SPECS`); `build_node` is the library used by `build_scene.py` |
| `gdw_textures.py` | library: `build_gtex` (new texture blocks), `clone_gmat` (new materials), `find_block` |
| `gdw_grow.py` | library: `replace_chunk_payload` / `append_to_chunk` (resize `RSRC`/`BRTR`, fix `FSIZ`/`SKIP`/`FDIR`), `find_brtr`, `top_chunks` |
| `patch_texture.py` | in-place texture swap (same size), matched by pixel content |
| `import_skeleton_blender.py` | runs **in Blender** (or `blender -b --python … -- --name FISH --skel 1766`): skinned, textured, animated model with one action per clip |
| `add_trigger.py BASE OUT` | scripted trigger: copies a breakable (FISH pier post) as a trigger object, adds targets, and a `GDControl` on the trigger's root that removes the targets (default step: suspend) when it's destroyed or hit (config block at the top) |
| `dump_gdcontrol.py LEVEL.GDW [REGEX]` | read-only: prints a level's `GDControl` scripting (timed start/stop/add/kill/show/hide/suspend steps and their targets) in readable form |


The game re-reads a level's `.GDW` from disk on stage re-entry (deploy by backup-and-swap into the Steam install's `data/`).

- **Relocating a static object:** patch `0x080017DA` (transform) **and** `0x080017DF` (AABB) by the same delta. A stale AABB causes intermittent culling and missing collision. No `MREG` edit needed.
- **Physics/buoyant objects** (e.g. `WhaleCarcass Body`) visibly drop and resettle after any move. That's expected: the shipped Y is the hand-placed resting height for that spot.
- **Nested nodes:** `new_local = parent_M⁻¹ @ (target_world − parent_translation)`; the AABB still shifts by the plain world-space delta.
- **Spawn markers** (no mesh, e.g. collectibles): scaling the marker transform (plus AABB) scales the spawned object (10× `CGO_Necklace` confirmed in-game).
- **Injecting a new resource works:** duplicate a `GMDL`, patch its mesh ID, append to the end of `RSRC`, then fix `RSRC` size, `FSIZ`, `SKIP` (keep `FDIR` 512-aligned), and the `FDIR` archive-2 offset by the same delta. Repointing a node's `PROP 0x08001873` to it renders correctly.
- **Blank base level works (2026-10-03, user-confirmed):** `scripts/strip_level.py IN OUT` removes FISH's scenery (classes `0x0107402F` plain model + `0x0106F06E` flora + `0x01072071`, the `Tiles` group, pier/post/boat templates and their reference copies: 809 top-level / 1,297 nodes) and keeps the gameplay layer. It keeps nodes that kept data points at (`ID_PROPS`, including **`0x08001376` = `NAWater2004`'s sun node: removing `Sun` stops the water surface rendering**), and hides (moves 50,000 down) the 8 nodes named in `ACTN` stage logic. `build_scene.py` takes template nodes from stock FISH, so it works on a stripped base. Details: `docs/brtr_editing.md` "Blank base level".
- **Transparency works (2026-10-03, user-confirmed):** 32-bit texture alpha alone makes pixels see-through. Node render settings pick the mode: normal = smooth blend, FISH seaweed values (`0x08001876` = `0x80000920`, `0x08001875` = `0x81000021`) = hard cut-out. Back faces depend only on the material's `TWOS` (clone GMAT 668 = two-sided, 1073 = one-sided). The pipeline maps Blender's Blend Mode (Opaque / Alpha Blend / Alpha Clip) and Backface Culling onto these. Details: `docs/brtr_editing.md` "Transparency".
- **Custom textures work (2026-10-03, user-confirmed):** images on Blender materials become new `GTEX` blocks (`scripts/gdw_textures.build_gtex`: plain variant, 24/32-bit, power-of-two resize; rebuilding shipped textures gives byte-identical blocks, 240/241 FISH) plus a new `GMAT` cloned from 1073 with `ID` and `TEXP` base texture replaced (`clone_gmat`). Handled automatically by `blender_export_scene.py` + `build_scene.py`. Details in `docs/brtr_editing.md` "Custom textures".
- **Blender scene → level in one command (2026-10-03, user-confirmed):** `scripts/blender_export_scene.py` (run in Blender; exports collection `JAWS`, scale baked into meshes, Y/Z swap, origin → (2160, −25, −3650), ×15; custom props `jaws_collision`, `jaws_gmat`) + `scripts/build_scene.py BASE OUT EXPORT_DIR --deploy TEST` (meshes + generated collision + nodes with full rotation; solid → template 77, non-solid → 79), then F10. Position/rotation/scale verified against Blender to 0.0001. How-to: `docs/brtr_editing.md` "Blender scene export".
- **Collision for custom meshes works (2026-10-03, user-confirmed):** `obj_to_gmdl.py --collision` pads the mesh to a multiple of 4 triangles, writes `TNOR`/`TFLG`, and appends a generated `MREG` (next free ID after the mesh). Place it with a template that has a `PRIM` (node 77) and `{'prim_region': <MREG id>}` in `insert_brtr_node.py`'s `SPECS`.
- **Custom meshes from OBJ work (2026-10-03):** `scripts/obj_to_gmdl.py` writes a minimal-layout `GMDL` (byte-identical on 132 shipped meshes; container sizes exclude the last child's padding) and appends it to `RSRC` (`--gmat` for material-less OBJs, `--scale` since Blender units are tiny in-game); a user-confirmed custom ring renders in-game. Step-by-step Blender → in-game workflow and the current live `TEST.GDW` contents: `docs/brtr_editing.md` ("Workflow: Blender model → in-game object"). **New resource IDs must be the next free ID** (one shared ID space, FISH 1–2832); `0x7000` was silently ignored. Swapping a node's mesh requires resizing its baked vertex colours (`0x0800187A`, one float4 per vertex); `insert_brtr_node.py` does it. Details in `docs/brtr_editing.md`.
- **Scripted triggers work (2026-10-03, user-confirmed):** `scripts/add_trigger.py`. Breaking a cloned pier post removes a target's visibility and collision. Rules: (1) the `GDControl` must sit on a **group-type node** (`0x010B10AA`/`0x010AA0A4`), because a destructible's hook (`MBRombolhato.m_robbcontrol` `0x08000673` / `m_megutcontrol` `0x0800067C`) starts the control's *live instance* and plain model nodes never get one; (2) **new IDs must be below `0x100000`** (the engine's runtime ID counter starts there; objects with IDs ≥ `0x100000` vanish); (3) steps at **delay −1** when the trigger deletes itself (posts have `m_killparent`). (4) One **suspend** step (`0x4B000400`) removes a target completely; hide (`0x8F000100`) and clearing `0x10`/`0x40` (`0x4F000040`) do too, while **kill alone leaves it solid** (user-tested one step per target). Details: `docs/brtr_editing.md` "Scripted triggers"; engine side in `docs/exe_analysis.md` "Object registry, live actions and destructibles".
- **Appending a brand-new `CHBR` node works (solved 2026-10-03)** with `scripts/insert_brtr_node.py` (clone a top-level node, new ID = max+1, new translation, optional mesh swap and PROP overrides, AABB recomputed from mesh vertices, full size cascade fixed). The July 3/3 failures all cloned node 302, a hidden render-layer companion. Every FISH rock/sand tile has a `" 1"`-suffixed twin (nodes 264–302) with `m_StaticLights` = 0, `m_RenderSetting` = `0x40000400`/`0x40002400` and no vertex colours, and those fields keep it invisible. **Clone a visibly rendered node instead.** `m_Viewport` (`0x080017DD`) = `1` renders only from above the water; **`0x20003` renders above and below (user-confirmed)**, so use that.

### BEACH/BEACHPST "Cut Objective" — resolved 2026-10-03: not cut (full write-up in `docs/cut_content.md`)

The suspected cut "destroy the sub → boulders clear" objective isn't real. The stuck "drone" under the bridge is a **SeaSeeker** (`ANSeekerRef 4`, `(-233, -17, 265)`), not a `TKSub`. It's deliberately configured stationary: `m_chase_shark`/`m_lights` = 1 (off), no `m_chasearea`, and it inherits the hunger drain. **`ANSeekerRef` PROP ID = `0x080002E9` + reflection field index**; 0 = inherit, booleans tri-state 0/1 off/2 on. No `ACTN` block, PROP or exe string references it or the `Level3_elzarokovek` rocks / `Kizaro_Lap_Kozepes` plate. By contrast, START's working version links `LastSeaSeekerRef` (child mission bricks, class `0x010D20D1`, objective `PROP 0x080005BF`) and the boulder `TunnelBlockingDust` through `ACTN` blocks on its stage-phase nodes. In-game with the rocks removed (user, BEACHPST), the canyon behind them is an empty unfinished stub. Killing the seeker triggers nothing.

## Executable Analysis — `Jaws.exe` (Ghidra) and the Mod

**Decompiled 2026-10-01.** Full detail in **`docs/exe_analysis.md`**; this is the summary. Ghidra 12.1.4 lives at `~/tools/ghidra_12.1.4_PUBLIC` (needs JDK 21), with the analyzed project at `~/tools/ghidra_projects/JAWS.gpr`. Headless helper scripts are in `scripts/ghidra/` (`DecompAt.java`, `DecompStringRefs.java`, and `CreateDecomp.java`, which first creates functions Ghidra missed, e.g. ones only reached through a vtable). The exe has a fixed image base (`0x400000`) and no ASLR, so all addresses below are stable.

**Player shark, verified in-game:**
- `0x90BC04` = singleton pointer to the **player shark controller** (set by the constructor at `0x664BD8`, cleared by its destructor; null in menus/loading).
- `ctrl+0x50` = the shark's scene object ("brick"). **World position = floats at `brick+0xA8`.**
- Controller fields: `+0x240` state (`7` = dead), `+0x2A8`/`+0x2B0` max/current **health**, `+0x2AC`/`+0x2B4` max/current **hunger** (user-verified), `+0x72C`–`+0x73C` five ability multipliers loaded from the save, `+0x54` `SharkConfig`.
- The shark model faces its local **+Z**, so heading comes from the world matrix's Z row.

**Brick (scene object) layout**, from the engine's world-matrix updater `0x696EA0`: `+0x0C` flags (`0x20` = world matrix stale), `+0x14` parent pointer, `+0x50` local 4×3 transform (same layout as BRTR `PROP 0x080017DA`), `+0x84` cached world 4×3 transform (translation at `+0xA8`).

**Stage loading (2026-10-03):** engine object = `[0x920E24]`, vtable `0x7F6018`. Slot `+0x78` = `0x6C3FD0`, the raw loader: appends `.GDW`, checks loaded `FDIR` sub-archive names first, loads immediately and stores its argument at `engine+0xB8`. Slot `+0x80` = `0x6C3C50`, `RequestStage(flags, name)` (`thiscall`, `ret 8`): only `engine+0x40C |= flags; strcpy(engine+0x410, name)`. The engine tick `0x6C7800` (vtable `+0x50`) handles flag `1`: unload (`vtbl+0x2C`), raw-load `engine+0x410`, re-init (`vtbl+0x28`). Flags `2`/`4`/`8`/`0x20` take other paths, not decoded. The dev "Open Stage" menu calls `+0x80(1, path)`, and a finished async load calls `+0x80(0x20, 0)`. A separate async state machine sits at `engine+0x510` (`FUN_006c4610` / `FUN_006c4ab0`, name at `+0x530`). The mod's F10 reload uses `+0x80(1, current name)`.

**`GDControl` = level scripting (decoded 2026-10-03, full tables in `docs/exe_analysis.md`).** `ACTN` blocks with class header `0x0203B039` (every `ACTN` has its own ID, second header word; list entries can be node or action IDs). Up to 8 timed steps: `m_CtrlN` (`PROP 0x08001819 + 3(N−1)`) = `[w0, w1, w2]`, `m_ListN` (`0x0800181A + 3(N−1)`) = target IDs. A step fires `w1 + rand(0…w2−w1)` ticks after start (`w1` signed; −1 = in the start pass itself, 0 = next tick). `w0` low bits: `0x1` start, `0x2` stop, `0x4` add to world, `0x8` kill, `0x200` spawn a copy, `0x80`/`0x100` show/hide (`m_nFlags 0x100`), `0x10`/`0x20`/`0x40` edit flags `0x10`/`0x40`, `0x400`/`0x800` suspend/resume, `0x1000` use the stored list. High bits pick the scope (brick vs node, recurse into children); `0x0F000000` is the default (89%). Engine: start `0x6B68A0`, executor `0x6B6C00`, interpreter `0x6B6DB0`. Targets resolve to the object's **live action instance** (`0x6C3010`, registered object `+0x24`) and the **registered object** itself (`0x6C2F90`, `m_nFlags` at `+0x18`); corrected 2026-10-03, the first decode had these swapped. 3,261 controls in 19 GDWs. `scripts/dump_gdcontrol.py` prints them readably; it also shows dangling target IDs (`missing#…`, 9–72 per level), likely objects deleted during development.

**Death paths:** every death goes through the controller's state setter **`0x65EDA0`** (`thiscall SetState(state,-1,-1)`, `ret 0xC`) with state `7`, from four call sites: health ≤ 0 (`0x65D871`), a **scripted `DIEM` kill message** (`0x65B871`, which also zeroes health and hunger), and two timer-based deaths (`0x668CC6`, `0x66D4E9`).

**Reflection field table:** every class field is registered by a stub calling `0x70B6A0` (6,457 sites). `scripts/dump_class_fields.py <out.json>` dumps all of them (691 class descriptors, 132 with resolved names). Each stub passes two integers: **`a` = offset of the property wrapper in the class's props object, `b` = offset of its mirrored copy in the runtime object (0 = none); the value sits at +4** (settled 2026-10-03 via `GDControl`, see `docs/exe_analysis.md`). A class's BRTR PROP IDs are consecutive in registration order (e.g. `ANSeekerRef`: `0x080002E9` + field index).

**Correction:** `NAPredator` is the **"predator vision" screen effect** (fields `m_magnification`, `m_power`, `m_strength`…), **not** the shark. The shark is driven by `MLSharkCtrl` + `SharkConfig`, and the camera/minimap by `MLSharkCamera`.

**Why the old position scans failed:** they only searched the exe's static `.data` section (`0x845000`–`0xE6C000`). The shark is heap-allocated at level load.

### Mod (`mod/`, d3d8 proxy) — current features

All user-tested 2026-10-01. Full controls and internals are in `mod/README.md`.

| Key | Feature |
|---|---|
| overlay | Shark world **X/Y/Z** (labeled `Shark`, or `Cam` fallback in menus) + **heading/pitch** |
| `F8` | **Teleport box**: type `X Y Z` / `X Z` / a bookmark slot number. `Ctrl+1..9` saves the current spot. Bookmarks live in hand-editable `C:\jaws_bookmarks.txt` (`slot x y z [name]`, `#` comments; reloaded when F8 opens if the file changed; plain coords, not tied to a level). Game keyboard input is blocked while the box is open (DirectInput device vtable patch). Teleport writes the brick's local translation (solved through the parent's world matrix) and world translation, and sets the stale flag; it sticks with no physics snap-back. |
| `F11` | **Invincible + infinite hunger**: refills health and hunger to max every frame, and hooks `SetState` to drop state-7 (dead) requests. Known limitation: a blocked *scripted* death leaves the shark alive but invisible and the game confused. The user has accepted this; don't chase it. |
| `F10` | **Reload current stage from disk** (2026-10-03): calls engine vtable `+0x80` `RequestStage(1, engine+0xB8 name)`; the engine tick unloads and re-reads the `.GDW` at a safe point. For testing GDW edits in place. `src/stage.{h,cpp}`. **User-confirmed working 2026-10-03.** |
| `F12` | **Object-ID registry dump** (2026-10-03, debug, read-only): registry entries + objects for the IDs in `C:\jaws_ids.txt` → `C:\jaws_iddump.txt`. `src/iddump.{h,cpp}`. |
| `F2`/`F3`/`F4`/`F5`/`F6` | Freecam / screenshot / fog / sim pause / foliage hide (unchanged) |

New source files: `src/shark.{h,cpp}` (position/facing/teleport/health/death hook), `src/input_block.{h,cpp}`, `src/bookmarks.{h,cpp}`. **Process-wide state rule:** the game recreates its D3D device hundreds of times per session, so anything that must persist (like bookmarks) can't live on `DeviceProxy`.

## Class Namespace Conventions

The engine uses a prefix-based class registry:

| Prefix | Domain |
|---|---|
| `GD` | Generic engine / rendering (GDModel, GDLight, GDFog) |
| `NA` | Gameplay / shark systems (NABiteTarget, NAWayPoint; note `NAPredator` is the predator-vision screen effect, not the shark — see Executable Analysis section) |
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

**Correction (2026-07-15) — M05 is in `KATATAMA.GDW`, not `FISH.GDW`:** Extracting `KATATAMA.GDW`'s BRTR scene (`scripts/rip_brtr_scene.py`, `NAME='KATATAMA'` → `scenes/KATATAMA_brtr.json`/`.obj`) surfaced `DrillingPlatform 1/2/3` (with `autogun_uw_laser_gun`, `Laser Autogun Root`, `OilRig LOD`), `PowerPlant 1` + `Ventillator`, `OilTank`/`OilTank_Darab*` debris, the `cutter_FIN_V2_opt_FIN_JAV_tores` Coast Guard Cutter (intact/`_rombolt`-destroyed variants), and `AURORA_LO0` — i.e. the complete Avril Bay mission set from the M05 walkthrough (3 oil platforms, shipyard power generator with two feed columns, Coast Guard Cutter, Aurora II). `FISH.GDW`'s BRTR, by contrast, contains none of this — it's pier/dock structures, beach houses, and tourist NPCs (Fisherman's Isle content only), confirming it is not the M05 mission space despite the earlier mapping. **Correction (2026-08-13):** the "corrupt/implausible size field" was actually the BRTR false-positive-offset bug (see "Locating `BRTR`" under Scene Extraction Pipeline) — `KATATAMA.GDW`'s naive `data.find(b'BRTR')` landed on a coincidental match inside `RSRC`, not the real chunk. Re-extracted with the now-fixed `rip_brtr_scene.py` (real BRTR @ `0x7993304`, size 9,122,556) — a clean 4,571-node scene, 2,083 with resolvable meshes. The KATATAMA scene extraction is no longer unverified/incomplete.

**Checked for cut content in KATATAMA (2026-07-15), none found:** exactly 3 `DrillingPlatform` groups exist (matches shipped "three in all"); the 35/923 GMDL mesh indices never placed by BRTR are small props and `_normal`/`_serult` damage-state variants (destruction-mechanic assets swapped in by code, not orphaned level geometry); `StageWreckQuest` (M05's quest class — confirmed via `m_scubadivers` field matching the shark-cage divers) and `MSKatatamaMission` (single `m_PreyID` field, likely an unrelated side-mission hunt target) showed no unused/dead fields comparable to the confirmed cut missions below. This doesn't rule out a cut area — nested BRTR parent transforms aren't resolved to world space yet (see Parent-child hierarchy open problem), so a spatial gap-hunt across the full level hasn't been done.

**Correction (2026-08-12) — `MINEMSHA.GDW` is Grand Occasus Canals (SC15 Up a Creek), not an unknown location:** user-supplied identification, verified against BRTR content — see table row above. This also resolves part of the cut Hot Pursuit mission investigation (see `docs/cut_content.md`, which has the full merged writeup — "Pursuit" and "Jet Ski Mission" were the same mission, official title "Hot Pursuit"): that mission's leftover objects (`JetskiChase`, `jetski_mountpoint`/`_a`, `jetskipath`, `ccjetski`) are concentrated almost exclusively in `MINEMSHA.GDW` (vs. the usual all-20-GDWs shared-asset-pool pattern), and `StagePursuitQuest2`'s gate fields — previously unexplained for an open-water chase — make much more sense as canal lock/sluice gates. A second, independent site was also found in `OPEN_NE.GDW`: a bare `HOTPURSUIT` anchor marker sitting near the `Brody's House` map location, which in-game has no house actually built at it. A fully-modeled second lighthouse (distinct from the bare-placeholder `Lighthouse02`) was found 2026-08-13 next to `MapItemPos_Coast Guard HQ`, a stronger match for the "near the lighthouse" mission-goal framing, but it's still ~5,900 units from the `HOTPURSUIT` marker, not adjacent. Not fully resolved; see `docs/mission_system.md` and `docs/ps2_cut_content_findings.md` for the full writeup.

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

**Full write-ups (evidence, coordinates, corrections) are in `docs/cut_content.md`**, with more in `docs/mission_system.md`. Summary:

- **Down the Hatch** (`MSHatchMission`, string `"Down the Hatch (unused!)"`): cut side challenge, swallow N collectables before a timer. Never placed in any GDW.
- **Hot Pursuit** (`StagePursuitQuest`/`StagePursuitQuest2`): cut **story** stage between M10 and M11, title in both the PS2 and PC exes. Jet-ski chase; goal text mentions protecting Amity Police Chief Candy Wilson's home (she is not the boss; `m_JetSkiBossIDList` is). Placed leftovers: `MINEMSHA.GDW` (`JetskiChase`/`jetskipath`/`ccjetski` nested in SC15's `SM16UpACreek` traffic, with a live A-pose NPC bug at `(-1254, 0, -787)`) and `OPEN_NE.GDW` (bare `HOTPURSUIT` marker near the empty `Brody's House` lot).
- **Candy Wilson:** cut character, PC-only text (absent from the whole PS2 build), no class, mesh, or placement anywhere.
- **Highlands Bay:** cut map area (string only, no `MapItemPos_` in any Open Ocean zone). **Dolphin Passage is NOT cut**: it's the real `OPEN_S`↔`OPEN_NE` transition channel.
- **Stage slots:** `MSStageSelect` has `m_Stage1ID`–`m_Stage18ID` (18 slots, 11 shipped). Exactly 7 side challenges have opening cutscenes (SC01/02/03/06/07/12/19); no proof they reuse the 7 unused slots. `MSStageSelect`'s live instance data is unlocated (probably `TITLE.GDW`'s `SCRT`).
- **Collectibles:** of catalog categories 01–13, only **Trident (10)** is never placed (mesh `TridentStaff` exists in `WRACK.GDW`). The others use 4 naming conventions (`CGO_*`, `BSCollectibleGameObject <Name>`, `<Name>Collectibles`, bare names).
- **ANSideMission numbering gap:** classes 15/21/22/25 map to SC14/20/21/24, class 33 to SC29, so classes 26–32 were removed (at least 3 cut side challenges).

### "Sole Predator" — original working title

*Sole Predator* was the game's original working title during development at Appaloosa Interactive (formerly Novotrade, Budapest), before Majesco licensed the Jaws IP and agreed to publish the game. The title change happened during production; the shipped build is *Jaws Unleashed*.

The string "Sole Predator" **does appear** in extracted textures as promotional/marketing copy describing the game's boasted features — early promotional assets baked into the build that survived the title change. It is **absent** from mission names, class names, mode names, and script strings — the rename was applied consistently to the code/data namespace but not to all texture assets.

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

### Lead: long-duration `GSMP` cat2 samples as possible dialogue — see `docs/audio_leads.md`

Unconfirmed. A handful of 7–17s, per-level-unique, GSFX-triggered cat2 samples might be spoken dialogue. The top candidate (`BEACH_id0590`, 44.58s) turned out to be a beach-radio song, so this lead is weak. Best remaining candidate: `TOWN_id0109`–`id0112` (4 consecutive IDs). The full list is in the doc.

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

The PS2 release is in `GAME_GDWs/ps2/` (all `.GDE` archives + `SLUS_210.62` exe); `GAME_GDWs/_FISH.GDE` is a PS2 file, not a PC dev build. **Full format notes are in `docs/ps2_asset_extraction.md`.** Summary:

- **Container is identical to PC `.GDW`** (same preamble and chunk walk). Only PS2-exclusive top-level chunk: `BNCH`.
- **Textures (`GTEXT`/`ZIPN`):** `ZIPN` is not compression — it's native PS2 GS pixel data: PSMCT32 (RGBA8888), PSMCT16 (RGBA5551), PSMT8 (palettized, GS-swizzled indices, RGBA or RGB palette). Extractors: `scripts/rip_gtext_ps2.py`, `scripts/rip_gtex_ps2.py`.
- **Meshes (`GMDL`):** extra `MTYP`/`MATS`/`SSET`/`STTA` wrappers; quantized `POSS` positions (`int16 * float scale`); `STRP` triangle strips (`0x7FFF` = strip break, winding flip = `(i%2==0) XOR flag(strip[i+2])`, drop degenerate triangles). Extractor: `scripts/rip_meshes_ps2.py`.
- **`SCRT`:** same tree format as PC, 14 unnamed children, PROP range `0x08001957`–`0x0800196A`.
- **`BNCH`:** shared name-interning table (3,495 names) plus ~1,272 80-byte transform records (field layout unverified).
- Open: `SSET`/`STTA` meaning, `POSS` `w` component, `BNCH` record↔name mapping.

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

- **Resolved** (details live in their sections): FISH whale position (mission relocation), scene `mesh_idx` mismatch, static terrain (it's in BRTR), skeletal animation, parent-child hierarchy, `SCRT`, `SKIP`, texture–mesh linkage, Blender mirroring (handedness), BRTR false-positive tag offset; and on 2026-10-03: brand-new node insertion, `PRIM` (collision link), `STRI`/BVH layout, "GTEXT" (not a tag), custom meshes/collision/textures/transparency, Blender scene export, blank base level, in-game stage reload (mod F10), field-registration integers (props/runtime offsets), `GDControl` scripting, custom scripted triggers (`add_trigger.py`). Also 2026-10-03: the BEACH/BEACHPST "cut objective" (not cut; stationary SeaSeeker + unfinished canyon stub, see its section).
- **`GDControl` / trigger leftovers** (scripting decoded and custom triggers working 2026-10-03; suspend, hide or clearing `0x10`/`0x40` each fully remove an object, kill alone leaves it solid (user-tested); the engine code that instantiates group-node actions at load isn't traced): the node flag `0x400000` (ops `0x2000`/`0x4000`), why kill keeps collision, spawn modes 3 vs 4, how quest code starts controls that no other control starts, and whether the dangling `missing#` target IDs are deleted objects or runtime-created ones.
- **Skeletal animation leftovers** — solved 2026-10-03 apart from bone names, how bodies bind to the shared human clip skeleton at runtime, playback rate, and `MORF`; see the Skeletal Animation section.
- **In-game cutscene voice acting** — still not conclusively found, but progress 2026-07-29: `GSFX` sound-trigger blocks fully decoded (see Audio System section), proving SMPB samples are NOT unused/cut as previously claimed — all are actively triggered, just appear to be short crowd/reaction barks. A short list of unusually long (7–44s), per-level-unique `GSMP` cat2 "SFX" samples was flagged as a lead, but the top candidate turned out to be a diegetic beach-radio song, not dialogue (user-confirmed by listening) — so this lead is weaker than initially thought; remaining candidates (esp. `TOWN_id0109`–`id0112`, 4 consecutive resource IDs) are still unconfirmed. External audio middleware and a separate movie-bank file format are both ruled out. (Ruled out: `SCRT` — see below, resolved and it's not audio-related.)
- **Unknown PROP IDs** — `0x080017DB`–`0x080017E4`, `0x08001874`–`0x0800187B`, and (new, from `SCRT`) `0x08001980`–`0x08001993` / PS2's `0x08001957`–`0x0800196A` seen on CHBR nodes; most meanings not yet determined (see PROP ID table above for partial decode).
- **`BNCH` record mapping (PS2)** — how the ~1,272 80-byte transform records map to the 3,495 names in the string pool.
- **Unused material data** — extra `TEXP` layers beyond the base texture, and GMAT colour/shininess/transparency parameters.
- **MREG `MOIL` content** — the large (~66 KB) `MOIL` sub-chunk inside `GMOA` blocks is undecoded. May contain AI pathfinding graph data or NPC navigation mesh.
- **New-node render flags, leftovers** — brand-new node insertion is **solved** (2026-10-03, see `docs/brtr_editing.md`). Still open: which of `m_StaticLights` / `m_RenderSetting` / missing vertex colours hides the companion layer, what the individual `m_Viewport` bits mean (`0x20003` is confirmed to cover above + underwater), and what the `TFLG` per-triangle flags mean exactly (generated collision with all edge bits set works).
- **Cut mission — Hot Pursuit, location confirmed across two GDWs but full scope not pinned down** — see `docs/cut_content.md` for the full writeup. `MINEMSHA.GDW` (Grand Occasus Canals) has a tightly-clustered jetski chase/spawn/path node group, live-reproducible in the shipped game as a broken A-posing NPC. `OPEN_NE.GDW` independently has a bare `HOTPURSUIT` anchor marker near the `Brody's House` map location, confirmed in-game (2026-08-12) to have no house actually built there. Still open: a second, better lighthouse candidate was found 2026-08-13 (a fully-modeled lighthouse next to `MapItemPos_Coast Guard HQ` in `OPEN_NE.GDW`, ~400 units away, vs. the previously-checked bare-placeholder `Lighthouse02`) but it's still ~5,900 units from the `HOTPURSUIT`/`Brody's House` cluster, not proven adjacent — see `docs/mission_system.md`; whether the mission spanned both GDWs as one sequence or represents two different development-time concepts isn't confirmed; the causal/scripted trigger logic is presumed hardcoded in `Jaws.exe`, same caveat as the BEACH submarine finding above.

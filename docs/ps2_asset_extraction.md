# PS2 Asset Extraction

Full-build asset extraction results, after `GAME_GDWs/ps2/` was populated with all 22 `.GDE` archives (see `ps2_dataset_inventory.md`). Supersedes the earlier single-file `_FISH.GDE`-only extraction (the old `textures/_FISH_PS2` and `models/_FISH_PS2` output directories have been deleted; `FISH_PS2` is now the canonical name, consistent with the other 21 levels).

---

## Scripts

| Script | Extracts | Output |
|---|---|---|
| `scripts/rip_gtext_ps2.py` | `GTEXT`-tagged textures (5-byte marker) | `textures/<NAME>_PS2/gtext/` |
| `scripts/rip_gtex_ps2.py` *(new)* | `GTEX`-tagged textures (4-byte marker, sprite/overlay system) | `textures/<NAME>_PS2/gtex/` |
| `scripts/rip_meshes_ps2.py` | `GMDL` meshes (triangle-strip format) | `models/<NAME>_PS2/` |

All three are run per-archive with `name`/`NAME` set to the level stem and `INPUT_FILE` pointed at `../GAME_GDWs/ps2/DATA/{name}.GDE`, following the same batch-substitution pattern documented in `CLAUDE.md` for the PC scripts.

## Totals

| Type | Count |
|---|---|
| `GTEXT` textures | 1,416 |
| `GTEX` textures | 5,581 |
| **Total textures** | **6,997** |
| Meshes | 10,655 |

## Per-Level Breakdown

| Level | GTEXT | GTEX | Meshes | | Level | GTEXT | GTEX | Meshes |
|---|---|---|---|---|---|---|---|---|
| AQUA2 | 48 | 252 | 298 | | MINEMSHA | 50 | 235 | 315 |
| AQUARIUM | 50 | 303 | 773 | | OPEN_NE | 130 | 316 | 996 |
| ARMADA | 78 | 222 | 526 | | OPEN_NW | 112 | 324 | 709 |
| BEACH | 62 | 284 | 642 | | OPEN_S | 121 | 316 | 785 |
| BEACHPST | 61 | 252 | 407 | | START | 71 | 258 | 435 |
| CHASE | 51 | 197 | 202 | | START2 | 82 | 287 | 690 |
| DEEPSEA | 47 | 251 | 330 | | TITLE | 48 | 235 | 74 |
| DEEPSEA2 | 46 | 293 | 633 | | TITLE0 | 2 | 2 | 0 |
| DOCKS | 51 | 235 | 377 | | TOWN | 69 | 320 | 469 |
| FISH | 49 | 248 | 293 | | WRACK | 53 | 225 | 306 |
| GAUNTLET | 47 | 222 | 238 | | KATATAMA | 88 | 304 | 862 |

`TITLE0` extracting 0 meshes matches PC's `TITLE0.GDW` (also 0 meshes documented in `CLAUDE.md`) — consistent, not a bug.

---

## The `GTEX` (Non-`GTEXT`) PS2 Texture System

PC has two texture systems (`GTEXT` for level textures, `GTEX` for sprite/overlay textures — see `CLAUDE.md`'s "Texture System (GTEX)" section). Only the `GTEXT` side had a PS2 extractor before this session. PS2's `GTEX` uses the same header conventions as PC's `GTEX` (`tex_id`/`flags`/optional `OBPR` type-tag block/`width`/`height`/`bpp`) but wraps pixel data in the PS2-native `ZIPN` format already decoded for `GTEXT` (see `CLAUDE.md`'s "PS2 Version Data" section for the `ZIPN` format itself — not re-derived here).

### Block Layout

```
GTEX [uint32 block_size]
  [uint32 tex_id][uint32 flags]
  [optional OBPR{ PROP{ prop_id=0x04000030, type="TEXC" } PROP{ prop_id=0x04000030, type="TEXB" } }]
  [uint32 const/hash][uint32 zero][uint32 width][uint32 height][uint32 bpp]
  ZIPN [uint32 size]
    [uint32 remaining][uint32 width][uint32 height][uint32 format][uint32 unknown=1]
    [pixel data]
```

Measured on `FISH.GDE`: 788 total `GTEX` blocks, 249 with a `ZIPN` payload (some with the optional `OBPR` block making the header 76 bytes instead of 28), the remaining ~540 metadata-only (no pixel data — declares dimensions but nothing else, matching PC's documented "32bpp GTEX without TGAN are metadata/reference blocks" behavior. These are runtime-filled render targets, e.g. reflections/shadow maps).

### Bugs Fixed While Building `rip_gtex_ps2.py`

1. **Off-by-one in the pre-`ZIPN` header size.** First pass checked for the `ZIPN` tag 16 bytes into the payload; the real layout has `const(4)+zero(4)+width(4)+height(4)+bpp(4)` = 20 bytes before `ZIPN`, not 16 — missed the `bpp` field. Fixed by checking `data[p+20:p+24] == b'ZIPN'` and reading `zipn_pos = p + 20`.
2. **`rip_gtext_ps2.py`** (existing script) threw `index out of range` on 4 blocks in `GAUNTLET.GDE`. Root cause: legitimate zero-byte `ZIPN` payloads (`zipn_size <= 20`, i.e. no pixel data beyond the sub-header) — same pattern as the `GTEX` metadata-only blocks above. Fixed by skipping these cleanly instead of attempting to decode.

### Validation

Spot-checked decoded output against raw bytes for a suspicious all-black, fully-opaque 128×128 texture (`tex_id=4` in `FISH.GDE`) — confirmed the entire 17,152-byte pixel payload (256 KB palette + index region) is genuinely all-zero in the source file, not a decode bug. This is a runtime render-target placeholder, correctly exported as blank, matching the documented PC behavior for the same case.

### Remaining Unsupported Formats

10 blocks across the full 22-archive run use pixel formats not yet decoded: `fmt=0x1` (×8, all 256×256, found in `START2.GDE`) and `fmt=0x800014` (×2). Low priority given the small count — not investigated further this pass.


---

# PS2 `.GDE` Format Notes

> Moved here from `CLAUDE.md` on 2026-10-02 to keep that file under its size limit. Text is verbatim.

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

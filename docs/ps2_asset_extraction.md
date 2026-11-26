# PS2 `.GDE` files: format and extraction

**In short:** the PS2 version's level files (`.GDE`) use the same container as the PC's `.GDW`. Only the resources inside are PS2-native.
- **Textures** are stored as raw PlayStation 2 Graphics Synthesizer pixels (`ZIPN`), not compressed.
- **Meshes** use triangle strips and compressed (quantized) positions.
- **`BNCH`**, the only PS2-only chunk, is a shared name table.

All three resource kinds are decoded and extracted: **6,997 textures and 10,655 meshes** from the 22 PS2 levels.

Related: `docs/ps2_dataset_inventory.md` (what the PS2 files are), `docs/ps2_cut_content_findings.md` (what the PS2 exe tells us), `docs/ps2_disassembly_notes.md` (tools).

Rewritten for readability on 2026-11-27. Old version: `docs/archive/ps2_asset_extraction_old_2026-11-27.md`.

---

## Contents

1. [The container](#1-the-container)
2. [Scripts and totals](#2-scripts-and-totals)
3. [Textures (`ZIPN`)](#3-textures-zipn)
4. [Meshes (triangle strips)](#4-meshes-triangle-strips)
5. [`SCRT` on PS2](#5-scrt-on-ps2)
6. [`BNCH`: the shared name table](#6-bnch-the-shared-name-table)
7. [Open questions](#7-open-questions)
8. [Old mistakes](#8-old-mistakes)

---

## 1. The container

**Identical to PC:**
- the same 44-byte first line, `GDED BINARY FORMAT, VERSION 2.6.3.16.`;
- the same chunk walk: `[tag][uint32 size][payload]`, padded to 4 bytes.

**Top-level chunks** (FISH): `FSIZ VERS EXBY GNRL WDIM RSPR CLAS RSRC BNCH BRTR SCRT SKIP FDIR ENDF`.
- The PC file has the same list, minus `BNCH`.
- **`BNCH` is the only PS2-only top-level chunk** (§6).

**Much smaller, not missing content:**

| | PS2 `FISH.GDE` | PC `FISH.GDW` |
|---|---|---|
| Whole file | 16.7 MB | 131 MB |
| `RSRC` | 12 MB | 111 MB |
| `BRTR` | 2.5 MB | 5.4 MB |

The difference fits PS2-resolution assets and a smaller memory budget.

**`_FISH.GDE`,** the single file studied before the full PS2 set arrived, was this PS2 FISH file (same size, 16.7 MB), not a PC development build. It's no longer in `GAME_GDWs/`; its old output folders `_FISH_PS2` were replaced by `FISH_PS2`.

---

## 2. Scripts and totals

| Script | Extracts | Output |
|---|---|---|
| `scripts/rip_gtext_ps2.py` | "GTEXT" textures | `textures/<NAME>_PS2/gtext/` |
| `scripts/rip_gtex_ps2.py` | `GTEX` textures with an optional `OBPR` | `textures/<NAME>_PS2/gtex/` |
| `scripts/rip_meshes_ps2.py` | `GMDL` meshes | `models/<NAME>_PS2/` |

- Run per level: set `name`/`NAME` to the level and point `INPUT_FILE` at `../GAME_GDWs/ps2/DATA/{name}.GDE`.
- For all levels, use the same substitution loop as the PC scripts (`CLAUDE.md` "Running Scripts").

**Totals:**

| Type | Count |
|---|---|
| "GTEXT" textures | 1,416 |
| `GTEX` textures | 5,581 |
| **All textures** | **6,997** |
| **Meshes** | **10,655** |

**Per level:**

| Level | GTEXT | GTEX | Meshes |
|---|---|---|---|
| AQUA2 | 48 | 252 | 298 |
| AQUARIUM | 50 | 303 | 773 |
| ARMADA | 78 | 222 | 526 |
| BEACH | 62 | 284 | 642 |
| BEACHPST | 61 | 252 | 407 |
| CHASE | 51 | 197 | 202 |
| DEEPSEA | 47 | 251 | 330 |
| DEEPSEA2 | 46 | 293 | 633 |
| DOCKS | 51 | 235 | 377 |
| FISH | 49 | 248 | 293 |
| GAUNTLET | 47 | 222 | 238 |
| KATATAMA | 88 | 304 | 862 |
| MINEMSHA | 50 | 235 | 315 |
| OPEN_NE | 130 | 316 | 996 |
| OPEN_NW | 112 | 324 | 709 |
| OPEN_S | 121 | 316 | 785 |
| START | 71 | 258 | 435 |
| START2 | 82 | 287 | 690 |
| TITLE | 48 | 235 | 74 |
| TITLE0 | 2 | 2 | 0 |
| TOWN | 69 | 320 | 469 |
| WRACK | 53 | 225 | 306 |

TITLE0 has no meshes on PC either.

---

## 3. Textures (`ZIPN`)

**In short:** `ZIPN` is **not** compression. It's the PS2 Graphics Synthesizer's own pixel layout, the bytes the hardware copies straight into video memory. Decoded 2026-07-08 and checked by rendering to PNG.

The scripts still call the two kinds "GTEXT" and "GTEX". On PC that split turned out to be one tag (`GTEX`) with two payload variants (`docs/texture_format.md`). The PS2 split very likely works the same way; not re-checked.

### "GTEXT" layout

Offsets from the end of the 8-byte tag and size:

| Offset | Field |
|---|---|
| `+0x00` | Texture ID (one per texture; 49 distinct in FISH) |
| `+0x04` | Unknown constant |
| `+0x08` | `OBPR{ PROP{ 0x04000030, "TEXB", value } }` |
| `+0x24` | Date stamp |
| `+0x28` | Unknown |
| `+0x2C` / `+0x30` / `+0x34` | Width / height / bpp |
| `+0x38` | `ZIPN` tag + size |
| `+0x40` | `ZIPN` header: remaining size, width, height, format, unknown (= 1) |
| then | Pixel data |

**False matches:** 6 of 55 raw "GTEXT" matches in FISH are coincidences inside `GMAT` data (followed by `REFL`/`BUMP`). Check that `OBPR` follows: `data[base+8:base+12] == b'OBPR'`.

### `GTEX` layout

```
GTEX [block_size]
  [tex_id][flags]
  [optional OBPR{ PROP{ 0x04000030, "TEXC" } PROP{ 0x04000030, "TEXB" } }]
  [const/hash][0][width][height][bpp]          20 bytes before ZIPN
  ZIPN [size]
    [remaining][width][height][format][1]
    [pixel data]
```

- FISH has 788 `GTEX` blocks. 249 have pixels; the optional `OBPR` makes the header 76 bytes instead of 28.
- **The other ~540 have no pixels.** They only declare a size: runtime render targets, as on PC.

### Pixel formats

Format = the `ZIPN` format field `& 0xFFFF`. The values match the PS2's documented `PSM` constants.

| Value | Name | Pixels | Order | Checked on |
|---|---|---|---|---|
| `0x00` | PSMCT32 | 4 bytes, RGBA8888 | Row by row | A 32×32 letter "N" |
| `0x02` | PSMCT16 | 2 bytes, RGBA5551 (bit 15 A, 14–10 R, 9–5 G, 4–0 B; little-endian) | Row by row | Sky/clouds 64×64; the 1024×512 "Open Ocean - South / Loading..." screen |
| `0x13` | PSMT8 | 1-byte index + 256-entry palette | **Swizzled** | Round UI reticles |

**PSMT8 details:**
- Payload = palette, then W×H index bytes.
- Palette = RGBA (4 bytes per entry, 1,024 bytes) when bit 16 (`0x10000`) of the format is clear; RGB (3 bytes, 768 bytes, alpha 255) when it's set.
- **The indices are in the GS's swizzled order**, not row by row. `unswizzle8()` in the script is the standard public PS2 8-bit de-swizzle (block / column / byte).

**Still undecoded:** 10 blocks across all 22 levels: format `0x1` (8 blocks, all 256×256, in START2) and `0x800014` (2). Low priority.

### Fixes made while writing the extractors

- **`rip_gtex_ps2.py`:** the header before `ZIPN` is 20 bytes (const, zero, width, height, bpp), not 16. It now checks `data[p+20:p+24] == b'ZIPN'`.
- **`rip_gtext_ps2.py`:** crashed on 4 GAUNTLET blocks whose `ZIPN` has no pixels (`zipn_size <= 20`). Those are now skipped.

**An all-black texture checked:** FISH `tex_id 4` (128×128, opaque black) really is all zeros in the file (17,152 bytes). A render-target placeholder, correctly exported blank.

---

## 4. Meshes (triangle strips)

Decoded 2026-07-08 and checked numerically. `rip_meshes_ps2.py` gets 293 real meshes from FISH (the PC parser got 3).

### Layout

```
GMDL [12-byte header]
  MTYP [4]
  MATS [12]        contains the literal "GMAT" as a type tag, not a nested chunk
  SSET [92]        not decoded
  STRP             triangle strips (below)
  STTA [96]        not decoded
  VERT             [uint32 vertex count], then:
    POSS           quantized positions
    NORM           float XYZ unit normals (same as PC)
    UVUV           float UV pairs (same as PC)
```

### `POSS`: quantized positions

```
[float scale]
N × [int16 x, int16 y, int16 z, int16 w]
```

- Position = each int16 × scale.
- `w` is only ever 0 or `INT16_MIN` in samples: probably a flag or padding. Unconfirmed.
- Checked by the values being small, bounded and symmetric (local mesh space), not by rendering.

### `STRP`: the strips

```
[uint32 count]
count × uint16
```

- Bit 15 = a flag; bits 0–14 = vertex index.
- **`0x7FFF` = strip break:** split the stream into separate strips there.
- Indices inside a strip are mostly sequential; the vertex buffer is pre-ordered to match.

### Strips → triangles

For position *i* in a strip, the triangle is `strip[i], strip[i+1], strip[i+2]`.

1. **Winding:** `flip = (i % 2 == 0) XOR flag(strip[i+2])`. Normal strip alternation, XORed with the flag of the newly entering vertex.
2. **Drop degenerate triangles:** where the three positions are collinear or nearly identical (cross product below a small threshold). They're filler that joins strip segments.

**How it was checked:** each triangle's face normal (cross product) was compared with the average of its three stored vertex normals.
- Mismatches dropped from 30 % to 0 % once the flag rule was found.
- The remaining mismatches were exactly the near-zero-area triangles.
- Result: 100 % on a clean test mesh; 77–100 % across 12 varied meshes.

---

## 5. `SCRT` on PS2

- Same tree format as PC (`PRPS` / `CHBR` / `PROP`).
- Smaller: 8,772 bytes against 12,576; 14 children against 20.
- **No node has a name property:** names live in `BNCH` instead (§6).
- Property IDs run `0x08001957`–`0x0800196A`: shifted from, but parallel to, the PC's `0x08001980`–`0x08001993`.

---

## 6. `BNCH`: the shared name table

PS2 only (163 KB in FISH; none in any PC file). Decoded 2026-07-08, except the records.

```
[uint32 build date]          20060316 = 2006-03-16
[uint32 size − 8]
[~101.8 KB record array]
[small trailer: 0xFF-filled gaps and a few counts]
[~58 KB string pool]
```

### The string pool (decoded)

- **3,495 NUL-terminated names**, each stored once: mesh instances, quest and script markers (`Stage0Quest`, `ch2_intro_moviestarter`), spawn generators (`ShrimpGen1`)…
- The last 15 are exactly the names of `SCRT`'s `Screen` tree: `Whale`, `WaterSurface`, `TransparencyAbove/Below/Blur`, `ReflectionAbove/Below/Blur`, `ScreenWater/Above/Below`, `MotionBlur`, `ZZZ`, `XXX`.
- **So `BNCH` is a shared name table.** PS2 stores each name once and refers to it, instead of storing the string in each node like the PC. That's why PS2 `SCRT` nodes have no names.

### The records (not confirmed)

- **80-byte records, ~1,272 of them.** The stride is from the spacing of `[1.0, 1.0, 1.0, 1.0]` groups: 206 found, mostly 80 bytes apart, all gaps multiples of 80.
- **Guess:** 5 rows of 4 floats: a scale or colour multiplier, three rotation rows, and a position. That would be the PC's 12-float transform padded to 16-byte rows for the PS2's vector unit. Not checked against known positions.
- **1,272 records against 3,495 names:** how a record maps to its name isn't known. Maybe only some objects have records, or there's an index table not yet found.

---

## 7. Open questions

- `SSET` and `STTA` in meshes: probably per-strip material or smoothing data (`STTA` looks like a small second index table).
- `POSS`'s `w` component.
- `MATS`'s value (e.g. 1034): probably a `GMAT` resource ID, not confirmed.
- `BNCH` record fields and the record ↔ name mapping.
- The two undecoded texture formats (`0x1`, `0x800014`).

---

## 8. Old mistakes

| Old claim | Now |
|---|---|
| `_FISH.GDE` is a small early PC development build | A PS2 file from the disc |
| `ZIPN` is compressed data | Native GS pixel storage |
| In "GTEXT" blocks, the second field is the texture ID | The first is (it increases per texture); the second is a constant |
| The PC file lacks `RSPR`, `SCRT` and `SKIP` | It has them; earlier scans stopped after `BRTR`. Only `BNCH` is PS2-only. |

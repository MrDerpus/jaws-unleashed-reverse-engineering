# Texture formats (`GTEX`) and the texture database

**In short:** every PC texture is a `GTEX` chunk holding a TGA image.
- Two variants: **plain**, and one with an **`OBPR`** property block.
- Pixels are 24-bit BGR, 32-bit BGRA, or 8-bit with a palette, stored bottom-up.
- Cyan `#00FFFF` is the transparent colour key.
- "GTEXT" is not a tag; it's `GTEX` followed by a size byte.
- **Texture IDs collide across levels:** the same ID can be a different image in another level, so always look textures up in the same level.

Extractors: `scripts/rip_textures.py` (plain) and `scripts/rip_gtex.py` (`OBPR` variant). Writing new textures: `docs/brtr_editing.md` §8. PS2 textures: `docs/ps2_asset_extraction.md`.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/texture_format_old_2026-11-27.md`.

---

## Contents

1. [The two variants](#1-the-two-variants)
2. [Plain variant layout](#2-plain-variant-layout)
3. [`OBPR` variant layout](#3-obpr-variant-layout)
4. [Pixel formats](#4-pixel-formats)
5. [Extraction](#5-extraction)
6. [The texture database](#6-the-texture-database)
7. [Notable textures](#7-notable-textures)
8. [Old mistakes](#8-old-mistakes)

---

## 1. The two variants

Walking `RSRC` as a chunk chain shows every texture is a plain `GTEX` chunk. FISH has 321.

| Variant | FISH count | Payload starts | Extractor |
|---|---|---|---|
| **Plain** | 258 | `[id][flags 1][stamp 0x0131F253][0][w][h][bpp]TGAN` | `rip_textures.py` (calls it "GTEXT") |
| **With `OBPR`** | 63 | `[id][flags 0x21]OBPR…[stamp][0][w][h][bpp]TGAN` | `rip_gtex.py` |

- The `OBPR` block holds a `PROP` with a type tag: `TEXB`, `TEXH` or `TEXD`. What they mean isn't known.
- **Why "GTEXT":** the size field after `GTEX` has low byte `0x54` (`'T'`) for most 24-bit sizes. Example: 512×512×3 + 0x54 = `0x000C0054`.
- Don't trust a raw `GTEXT` string match without checking the size. Many are coincidences inside other data.

---

## 2. Plain variant layout

Offsets from the `GTEX` tag:

| Offset | Field |
|---|---|
| `+0x00` | `GTEX` tag |
| `+0x04` | Block size |
| `+0x08` | Texture ID |
| `+0x18` | Width |
| `+0x1C` | Height |
| `+0x20` | Bits per pixel |
| `+0x24` | `TGAN` and 8 more bytes |
| `+0x30` | Standard 18-byte TGA 1.0 header (repeats width, height, bpp) |
| **`+0x42`** | **Pixel data** |

- Pixel byte count = `block_size − 0x54`.
- After the pixels there's a 26-byte TGA 2.0 footer (8 zero bytes + `TRUEVISION-XFILE.\0`). 18 of its bytes fall inside the block size; the other 8 spill past it.

**Evidence:** on all 242 real plain blocks in FISH, the TGA header's width, height and bpp (`+0x3C`/`+0x3E`/`+0x40`) match the fields at `+0x18`/`+0x1C`/`+0x20`. A "Sole Predator" title texture that came out sheared under the old offset extracts cleanly at `+0x42`.

---

## 3. `OBPR` variant layout

```
[GTEX][block_size]
  [texture_id][flags]
  [optional OBPR / PROP blocks]
  [width][height][bpp]          always the 3 words just before TGAN
  TGAN
    [4-byte size prefix = tgan_size − 4]
    [18-byte TGA 1.0 header]
    [pixel data]
    [sometimes: 26-byte TGA 2.0 footer]
```

- **Pixel data always starts at `tgan_pos + 8 + 22`** (a fixed 22-byte header: 4 + 18).
- Don't compute the header size as `tgan_size − pixel_size`. `tgan_size` sometimes includes the footer and sometimes doesn't (both seen in FISH).
- **Evidence:** on 90 of 90 sampled FISH blocks, the TGA header's width, height and bpp match the values before `TGAN`.

**Blocks to skip:**
- 32-bit blocks without `TGAN`: metadata or reference blocks with no pixels.
- 32-bit blocks with descriptor `0x00` and all-zero pixels: **runtime render targets** the engine fills in. Exporting them blank is correct.

**Other `TGAN`-family tags** in the exe's dispatch: `TGAF`, `DXTF`, `ZIPN`, `ZIPT`.
- In PC `.GDW` files, `DXTF`/`ZIPN`/`ZIPT` matches are coincidences inside other data.
- `ZIPN` is real on PS2: native GS pixel data, not compression (`docs/ps2_asset_extraction.md`).

---

## 4. Pixel formats

The game uses DirectX 8. 32-bit textures are `D3DFMT_A8R8G8B8`. That name lists bits from most to least significant, so the bytes in the file are B, G, R, A.

| bpp | Bytes per pixel | Order | TGA descriptor |
|---|---|---|---|
| 24 | 3 | **B, G, R** | `0x00` |
| 32 | 4 | **B, G, R, A** | `0x08` (8 alpha bits) |
| 8 | 1 | Index into a palette | |

**8-bit textures:**
- Payload = 768-byte palette (256 × RGB), then one index byte per pixel.
- Only 2 exist in all 20 levels: TITLE `0x139` and GAUNTLET `0x18B`. Both are 64×64, the same small UI icon (a vehicle silhouette).
- Both palettes are the same inverted grey ramp: `palette[i] = (255−i, 255−i, 255−i)`.
- Output suffix `idx8.png`.

**All textures are stored bottom-up.** Flip on extract.

**Chroma key: cyan `#00FFFF`** (D3D `0xFF00FFFF`, at `0x725427` in the exe).
- The extractors make pixels with R < 20, G > 235, B > 235 transparent.
- Read R, G, B from the BGR(A) positions above.

**Evidence for the byte order:** a kelp texture renders blue-teal under the old orders and correct green/brown under BGRA.

---

## 5. Extraction

| | Plain | `OBPR` |
|---|---|---|
| Script | `scripts/rip_textures.py` | `scripts/rip_gtex.py` |
| Level variable | `name` | `NAME` |
| Output | `textures/<LEVEL>/gtext/` | `textures/<LEVEL>/gtex/` |
| File name | `texture_<seq>_id<id>_<W>x<H>_<rgba32\|rgb24>.png` | `gtex_<seq>_id<id>_<W>x<H>_<rgba32\|rgb24>.png` |
| Total, all 20 levels | **4,923** (TITLE0 0; others 176–357) | **2,787** |

- Both run from `scripts/` (they use `../GAME_GDWs/`). The all-levels loop is in `CLAUDE.md` "Running Scripts".
- Unknown bpp values are written as `.raw` files in `textures/<LEVEL>/gtext/`. None remain.
- The totals are from the re-extraction of 2026-07-29 after the fixes in §8. The fixes recovered blocks that had been silently dropped (4,673 → 4,923 plain; ~1,660 → 2,787 `OBPR`). They weren't new content.

---

## 6. The texture database

`textures/texture_db.json`, built by `python3 scripts/build_texture_db.py` (run again after re-extracting).

**Contents (all 20 levels):**
- **1,049 distinct texture IDs**, in the range 1–4146 (3,097 gaps).
- **7,710 entries** (one per level the ID appears in).
- **911 IDs appear in more than one level**; 138 in only one.

**Schema:**

```json
{
  "<texture_id>": [
    { "gdw": "AQUARIUM", "file": "textures/AQUARIUM/gtext/texture_0042_id0000002a_256x256_rgb24.png",
      "w": 256, "h": 256, "bpp": 24, "src": "GTEXT" }
  ]
}
```

**The same ID is not always the same image.**
- Example: ID `0x2E9` (745) is three unrelated images:

  | Level | Image | Size |
  |---|---|---|
  | BEACH | A Spanish "ability unlocked" tutorial popup | 640×480 |
  | OPEN_NW | "The Underwater Caves / Loading..." splash | 1024×512 |
  | OPEN_NE | The Amity Island map (§7) | 512×256 |

- The other 910 shared IDs haven't been checked one by one. Treat "same ID in two levels" as unverified.
- Texture binding (`docs/rsrc_formats.md` §3) therefore looks textures up in the same level only.

---

## 7. Notable textures

### The Amity Island map

- `OPEN_NE` `gtex_0123_id000002e9_512x256_rgba32.png`: the overview map shown on `^MAP^` (`MAP OF AMITY ISLAND` strings in the exe; `docs/mission_system.md`). Normal shipped UI.
- Its painting shows a rounded landform inland near BEACH, with a lighter, stream-like gap in the trees leading to it from the coast. It was looked at during the BEACH "submarine objective" investigation. That turned out not to be cut content (a stationary SeaSeeker; `docs/cut_content.md`), and a painted map isn't terrain data anyway.

### Artist's handwritten notes on the Sharpnose Shark skin

Found 2026-11-25. The **Sharpnose Shark** skin (256×256, 24-bit) has an artist's handwritten notes in its unused space.

**Where it is** (identical image, same md5):

| Level | Texture | Material | Mesh | Node |
|---|---|---|---|---|
| TOWN | `0x152` (`textures/TOWN/gtext/texture_0189_id00000152_256x256_rgb24.png`) | 1268 | 2765 (`models/TOWN/TOWN_mesh_0398.obj`) | `SharpnoseShark SkeletonModel` 33110 |
| OPEN_NE | `0x15F` | 1427 | 3145 | 45876, under `SharpnoseSharkOverlay` |
| TITLE | `0xEC` | 716 | 1050 | 613, under `Animal Bios Menu Root` › `Animal Bios Description MenuItem` › `Animal Bios Description Page 50` |

- The mesh has one submesh of 504 triangles.
- So the shark swims as an ambient creature in TOWN and OPEN_NE, and shows in the Animal Bios menu.
- The PS2 build has the notes too: `TITLE_PS2` `0xF2` (256×256) and `OPEN_NE_PS2` `0x15F` (128×128).

**Transcription** (white handwriting over a painted mossy wall with a brick patch):
- Top centre: *"The tooth is from a meglodon …. the biggest shark known in prehistory"*, then a small doodle. "meglodon" is the artist's spelling. It refers to the painted megalodon tooth at the right edge.
- Bottom left, diagonal: *"I feel strange leaving all this space unused … but I also didn't want to stretch the texture"*.
- Squeezed in above it: *"Like anyone will ever see this"*. A mark above that looks like an initial ("R"?), unreadable.
- At the bottom: *"I like this Brick"*, with an arrow to the brick patch.

**Never visible in game.**
- The model's UVs (V stored offset by +1, range 1–2) cover 44 % of the sheet: body, fins, the open-mouth piece, and a small triangle on the tooth.
- The notes, the brick and the wall are outside every UV island. The artist's guess was right.

---

## 8. Old mistakes

| Old claim | Now |
|---|---|
| "GTEXT" and "GTEX" are two texture systems | One tag, `GTEX`, with two payload variants (2026-10-03) |
| Plain pixels start at `+0x54` | `+0x42`. The old value mixed up the TGA header with the trailing footer and produced sheared images (2026-07-29). |
| `OBPR`-variant header size = `tgan_size − pixel_size` | Fixed 22 bytes; `tgan_size` sometimes includes the footer (2026-07-29) |
| 32-bit plain textures are RGBA, no swap | BGRA (a blue tint on warm textures, 2026-07-29) |
| 32-bit `OBPR` textures are ARGB | BGRA (an R/G swap, 2026-07-29) |
| 24-bit `OBPR` textures are R, B, G (swap G↔B) | Straight BGR (2026-07-29) |
| 59 `.raw` dumps are textures in an unknown format | 2 were the 8-bit textures; 57 were false `GTEXT` matches inside `GMAT` material data (readable `SHIN`/`SILL`/`TRAN`/`COLS` tags, absurd sizes). The bad output files were deleted 2026-07-29; the game files are untouched. |
| One global texture ID space; a level pulls textures from several GDWs | IDs collide across levels (§6). Look up in the same level only. |

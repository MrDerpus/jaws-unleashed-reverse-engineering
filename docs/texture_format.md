# Texture formats (GTEX / "GTEXT") and the texture database

Moved word for word from the root `CLAUDE.md` on 2026-11-25 to keep that file short. Where this disagrees with older docs, this text is the newer one.

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

## Artist's handwritten notes on the Sharpnose Shark skin (found 2026-11-25)

The **Sharpnose Shark** skin is a 256×256 24bpp texture with an artist's handwritten notes in its unused space. The same image (identical md5) appears in three GDWs under three IDs: `TOWN` `0x152` (`textures/TOWN/gtext/texture_0189_id00000152_256x256_rgb24.png`), `TITLE` `0xEC` and `OPEN_NE` `0x15F`. The PS2 build has it as well (`TITLE_PS2` `0xF2` at 256×256, `OPEN_NE_PS2` `0x15F` at 128×128), and the notes are present in both PS2 copies.

**Chain:** texture → `GMAT` (TOWN 1268 / TITLE 716 / OPEN_NE 1427) → one-submesh, 504-triangle `GMDL` (TOWN 2765 = `models/TOWN/TOWN_mesh_0398.obj`, TITLE 1050, OPEN_NE 3145) → node `SharpnoseShark SkeletonModel` (TOWN 33110; OPEN_NE 45876 under `SharpnoseSharkOverlay`; TITLE 613 under `Animal Bios Menu Root` › `Animal Bios Description MenuItem` › `Animal Bios Description Page 50`). So the model appears as an ambient creature in TOWN and OPEN_NE, and in the Animal Bios menu.

**Transcription** (white handwriting over a painted mossy wall with a brick patch):
- Top centre: *"The tooth is from a meglodon …. the biggest shark known in prehistory"*, with a small doodle after it. "meglodon" is the artist's spelling. It refers to the painted megalodon tooth at the right edge.
- Bottom left, written diagonally: *"I feel strange leaving all this space unused … but I also didn't want to stretch the texture"*. Squeezed in above it: *"Like anyone will ever see this"*. The mark above that looks like an initial ("R"?) and is unreadable. At the bottom: *"I like this Brick"*, with an arrow pointing at the brick patch.

**UV check:** the model's UVs (V stored offset by +1, range 1–2) cover 44% of the sheet: the body, the fins, the open-mouth/jaw piece and a small triangle on the megalodon tooth. **The notes, the brick and the wall background are outside every UV island, so they are never visible in game.** The artist's guess was right.

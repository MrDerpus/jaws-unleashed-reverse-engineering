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

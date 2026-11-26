# Jaws.exe Static Analysis (Ghidra)

*Started 2026-10-01. `CLAUDE.md` at the project root is the actively-maintained summary; this file holds the detail.*

The first time this project decompiled the game executable itself rather than only parsing `.GDW` data. It solved the long-standing "where is the player's position" problem (see `mod/README.md`, XYZ Overlay Accuracy) and fed the mod's teleport, invincibility and hunger features. All addresses below are virtual addresses in the shipped PC `game_binary/Jaws.exe`. It has no ASLR and a fixed image base of `0x400000`, so they're stable across runs.

---

## Tooling

- **Ghidra 12.1.4** at `~/tools/ghidra_12.1.4_PUBLIC` (needs a full JDK 21: `openjdk-21-jdk`. The JRE alone is rejected). `support/launch.properties` has `JAVA_HOME_OVERRIDE=/usr/lib/jvm/java-21-openjdk-amd64`.
- **Project:** `~/tools/ghidra_projects/JAWS.gpr`, with `Jaws.exe` imported and fully auto-analyzed (~10 min). Open it in the GUI with `~/tools/ghidra_12.1.4_PUBLIC/ghidraRun` → File → Open Project. Close the GUI before running headless scripts against the same project.
- **Headless helper scripts** (copies in `scripts/ghidra/`, run from `~/tools/ghidra_scripts/`):
  - `DecompStringRefs.java <outfile> <string>...` decompiles every function referencing an exact-match string.
  - `DecompAt.java <outfile> <hexaddr>...` decompiles the function containing each address and lists its callers.
  - `RefsDecomp.java <outfile> <addr|f:addr>...` decompiles every function that references each address (e.g. a global or a string), each followed by its callers; `f:ADDR` decompiles the function containing ADDR, creating it if missing (used on the Sentinels `0.BIN` for `EXTR`, 2026-11-26). Script paths must not contain a dash (Ghidra OSGi bundle error).
  ```bash
  ~/tools/ghidra_12.1.4_PUBLIC/support/analyzeHeadless ~/tools/ghidra_projects JAWS \
      -process Jaws.exe -noanalysis -readOnly \
      -scriptPath ~/tools/ghidra_scripts -postScript DecompAt.java /tmp/out.c 0x65eda0
  ```
- **Limitation:** many small functions are reached only through vtables or static-initializer tables and are never recognized as functions by auto-analysis. Ghidra reports `ref from ... in <none>` for them. Read those with plain `i686-w64-mingw32-objdump -d -M intel --start-address=... --stop-address=...` instead. Plain byte-pattern scans in Python over the exe also worked well (all the field-registration, vtable and call-site searches below were done that way).

**Exe sections** (`objdump -h`): `.text` `0x401000`–`0x7CE000`, `.rdata` `0x7CE000`–`0x845000`, `.data` `0x845000`–`0xE6C000` (size `0x627000`), `.idata`, `.rsrc`. Imports include `d3d8.dll` (`Direct3DCreate8` only), `DINPUT8.dll`, `DSOUND.dll`, `WINMM.dll`. No D3DX, no packer.

---

## Ecco: Defender debug symbols (`ecco.elf`, found 2026-11-25)

The Appaloosa Dreamcast dev kit (`docs/GDW_FORMAT.md` "The dev kit") holds an **unstripped build of Ecco: Defender**: `ECCO.ELF` (13,166,002 bytes, 2000-06-01/02) plus its linker map `0.MAP` (`Link Map of "debug.elf"`, 25,755 lines). Identical copies sit on the `144 M` dev disc and in the recovered hard disk's `Z` build folder; the `269 M` disc has the same `0.MAP`. It is the build behind that date's `0.BIN`.

- Renesas SH-4 ELF, little-endian, Hitachi/cfront-style mangled C++ (`_Execute__11NAWhirl2000Fv` = `NAWhirl2000::Execute()`).
- **12,156 named functions**, ~180 source files (`gdbrick.cpp`, `gdres.cpp`, `gdtile.cpp`, `gdcamera.cpp`, `gdexec.cpp`, `NAWhirl.cpp`, `Shark_1.cpp`, `Dclasses.cpp`, …; full list via the map's `From file:` lines).
- **`.debug` = DWARF version 1** (7.3 MB) with complete class layouts: 2,168 classes/structs with base classes, member names, types and offsets. `.line` holds line tables. readelf/objdump/Ghidra don't read DWARF v1, so `scripts/dwarf1_classes.py` parses it; the full dump is `docs/ecco_defender_classes.txt`.
- **How it carries over to Jaws:** names do, offsets only partly. Jaws is a later code line (via Sentinels), x86 instead of SH-4.
  - Class-specific fields mostly keep their order and spacing; only the base class in front of them grew. Comparing the Jaws reflection table (`dump_class_fields.py`) with the Defender layouts by field name gives one constant shift per class for `GDFog`, `GDSector`, `GDFont`, `GDRotSprite`, `NAWhirl2000`, `NAFade`, `MLParticle`, `MLOldParticle`, `MLModelParticle` and others; `GDModel`, `GDSprite`, `NAFlare`, `NAParticle2000` show 2–3 shifts (fields added in between).
  - The core `GDBrick` was reorganised (table in "Scene Object (Brick) Memory Layout").
  - The SH-4 code can't be matched to x86 byte for byte; functions have to be matched by strings, constants, field offsets and call structure.
- **Jaws functions named from it (2026-11-25): 812**, applied to the Ghidra project (backup before: `~/tools/ghidra_projects/JAWS.rep.bak_preEccoNames`) and listed in `docs/jaws_function_names.tsv` (Jaws address, name, Defender symbol, how it was found). Three independent methods, each checked against the others:
  - **Vtables (605):** `scripts/ecco_jaws_vtables.py`. 424 classes (object, `Props` and `Factory` vtables) exist in both games. Per family, Defender slots are aligned to Jaws slots by *which classes override them* (Defender: the slot's symbol belongs to the class; Jaws: the slot differs from the parent's). Jaws inserted virtuals early in `GDAct`/`GDBrick`: `GDAct` `GetFactory` 8 → 16, `Execute` 10 → **18** (the shark tick slot), `OnActivate`/`OnDeactivate` 12/13 → 20/21; `GDBrick` `GetFactory` 11 → 19, `Execute` 14 → **22** (the `NAWhirl2000` tick `0x63D100`). Destructor = slot 0 everywhere. The Jaws "factory vtable" is Defender's `<Class>Factory` (`GetClassName`, `Create`, `CreateProps`, `DeleteProps`, `GetBase`).
  - **Strings and constants (128):** `scripts/ecco_jaws_strings.py`. Defender's compiler loads strings as *table base + offset* from the literal pool; both words are combined. Gives the whole `GDFile` text reader/writer (`ReadChunkID`, `ReadInt`, `WriteResID`…) and, through chunk tags and version stamps, the GDW loader: `GDLoadGame` (`0x693180`, `0x6C4E90`), `GDBrickProps::LoadTree` (`0x699360`), `GDObjWizard::LoadClasses` (`0x70C580`), `GDMesh::Load` (`0x6D15F0`), `GDMaterial::Load` (`0x6CE010`), `GDTexture::Load` (`0x7053C0`), `GDBoneData::Load`, `GDMeshRegions::Load` (`0x6E3CB0`), `GDTileMap::LoadWorldDim`, `GDMovie::Load`/`Play`.
  - **Call graph and locality (79):** `scripts/ecco_jaws_callgraph.py` spreads names from known pairs to their callees/callers (order-independent voting, both sides must agree), and fills gaps between two named functions of the same Defender source file when both gaps hold the same number of functions (file from `0.MAP`). Found e.g. `GDBrick::CalcAbsMatrix` `0x696EA0`, `GDBrick::InvalidatePos` `0x6970B0`, `GDMatrix::Multiply` `0x6D0070`, `GDBase::GetObj` `0x692650`, and `NAWhirl2000::CalculateDisplacement` `0x63BD80` (already known as the current's force function: independent confirmation).
  - **Precision check:** neighbouring named functions in Jaws should come from the same Defender source file. They do for 96% (vtables), 94% (strings) and 79% (call graph; some are file boundaries). Treat call-graph and locality names as likely, not certain.
  - **Limits:** only code shared with Defender can be named (Jaws-only classes such as `MLSharkCtrl` get nothing). Most names are virtuals (destructors, `GetFactory`, `Execute`, `OnActivate`…); non-virtual engine code is reached only through the call graph, which stalls because the compilers inline differently. `0.MAP` is from a slightly different build (`debug.elf`), so its addresses don't match the ELF; it's only used for file membership.
  - Pipeline: Ghidra `scripts/ghidra/FuncRanges.java` (function list) + the Jaws class → factory/object/props vtable table from the earlier `JawsFactories` Ghidra script (`~/tools/ghidra_scripts`), then the three scripts above; see `docs/scripts.md`.
- **GDED text format: Jaws can read it, but nothing writes it (checked 2026-11-25).**
  - `GDFile` (base vtable `0x7F5B2C`, abstract: slots 1–5/7/8 are `_purecall`) handles both encodings. Layout as in Defender, shifted by the vptr: `+0x04` `m_nMode`, `+0x08` `m_nType` (**0 = binary, 1 = text**), `+0x10` written tabs, `+0x14` chunk level. Every `Read*`/`Write*` branches on `m_nType`; in text mode the writers print `Name: value` lines indented by chunk level (`%s: "%s"`, `%s: %c%c%c%c ` for resource IDs, `%s: %d-%d-%d` for class IDs, keyword defaults such as `STRING`, `ResID`, `CHAR`), and the readers tokenise (errors "Bad integer value.", "Bad Chunk ID (included non ASCII characters).").
  - **`ReadHeader` `0x6BBAC0`, called from `GDLoadGame` `0x693180`,** reads `GDED`, then `BINARY` → type 0 or **`TEXT` → type 1**, anything else fails, then `FORMAT, VERSION a.b.c.d`. So a level file starting `GDED TEXT FORMAT, VERSION …` passes the header check and the chunk loaders then read through the text tokenizer. Untested in-game; whether every loader copes (e.g. raw buffers via `ReadMemBuffer`) is unknown, and there is no text sample to start from.
  - **The writer is unreachable.** `WriteHeader` (`0x6BA970`, slot 32: writes `GDED` + `TEXT`/`BINARY` + ` FORMAT, VERSION %d.%d.%d.%d.`) and all other `Write*` methods are referenced only from the four `GDFile` vtables, and:
    - File classes (MSVC virtual inheritance): A `0x7F5C0C` (disk file of the PC file system), B `0x7F5CF4` = `GDMemFile` (mode 1 only allocates a growing 16 KB-step buffer; `Close` frees it, never writes to disk), C `0x7F5DDC` (wraps a stream, created by the stage loader `0x6C4382`/`0x6C5501`).
    - File systems sit in a priority list at `0x920D00` (PC file system vtable `0x7FB5DC`: `GetFileSize` `0x727F90`, `OpenFile` `0x728170`, `CreateFile` `0x6C2240` at `+0x28`, `GetFileData` `0x728060`); the engine keeps the current one at `[0x920E24]+0x8C`. Every disk open passes mode 0 (read).
    - The only `CreateFile` call (`0x6C4BBB`, async stage loader `0x6C4AB0`, state 2) opens the memory file in mode 0 and attaches the already loaded level data (`0x6C0D60`).
    - No game code opens a file in mode 1; Defender's game build likewise has `Load(GDFile&)` for every class but no `Save`: saving lived in the editor (Game World Builder), and the writer primitives survive only because they are virtual.
  - **Feasibility check (2026-11-25, static): a full text level looks loadable.**
    - All 23 `GDFile` read helpers (`0x6BC240`–`0x6C08A0`) have a text branch (`m_nType == 1`). They tokenise on ` \r\n\t`, read a `label:` (delimiter `:`), then the value. Strings are quoted (`"`), and numbers go through `sscanf`.
    - Chunks: `ReadChunkID` reads `Chunk: TAGN` (the writer prints `Chunk: %c%c%c%c %s%s%s {`, with an optional `/name/` comment) and returns end-of-chunk on `}`. The skip function `0x6C08A0` skips an unknown chunk by counting braces, ignoring any inside quotes.
    - Raw buffers (`ReadMemBuffer` `0x6BFCE0`: texture pixels `TGAN`, `DXTF` data `0x703B90`, `BNCH`, sample data and so on) have a text form: label, then one `%x` hex token per byte. That roughly triples the size but works. Binary-only alignment padding is skipped in text mode.
    - Of the 79 non-helper functions that read through `GDFile`, the only direct raw read (`vtable+0x1C`) is in the `FDIR`/`FSIZ` handler `0x6C3D90`: 24 raw bytes per `FDIR` name. That chunk is only needed for the embedded loading-screen sub-archives, so it can be left out (or written byte for byte). The other two hits (`0x690AD0`, `0x691030`) call an animation track object's own `Load`, not a file read.
    - `GDLoadGame` calls `GetFileSize` (`+0x14`) only for the loading bar. A level without `BRTR` hangs forever ("Brick Tree not found").
    - **In-game test PASSED (2026-11-25, user-confirmed):** `custom_levels/TXTMODE.GDW`, the pruned blank FISH base (105.6 MB binary) rewritten entirely in the text format (240 MB of text + the unchanged 14 MB loading-screen sub-archive appended, FDIR offsets and FSIZ patched), loads through F9 and plays normally; loading takes about 20 s (the game reads text one byte per virtual call). So Jaws still loads the editor's text format end to end.
    - How the text was produced: the mod's GDFile trace (`mod/src/gdtrace.cpp`, switch file `jaws_gdfile_trace.on`) logs every raw read with its caller during a binary load; `scripts/gdw_to_text.py` maps each caller to its reader (int, real, string, vector, ...) and writes that value in the reader's text syntax. Return addresses used: chunk-end decision `Tell` `0x6C0375`, tag/size reads `0x6C03D1`/`0x6C03E7`, unknown-chunk skip seek `0x6C08C2`.
    - **Text edit test PASSED (2026-11-25, user-confirmed):** changing `FogAbove`'s colour (`PROP 0x08001853`) in the text level to 0.56, 0, 0.29 changed the above-water fog in-game. Verdict (user): working, but not practical as an editing route compared with the binary tools; kept as a curiosity, no further work planned.
    - **Editing rules (2026-11-25):** a text editor that saves the whole file breaks it: the header must end in raw `\r\n\r\n` (read as 4 raw bytes; converted to `\n\n` the load hangs), and the raw `FDIR` name plus the binary loading-screen sub-archive after the text get re-encoded (user's editor grew the file by 7 MB). Also the `FDIR` offsets (and `FSIZ`) are absolute, so an edit must keep the byte length (pad a shortened line with trailing spaces; the reader skips them) or the offsets must be recomputed. Safe ways: `sed`/a script on the file, or an editor that keeps binary bytes and CRLF untouched.
    - Text cannot hold NaN/Inf (`atof`): the only ones in stock data are 3,293 uninitialised weights of unused bone slots (index −1) in `WGHT`, written as 0.
    - The trace needs a load of the *same* file; one trace converts one level. Example `TXTBASE` load: 1.68 M reads, 76,762 chunks (1,763 skipped by the loader as unknown).
  - Side effect: Jaws `GDFile` slot 33 is `WriteChar` (default keyword `"CHAR"`); the string matcher had paired it with `NAGeneralAct::FireIceNeedles` (dropped, not applied).
- **`/DEBUGBIN/0.BIN` is not usable** (2,919,116 bytes, 2000-04-17; same bytes on the `132 M` and `144 M` discs and the hard disk). Only the first 0x80000 bytes are program code; the rest is GDE level data (it matches part of the hard disk's `330_MHQ.gde` but not the disc's newer `330_MHQ.GDE`). The file was already cross-linked when it was burned in 2000. No strings, no symbols.

---

## Reflection Field Registration (class → field table)

Every reflected class field is registered by a tiny static-initializer stub, all calling one recorder function, **`0x70B6A0`** (6,457 call sites):

```
mov  eax, [typedesc_ptr]     ; field type descriptor
push A                       ; small integer (see below)
push B                       ; small integer (see below)
push eax
push classdesc               ; class descriptor address
push name                    ; "m_..." field name string
push 0
mov  ecx, fielddesc          ; static field-descriptor object being filled
call 0x70B6A0                ; just stores the args + links into a global list at 0x93C630
```

Class names come from small getter stubs next to each class's constructor: `mov eax, <name string>; ret`, then `mov eax, [parent?]; ret`, then `mov eax, <classdesc>; ret` (twice).

**`scripts/dump_class_fields.py <out.json>`** scans the exe for both patterns. It finds **6,457 fields across 691 class descriptors**, but only 132 descriptors get a resolved class name, because the name-getter pattern match is incomplete. Output is `{"ClassName@0xdesc": [{name, a, b, typedesc_ptr, reg}, ...]}`.

**Resolved 2026-10-03, see the `GDControl` section below: `a` = props-object offset of the property wrapper, `b` = runtime-object offset of its mirror, value at +4.** Earlier notes: One looks like an in-object offset, but the evidence is mixed:
- In subclasses, the first integer starts right after the base class (`GDModel` fields start at `0xE0`), which suggests offset.
- But for the base brick class, `mtx` registers as (`0x30`, `0x4C`). The engine's own world-matrix code reads the local matrix at **`+0x50`**, which is `0x4C + 4`. That fits the second integer being the offset of a property wrapper with a 4-byte header, not the first.
- Most simple fields are spaced 8 bytes apart even when they're floats, consistent with each property being a `[4-byte header][value]` wrapper.

**Treat the dumped integers as hints only, and confirm any offset against code that actually reads it** (as done for every offset in the sections below).

---

## Scene Object ("Brick") Memory Layout

From the engine's world-matrix updater **`0x696EA0`** (called before any world-space read when the stale flag is set):

| Offset | Field |
|---|---|
| `+0x0C` | flags, loaded from the node's saved `m_nFlags` (BRTR `PROP 0x080017D9`). `0x20` = cached world matrix is stale; `0x20000000` = skip parent composition (the transform is absolute world space). Confirmed 2026-10-01 against BRTR data: FISH `fenyo` trees and `Box0N` children with flags `0x2000005A` only land in the right place when not composed; the updater sets `0x400` after recomputing |
| `+0x14` | parent brick pointer (or null) |
| `+0x4C` | property header for the local matrix |
| `+0x50` | **local transform**: 12 floats, X/Y/Z basis rows then translation (same layout as BRTR `PROP 0x080017DA`) |
| `+0x84` | **cached world transform** = local × parent world (computed by `0x6D0070`), same layout. **World translation at `+0xA8`** |

The updater recurses up the parent chain first if the parent is also stale. This matches the BRTR-side finding that nested `CHBR` transforms are local to their parent.

The base brick class's field registration (descriptor `0x91DAF0`) lists `m_Name`, `m_nFlags`, `mtx`, `m_ExecFilter`, `m_CameraFilter`, `m_Viewport`, `m_CreatorDistance`, `m_RoomMask`, in the same order BRTR stores name → flags → transform. Its strings sit next to the `(%.0f %.0f %.0f) [%.0f %.0f %.0f]` and `GDStdBrick` strings, so this is very likely `GDStdBrick`.

**Compared with Ecco: Defender's `GDBrick` (2026-11-25, from `ecco.elf` debug info, see "Ecco: Defender debug symbols" below).** Jaws' `0x696EA0` is Defender's `GDBrick::CalcAbsMatrix`, same logic. The names carry over but the layout was reorganised. Jaws offsets below come from decompiling `0x696EA0`, `0x696F40`, `0x696580`, `0x695F30` (collision pair test) and `0x6974B0` (`SetAbsMatrix`-like: sets `0x40420`, then walks children).

| Defender field | Defender | Jaws | Jaws evidence |
|---|---|---|---|
| `m_nFlags` value (`GDPropFlags.i`) | `+0x08` | `+0x0C` | flags `0x20` stale, `0x400` inverse dirty, `0x40000`, `0x20000000` absolute |
| `m_pParent` | `+0x14` | `+0x14` | parent composition |
| `m_pChild` / sibling `m_pNext` | `+0x70` / `+0x18` | first child `+0x1C`, next sibling `+0x10` | `0x6974B0` loop `[+0x1C]` → `[+0x10]` |
| `m_PrimAttacks` / `m_PrimSensors` | `+0xB4` / `+0xB8` | `+0x3C` / `+0x40` | `0x695F30`: `mask & a[+0x3C] & b[+0x40]` |
| `mtx` (`GDPropMatrix`: 4-byte header + `GDMatrix`) | `+0x24` | `+0x4C` (matrix `+0x50`) | |
| `m_CurMtx` (world) | `+0x80` | `+0x84` | |
| inverse world matrix | (none) | `+0xB4` | rebuilt by `0x6D0370` when flag `0x400` is set; new in Jaws |
| `m_pOldMtx` (previous-frame matrix) | `+0xB0` | probably `+0xE4` | compared with `+0x84` to detect movement |

`GDMatrix` = `GDMatrix3` (`_11`…`_33`, 9 floats) + `GDVect t`, which is why world translation sits at `+0x84 + 0x24 = +0xA8`. Not mapped yet: Jaws `+0x18` (pointer whose `+0xD8` is used as a fallback collision list), `+0xE8`, `+0xF0`, `+0xF4`.

---

## Player Shark Controller

### Finding it

- **`NAPredator` is not the shark.** Its fields (`m_magnification`, `m_power`, `m_freqpower`, `m_strength`, `m_smoothrate`) describe the **"predator vision" screen effect** (compare `PredatorEffectNONPS2` in FISH.GDW's BRTR). `docs/class_registry.md` previously listed it as "Shark/predator AI".
- The shark is driven by **`MLSharkCtrl`** (class descriptor `0x90B388`, one field `m_cfg` → `SharkConfig`). Its strings sit among the `Jaws.*` sound events and debug strings (`SharkRelPos`, `CHEAT`, `autocolli %5.0f`, `TailCombo!`).
- The debug routine that prints **`"SharkRelPos"`** (`0x671060`) is slot 21 of vtable **`0x7F28FC`**. That vtable is installed by a constructor at **`0x664BD8`**, which also does `mov [0x90BC04], esi`. The matching destructor at `0x664C20` clears the global back to 0. **So `0x90BC04` is a singleton pointer to the player shark controller.** ~194 code references to it.

### Pointer chain (verified in-game 2026-10-01)

```
ctrl  = *(DWORD*)0x90BC04          // null outside gameplay (menus, loading)
brick = *(DWORD*)(ctrl + 0x50)     // the shark's scene object
pos   = (float*)(brick + 0xA8)     // world X, Y, Z
```

Verified on FISH.GDW: spawn reads `(2000, -6.4, -3630.7)` against the BRTR spawn (`GWside` / `SharkPosReal`) at `(1998, -7, -3628)`. Values change smoothly while swimming and repeat exactly at the same spot, and Y ≈ 0 at the water surface.

**Facing:** the shark model faces its **local +Z**. In FISH.GDW's BRTR, the `GWside` child nodes `FixedBrickHead` / `Mouthbrickcsont` / `VerBrick` sit at local +Z (1.4–1.7), the tail (`FixedBrickFarok`, "farok" = tail) at −3.4, the dorsal fin (`FelsoUszonyFixedBrick`) at +Y, and the right fin (`Jobb...` = right) at +X. So heading comes from the world matrix's Z basis row (floats 6–8 at `+0x84`). The model has a uniform scale of ~2.1, so normalize first.

### Controller fields (confirmed by reading code)

| Offset | Meaning | Evidence |
|---|---|---|
| `+0x50` | shark brick pointer | `SharkRelPos` routine |
| `+0x54` | `SharkConfig` object pointer | ability setup reads tuning floats from it (`+0xD84`, `+0xD8C`, `+0x10C`, `+0xB98`) |
| `+0x240` | state machine value (`int`). **`7` = dead** | is-dead check `0x664770`; state setter below |
| `+0x204` | held prey / bite target (receives damage message `0x27`) | bite damage `0x65CB30` (2026-10-12) |
| `+0x248` | sub-state while holding prey (`6` = full `Shark_GW_Pitbull04`, `9`/`0x16` = 2-bite variants, `0xF` = shake/tear) | bite damage `0x65CB30` (2026-10-12) |
| `+0x244` | secondary state value (initialized to `-1` alongside `+0x240`) | constructor `0x66693D` |
| `+0x2A8` | **max health** | ability setup `0x53AD50` |
| `+0x2AC` | **max hunger** | ability setup `0x53AD50` |
| `+0x2B0` | **current health** (float) | clamped to `+0x2A8`; is-dead check tests `<= 0` |
| `+0x2B4` | **current hunger** (float) | clamped to `+0x2AC`; user-verified in-game (refilling it keeps the hunger bar full) |
| `+0x72C`–`+0x73C` | five ability multipliers (floats) | ability setup: `= save_byte * const`, from save-state bytes `0x8D0124`–`0x8D0128` |
| `+0x680` | **last / collision-resolved position** (3 floats): copied from the brick's world translation after the scene update (`0x666611`), also copied from the brick at the end of the collision step `0x65BFC0` and at `0x670485` (`0x5BEB80` is just a getter returning `obj+0x24`, corrected 2026-10-12). The collision move sweeps from here to the brick's new position each frame, so a teleport must move it too (mod F8 fix, 2026-10-04). | code above; runtime scan |
| `+0x58` | object whose `+0xA8` also mirrors the shark's world position (also referenced from `+0xCC`, `+0x16C`) | runtime scan 2026-10-04 |
| `+0x810` | **collision off**: while non-zero the collision step `0x65BFC0` returns at once (no push-out, no safe-point teleport). Set to 1 by the state machine at `0x669D8C`, cleared at init `0x664EC0`; no other reader. The mod's F7 no-clip holds it at 1 (user-confirmed 2026-10-12) | `0x65C043` |
| `+0x864` / `+0x834` | safe points (two 4×3 world matrices): the shark's world matrix saved after 40 collision-free frames (`+0x89C` counter), older copy shifted to `+0x834`; flags `+0x898`/`+0x894` = valid | `0x65BFC0` |
| `+0x704` | flag; when set and the requested state is `0`, the state setter substitutes state `0x1D` (and clears controller `+0x3C`) | state setter `0x65EDA0` |

**Ability setup `0x53AD50`** recomputes max health/hunger from the ability multipliers and `SharkConfig` tuning values, then clamps current to max: `max_hp = (cfg[0xD8C] * ability[0x73C] + k1) * k2` (constants `k1`/`k2` at `0x7CE0D8` / `0x7CEB90`), and the same shape for hunger with `cfg[0xD84]` / `ability[0x738]`.

### Collision step and no-clip (2026-10-12)

Found with a hardware write-watch trace on the shark's position fields (mod `Shift+F7`, `src/hwtrace.cpp`); the static guess that `0x5BEB80` was the sweep was wrong (it is a getter returning `obj+0x24`).

- **`FUN_0065BFC0`** (controller vtable slot at `0x7F2958`) is the per-frame terrain collision step. It returns at once if `ctrl+0x810 != 0` or state is `0x10`/`0x16`. Otherwise it queries contacts with `0x6C80C0(brick, 0x18001, -1, -1, 0xE)` (result record at `[0x920E24]+0x2B8`) and pushes out with **`0x4E4DA0`** (moves the brick back along the contact normal by the penetration depth through `0x6CEFA0` (add vector to translation), then removes the velocity into the surface), up to 8 times. While holding prey (`+0x204`) it runs a paired version (`0x4E4F20`) against the prey too.
- After 8 failed tries it sets "stuck"; after more than `0x59` stuck frames it logs `SafePoint Teleport jobbik/rosszabbik` and moves the shark to a saved safe point (`+0x864`/`+0x834`), zeroing velocities. This is why an F8 teleport into solid geometry used to end up somewhere nearby, often behind a wall.
- At the end it copies the brick's world position into `+0x680`.
- **`FUN_00671AB0`** (next slot, `0x7F2960`) handles object contacts (mask `0xC00`: boats, debris; `Jaws.ImpactObject` sound, hit reactions, `autocolli hit shark`), with its own push-out loop (4 tries). It ignores `+0x810`, so no-clip still collides with those.
- `FUN_004E50D0` is the same push-out loop used by other actor classes (boats, NPCs).

**No-clip** = hold `ctrl+0x810` = 1 (mod F7). User-tested 2026-10-12: passes through the ground and most solid objects, F8 teleports into geometry stay put. (Then limited to the water; air swim added 2026-11-25, see "Water height functions, full picture".)

### State setter and every death path

**`0x65EDA0`** is a `thiscall SetState(int state, int, int)` method, ~16 KB (a big switch), ending in `ret 0xC`. Its first instruction is a 6-byte `mov edx, [0x920E24]`, which is where the mod's hook patches in. It's called with ~40 distinct state values. State `7` (dead) is requested from exactly four places:

| Call site | Trigger |
|---|---|
| `0x65B871` | **Scripted kill message.** The message handler checks for the 4-byte ID `0x4449454D` (`"MEID"` read as a dword, i.e. bytes `D I E M`), and if not already dead, zeroes current health **and** hunger, then calls `SetState(7, -1, -1)`. This is how missions kill the shark directly. |
| `0x65D871` | Normal death: current health `<= 0` → zero health, `SetState(7)`. |
| `0x668CC6` | Timer-based: a game clock (`[world+0xB0]`) compared against an int limit at controller `+0x5B0`. |
| `0x66D4E9` | Timer-based: a similar comparison against controller `+0x5AC`. |

Blocking `SetState(7)` (the mod's F11 death block) stops all four. But scripted deaths also hide the model and tell the mission the shark died through other paths, so after a blocked scripted kill the shark stays alive, invisible, and the game otherwise behaves as if it died. Health/timer deaths block cleanly.

### Bite animation `Shark_GW_Pitbull04` and bite damage (2026-10-12)

`Shark_GW_Pitbull04` is one of the great white's 73 clips (AQUARIUM `SKEL 2515`: frames 997–1036, 40 frames). It is the shark's normal grab-chew-shake move on held prey (user viewed it in Blender: "a regular eating animation"), and the bite damage is timed to frames in it. Found by searching `Jaws.exe` for the string `SHARK_GW_PITBULL04` (`0x8B7890`) with `DecompStringRefs.java`.

**Clip-frame table, `0x6651BB`–`0x6652A7`** (inside an unrecognized function near the controller constructor `0x664BD8`). For each clip name the code calls the animation object's vtable `+0x1C` (clip start frame) and `+0x20` (clip end frame) and stores the results in globals; neighbours in the same table are `SHARK_GW_RELEASE`, `SHARK_GW_KIKOP_GYORS` ("spit out, fast"), `SHARK_GW_FAROKCSAP` ("tail whip") and `SHARK_GW_DIE_I17L31O_`. Pitbull04's entries:

| Global | Value |
|---|---|
| `0x90BCB4` / `0x90BCB8` | start / end (full clip) |
| `0x90BCBC` / `0x90BCC0` / `0x90BCC4` | start +12 / +23 / +33 |
| `0x90BCC8` / `0x90BCCC` | start / end (second copy) |
| `0x90BCD0` / `0x90BCD4` | start +5 / +11 |
| `0x90BCD8` / `0x90BCDC` | start / end (third copy) |
| `0x90BCE0` / `0x90BCE4` | start +5 / +11 |

**Playback:** `0x66B187` and `0x66B475` (both in the big shark update code, not recognized as functions) call `0x65E610` (play clip, with the start/end globals and a speed from `0x5BEBC0`), set controller `+0x248` (sub-state) to `6`, and play the sound `Jaws.Chew` (`0x8B4DF5`/`0x8B4E09`).

**Damage, `0x65CB30`** (per tick, called from `0x67003B`). In state `5` (`+0x240`, prey in the mouth; `+0x204` = the held target), `0x4DD1F0(frame)` returns 1 when the animation passed `frame` this tick (previous < frame ≤ current). At each such frame the shark sends message `0x27` (damage) to the held target:

| Sub-state `+0x248` | Damage frames | Bites |
|---|---|---|
| `6` (full Pitbull04) | start +12, +23, +33 (AQUARIUM: 1009, 1020, 1030) | 3 |
| `9` | start +5, +11 | 2 |
| `0x16` (22) | start +5, +11 | 2 |

Damage = `(cfg[0xD74] * ctrl[0x730] + k1) * cfg[0x4AC]`, with `cfg` = `SharkConfig` (`ctrl+0x54`) and `k1` at `0x7CE0D8` (the same constant as max health). `ctrl+0x730` is one of the five ability multipliers loaded from the save (`+0x73C` is health and `+0x738` hunger, so this is one of the other three; probably bite strength, not confirmed). After the hit, the code starts the live action at `cfg[0x850]` (`0x6C3010`) on the target (`0x5525C0`).

Sub-state `0xF` (15) doesn't use Pitbull04: it deals damage from how far the shark moved (`|dx| + |dz|` against `0x90BEA4`/`0x90BEA8`, times `cfg[0x46C]`, once over the `cfg[0x474]` threshold), plays `Jaws.Tear` and prints the debug string `Razas damage!` (Hungarian *rázás* = shaking), probably the thrashing tear-apart.

**Open:** what puts the shark into state 5 and sub-states 9 / 22, which ability `+0x730` is, and whether "04" means earlier Pitbull versions existed (the exe names only this one).

### Tick, input, water height and the animation runtime (2026-10-21, found during the Ecco port)

Found while porting Ecco's dolphin controller (`docs/ecco_dolphin_controller.md`); everything here was used by the mod's Ecco
mode, which is user-confirmed working, so the addresses and the behaviours described are tested in-game unless marked otherwise.

**Per-frame tick.** `MLSharkCtrl`'s tick is vtable `0x7F28FC` slot `0x48` (address `0x7F2944`) = **`0x667FB0`** (thiscall, no
args). All of the shark's own movement happens inside it. Replacing the slot (mod `ecco.cpp`) replaces the movement while the
rest keeps working: the camera follows, the F8 teleport and terrain push-out still apply to the brick afterwards, so collision
is resolved outside the movement code. To move the brick yourself: write its world matrix (`+0x84`) and its local matrix
(`+0x50`, solved through the parent's world matrix) and set flag `0x20` (stale) at `+0x0C`; call the world updater `0x696EA0`
first if the flag is already set, as the stock tick does.

**Pad (controller input).** `[[0x920E24]+0x88]+8` → `[buttons][previous buttons][stick X][stick Y]`. Swim = bit `2` or
`0x800000`; the d-pad bits `0x100`/`0x200` (left/right), `0x40`/`0x80` (up/down). The stock stick reader `FUN_0065EAE0` uses a
`0x1000` deadzone rescaled to ±`0x4000` and flips Y unless the invert option byte `0x8D1DC1` is set; it also prints
"Nem Invert" (debug, emptied in release) on every call.

**Water height.** Function pointer at **`0x8B2E9C`**: `float cdecl f(const float* pos)`, returns the water surface height at a
position, or `-2147483648.0` (`0x7D388C`) when the level has no water. The water action sets it to `0x633260`/`0x633320`, which
return the water brick's world Y (`[0x902EA4]+0xAC`), i.e. a flat plane.

**Water height functions, full picture (2026-11-25, air-swim work, user-tested).** The water action (`0x630DC0`/`0x630E70`/`0x631A..`)
sets three pointers together, all `float cdecl f(const float* pos)`, all returning `-2147483648.0` where there is no water:
`0x8B2E94` = **wave surface** height (`0x6331E0`/`0x633280`/`0x6331D0`; 197 call sites), `0x8B2E98` (`0x633390`/`0x633400`/`0x633370`;
3 sites, not identified), `0x8B2E9C` = flat water level (107 sites). Every call site is `call [ptr]`, so a wrapper can identify the
caller from its return address (site + 6). (Earlier notes took `0x8B2E94` for ground height; it is the water surface: `0x66E4A7`
adds `SharkConfig.m_felszineny` "surface Y" to it.)
- **Shark airborne physics uses the wave surface:** `0x66D6FB`/`0x66D70E` measure two body points against it; both above →
  `ctrl+0x4A0` = 1 (airborne; jump states 2/0x18/0x1B/0x29/10), one above → fraction out of water blends air and water physics.
  `0x66D762` sets the near-surface flag `ctrl+0x828`; `0x66D2E4` clears `ctrl+0x5A8` (on-ground state) once Y ≤ surface;
  `0x6703A7`/`0x6703EB` the surface wake.
- **Shark, flat level:** `0x67031E`/`0x67033C` set bit `0x40000` in the previous-buttons word at `[ctrl+0x58]+0x38` when out of
  the water, i.e. block the `0x40000` (charge/jump) button press edge in the air (the pad words `[buttons][prev]` are also at
  `[[0x920E24]+0x88]+8`). `0x66DDC5`/`0x66DDFB` = **max depth**: when `SharkConfig.m_depthvizsg` (`+0xE4C`) is on, the brick's local Y
  is raised to at least `water − m_maxdepth` (`+0xE54`). `0x669CA2` gates a wave-surface snap that didn't run in testing.
  `0x6607DC` (state setter) places a splash at the surface.
- **Shark-follow camera** = object at global `0x90BC10`, vtable `0x7F29E4` (ctor `0x6752A0`, created at `0x55ABE4`), tick
  `0x678230`; nearly all of its code in `0x675000`–`0x680000` plus `0x6643D0`/`0x664520` reads the flat level. `cam+0xB4` =
  above/below-water mode. The above-water placement `0x676AC0` puts the camera at `water + camcfg[0xDC]` (site `0x676C3B`) and
  aims at `sharkY + camcfg[0xEC]` (at least `water + camcfg[0xE4]`), so in a jump the camera stays by the waves looking up.
- Other readers: `0x48DF10` (vtable `0x7D7464`) puts an object on the wave surface above a brick (fin/wake marker); the
  `0x4F3920`–`0x5166F0` group (one vtable each) are other swimmers/boats.
- The mod's F7 air swim lifts the surface for the shark sites above (not the max-depth pair) and gives `0x676C3B` the camera's
  own height (`mod/src/noclip_guard.{h,cpp}`).
- Global `0x90BC08` = shark brick, `0x90BC0C` = effects/message object (`FUN_00694860(0x2E, …)` spawns splashes).

**Shark clip animator** at **`ctrl+0xBC`**:
- `PlayClip` `0x65E610` → `0x4DCF70` (a two-slot cross-fader). Per-tick update **`0x4DD250`** (thiscall `(animator, int
  reset)`, `ret 4`), called from the shark tick at `0x66DF91`. Frame step = speed × `[engine+0xB4]`. Posing goes through
  `0x6F6150`, cross-fades through `0x6F6230`.
- Fields: `+0x10` skeleton model, `+0x14` frame, `+0x1C`/`+0x20` start/end, `+0x24`/`+0x28` cross-fade length/remaining,
  `+0x2C`/`+0x30`/`+0x34` slot B start/end/frame, `+0x3C` weight, `+0x44`/`+0x48` speeds, `+0x58` reference frame, `+0x60`
  flags (`8` = loop; `1`/`2`/`4` select special per-bone paths, not decoded).
- **It can be driven from outside:** save its first `0x80` bytes, write a clip range and frame (speed 0, no cross-fade, weight
  1), call `0x4DD250(anim, 0)`, restore the bytes. The bones take the written pose and the shark logic's own clip timing and
  "clip ended" checks are unaffected (mod `PoseDolphin`).
- A second animator at **`ctrl+0x15C`** runs while `ctrl+0x24C` is set. Not identified.
- **Clips are looked up by name only.** The controller never checks which skeleton or mesh it is driving: a foreign 28-bone
  rig (padded to 40 bones) whose `ANIM` lists the 73 `Shark_GW_*` names plays as the player (`DOLPHIN` level). Whether
  anything really needs 40 bones wasn't tested; the padding was a precaution.

**Other animation code:**
- The generic clip-player action `0x6F75A0` (start `+0x40`, end `+0x48`, speed `+0x50`, frame `+0x64`, loop count `+0x88`)
  serves other animated objects.
- `0x6F5EB0` (thiscall `(start, end, float frame)`) poses a skeleton model at a fractional frame. It also sums the per-frame
  root-motion deltas (`SKEL +0x1C`, 12 bytes per frame) between the last and the new frame, wrapping at the clip end, into the
  model's `+0x1D8` delta, then interpolates every bone between the two neighbouring frames (`FUN_006E9E90`).
- **SKEL resource object** (loader `0x6F47D0`, reached through the skeleton model's vtable `+0x84`): `+0x1C` root-motion array,
  `+0x20` frame count, `+0x24` morph frame count, `+0x40` vertex count, `+0x4C` morph data.

**`ANIM` header's second word, solved:** it is the total byte length of the clip names (Σ `name_len`, NULs included,
alignment padding excluded). Checked on all 345 `ANIM` chunks in the 20 shipped GDWs, 345 match.

**Drawing from the d3d8 proxy (mod side).** The game sets the view matrix several times per frame (reflection and refraction
passes render to textures). The last view and projection set while the back buffer is the render target are the main camera;
drawing at `EndScene` with them places objects correctly in the world (mod `sonar.cpp`). Whether the depth buffer is still
the scene's at that point wasn't checked separately (the sonar draws with depth test on and looked right).

### Other globals seen nearby (unexplored)

- `0x920E24`: a top-level engine/world object referenced everywhere (`+0x80`, `+0x84`, `+0x88` sub-objects; `+0xB0` looks like a game clock).
- `0x8DA1C0`: the `DDGameState` object (`+0x104` `m_angry`, `+0x12C` `m_koteldied`; see "Cut Aurora rope").
- `0x90BC08`: cleared at the end of the `SharkRelPos` routine; a neighbor of the controller singleton.
- `0x93BE68`: the debug-print object that `SharkRelPos` / `TailCombo` strings are sent to (`call 0x703BD0`).
- `0x8D1EBC` / `0x8D1EC0`: written from controller `+0x2A8..+0x2B4` in the `SharkRelPos` routine, likely a HUD copy of the health/hunger values.

---

## Mission class `MSMineAllMineMission` (SC17)

Name getter `0x52A1A0`, constructor installs vtable `0x7DFFE0` at `0x52A4FC`. Fields, in BRTR property order on `MineAllMine Mission Root`: `m_WhaleID` (`0x08000AE5`), `m_SharksID` (`0x08000AE6`, list), `m_Easy/Medium/HardSharkNum` (`0x08000AE7–9`), `m_Easy/Medium/HardWhaleDeadHurt` (`0x08000AEA–C`, floats). The class's own vtable slots are mostly generic mission-base methods, so the exact code that offsets the whale by the root's transform wasn't traced. The effect was verified in-game instead (see `CLAUDE.md`, "Reference Instancing, Absolute Transforms, and Mission Relocation").

## Camera class `MLSharkCamera`

Class descriptor `0x907120`, name getter `0x672440`. ~150 registered fields covering the third-person follow camera **and the minimap** (`m_target`, `m_distance`, `m_abovedistance`, `m_viewheight`, smoothing pairs, boss/charge/strafe/zlock camera modes, `m_mapsprite`, `m_maproot`, `m_mapdist`, `m_northsprite`, `m_northbrick`, enemy/game-object map sprites, etc.). The listed integer offsets are subject to the registration-integer caveat above. Not yet needed. The pointer chain above made camera-based position reading unnecessary.

---

## Why the earlier memory scans failed

The mod's `F7`/`F9` scanners searched `0x845000`–`0xE70000`. That's exactly `.data`, the exe's static data section. The shark controller and its brick are heap objects allocated at level load, so they were never in range. The old `0x008CFC88` "position" candidate was a static scratch variable written by several entities. The old god-mode addresses (`0x8F11A8` etc.) were likewise static copies, which is probably why that code crashed after level transitions.

---

## `GDControl`: level scripting timelines (decoded 2026-10-03)

Most level scripting (cutscene sequencing, spawning effects, killing or hiding objects, checkpoint clean-up, barrier removal) is done by `GDControl` actions: `ACTN` blocks with class header `0x0203B039`. Dump any level's controls in readable form with **`scripts/dump_gdcontrol.py GAME_GDWs/<NAME>.GDW [REGEX]`**. Across the 19 levels with a scene graph there are 3,261 controls and 82 distinct action words.

### Where it lives

| What | Address |
|---|---|
| Class name getter (`"GDControl"`, `0x8B9CB0`) | `0x6B6180`, vtable slot 0 of `0x7F5780` |
| Reflection descriptor | `0x91FED0` (returned by `0x6B6280`), 17 fields: `m_Ctrl1`/`m_List1` … `m_Ctrl8`/`m_List8`, `m_DeactProps` |
| Props constructor / runtime constructor | `0x6B6030` (0xC4 bytes) / `0x6B66F0` (0x130 bytes) |
| Property type `GDPropControl` (`0x8B9CA0`) | vtable `0x7F5768`, 16 bytes = vtable + `[w0, w1, w2]`; copy `0x6B5FB0`, serialize `0x6B5FD0` (3 × `0x6BC570`) |
| Start (schedule the steps) | `0x6B68A0` |
| Per-tick executor | `0x6B6C00` |
| Step interpreter | `0x6B6DB0` (`thiscall`: control, `&Ctrl`, list) |
| Deactivate when finished | `0x68EB10` |

### BRTR layout

`ACTN [size] [u32 class 0x0203B039] [u32 action ID] PRPS…`. **Every `ACTN` block has its own ID** (the boulder's control in START is 2084, its node is 2083), and list entries may be node IDs or action IDs. Props: `m_CtrlN` = `PROP 0x08001819 + 3(N−1)` (12 bytes `[w0, w1, w2]`), `m_ListN` = `PROP 0x0800181A + 3(N−1)` (`[u32 n] + n IDs`), `m_DeactProps` = `PROP 0x08001831`, instance name = `PROP 0x080017C3` (shared by all action classes).

### Timing

At start, step *i* gets a fire tick `w1 + rand(0 … w2 − w1)`, or exactly `w1` when `w2 ≤ w1` (`w1` is signed). The total length is the latest step. The counter starts at −1 and the executor runs once right away, so **t = −1 fires the moment the control starts** and t = 0 one tick later. A step whose `w0 & 0xFFFF` is 0 does nothing. After the last tick the control deactivates itself (`0x68EB10`). Delay values in the data are mostly 0, then 1, 15, 30, 20, 60, 120, and "300 to 400 random".

### Targets

Each list ID is looked up twice through the ID registry (`0x6B8A00`, a hash map at `engine+0x50`, see "Object registry" below). **Corrected 2026-10-03 from live memory dumps (mod F12); the first version of this section had the two roles swapped:**

- **`0x6C3010` → the live action instance.** It calls the registered object's slot `+0x04` (always 1) and then `+0x24`, which jumps to slot `+0x20` = `0x401640`, `mov eax,[ecx+0x24]`: it returns **registered object `+0x24`**, the object's live (running) action. For an action ID that's the action's own runtime instance; for a node ID, the node's action. **Null if the action has no live instance**, and then the step skips that target. Action instance flags at `+0x0C` (`0x2` active, `0x8000000` started, `0x1` killed); children `+0x1C`, next `+0x10`.
- **`0x6C2F90` → the registered object itself** (for a node, the node; for an action, its owner node). Its `m_nFlags` (BRTR `PROP 0x080017D9`) are at **`+0x18`** (e.g. a node with BRTR flags `0x2000005A` shows `0x2000005A` there); children `+0x28`, next sibling `+0x20`.

Lookups that return null are skipped. IDs defined nowhere in the file (9 to 72 distinct IDs per level, e.g. START's `SzetfroccsenoDarabokController3` still adds blood-splash pieces 639–642, which don't exist) are dangling references, probably objects deleted during development. Some could be created at runtime; not checked.

### Action word `w0`

**Operations (low 16 bits)**, applied to every target in the list:

| Bit | Effect in `0x6B6DB0` | Name in dump | Example instances |
|---|---|---|---|
| `0x0001` | live action flags \|= `0x2` (if scope `0x01000000`), object `m_nFlags` \|= `0x2` (if `0x10000000`); with `0x10000` also (re)start the target's action (`0x694C70`/`0x68EA80`) | start | `IntroStarter` → `IntroMovie` (1,936 uses) |
| `0x0002` | clear those `0x2` bits (only when `0x1` isn't set) | stop | `PostStateControl` |
| `0x0004` | add the target to the world (`0x6C2EB0` → `0x698720`) | add | `ArbocDestroyController` → debris + dust |
| `0x1000` | same path as `0x4`, and the executor passes the list as stored in the file instead of the runtime copy | add(stored-list) | `MovieStarter_601` → `Lvl6_Movie601` |
| `0x0008` | live action flags \|= `0x1` (the action ends and takes its object with it); with `0x200000` also object `m_nFlags` \|= `0x20000` | kill | `PortalKinyiro` ("portal killer"), `…Killer` |
| `0x0200` | instantiate a copy of the object (`0x697BB0`, mode 3, or 4 with `0x20000`); with `0x200000` create it as a child of the controller's owner at its world position | spawn-copy | `FoamControl`, rocket/grenade explosions |
| `0x0010` / `0x0020` / `0x0040` | `0x10`: set `0x40`, clear `0x10`. `0x20`: set `0x10`, clear `0x40`. `0x40`: clear both. On the live action's flags (scope `0x04000000`) and/or object `m_nFlags` (scope `0x40000000`) | flags… | `PalyavegiKizaroKiller` ("level-end barrier killer") → `KijaratKizaro`: `0x40` |
| `0x0080` / `0x0100` | clear / set `0x100` = **don't render** (live action: scope `0x08000000`; object `m_nFlags`: scope `0x80000000`) | show / hide | `real_shark_norender` → `GWside`; `Harpoon Deact` |
| `0x0400` / `0x0800` | object `m_nFlags` set / clear `0x20000` (`0x6B71C0`, scope `0x40000000`) | suspend / resume | `FecsegesSzunetel` / `FecsegesUjra` ("chatter pauses / again") on a sound area; `…MapitemKiller` |
| `0x2000` / `0x4000` | object `m_nFlags` set / clear `0x400000` (meaning unknown) | node±0x400000 | DEEPSEA `bummcontroll` (exploding tanks/pipes) |

**Scope and modifier bits (high 16 bits):** `0x01000000` live-action enable bit, `0x10000000` object enable bit, `0x04000000`/`0x40000000` live-action/object `0x10`–`0x40` group, `0x08000000`/`0x80000000` live-action/object render group, `0x00400000`/`0x00800000` also recurse into children (`0x10`–`0x40` group / render group), `0x00010000` restart on start, `0x00020000` spawn mode 4, `0x00200000` "at self / also suspend". `0x0F000000` with no modifiers is the default (5,856 of 6,547 steps, 89%). `0x02000000` isn't tested by the interpreter.

**Flag meanings:** `m_nFlags 0x100` = not rendered, confirmed by the "norender" control and by invisible blocker plates (`Kizaro_Lap_Kozepes`, flags `0x15A`). `0x2` = enabled/active (set on almost every BRTR node). `0x20000` = suspended. On a live action, flag `0x1` = killed. `0x10`/`0x40`: barrier "killers" clear them and invisible walls have them; clearing them at runtime removes visibility as well as collision (below), so they're more like "active in the world" bits than pure collision bits.

**Measured effect of single steps on a plain model node** (2026-10-03, user-confirmed, one step per target, fired by a destructible's hook):

| Step | Visible after | Solid after |
|---|---|---|
| `0x4B000400` suspend (object `m_nFlags` `0x20000`) | no | no |
| `0x8F000100` hide (object `m_nFlags` `0x100`) | no | no |
| `0x4F000040` clear `0x10`/`0x40` | no | no |
| `0x0F000008` kill (live action flag `0x1`) | no | **yes** |

So suspend, hide or clearing `0x10`/`0x40` each remove an object completely, and kill alone leaves an invisible wall. Note that `0x100` set **in the BRTR file** doesn't remove collision (the `Kizaro_Lap_Kozepes` blocker plates are invisible and solid), while setting it **at runtime** did; the engine probably only re-evaluates collision when a flag changes.

### Example: START's tunnel boulder

```
[node 2083 "TunnelBlockingDust"] SeaSeekerQuestEventControl  (act 2084)
  1: t=0  0x4b000400 suspend  -> TunnelBlockingDust
  2: t=0  0x0f000008 kill     -> TunnelBlockingDust
[node 677 "SecondPart"] CheckPointCleanUp
  3: t=0  0x0f000008 kill     -> TunnelBlockingDust
```

No other `GDControl` starts `SeaSeekerQuestEventControl`, so the seeker quest code presumably starts it directly.

### Registration integers, resolved

`GDControl` settles the "two integers" question from the reflection section above. **The first integer (`a`) is the offset of the property wrapper in the props object; the second (`b`) is the offset of a mirrored copy in the runtime object (0 = none). The value sits 4 bytes in, after the wrapper's vtable.** `m_Ctrl1` (`a` = `0x48`): the executor reads the props at `+0x48`/`+0x4C`. `m_DeactProps` (`a` = `0x128`) is read at `+0x12C`. `m_List1` (`b` = `0x3C`): the executor uses runtime `+0x3C` unless bit `0x1000` is set. This also fits the base brick's `mtx` (`0x30`, `0x4C`), which the brick reads at `+0x50`.

## Object registry, live actions and destructibles (2026-10-03)

Found while getting a scripted trigger to work (see `docs/brtr_editing.md` "Scripted triggers"); confirmed with the mod's **F12 registry dump** (`mod/src/iddump.cpp`), which reads these structures from the running game.

### Object registry

- Hash map at **`engine + 0x50`** (`engine = [0x920E24]`): `+4` bucket count (16,381 in FISH), `+8` bucket array; entry `[0] id, [1] ?, [2] object, [3] next`. `0x6B8A00` looks up, `0x6B8450` inserts (fails if the key exists), `0x6B8600` inserts or overwrites. Any 32-bit ID works structurally.
- **Registration** (`0x692C10`, run for every loaded node and action): with the loader's "keep file IDs" flag set, an object is registered under its file ID if free; otherwise (or without the flag) it gets **`++engine+0x14`**, the runtime counter, and the old ID is mapped to the new one.
- **The runtime counter starts at about `0x100000`** (`0x100324` after loading FISH, `0x1008B2` a few seconds later). Objects the engine creates itself (reference copies, spawned effects) are numbered from there. **File IDs at or above `0x100000` collide with those and the objects vanish** (tested: a rock at `0x10000A` never appeared; IDs up to `0xFFF00` work). New content should use unused IDs below `0x100000`.
- **Registered objects are definitions with their properties inline at the reflection `a` offsets** (e.g. a `GDControl`'s `m_Ctrl1` value at `+0x4C`, `a` = `0x48`, `+4`). Common layout: `+0x04` own ID, `+0x08` runtime class ID (file class with remapped low bits), `+0x18` `m_nFlags`, `+0x1C` owner (actions), `+0x24` live instance / live action.
- **Nodes** (e.g. vtable `0x7F68F0` for a plain model): `+0x18` `m_nFlags`, `+0x20` next sibling, `+0x24` live action, `+0x28` first child, `+0x2C` action definition (the node's `ACTN`).

### Live action instances

- An action **definition** (one per `ACTN`) only does something through a **live instance** stored at its `+0x24`. `0x698700` creates it (`if !def->vt20(): def[9] = def->vt48()`); the instance's destructor (`0x68E770`) clears it again. `GDControl`: definition vtable `0x7F5804` (0x130 bytes, `0x6B66F0`), instance vtable `0x7F5798` (0xC4 bytes, `0x6B6030`).
- **Who gets an instance at load:** actions on **group-type nodes** (classes `0x010B10AA`, `0x010AA0A4`) do; actions on **plain model nodes** (`0x0107402F`) don't (live dumps: the pink post root had one, the monkey and FISH's `LoadingPredatorEffect` didn't). All 132 shipped destructible-hook targets sit on group-type nodes, all with `m_nFlags` = 0. `GDControl` step `0x4` ("add", `0x698720`) also instantiates. The engine code that instantiates at load wasn't traced; the rule is empirical.
- **Starting** an instance is `0x68EA80`: sets `0x2` (active), calls slot `+0x50`, sets `0x8000000` (started), then follows the instance's `+0x20` chain (`m_OnActivate`). It does nothing if the instance is already active and started. `0x68EB10` deactivates.
- **Start-pass timing:** `GDControl` start (`0x6B68A0`) schedules the steps and immediately runs one executor pass with the counter at −1, so **steps with delay −1 run in the same instant the control starts**; delay 0 runs on the next tick. This matters when starting the control deletes its owner (see `MBRombolhato.m_killparent`).

### `MBRombolhato`, the destructible (breakable objects)

- `ACTN` class `0x02169168`; definition vtable `0x7D9998` (0x228 bytes, `0x4A4430`, name getter `0x4A3990`), runtime vtable `0x7D99F8` (0xF8 bytes, `0x4A4C60`). **PROP ID = `0x08000661` + field index** (55 fields): `m_type`, `m_darabokid` (pieces node), `m_maxhitpoint` (`0x663`), …, `m_robbcontrol` (`0x673`, "explosion control", run when destroyed), `m_felulrolcolli`, `m_toclone`, `m_maradclone` (remains), `m_szetroppen`, `m_killparent` (`0x679`), `m_megutclone`, `m_megutclonevegen`, **`m_megutcontrol`** (`0x67C`, run on every non-fatal hit), …, `m_killotherrombolhato` (`0x692`), `m_pusztulomessage`, `m_colliremains`, `m_tarsaivalpusztul`, `m_reborn`, `m_addpoint`. Full table via `scripts/dump_class_fields.py`.
- Runtime fields: `+0x48` mirror of `m_robbcontrol`, `+0x50` of `m_megutcontrol`, `+0xE8` hit points.
- **Hit/destroy handler `0x4A5080`** (mode 0/1/2): if hit points ≤ 0 → sounds/messages, kill listed destructibles, spawn remains, **start `m_robbcontrol`** (`0x6C3010` → `0x68EA80`), … ; otherwise **start `m_megutcontrol`**. The collision handler `0x4A5F10` subtracts damage and calls it in mode 2; `0x4A5E00` handles losing supports.
- Shipped use: 111 destructibles use `m_robbcontrol`, 21 `m_megutcontrol` (e.g. AQUARIUM's `ParavanTorik` screens open a portal and advance the quest; DEEPSEA's tanks start explosion chains; DEEPSEA2's lamps kill their light cones). FISH's pier posts have both hooks empty.

## Cut story mission "Hot Pursuit": `StagePursuitQuest` / `StagePursuitQuest2` (decoded 2026-10-10)

**The mission logic is fully compiled into the shipped PC exe, not stubbed.** Two versions exist side by side: `StagePursuitQuest` (an earlier, kill-driven draft with no win or lose condition) and `StagePursuitQuest2` (a complete mission: gate sequence, lose-by-distance, boss fight, completion). Both have an event class (`StagePursuitQuestEvent`, `StagePursuitQuest2Event`) that is a plain `NAQuestEvent` subclass with no fields of its own, the same base the shipped `StageDocksQuest`, `StageDeepSeaQuest` and `NAQuestEventKatatama` events use. Decompiled output came from `CreateDecomp.java` over the vtable entries; code range `0x5FB300`–`0x5FD000`.

| | `StagePursuitQuest` | `StagePursuitQuest2` |
|---|---|---|
| Class descriptor | `0x8FE120` | `0x8FE418` |
| Object vtable | `0x7EDFE8` | `0x7EE180` |
| Tick (`vtbl+0x48`) | `0x5FBA00` | `0x5FC800` |
| Activate (`+0x50`) / deactivate (`+0x54`) | `0x5FB960` / `0x5FB9F0` | `0x5FC730` / `0x5FC7F0` |
| Message handler (`+0x68`) | `0x5FBB80` | `0x5FCD10` |
| Advance to step N (`+0x6C`) | `0x5FBBF0` | `0x5FCDF0` |
| Object size | `0x1AC` | `0x24C` |

On activation each quest stores itself in the global **`0x8FE494`** ("current pursuit quest", cleared on deactivate). Pursuit quest events send their message number to whatever object that global points at.

**Fields** (registration `b` → runtime offset; for ID lists `b` is the wrapper, count at `b+4`, array pointer at `b+8`; for single values the value is at `b+4`):

| Field | Quest | Quest2 | Used as |
|---|---|---|---|
| `m_JetSkiIDList` | `0x174` | `0x174` | the jet skis being chased |
| `m_GateIDList` | `0x180` | – | gate-opening actions (Quest) |
| `m_GateOpenPosIDList` | – | `0x180` | marker nodes: open gate *i* when a jet ski gets near marker *i* |
| `m_GateClosePosIDList` | – | `0x18C` | marker nodes: a jet ski counts as "through gate *i*" within 100 units of marker *i* |
| `m_GateOpenerIDList` | – | `0x198` | actions started to open each gate |
| `m_GateCloserIDList` | `0x18C` | `0x1A4` | actions started to close each gate |
| `m_JetSkiBossIDList` | – | `0x1B0` | extra jet skis that only matter in the boss phase |
| `m_OnAccomplished` | – | `0x1BC` | action started on success |
| `m_OnBossFight` | – | `0x1C4` | action started when the boss phase begins |
| `m_PursuitLostDist` | – | `0x1CC` (float) | lose distance |

Inherited from the shared quest base (descriptor `0x8FE1D0`): `m_checkpoints`, `m_checkpointactions`, `m_events` (one action per mission state; `+0x6C` "advance to step N" starts `m_events[N]` when the current state is N−1), `m_missionbricks`. Quest state is at `+0x6C`. A jet ski counts as dead when its AI state (`ai+0xC28 + ai[+0xC24]*8`, `ai` = registered object `+0x20`) is `5`.

### `StagePursuitQuest2`: how the mission plays

State `+0x6C`: **0** = chase running, **8** = boss fight, **5** = accomplished, **6** = failed, **7** = inactive.

**State 0, every tick** (`0x5FC800`). The shark's position comes from the brick at `[0x90BC08]` (`+0xA8`). Two 1-based counters start at 1: next gate to open `g` (`+0x1DC`) and next gate to close `c` (`+0x1E0`), plus a per-jet-ski "passed gate" counter at `+0x1EC + 4i`.
- **Lose:** if the *nearest* live jet ski is farther from the shark than `m_PursuitLostDist`, the game shows *"The jet skiers have escaped! Mission failed!"* and the state goes to 6.
- **Gates open ahead of the jet skis:** when any live jet ski comes within **150** units of `m_GateOpenPosIDList[g−1]`, start `m_GateOpenerIDList[g−1]`, `g++`.
- **Gates close behind them:** a jet ski within **100** units of `m_GateClosePosIDList[c−1]` is marked as through gate `c`. Once `c < g` and every marked jet ski is more than **150** units past that marker, start `m_GateCloserIDList[c−1]`, `c++`.

So the jet skis race through a chain of gates that open in front of them and shut again behind them. The shark has to stay within `m_PursuitLostDist` of them, and if it doesn't make it through before a gate shuts, it's cut off and loses them. This matches the canal (lock/sluice gates) reading of `MINEMSHA.GDW`.

**Message 5 → boss fight** (`0x5FCD10`): only if the state isn't already 8 *and* every gate has been closed (`c > count(m_GateCloserIDList)`). Shows *"Destroy all the jet skis! Press ^CONT^ to continue."*, starts `m_OnBossFight`, state 8. Something in the level (presumably an area trigger at the end of the canal, through a `StagePursuitQuest2Event`) was meant to send message 5 once the jet skis arrive.

**State 8, every tick:** counts live, active (`flags & 2`) jet skis in both `m_JetSkiIDList` and `m_JetSkiBossIDList`. At zero it starts `m_OnAccomplished`, state 5.

**State 6 (failed):** resets something in `[0x920E24]+0x88`, calls `0x69AC70(0x8000)`, then `RequestStage(2, "")` (engine vtable `+0x80` with flag 2 and an empty name; flag 2 isn't decoded, probably "restart current stage").

**Messages** (`+0x68`): 0 or 4 → state 0 (start or resume chase), 1 → 5 (accomplished), 2 → 6 (fail), 3 → 7 (stop), 5 → boss fight (above), 10000–10063 → increment counter slot `+0x70 + 4(n−10000)` (generic quest counters).

**The on-screen texts** go through `0x4928D0(text, 4, 0x98967F)` and only show when the global `[0x8DA1EC]` is non-zero. That global has 134 references across the exe, so it's a general mission-HUD flag, not a debug switch.

**`"NNNNNNZZZZZ"`:** set at `+0x1E8` (with mask `0x2000` at `+0x1E4`) on activation but never read by Quest2's code. A leftover from the first version (below).

### `StagePursuitQuest` (first version): kill-driven gates

No lose condition, no boss phase, no completion action. The tick (`0x5FBA00`) counts live jet skis. Each time one dies, it starts the next action in `m_GateIDList` (opens the next gate) and sets a new **waypoint-group mask** on every jet ski: `mask = 1 << (pattern[k] − 'A')`, with pattern **`"OOOOOOZZZZZ"`** and `k` = gates opened so far. The mask starts at `0x2000` = `'N'`, so the sequence is N, then O after kills 1–5, then Z. The mask goes to jet-ski AI `+0x318`. The code also ORs together the group bits of each live jet ski's current waypoint (`ai+0xA80` → registered object `+0x108`), and once every jet ski is on an allowed waypoint it starts the next `m_GateCloserIDList` action. **So `OOOOOOZZZZZ` / `NNNNNNZZZZZ` are waypoint-group letter sequences** (A–Z = bits 0–25, which fits the `m_waypointgroups` field seen elsewhere), not cheat codes. Killing a jet skier diverted the rest onto a different route group. Messages: 0 → 0, 1 → 5, 2 → 6, 10045 (`0x273D`) → 7, 10062 (`0x274E`) → 0, else counters.

### Running it in-game (proof of concept, 2026-10-10, user-tested)

`scripts/build_pursuit_test.py` builds `edited_levels/PURSUIT.GDW` from stock MINEMSHA (the canal) and installs it as the custom level `PURSUIT` (mod F9). **Confirmed in-game: the gate opens, the lose condition fires ("The jet skiers have escaped!", then the stage restarts), the end-zone event starts the boss phase ("Destroy all the jet skis!"), and killing the jet ski fires `m_OnAccomplished`.** Five test builds; what each one taught:

- **Quest instance:** a root-level `ACTN` (class `0x0208D08C`, right after the root `PRPS` like MINEMSHA's `Stage0Quest`), base fields `0x08001161`–`64` as empty lists, `0x080017C4` = 2. That runs from load. The same quest on a group node with `0x080017C4` = 0, started by an area trigger, never ran (but that test also had the holder bug below, so it isn't conclusive).
- **Jet skis are listed by their `ANPosition` marker** (`jetski 1`, node 2670), as the shipped quests do with their boats. `ANPosition`'s vtable (`0x7D0AEC`) slot `+0x24` is `0x69A210`: look up the object ID at `+0xF4` (the spawned copy, a runtime ID such as `0x1001EF`) with `0x6C2FD0`, which returns that object's live brick. So `0x6C3010(marker)` gives the moving jet ski.
- **`0x6C3010` on a node** returns the registered object's `+0x24` (vtable `+0x24` → `0x401650` → `+0x20` → `0x401640` `mov eax,[ecx+0x24]`), i.e. its live brick, or null if it has none. **A node only gets a live brick when its `m_nFlags` has `0x10` ("in world")**: the empty group node copied from MINEMSHA's `NorthBrick` (flags `0x2`) got none. As a position marker the quest then compares against nothing (the gate never opened); as the holder of the `GDControl`s and the quest event, none of its actions got a live instance, so neither the quest nor the area triggers could start them. Flags `0x12` (like `SHARRRK`) fixed both.
- **Area triggers copied from FISH's exit (`PRPS` only) fire in MINEMSHA**, with `m_target` set to the level's shark node and `m_enter_act` listing action IDs on an in-world group node.
- **The shark position `[0x90BC08]`:** set to the shark's brick when the shark controller activates (`0x664EA9`); before that it points at a placeholder brick made at `0x55AB90`, and the controller's teardown clears it (`0x6711BE`). The root quest ran from load without hitting the placeholder.
- **`RequestStage` flag 2** (the fail path) restarts the current stage.
- **The jet ski doesn't drive its route here.** MINEMSHA's `jetski 1` only loiters near its start (repointing its route, `PROP 0x080001F0`, changed nothing; it has a second route field `0x080001FC` = `JetskiChase`), probably because SC15's `UpACreekMission` drives the canal traffic. So it can never pass a close marker and get 150 units past it, the gate never closes, and with closers the boss phase stays locked. The last build lists **no closers**: "all gates closed" (closer count < next-to-close index) is then true from the start. `m_GateClosePosIDList` must stay non-empty because the chase tick reads entry `[c−1]` every frame.
- **Boss-phase quirk:** state 8 counts jet skis whose brick and AI are flagged active (`+0xC & 2`). Swimming far away despawns or deactivates the range-spawned copy, which counts as destroyed and completes the mission. The lose check only runs in state 0, so it doesn't catch this.

### Getting the jet ski to race (v6–v10, 2026-10-11, user-tested)

**Result: the full sequence works through the real gate logic, with the jet ski driving the route on its own (v10).** In v9 a jet ski drives up MINEMSHA's main canal through two gates. Each gate opens as it approaches and shuts behind it, and only once both have shut does the end zone start the boss phase ("Destroy all the jet skis!"). Killing the jet ski fires `m_OnAccomplished`. What it took:

- **Boat markers (`ANPosition`, class descriptor `0x8CBB10`, 98 fields): PROP = `0x080001EE` + field index.** Fields 1 and 2 (`0x080001EF`, `0x080001F0`) hold the route (`GDPath` node ID). The canal's sail boats, which drive the full canal, set both and have no chase mode. Field 13/14 are `m_chase_proc` / `m_chase_area` (`0x080001FB` / `0x080001FC`, a `GDPath` used as an area). Others: `m_lookdistance` `0x080001F4`, `m_speed` `0x08000212`, `m_crew` `0x08000213`, `m_customcrew` `0x08000214` (rider reference list), `m_runaway` `0x0800022D`, `m_alarmer` `0x08000228`, `m_targeting` `0x0800023B`. Tri-state 0 = inherit, 1 = off, 2 = on. (The dump's names for these fields are shifted by drift, so only names checked against values are listed here.)
- **Boats do follow their routes.** The F12 boat probe (below) showed `jetski 1` and its copies in state 2, sub-state 3 ("path mode") with their path found. Both stock jet-ski routes (`jetskipath`, `JetskiChase`) are small loops inside the starting cove, which looks like loitering. A copy set up like the ocean boats (`m_runaway` 2, `m_alarmer` 1) fled from the shark instead (sub-states 6/2).
- **`ANShip` activation (`FUN_00410DA0`):** path ID at AI `+0xE20` → `0x692630` (registry lookup); with a path it pushes state 2/3 plus 0/3 and picks the nearest path point (`+0x2B4`); without one, state 2/1 plus the "no path" byte `+0xA78`; a flag at `+0xD8C` gives state 2/7. It also sets the waypoint-group mask `+0x318` = `0x2000` ('N'), the mask `StagePursuitQuest` (the first draft) changes.
- **A spawned boat is removed when it leaves its marker's bounding box (`PROP 0x080017DF`).** `jetski 1`'s box covers only the cove (x −1662…−845, z −1195…−377), and the copy kept vanishing about 500 units up the canal and respawning. Giving the marker a box around the whole route (+100) fixed it. SC15's other crew markers have similar ±300 boxes. The top-level sail boats have tiny boxes and still drive the whole canal, so the rule may only apply to some setups; not checked further.
- **The route:** a reversed copy of the sail boats' `vitorlas_a1_a2 path` (node 2658, open, 24 points, ~1,230 units, so every point is water), placed at the source path's world transform since its points are local to it.
- **The loiterer removed:** `scripts/build_pursuit_test.py` cuts `jetski 1` and its rider out of `BRTR` (`remove_nodes`, which fixes every ancestor's size) after copying them; nothing else references them.
- **Speed (v10):** with `jetski 1`'s `m_speed` 250 and `m_turnd`/`m_stopd` 0 (inherit), the copy drove north but rammed the canal's bends (the route was made for slow sail boats), got stuck or wrecked itself, and only kept going while the shark chased it. **`m_speed` 120, `m_turnd` 40, `m_stopd` 20 (the ocean boats' values) fixed it: the jet ski drives the canal route by itself** (user-tested 2026-10-11).
- **Still open:** the route is open and ends in the canal's north-west corner (the sail boats' start), so after the last point the jet ski drives straight into the bank near the end zone and gets stuck. Close the route or end it in open water. Also not done yet: several jet skis plus `m_JetSkiBossIDList`, solid gates, on-screen goal text.

**Mod F12 boat probe (2026-10-11):** for an `ANPosition` marker, F12 follows marker → spawned copy (`+0xF4`) → live object → `ANShip` AI (`+0x20`) and prints position, state stack, path ID and object, and flags. Runtime-spawned copies are registered *as* the live object (vtable `+4` = "not a definition"), while file nodes resolve through `+0x24`. The probe emulates `0x6C2FD0` by reading the shared `mov eax,1` / `xor eax,eax` stubs. Code: `mod/src/iddump.cpp`.

### Open
- Which level data was meant to instantiate the quest: **none survives**. No GDW contains a `StagePursuitQuest*` instance (searched by class ID, 2026-10-10).
- `0x69AC70(0x8000)` in the fail path (`RequestStage` flag 2 restarts the stage, seen in-game).
- The jet-ski AI is `ANShip` (definition object `0x1264` bytes; only ANShip code, `0x410000`–`0x41D000`, writes the state stack at `+0xC24`/`+0xC28`, state 5 at `0x41691A`). Route following works (see above; speed 120 with turn/stop distances 40/20 on the canal); `+0xA80` (current waypoint) used by the first draft is still unexplored.

## Cut Aurora rope: `NAAuroraRope` and friends (decompiled 2026-11-02)

How the cut tutorial ending played (tension, reeling, snagging, the HUD, the two endings) is written up in `docs/cut_content.md` "How the rope fight worked". This section only lists the engine side. Static analysis only (Ghidra headless + objdump); nothing was run in-game.

| Class | Address | What |
|---|---|---|
| `NAAuroraRope` | descriptor vtable `0x7DA4C0`, getter `0x4BB630`, field descriptor `0x8DB828` (37 fields) | subclass of `NARope` (getter `0x5AA050`) |
| | runtime vtable `0x7DA4D4` | slot 22 tick **`0x4BC670`**, slot 23 activate `0x4BC470`, slot 24 deactivate `0x4BD010` |
| | props vtable `0x7DA56C` | props created at `0x4BB5B0` → ctor `0x4BBDC0` (0x374 bytes, `m_treshold` default 1.1) |
| | runtime object `0x4BB530` (0x2B4 bytes) | message hook `0x4BBD90` (installed at `+0x48`) handles message **`0x29A`** → damage handler **`0x4BD100(float)`**; segment helper `0x4BC610` |
| `NAAuroraRopeExcluder` | getter `0x4BD360`, descriptor `0x8DC8E0`, runtime vtable `0x7DA5E8`, tick `0x4BD780` | subclass of `NARopeExcluder` (`0x5AC6F0`) |
| `NAAuroraRopeBuoyRopeInteractor` | getter `0x574BD0`, vtable `0x7E69CC`, tick `0x574DC0` | not decoded |
| `MBAurora` | getter `0x4B77F0`, descriptor `0x8DCD00`, collision handler `0x4B9610` | mask `0x4000` → push + rope damage (≤ once per 30 ticks); mask `0x8` → `m_angry` |
| `MBShipRope` | getter `0x4C0830`, descriptor `0x8DBD48` | stripped copy of the tension core; placed once, in OPEN_S |

**Props field values** (wrapper `a` + 4): `m_maxhp` `0x238`, `m_treshold` `0x240`, `m_capaszaja` `0x250`, `m_aurora` `0x258`, `m_kotelauroravege` `0x260`, `m_kotelforce` `0x268`, `m_halfdist` `0x270`, `m_kotelsebzicapatfeszules` `0x280`, `m_kotelsebez` `0x288`, `m_kotelhajothuzza` `0x290`, `m_kotelhajothuzzacsaktol` `0x298`, `m_hajothuzfesz` `0x2A0`, `m_feszulhpszorzo` `0x2A8`, `m_kotelalap` `0x2B0`, HUD sprites `0x2B8`–`0x310` (`keret`, `hudcapa`, `fazisok` list `0x2C8`, `szinesfazisok` list `0x2D4`, `hudhosszu`, `belseje`, `hudhajo`, sizes/positions), `m_maxscale` `0x318`, `m_damagetime` `0x320`, `m_minlen` `0x328`, `m_maxlen` `0x330`, `m_belsofeszulkotelkifele` `0x338`, `m_behuz` `0x340`, `m_kienged` `0x348`, `m_nemhuztime` `0x350`, `m_font` `0x358`, `m_kozelvantav` `0x360`, `m_kozelvansebez` `0x368`, `m_finalmovie` `0x370`.

**Runtime fields:** `+0x18` props, `+0x1FC` segment count, `+0x260` segments (stride `0x3C`), `+0x270`/`+0x274` rest/actual length, `+0x284` rope HP, `+0x298` last damage time, `+0x29C` flash, `+0x2A0` current line length L, `+0x2A4` last pull time, `+0x2AC` HUD slide offset, `+0x2B0` frames held at `m_minlen`.

**Formulas:** stretch `r = actual / L`; tension `t = 1 − halfdist / (halfdist + r − treshold)`. HP `−= feszulhpszorzo · t` per tick. Shark damage goes out as message **`0x41`** with a pull of `kotelforce` × the rope vector. HUD phase = `(maxhp − hp) · 4 / maxhp`; HUD x = `(640 − hudfulllen) / 2`; it is hidden while `[0x920E24]+0xA8 & 8`. Rumble on rope damage: `0x6C9010(2, 30, 0, 30)`.

**Globals and calls it touches:**
- `[0x8DA1C0]` = the `DDGameState` object. `+0x104` = `m_angry`, **`+0x12C` = `m_koteldied`**, which is set when the rope's HP reaches 0 and is the flag `MBStageTutorial` waits for.
- Final movie: `0x692630` / `0x698720`. Before it starts, a type check (`0x6927A0` against `0x8DE6F0`, class unidentified) is followed by `[[0x8DA1C0]+0x20]+0x40 = 6`, meaning unknown.
- Float constants: `0x7DA5D0` = 160, `0x7D3894` = 4, `0x7CE0D8` = 1, `0x7CE024` = 0, `0x7CE7B8` = 0.8.

**Open:** `NARope`'s own fields (segment setup), the interactor, state 6, what collision mask `0x4000` is.

## Draw distance and fog (2026-10-17)

The "small render radius" is level data plus one water action, not a hardcoded limit.

- **Camera:** `GDCamera` fields `m_nFOV`, `m_nRatio`, `m_NearPlane`, `m_FarPlane` (BRTR `PROP 0x080017FD`–`0x08001800`); runtime near/far at `+0x114`/`+0x11C`. `0x69B400` is the point-vs-frustum outcode test (near, far, four sides); `0x69B2A0` builds the frustum. Every level's `SharkCamera` has far plane **600**.
- **Fog objects:** `GDFog` (`m_FogStart`/`m_FogEnd` = `PROP 0x0800184D`/`0x0800184E`, runtime `+0x12C`/`+0x134`). Each level has `FogAbove`, `FogBelow`, `FogReflection`, `FogTransparentAbove/Below`.
- **`NAWaterYCamera`** (action class `0x02071070`, live vtable `0x7F0120`; PROP = `0x08001330` + field index, fields `m_viewportabove` … `m_transparencyfarplanefrombelow`) switches between above- and underwater rendering. Runtime: `+0x80`/`+0x88` = IDs of the above/below fog, `+0x90`/`+0x98` = `m_fogbelowstartPC`/`EndPC` (stock 30/170 in OPEN_S), `+0xB0`/`+0xB8` = `m_fogstartbottom`/`endbottom` (deep water, below `m_fogbottomy` `+0xC0`, interpolated in between), `+0x150` = 0 above / 1 below. Its tick **`0x62B430`** runs every frame underwater: it writes those values into the below fog (`+0x12C`/`+0x134`, plus `+0x144..+0x14C` colour) **and sets the current camera's far plane (`+0x11C`) to the fog end**. So underwater the fog end is the draw distance, and `FogBelow`'s own values (40/80) are overridden. Crossing the surface calls `0x62AC40` (going above) or `0x62AEF0` (going below): they show/hide the viewport objects, set the camera far plane once from `*(lookup(cam+0x2E4 or +0x2EC) + 0x50)`, and set the music underwater flag `0x8B2E7C`. Init: `0x62B1B0`. `0x5519A0(mask)` (cdecl) = current camera; `0x6C3010` (thiscall on the engine, `(id, 0)`) = live object by ID.
- **Tests on OPEN_S** (custom levels `FAR_*.GDW`, user-tested; project copies deleted 2026-11-26): far plane 3000 + above fog 1000–2900 shows distant objects fine. Underwater fog 800–2500 crashed on load; 300–1200 made the shipwreck flicker or appear only up close, barriers appear only when very close, NPCs get culled more (none of it in stock). 100–400 = no problems. Why a longer underwater far plane breaks per-object visibility isn't traced.
- **Mod:** `Shift+F4` far view (`mod/src/farview.{h,cpp}`) applies these values at runtime.

## Movie playback (2026-10-16)

`FUN_007221E0` plays the pre-rendered `movie\*.WMV` files through DirectShow: `CoCreateInstance(CLSID_FilterGraph)` → `IGraphBuilder` (IID at `0x804CC4`), path built with `"%s.WMV"` (`0x8BD0E4`) and widened by hand, then `IGraphBuilder::RenderFile` (vtable `+0x34`) and `IVideoWindow` (IID at `0x8053C4`) sized to the game window. It loops pumping window messages until the movie ends or a skip key is pressed. If `RenderFile` fails it returns silently, so a missing file just skips the movie. The movies are WMV2 + WMA2 (720×480). Under Valve's Proton 10.0 they showed Proton's "video not available" placeholder (no decoder for these formats in a non-Steam game); under GE-Proton11-9 they play (user-confirmed). See `mod/README.md` "Deploy".

**Which movies are requested:** the names aren't in the exe. They are `PROP 0x080005E6` on movie-play actions in the levels, and all 12 match the 12 shipped files (nothing is requested that's missing): TITLE.GDW `INTRO` and `SHARK` (`PC MPEG Demo 1 Loader` / `… 1`), `Movie Scene 1–6` = `JAWSC4`, `JAWSC10`, `JAWSC7`, `JAWSC11`, `JAWSC8`, `JAWSC9` (menu order), `Trailers Page 0` `FLUX`/`PSYCHO`/`INF`, and CHASE.GDW `OUTSCENE` (`MPGPlay 3_pc`, the ending). The gaps in the `JAWSC` numbers (no 1–3, 5, 6) are not referenced anywhere; they may follow the film's scene or chapter numbering, which isn't verified.

## Push barriers: `ANTol` buoys and `NAWhirl2000` currents (2026-11-23)

Both "Current's too strong." boundaries push the shark instead of blocking it. Strength tables and the DOCKS gaps are in `docs/speedrun_glitches.md` section 13.

- **`ANTol`** (*tol* = push; class descriptor `0x8CB868`, vtable `0x7D18D4`), on the buoy template `BolyaDef`. BRTR `PROP 0x080002B2` + field index: `m_type`, `m_radius`, `m_fmul`, `m_delay`, `m_forcemax`. Runtime: `+0x100` next tick time, `+0x104` radius² (set by init `0x43F670` from `+0x114`), `+0x10C` type, `+0x11C` fmul, `+0x124` delay, `+0x12C` forcemax.
- **Tick `0x43F6A0`:** when the game clock (`[0x920E24]+0xB0`) passes `+0x100`, re-arm it `m_delay` ticks ahead; take the shark brick (`[0x90BC08]`) and the buoy's world positions (`+0xA8`/`+0xB0` = x, z; y ignored); if d² < r², push = the buoy's world Z axis (`+0x9C`–`+0xA4`, passed through `0x7080C0`) × (1 − d²/r²) × fmul; if `m_type` ≠ 0, clamp its length to `m_forcemax`. Then `0x694860(0x5F, vec)` and a `MSG_WHIRL` broadcast through `0x6C6120`. `0x43F700` is the same test for a given (x, z).
- The push follows the buoy's facing, not the direction away from the buoy, so overlapping buoys in a line add up.
- **`NAWhirl2000`** (descriptor `0x902FF8`, vtable `0x7F0A4C`, force function `0x63BD80` at slot `+0x84`): push along the path direction = force × (1 − d/rad), d = 3D distance to the path line. Runtime rad `+0x154`, grad `+0x15C`, force `+0x164`.
- **Message:** `0x63DD50` shows "Current's too strong." (string `0x8B2128`) and arms a timer. Message names: `MSG_WHIRL` = string `0x84F12C` (table `0x8D3FBC`), `MSG_ARAMLAT` (*áramlat* = current) `0x8D3F48`.
- Not traced: how the shark controller turns `MSG_WHIRL` into motion (so push units aren't converted to swim speed yet).
- **Current tick** `0x63D100` (2026-11-25): refreshes the shark brick `[0x90BC08]`, copies its world position (`+0xA8`–`+0xB0`) and calls its own force function (vtable `+0x84`, thiscall `(pos*, out*)`, `ret 8`; also slot `0x7D952C` of a second class). Only if that returns non-zero does it push the shark (`0x694860(0x5F, vec)`), broadcast `MSG_WHIRL` and send `0x65`. Out of range it returns 0 with `*out = 0`. Then it does the same for its other targets (`m_targets`). The mod's no-clip returns 0 for the shark's position (`mod/src/noclip_guard.cpp`).
- **Area trigger tick** (`ANSphereCheck`, vtable `0x7D128C`, tick `0x43BF60` at slot `+0x58`, init `0x43BF20`): every `+0x144` ticks (next time `+0x104`) calls `0x43BDE0`, which looks up the target `+0x11C` (`0x6C3010`, a live brick) and returns 1 when it is **outside** (distance² `+0x10C` > radius² `+0x108`; `m_type` `+0x114`: 2 = also outside above `+0x14C`/below `+0x154`, 3 = never inside below `+0x154`). `+0x100` keeps the last result; outside → inside runs the enter list (`+0x138` count, `+0x13C` ids), inside → outside the leave list (`+0x12C`/`+0x130`), each through `0x552190`. The swim-out prompt (`MBSwimoutChecker`, vtable `0x7D8AB0`, `0x496B10` shows "Do you want to leave this stage?") is one of the actions such a trigger starts.

## Control bindings and the profile (2026-11-25)

Found while adding the mod's `jaws_config.txt` control layout (`mod/src/config.cpp`).

- **Live bindings:** three arrays of 31 dwords, indexed by action: `0x8A0094` keyboard (DirectInput scan codes, e.g. `0x11` W, `0x39` Space; built-in defaults carry a `0x1000` bit), `0x8A0208` second slot (mouse buttons `0x103`–`0x10C`, `-1` unbound), `0x8A0300` gamepad (button numbers). Default keyboard table `0x8A0110` (or `0x89FF20` when `[0x8D681C]` ≠ 0). `0x8A018C` (or `0x89FF9C`) is a second keyboard table registered next to the main one and never saved (fixed extra keys). `0x8A0284`/`0x8A037C` are referenced at `0x546A93` together with the live arrays (not traced; probably the controls menu's defaults).
- **Input object** = static global `0x8D67F8` (vtable `0x7D6460`, constructed by the static initialiser `0x483C80`). Slot `+4` `0x483CE0` = startup: copies the default keyboard table into `0x8A0094`, creates the keyboard device `[0x8D6818]` (and mouse `[0x8D6800]` or pad `[0x8D67FC]`). Slot `+0xC` `0x483F30` = rebuild: `0x6C9450(-1)`, `0x6C9450(0)` clear the input manager's bindings (`[[0x920E24]+0x88]`), then `0x4842E0(0, mask, action)` per action registers the keyboard, extra-key and mouse/pad codes through `0x6C8D40` (skips `-1`). Plain `ret`, no stack arguments; slot `+0x10` `0x483F00` jumps to it.
- **Profile** (global `0x8D0110`, 0x1DB4 bytes, written verbatim to `PROFILE<N>.sav`): `+0x5C`, `+0xA8`, `+0xF4` = 19 dwords each (keyboard `& 0xFF`, second slot `& 0x1FF`, gamepad `& 0xFFFF`), each `action << 16 | code`, actions in the order of the table at `0x7E07E0` (`2 5 6 7 8 A C 0 B 9 3 18 19 16 17 4 1B 1 D`). Unbound = `0x1FF` (second slot) / `0xFF` (pad). (This corrects the older "`0x54`–`0x138`" range guess in the save notes.) Compared on the user's saves: a fresh default profile and the user's own layout differ in exactly these entries.
- **Load** (`0x539B30`): `fread` the save into `0x8D0110`, then for each of the 19 entries writes `array[entry >> 16] = entry & 0xFFFF` in all three arrays.
- **New game** (`0x537090`, called from `0x536738`): zeroes the profile, sets name `.....`, then fills the three binding tables **from the live arrays**. It never resets the arrays, so a new game inherits whatever layout is live. The stock game therefore resets to the defaults only because each session starts with the defaults, and loading a save first (then quitting to the menu) carries its layout into the new game.
- Controls-menu display (`0x539120`) and the menu's binding list (`0x54EC90`) read the arrays (`& 0xFF` / `& 0x1FF` / `& 0xFF`).
- **Action names** (the controls menu builds its list at `0x54E6E0` with `0x54EC90(label, action)`): `0` SHARK VISION, `1` DODGE, `2` SWIM, `3` TARGET LOCK, `4` MAP, `5` TURN UP, `6` TURN DOWN, `7` TURN LEFT, `8` TURN RIGHT, `9` TAIL WHIP, `0xA` CHARGE ATTACK, `0xB` STEALTH ATTACK, `0xC` BITE, `0xD` CAMERA MODE, `0x16` NEXT BODY PART, `0x17` PREVIOUS BODY PART, `0x18` NEXT TARGET, `0x19` PREVIOUS TARGET, `0x1B` PAUSE.
- **Code meanings** (menu text, `0x539120`; key names via `0x537550` = `MapVirtualKeyEx` + `ToAsciiEx` + name tables): keyboard = DirectInput scan code; second slot `0x103`/`0x104`/`0x105` = left/right/middle mouse button, other codes = "mouse button N" (code − `0x102`), `0x10B`/`0x10C` = mouse wheel; gamepad `< 0x17` = "BUTTON N" (code − 5), `0x17`–`0x1A` = d-pad up/right/down/left; `0xFF`/`0x1FF` = unbound. `[0x8D681C]` = the launch option Gamepad (vs Mouse & Keyboard), written by the startup settings code `0x729630` from its field `+0x118` (probably `pcrt.ini` `KeyboardLayout`, unverified). When set, input init creates a pad device (`[0x8D67FC]`) instead of the mouse, the rebuild registers the pad column instead of the mouse one, and the menu shows the pad column: mouse bindings are inactive in Gamepad mode.
- Open: what `0x1000` in the default keyboard codes means (save-loaded codes lack it and still work); which wheel direction `0x10B` is.

## Open items

- ~~Meaning of the two integers in each field registration~~: resolved 2026-10-03, see "`GDControl`… Registration integers, resolved".
- `GDControl` leftovers: the `0x400000` flag (`0x2000`/`0x4000`), why kill hides but keeps collision, why file-set `0x100` keeps collision but runtime-set `0x100` doesn't, spawn modes 3 vs 4, and the engine code that gives group-type nodes' actions a live instance at load.
- How the shark controller applies `MSG_WHIRL` (`0x5F`) pushes from buoys and currents (see "Push barriers").
- Complete the class-name resolution in `dump_class_fields.py` (132/691 named).
- The full state-value enumeration of `SetState` (~40 states; only `7` = dead identified).
- `0x920E24` engine object layout.
- The second shark animator (`ctrl+0x15C`, gated by `ctrl+0x24C`), the animator flag bits `1`/`2`/`4`, and whether a player skeleton needs exactly 40 bones (2026-10-21).
- Whether the scripted-death side effects (model hide, mission notification) can also be suppressed cleanly. The user said this isn't wanted (2026-10-01), so it's parked.

## On-screen message tables (2026-10-04)

The game's on-screen messages (prompts, hints, mission text) live in **5 language tables of 1,000 `char*` each**, in writable `.data`. `[0x854D14 + 4*lang]` points at each table; English is `0x84FEF0`, the other four follow at `0x850E94`, `0x851E34`, `0x852DD4`, `0x853D74`.

- **Startup** (`FUN_00453ac0`): creates a hash (`FUN_006b8140(0x7F7, 0x18)`: flag `0x8` = case-insensitive, `0x10` = keys aren't copied) and adds every English message as key → number 1…1000 (`FUN_006b8300`).
- **Lookup** (`FUN_00453d00(text)`): hashes the English text (`FUN_006b8910`), and if found returns `tables[lang][n − 1]`, with `lang = [0x920E24]+0x38` clamped to 0…4. Otherwise it returns the text unchanged.
- So code refers to messages by their English text, e.g. `MBSwimoutChecker` pushes the mixed-case `"Do you want to leave this stage?…"` (`0x8A13E0`, pushed at `0x496B4B`), which resolves case-insensitively to slot 201.
- Because the hash keys are the original strings, **repointing a table slot changes the displayed text without breaking the lookup**. The mod does this per stage (`mod/src/messages.cpp`, file `jaws_messages.txt`). User-confirmed 2026-10-04.

Exit-related slots: **598** `\nDO YOU WANT TO ENTER THIS AREA?…` (the `LoadChecker` prompt used by area-trigger exits; the game puts the destination name, e.g. `OPEN OCEAN - SOUTH`, in front of it), **201** leave this stage (`MBSwimoutChecker`), **199**/**851** completed stage, **200** stage locked. In the game font `[` and `]` draw the Esc and Enter key icons; `^OK^`, `^CANCEL^`, `^CONT^` are the button tokens. Full numbered list: `docs/game_messages.txt` (`scripts/dump_messages.py`).

## Stage loading and the F10 reload (2026-10-03)

- **Engine object** `[0x920E24]`, vtable `0x7F6018` (the base class's is `0x7D2810`; both share the slots below). Found by locating the dword `0x6C3FD0` in `.rdata`. **Caution:** the tables at `0x7D2818`/`0x7F6020` are 8 bytes off; reading slots from them gives wrong functions.
- **`+0x78` = `0x6C3FD0`, raw stage loader `(name)`**: copies the name, appends `.GDW` if there's no extension, records the file name at `0x920D20`, checks already-loaded `FDIR` sub-archives by name first, otherwise opens the file and runs the chunk walker (`FUN_00693180`). Stores the argument at `engine+0xB8`. It loads immediately, so it must only run from the engine's own tick.
- **`+0x80` = `0x6C3C50`, `RequestStage(flags, name)`**: `thiscall`, `ret 8`. Its entire body: `engine+0x40C |= flags; if (name) strcpy(engine+0x410, name)`.
- **Engine tick `FUN_006C7800`** (vtable `+0x50`), request flags `engine+0x40C`:
  - `8`: clear flags, `vtbl+0x2C` (unload).
  - `1`: clear flags, `vtbl+0x2C` (unload), `FUN_006b5cf0`, `vtbl+0x78(engine+0x410)` (load), then re-init `vtbl+0x28`.
  - `0x20`, `4`, `2`: other paths (pause/reset-style; not decoded).
- **Callers:** the leftover dev "Open Stage" window command (`0x99`, handler near `0x726457`) calls `+0x80(1, path)`. `FUN_006c4ab0` calls `+0x80(0x20, 0)` when an async load completes. Startup (`FUN_00726be0`) calls `+0x78` directly with the initial stage.
- **Async state machine** at `engine+0x510` (`[0x144]`, 0 = idle, 1 = load, 2/3 = disc streaming), name at `+0x530`, progress float at `+0x598`. Driven by `FUN_006c4610` (from `0x729cd0`) and `FUN_006c4ab0`. Not used by the mod.
- **Byte-scan trick:** calls through `[0x920E24]` vtable `+0x78` were found by scanning for the engine pointer's address followed within 40 bytes by `FF 5x 78` (`call [reg+0x78]`): six sites, including `0x6C46F8` and `0x727055`.
- **Mod:** F10 calls `+0x80(1, <engine+0xB8>)` after checking the vtable slot really holds `0x6C3C50` (`mod/src/stage.cpp`).

---

## Moved from CLAUDE.md (2026-11-25)

The text below was moved word for word from the root `CLAUDE.md`. It is newer than earlier sections of this file where they disagree.

## Executable Analysis — `Jaws.exe` (Ghidra) and the Mod

**Decompiled 2026-10-01.** Full detail in **`docs/exe_analysis.md`**; this is the summary. Ghidra 12.1.4 lives at `~/tools/ghidra_12.1.4_PUBLIC` (needs JDK 21), with the analyzed project at `~/tools/ghidra_projects/JAWS.gpr`. Headless helper scripts are in `scripts/ghidra/` (`DecompAt.java`, `DecompStringRefs.java`, and `CreateDecomp.java`, which first creates functions Ghidra missed, e.g. ones only reached through a vtable). The exe has a fixed image base (`0x400000`) and no ASLR, so all addresses below are stable.

**Player shark, verified in-game:**
- `0x90BC04` = singleton pointer to the **player shark controller** (set by the constructor at `0x664BD8`, cleared by its destructor; null in menus/loading).
- `ctrl+0x50` = the shark's scene object ("brick"). **World position = floats at `brick+0xA8`.**
- Controller fields: `+0x810` collision off (no-clip, see the mod table), `+0x240` state (`7` = dead), `+0x2A8`/`+0x2B0` max/current **health**, `+0x2AC`/`+0x2B4` max/current **hunger** (user-verified), `+0x72C`–`+0x73C` five ability multipliers loaded from the save, `+0x54` `SharkConfig`.
- The shark model faces its local **+Z**, so heading comes from the world matrix's Z row.

**Brick (scene object) layout**, from the engine's world-matrix updater `0x696EA0`: `+0x0C` flags (`0x20` = world matrix stale), `+0x14` parent pointer, `+0x50` local 4×3 transform (same layout as BRTR `PROP 0x080017DA`), `+0x84` cached world 4×3 transform (translation at `+0xA8`).

**Stage loading (2026-10-03):** engine object = `[0x920E24]`, vtable `0x7F6018`. Slot `+0x78` = `0x6C3FD0`, the raw loader: appends `.GDW`, checks loaded `FDIR` sub-archive names first, loads immediately and stores its argument at `engine+0xB8`. Slot `+0x80` = `0x6C3C50`, `RequestStage(flags, name)` (`thiscall`, `ret 8`): only `engine+0x40C |= flags; strcpy(engine+0x410, name)`. The engine tick `0x6C7800` (vtable `+0x50`) handles flag `1`: unload (`vtbl+0x2C`), raw-load `engine+0x410`, re-init (`vtbl+0x28`). Flags `2`/`4`/`8`/`0x20` take other paths, not decoded. The dev "Open Stage" menu calls `+0x80(1, path)`, and a finished async load calls `+0x80(0x20, 0)`. A separate async state machine sits at `engine+0x510` (`FUN_006c4610` / `FUN_006c4ab0`, name at `+0x530`). The mod's F10 reload uses `+0x80(1, current name)`.

**`GDControl` = level scripting (decoded 2026-10-03, full tables in `docs/exe_analysis.md`).** `ACTN` blocks with class header `0x0203B039` (every `ACTN` has its own ID, second header word; list entries can be node or action IDs). Up to 8 timed steps: `m_CtrlN` (`PROP 0x08001819 + 3(N−1)`) = `[w0, w1, w2]`, `m_ListN` (`0x0800181A + 3(N−1)`) = target IDs. A step fires `w1 + rand(0…w2−w1)` ticks after start (`w1` signed; −1 = in the start pass itself, 0 = next tick). `w0` low bits: `0x1` start, `0x2` stop, `0x4` add to world, `0x8` kill, `0x200` spawn a copy, `0x80`/`0x100` show/hide (`m_nFlags 0x100`), `0x10`/`0x20`/`0x40` edit flags `0x10`/`0x40`, `0x400`/`0x800` suspend/resume, `0x1000` use the stored list. High bits pick the scope (brick vs node, recurse into children); `0x0F000000` is the default (89%). Engine: start `0x6B68A0`, executor `0x6B6C00`, interpreter `0x6B6DB0`. Targets resolve to the object's **live action instance** (`0x6C3010`, registered object `+0x24`) and the **registered object** itself (`0x6C2F90`, `m_nFlags` at `+0x18`); corrected 2026-10-03, the first decode had these swapped. 3,261 controls in 19 GDWs. `scripts/dump_gdcontrol.py` prints them readably; it also shows dangling target IDs (`missing#…`, 9–72 per level), likely objects deleted during development.

**Bite animation `Shark_GW_Pitbull04` (2026-10-12):** the great white's normal grab-chew-shake clip (AQUARIUM `SKEL 2515` frames 997–1036), and the bite damage is timed to it. A clip-frame table at `0x6651BB`–`0x6652A7` stores its start/end and frames start +12/+23/+33 and +5/+11 in globals `0x90BCB4`–`0x90BCE4`. `0x66B187`/`0x66B475` play it (sub-state `ctrl+0x248` = 6, sound `Jaws.Chew`). In state 5 (prey held at `ctrl+0x204`), `0x65CB30` sends a damage message (`0x27`) each time the animation passes one of those frames: 3 bites in sub-state 6, 2 in sub-states 9/22. Damage = `(cfg[0xD74] × ctrl[0x730] + k1) × cfg[0x4AC]`, so a save ability (probably bite strength, unconfirmed) scales it. Sub-state 15 is a separate shake/tear (`Jaws.Tear`, debug `Razas damage!`). Open: what enters states 5/9/22. Details: `docs/exe_analysis.md` "Bite animation".

**Shark tick, input, water and animation runtime (2026-10-21, from the Ecco port; full detail `docs/exe_analysis.md` "Tick, input, water height and the animation runtime"):** the shark tick is vtable slot `0x7F2944` = `0x667FB0`, and replacing it replaces the movement while collision push-out, F8 and the camera keep working (collision is resolved outside the movement code). Pad = `[[0x920E24]+0x88]+8` (`[buttons][prev][X][Y]`, swim `2`/`0x800000`). Water height = fn ptr `0x8B2E9C` (`float f(const float* pos)`, `-2147483648.0` = no water). Clip animator at `ctrl+0xBC` (update `0x4DD250`, fields: `+0x14` frame, `+0x1C`/`+0x20` range, `+0x3C` weight, `+0x44` speed, `+0x60` flags, `8` = loop) can be posed from outside by save/write/update/restore; clips are found **by name only**, so any skeleton whose `ANIM` carries the shark clip names plays as the player. Second animator `ctrl+0x15C` (gate `ctrl+0x24C`) unidentified. `0x6F5EB0` poses at a fractional frame and sums the `SKEL` root-motion deltas; SKEL loader `0x6F47D0` (`+0x1C` root motion, `+0x20` frames, `+0x40` vertices). `ANIM`'s second header word = total name bytes (345/345 shipped chunks).

**Death paths:** every death goes through the controller's state setter **`0x65EDA0`** (`thiscall SetState(state,-1,-1)`, `ret 0xC`) with state `7`, from four call sites: health ≤ 0 (`0x65D871`), a **scripted `DIEM` kill message** (`0x65B871`, which also zeroes health and hunger), and two timer-based deaths (`0x668CC6`, `0x66D4E9`).

**On-screen message tables (2026-10-04):** `[0x854D14 + 4*lang]` → 5 language tables of 1,000 message pointers (English `0x84FEF0`, writable `.data`). Code asks for a message by its English text: `FUN_00453d00` looks it up in a case-insensitive hash built once at startup (`FUN_00453ac0`) and returns `tables[lang][n − 1]`, lang = `[0x920E24]+0x38`. Repointing a slot changes the text (the mod's message overrides). Exit prompts: slot 598 "enter this area" (`LoadChecker`, the game prefixes the destination name), 201 "leave this stage" (`MBSwimoutChecker`), 199/851 completed stage, 200 locked. `[`/`]` render as the Esc/Enter key icons. List: `docs/game_messages.txt`.

**Reflection field table:** every class field is registered by a stub calling `0x70B6A0` (6,457 sites). `scripts/dump_class_fields.py <out.json>` dumps all of them (691 class descriptors, 132 with resolved names). Each stub passes two integers: **`a` = offset of the property wrapper in the class's props object, `b` = offset of its mirrored copy in the runtime object (0 = none); the value sits at +4** (settled 2026-10-03 via `GDControl`, see `docs/exe_analysis.md`). A class's BRTR PROP IDs are consecutive in registration order (e.g. `ANSeekerRef`: `0x080002E9` + field index).

**Correction:** `NAPredator` is the **"predator vision" screen effect** (fields `m_magnification`, `m_power`, `m_strength`…), **not** the shark. The shark is driven by `MLSharkCtrl` + `SharkConfig`, and the camera/minimap by `MLSharkCamera`.

**Why the old position scans failed:** they only searched the exe's static `.data` section (`0x845000`–`0xE6C000`). The shark is heap-allocated at level load.

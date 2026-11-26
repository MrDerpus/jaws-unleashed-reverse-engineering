# Jaws.exe (Ghidra)

**In short:** this is the game program's side of the project, from decompiling `game_binary/Jaws.exe` in Ghidra. It covers:
- where the player shark lives in memory: position, health, hunger, state, collision, bite;
- how objects, scripts and stages work at runtime;
- the decoded logic of the cut *Hot Pursuit* and the Aurora rope fight;
- draw distance, movies, push barriers, controls and on-screen messages;
- the 812 function names carried over from *Ecco: Defender*'s debug build.

All addresses are virtual addresses in the shipped PC exe. It has a fixed image base `0x400000` and no ASLR, so they're stable across runs. This work fed the mod's overlay, teleport, invincibility, no-clip and reload (`mod/README.md`).

Rewritten for readability on 2026-11-27. Old version: `docs/archive/exe_analysis_old_2026-11-27.md`.

---

## Contents

1. [Tooling](#1-tooling)
2. [Ecco: Defender debug symbols](#2-ecco-defender-debug-symbols)
3. [GDED text format](#3-gded-text-format)
4. [Reflection field registration](#4-reflection-field-registration)
5. [Scene objects ("bricks")](#5-scene-objects-bricks)
6. [Player shark controller](#6-player-shark-controller)
7. [Other classes: SC17 mission, camera](#7-other-classes-sc17-mission-camera)
8. [`GDControl`: level scripting](#8-gdcontrol-level-scripting)
9. [Object registry, live actions and destructibles](#9-object-registry-live-actions-and-destructibles)
10. [Cut story mission Hot Pursuit](#10-cut-story-mission-hot-pursuit)
11. [Cut Aurora rope](#11-cut-aurora-rope)
12. [Draw distance and fog](#12-draw-distance-and-fog)
13. [Movie playback](#13-movie-playback)
14. [Push barriers](#14-push-barriers)
15. [Control bindings and the profile](#15-control-bindings-and-the-profile)
16. [On-screen message tables](#16-on-screen-message-tables)
17. [Stage loading and the F10 reload](#17-stage-loading-and-the-f10-reload)
18. [Open items](#18-open-items)
19. [Old mistakes](#19-old-mistakes)

---

## 1. Tooling

**Ghidra:**
- Version 12.1.4 at `~/tools/ghidra_12.1.4_PUBLIC`. It needs a full JDK 21 (`openjdk-21-jdk`; the JRE alone is rejected). `support/launch.properties` has `JAVA_HOME_OVERRIDE=/usr/lib/jvm/java-21-openjdk-amd64`.
- Project `~/tools/ghidra_projects/JAWS.gpr`: `Jaws.exe` imported and fully analysed (~10 min).
- GUI: `~/tools/ghidra_12.1.4_PUBLIC/ghidraRun` → File → Open Project. Close it before running headless scripts on the same project.

**Headless helpers** (copies in `scripts/ghidra/`, run from `~/tools/ghidra_scripts/`; paths must not contain a dash, or Ghidra's OSGi loader fails):

| Script | Does |
|---|---|
| `DecompStringRefs.java <out> <string>...` | Decompiles every function referencing an exact string |
| `DecompAt.java <out> <hexaddr>...` | Decompiles the function containing each address, and lists its callers |
| `RefsDecomp.java <out> <addr\|f:addr>...` | Decompiles every function referencing each address, with callers. `f:ADDR` decompiles the function containing ADDR, creating it if needed. |
| `CreateDecomp.java` | Creates functions Ghidra missed (e.g. reached only through a vtable), then decompiles |
| `FuncRanges.java` | Function list (for the name matching in §2) |

```bash
~/tools/ghidra_12.1.4_PUBLIC/support/analyzeHeadless ~/tools/ghidra_projects JAWS \
    -process Jaws.exe -noanalysis -readOnly \
    -scriptPath ~/tools/ghidra_scripts -postScript DecompAt.java /tmp/out.c 0x65eda0
```

**Limitation:** many small functions are reached only through vtables or static-initialiser tables, so auto-analysis misses them (`ref from ... in <none>`). Read those with `i686-w64-mingw32-objdump -d -M intel --start-address=... --stop-address=...`. Plain byte-pattern scans in Python worked well too; all the field-registration, vtable and call-site searches below were done that way.

**Exe sections** (`objdump -h`):

| Section | Range |
|---|---|
| `.text` | `0x401000`–`0x7CE000` |
| `.rdata` | `0x7CE000`–`0x845000` |
| `.data` | `0x845000`–`0xE6C000` |

Plus `.idata` and `.rsrc`. Imports include `d3d8.dll` (`Direct3DCreate8` only), `DINPUT8.dll`, `DSOUND.dll`, `WINMM.dll`. No D3DX, no packer.

---

## 2. Ecco: Defender debug symbols

**In short:** Appaloosa's Dreamcast dev kit has an unstripped *Ecco: Defender* build with full symbols and class layouts. Names carry over to Jaws; offsets only partly. 812 Jaws functions were named from it.

### The files

- `ECCO.ELF` (13,166,002 bytes, 2000-06-01/02) plus its linker map `0.MAP` (`Link Map of "debug.elf"`, 25,755 lines). Background: `docs/gwb_lineage.md` §5.
- Identical copies on the `144 M` dev disc and in the recovered hard disk's `Z` build folder; the `269 M` disc has the same `0.MAP`. It's the build behind that date's `0.BIN`.
- Renesas SH-4 ELF, little-endian, Hitachi/cfront-style mangled C++ (`_Execute__11NAWhirl2000Fv` = `NAWhirl2000::Execute()`).
- **12,156 named functions**, ~180 source files (`gdbrick.cpp`, `gdres.cpp`, `NAWhirl.cpp`, `Shark_1.cpp`, …; full list from the map's `From file:` lines).
- **`.debug` is DWARF version 1** (7.3 MB): 2,168 classes and structs with bases, members, types and offsets. readelf, objdump and Ghidra can't read DWARF v1, so `scripts/dwarf1_classes.py` parses it. Full dump: `docs/ecco_defender_classes.txt`.

**`/DEBUGBIN/0.BIN` is not usable** (2,919,116 bytes, 2000-04-17; the same on the `132 M` and `144 M` discs and the hard disk). Only the first 0x80000 bytes are code; the rest is level data, cross-linked when the disc was burned. No strings, no symbols.

### How it carries over to Jaws

Jaws is a later code line (via *Sentinels*), on x86 instead of SH-4.
- **Class-specific fields** mostly keep their order and spacing; only the base class in front grew. One constant shift per class for `GDFog`, `GDSector`, `GDFont`, `GDRotSprite`, `NAWhirl2000`, `NAFade`, `MLParticle` and others. `GDModel`, `GDSprite`, `NAFlare`, `NAParticle2000` show 2–3 shifts (fields added in between).
- **`GDBrick` was reorganised** (§5).
- SH-4 code can't be matched to x86 byte for byte. Functions are matched by strings, constants, field offsets and call structure.

### The 812 names

Applied in the Ghidra project (backup: `~/tools/ghidra_projects/JAWS.rep.bak_preEccoNames`) and listed in `docs/jaws_function_names.tsv` (address, name, Defender symbol, method). Three methods, each checked against the others:

1. **Vtables (605),** `scripts/ecco_jaws_vtables.py`.
   - 424 classes (object, `Props` and `Factory` vtables) exist in both games.
   - Slots are aligned by *which classes override them*.
   - Jaws inserted virtuals early in `GDAct` and `GDBrick`:

     | Method | Defender slot | Jaws slot |
     |---|---|---|
     | `GDAct::GetFactory` | 8 | 16 |
     | `GDAct::Execute` | 10 | **18** (the shark tick slot) |
     | `GDAct::OnActivate` / `OnDeactivate` | 12 / 13 | 20 / 21 |
     | `GDBrick::GetFactory` | 11 | 19 |
     | `GDBrick::Execute` | 14 | **22** (the `NAWhirl2000` tick `0x63D100`) |

   - The destructor is slot 0 everywhere. The Jaws "factory vtable" is Defender's `<Class>Factory` (`GetClassName`, `Create`, `CreateProps`, `DeleteProps`, `GetBase`).
2. **Strings and constants (128),** `scripts/ecco_jaws_strings.py`.
   - Defender loads strings as *table base + offset*; both words are combined.
   - Gives the whole `GDFile` reader and writer (`ReadChunkID`, `ReadInt`, `WriteResID`, …).
   - Through chunk tags and version stamps, it also gives the loader:

     | Function | Address |
     |---|---|
     | `GDLoadGame` | `0x693180`, `0x6C4E90` |
     | `GDBrickProps::LoadTree` | `0x699360` |
     | `GDObjWizard::LoadClasses` | `0x70C580` |
     | `GDMesh::Load` | `0x6D15F0` |
     | `GDMaterial::Load` | `0x6CE010` |
     | `GDTexture::Load` | `0x7053C0` |
     | `GDMeshRegions::Load` | `0x6E3CB0` |

     Also `GDBoneData::Load`, `GDTileMap::LoadWorldDim`, `GDMovie::Load`/`Play`.
3. **Call graph and locality (79),** `scripts/ecco_jaws_callgraph.py`.
   - Spreads names from known pairs to callees and callers; both sides must agree.
   - Fills gaps between two named functions of the same source file when both gaps hold the same number of functions.
   - Found e.g. `GDBrick::CalcAbsMatrix` `0x696EA0`, `GDBrick::InvalidatePos` `0x6970B0`, `GDMatrix::Multiply` `0x6D0070`, `GDBase::GetObj` `0x692650`, and `NAWhirl2000::CalculateDisplacement` `0x63BD80` (already known as the current's force function: an independent confirmation).

**Precision check:** neighbouring named functions should come from the same Defender source file. They do for 96 % (vtables), 94 % (strings) and 79 % (call graph). Treat call-graph names as likely, not certain.

**Limits:**
- Only code shared with Defender can be named. Jaws-only classes like `MLSharkCtrl` get nothing.
- Most names are virtuals. Non-virtual engine code is reached only through the call graph, which stalls because the compilers inline differently.
- `0.MAP` is from a slightly different build, so its addresses don't match the ELF. It's used only for file membership.

**Pipeline:** `FuncRanges.java` + the class → vtable table from the `JawsFactories` Ghidra script, then the three scripts. See `docs/scripts.md`.

**Side effect:** Jaws `GDFile` slot 33 is `WriteChar` (default keyword `"CHAR"`). The string matcher had paired it with `NAGeneralAct::FireIceNeedles`; that name was dropped.

---

## 3. GDED text format

**In short:** Jaws can still read the editor's text level format, and a whole level rewritten as text loads and plays (user-confirmed 2026-11-25). Nothing in the game can write it. The user judged it not practical for editing; closed.

### Reading: built in

- `GDFile` (base vtable `0x7F5B2C`, abstract) handles both encodings. Layout as in Defender, shifted by the vptr:

  | Offset | Field |
  |---|---|
  | `+0x04` | `m_nMode` |
  | `+0x08` | `m_nType`: **0 = binary, 1 = text** |
  | `+0x10` | Written tabs |
  | `+0x14` | Chunk level |

- Every `Read*` and `Write*` branches on `m_nType`.
  - In text mode the writers print `Name: value` lines indented by chunk level (`%s: "%s"`, `%s: %c%c%c%c ` for resource IDs, `%s: %d-%d-%d` for class IDs).
  - The readers tokenise (errors "Bad integer value.", "Bad Chunk ID (included non ASCII characters).").
- **`ReadHeader` `0x6BBAC0`**, called from `GDLoadGame` `0x693180`, reads `GDED`, then `BINARY` (type 0) or **`TEXT` (type 1)**, then `FORMAT, VERSION a.b.c.d`.

**Static check, all passed:**
- All 23 read helpers (`0x6BC240`–`0x6C08A0`) have a text branch. They tokenise on ` \r\n\t`, read a `label:`, then the value. Strings are quoted; numbers go through `sscanf`.
- **Chunks:** `ReadChunkID` reads `Chunk: TAGN` and returns end-of-chunk on `}`. The skip function `0x6C08A0` skips an unknown chunk by counting braces (ignoring any inside quotes).
- **Raw buffers** (`ReadMemBuffer` `0x6BFCE0`: texture pixels, `DXTF` data, `BNCH`, samples) have a text form: one `%x` hex token per byte, about three times the size.
- Binary-only alignment padding is skipped in text mode.
- Of 79 functions that read through `GDFile`, the only direct raw read is in the `FDIR`/`FSIZ` handler `0x6C3D90` (24 raw bytes per name), needed only for the loading-screen sub-archives.
- `GetFileSize` is used only for the loading bar. A level without `BRTR` hangs ("Brick Tree not found").

### In-game tests (user-confirmed 2026-11-25)

- **A full text level loads and plays.** `custom_levels/TXTMODE.GDW`: the pruned blank FISH base (105.6 MB binary) rewritten as text (240 MB, plus the unchanged 14 MB sub-archive, with `FDIR` and `FSIZ` patched). Loading takes ~20 s, because the game reads text one byte per virtual call.
- **A text edit works.** Changing `FogAbove`'s colour (`PROP 0x08001853`) to 0.56, 0, 0.29 changed the above-water fog.

**How the text was made:**
- The mod's read trace (`mod/src/gdtrace.cpp`, switch file `jaws_gdfile_trace.on`) logs every raw read with its caller during a binary load.
- `scripts/gdw_to_text.py` maps each caller to its reader (int, real, string, vector, …) and writes the value in that reader's text syntax.
- Return addresses used: chunk-end `Tell` `0x6C0375`, tag/size reads `0x6C03D1`/`0x6C03E7`, unknown-chunk skip `0x6C08C2`.
- The trace must be of a load of the *same* file; one trace converts one level. The `TXTBASE` load made 1.68 M reads and 76,762 chunks (1,763 skipped as unknown).
- Text can't hold NaN or Inf. The only ones in stock data are 3,293 uninitialised weights of unused bone slots in `WGHT`, written as 0.

**Editing rules:**
- **A text editor that saves the whole file breaks it.**
  - The header must end in raw `\r\n\r\n`; converted to `\n\n`, the load hangs.
  - The raw `FDIR` name and the binary sub-archive after the text get re-encoded (the user's editor grew the file by 7 MB).
- The `FDIR` offsets and `FSIZ` are absolute. Keep the byte length (pad a shortened line with trailing spaces) or recompute them.
- **Safe:** `sed` or a script, or an editor that keeps binary bytes and CRLF untouched.

### Writing: unreachable

- `WriteHeader` (`0x6BA970`, slot 32) and every other `Write*` method are referenced only from the four `GDFile` vtables.
- **File classes:**

  | Vtable | What |
  |---|---|
  | `0x7F5C0C` | Disk file of the PC file system |
  | `0x7F5CF4` | `GDMemFile`: mode 1 only grows a buffer; `Close` frees it, never writes |
  | `0x7F5DDC` | Wraps a stream; created by the stage loader (`0x6C4382`/`0x6C5501`) |

- **File systems** sit in a priority list at `0x920D00`. The PC file system's vtable is `0x7FB5DC`: `GetFileSize` `0x727F90`, `OpenFile` `0x728170`, `CreateFile` `0x6C2240` (`+0x28`), `GetFileData` `0x728060`. The current one is at `[0x920E24]+0x8C`.
- **Every disk open uses mode 0 (read).** The only `CreateFile` call (`0x6C4BBB`, async loader `0x6C4AB0`) opens the memory file in mode 0 and attaches already loaded data.
- Defender's game build likewise has `Load` for every class but no `Save`. Saving lived in the editor; the writer survives only because it's virtual.

---

## 4. Reflection field registration

**In short:** every class field is registered by a tiny stub calling `0x70B6A0`. The two integers it passes are the field's offset in the props object (`a`) and in the runtime object (`b`); the value sits 4 bytes in.

**The stub** (6,457 call sites):

```
mov  eax, [typedesc_ptr]     ; field type descriptor
push A                       ; props-object offset of the wrapper
push B                       ; runtime-object offset of its mirror (0 = none)
push eax
push classdesc               ; class descriptor
push name                    ; "m_..." field name
push 0
mov  ecx, fielddesc          ; static field descriptor being filled
call 0x70B6A0                ; stores the args and links into a list at 0x93C630
```

**Class names** come from getter stubs next to each constructor: `mov eax, <name>; ret`, then `mov eax, [parent?]; ret`, then `mov eax, <classdesc>; ret` (twice).

**`scripts/dump_class_fields.py <out.json>`** finds 6,457 fields in 691 class descriptors. Only 132 descriptors get a name, because the getter pattern match is incomplete. Output: `{"ClassName@0xdesc": [{name, a, b, typedesc_ptr, reg}, ...]}`.

**The integers, settled via `GDControl` (2026-10-03):**
- `m_Ctrl1` (`a` = `0x48`): the executor reads the props at `+0x48`/`+0x4C`.
- `m_DeactProps` (`a` = `0x128`): read at `+0x12C`.
- `m_List1` (`b` = `0x3C`): the executor uses runtime `+0x3C` unless op bit `0x1000` is set.
- The base brick's `mtx` registers as (`0x30`, `0x4C`) and the brick reads its matrix at `+0x50`.

**PROP IDs:** a class's level `PROP` IDs are consecutive in registration order (e.g. `ANSeekerRef` = `0x080002E9` + field index). Exact names come from the level's `CLAS` table (`docs/scene_graph.md` §2).

---

## 5. Scene objects ("bricks")

From the world-matrix updater **`0x696EA0`** (`GDBrick::CalcAbsMatrix`), called before any world-space read when the stale flag is set:

| Offset | Field |
|---|---|
| `+0x0C` | Flags, loaded from the node's `m_nFlags`. `0x20` = world matrix stale; `0x400` = inverse dirty; `0x20000000` = absolute (skip the parent) |
| `+0x10` | Next sibling |
| `+0x14` | Parent (or null) |
| `+0x1C` | First child |
| `+0x3C` / `+0x40` | Attack / sensor masks (`m_PrimAttacks` / `m_PrimSensors`) |
| `+0x4C` | Property header of the local matrix |
| `+0x50` | **Local transform**: 12 floats, the same layout as `PROP 0x080017DA` |
| `+0x84` | **Cached world transform** = local × parent world (`0x6D0070`). **World translation at `+0xA8`.** |
| `+0xB4` | Inverse world matrix, rebuilt by `0x6D0370` when flag `0x400` is set (new in Jaws) |
| `+0xE4` | Probably the previous frame's matrix, compared with `+0x84` to detect movement |

- The updater recurses up the parent chain if the parent is also stale. This matches nested nodes being local to their parent.
- The `0x20000000` rule was confirmed 2026-10-01: FISH's `fenyo` trees and `Box0N` cards (flags `0x2000005A`) only land right when not composed.
- `GDMatrix` = `GDMatrix3` (9 floats) + `GDVect t`, hence world translation at `+0x84 + 0x24`.
- The base brick's field registration (descriptor `0x91DAF0`) lists `m_Name`, `m_nFlags`, `mtx`, `m_ExecFilter`, `m_CameraFilter`, `m_Viewport`, `m_CreatorDistance`, `m_RoomMask`, in the level file's order. Its strings sit next to `GDStdBrick`, so this is very likely `GDStdBrick`.
- **Not mapped:** `+0x18` (a pointer whose `+0xD8` is a fallback collision list), `+0xE8`, `+0xF0`, `+0xF4`.

### Compared with Defender's `GDBrick`

Jaws offsets come from decompiling `0x696EA0`, `0x696F40`, `0x696580`, `0x695F30` (collision pair test) and `0x6974B0` (sets `0x40420`, walks children).

| Defender field | Defender | Jaws | Jaws evidence |
|---|---|---|---|
| `m_nFlags` value | `+0x08` | `+0x0C` | Flags above |
| `m_pParent` | `+0x14` | `+0x14` | Parent composition |
| `m_pChild` / `m_pNext` | `+0x70` / `+0x18` | `+0x1C` / `+0x10` | `0x6974B0` loops `[+0x1C]` → `[+0x10]` |
| `m_PrimAttacks` / `m_PrimSensors` | `+0xB4` / `+0xB8` | `+0x3C` / `+0x40` | `0x695F30`: `mask & a[+0x3C] & b[+0x40]` |
| `mtx` | `+0x24` | `+0x4C` (matrix `+0x50`) | |
| `m_CurMtx` (world) | `+0x80` | `+0x84` | |
| Inverse world | none | `+0xB4` | New in Jaws |
| `m_pOldMtx` | `+0xB0` | probably `+0xE4` | |

---

## 6. Player shark controller

### Finding it

- **`NAPredator` is not the shark.** Its fields (`m_magnification`, `m_power`, `m_freqpower`, `m_strength`, `m_smoothrate`) are the **predator-vision screen effect** (compare FISH's `PredatorEffectNONPS2`).
- **The shark is `MLSharkCtrl`** (class descriptor `0x90B388`, one field `m_cfg` → `SharkConfig`). Its strings sit among the `Jaws.*` sound events and debug strings (`SharkRelPos`, `CHEAT`, `autocolli %5.0f`, `TailCombo!`).
- The debug routine printing `"SharkRelPos"` (`0x671060`) is slot 21 of vtable **`0x7F28FC`**. The constructor at **`0x664BD8`** installs it and does `mov [0x90BC04], esi`; the destructor at `0x664C20` clears it.
- **So `0x90BC04` is the player-controller singleton.** About 194 code references.

### Pointer chain (verified in-game 2026-10-01)

```
ctrl  = *(DWORD*)0x90BC04          // null outside gameplay (menus, loading)
brick = *(DWORD*)(ctrl + 0x50)     // the shark's scene object
pos   = (float*)(brick + 0xA8)     // world X, Y, Z
```

- On FISH, spawn reads (2000, −6.4, −3630.7) against the level's `SharkPosReal` at (1998, −7, −3628).
- Values change smoothly while swimming, repeat exactly at the same spot, and Y ≈ 0 at the surface.

**Facing:** the model faces its **local +Z**.
- `GWside`'s head parts (`FixedBrickHead`, `Mouthbrickcsont`, `VerBrick`) sit at local +Z (1.4–1.7).
- The tail (`FixedBrickFarok`) is at −3.4, the dorsal fin (`FelsoUszonyFixedBrick`) at +Y, the right fin (`Jobb…`) at +X.
- So heading = the world matrix's Z row (floats 6–8 at `+0x84`). The model is scaled ~2.1, so normalise first.

### Controller fields

All confirmed by reading code.

| Offset | Meaning | Evidence |
|---|---|---|
| `+0x50` | Shark brick | `SharkRelPos` routine |
| `+0x54` | `SharkConfig` | Ability setup reads tuning floats from it (`+0xD84`, `+0xD8C`, `+0x10C`, `+0xB98`) |
| `+0x58` | Object whose `+0xA8` also mirrors the shark's position (also referenced from `+0xCC`, `+0x16C`) | Runtime scan 2026-10-04 |
| `+0xBC` | Clip animator | §6 "Animation runtime" |
| `+0x204` | Held prey / bite target (gets damage message `0x27`) | `0x65CB30` |
| `+0x240` | State (`int`). **7 = dead.** | Is-dead check `0x664770` |
| `+0x244` | Second state value (set to −1 with `+0x240`) | Constructor `0x66693D` |
| `+0x248` | Sub-state while holding prey: 6 = full `Pitbull04`, 9 / 0x16 = 2-bite variants, 0xF = shake/tear | `0x65CB30` |
| `+0x2A8` / `+0x2B0` | **Max / current health** | Clamped; is-dead tests `<= 0` |
| `+0x2AC` / `+0x2B4` | **Max / current hunger** | User-verified in-game |
| `+0x680` | Last collision-resolved position (3 floats) | Below |
| `+0x704` | Flag: when set and state 0 is requested, the setter uses 0x1D instead (and clears `+0x3C`) | `0x65EDA0` |
| `+0x72C`–`+0x73C` | Five ability multipliers | Save bytes `0x8D0124`–`0x8D0128` × const |
| `+0x810` | **Collision off** | §6 "Collision step" |
| `+0x834` / `+0x864` | Safe points (two 4×3 world matrices); valid flags `+0x894`/`+0x898` | `0x65BFC0` |

**`+0x680`:**
- Copied from the brick's world translation after the scene update (`0x666611`), at the end of the collision step `0x65BFC0`, and at `0x670485`.
- The collision move sweeps from here to the brick's new position each frame. **So a teleport must move it too** (mod F8 fix, 2026-10-04).

**Ability setup `0x53AD50`:**
- `max_hp = (cfg[0xD8C] × ability[0x73C] + k1) × k2`, with `k1`/`k2` at `0x7CE0D8` / `0x7CEB90`.
- Hunger has the same shape with `cfg[0xD84]` / `ability[0x738]`.
- Then current values are clamped to the new maximums (never raised).

### Collision step and no-clip

Found 2026-10-12 with a hardware write-watch on the shark's position (mod `Shift+F7`, `src/hwtrace.cpp`).

**`0x65BFC0`** (controller vtable slot `0x7F2958`) is the per-frame terrain collision step.
- Returns at once if `ctrl+0x810` ≠ 0, or the state is `0x10` (FIXBITE) or `0x16` (a death animation).
- Otherwise:
  1. queries contacts with `0x6C80C0(brick, 0x18001, -1, -1, 0xE)` (result at `[0x920E24]+0x2B8`);
  2. pushes out with **`0x4E4DA0`**: back along the contact normal by the penetration (`0x6CEFA0` adds to the translation), then removes the velocity into the surface;
  3. repeats up to 8 times.
- While holding prey (`+0x204`), a paired version (`0x4E4F20`) also tests the prey.
- After 8 failed tries it counts a stuck frame. After more than `0x59` stuck frames it logs `SafePoint Teleport jobbik/rosszabbik` and moves the shark to a safe point (`+0x864`/`+0x834`), zeroing velocity. That's why F8 teleports into rock used to end up nearby, often behind a wall.
- At the end it copies the brick's position into `+0x680`.
- Collision is swept from the start-of-frame position (`docs/speedrun_glitches.md` §13).

**Object contacts:** **`0x671AB0`** (next slot, `0x7F2960`), mask `0xC00` (boats, debris). It plays `Jaws.ImpactObject`, does hit reactions (`autocolli hit shark`) and has its own 4-try push-out. It ignores `+0x810`, so no-clip still collides with objects.

`0x4E50D0` is the same push-out loop for other actors (boats, NPCs).

**No-clip** = hold `ctrl+0x810` = 1 (mod F7). User-tested 2026-10-12: passes through the ground and most solid objects; F8 teleports into geometry stay put. `+0x810` is set elsewhere only by the dead state (`0x669D8C`) and cleared at init (`0x664EC0`). Air swimming was added 2026-11-25 (§6 "Water height").

### State setter and every death path

**`0x65EDA0`** = `thiscall SetState(int state, int, int)`, ~16 KB (a big switch), `ret 0xC`. Its first instruction is a 6-byte `mov edx, [0x920E24]`, where the mod hooks in. It's called with ~40 distinct states.

State 7 (dead) is requested from exactly four places:

| Call site | Trigger |
|---|---|
| `0x65B871` | **Scripted kill message.** The handler checks for the dword `0x4449454D` (`"DIEM"`). If not dead already, it zeroes health **and** hunger and calls `SetState(7, -1, -1)`. This is how missions kill the shark directly. |
| `0x65D871` | Health ≤ 0 |
| `0x668CC6` | A timer: the game clock `[world+0xB0]` vs an int limit at `ctrl+0x5B0` |
| `0x66D4E9` | A similar timer at `ctrl+0x5AC` |

**Blocking `SetState(7)`** (the mod's F11) stops all four. Health and timer deaths block cleanly. But scripted deaths also hide the model and tell the mission the shark died through other paths, so after a blocked scripted kill the shark stays alive and invisible while the game acts as if it died. Accepted; not to be chased (user).

### Bite animation `Shark_GW_Pitbull04` and bite damage

Found 2026-10-12 via the string `SHARK_GW_PITBULL04` (`0x8B7890`).

- One of the great white's 73 clips: AQUARIUM `SKEL 2515`, frames 997–1036 (40 frames).
- The normal grab-chew-shake on held prey (user, in Blender: "a regular eating animation"). The bite damage is timed to its frames.

**Clip-frame table** (`0x6651BB`–`0x6652A7`, inside an unrecognised function near the constructor). For each clip name the code asks the animation object for its start (vtable `+0x1C`) and end (`+0x20`) and stores them in globals. Neighbours: `SHARK_GW_RELEASE`, `SHARK_GW_KIKOP_GYORS` ("spit out, fast"), `SHARK_GW_FAROKCSAP` ("tail whip"), `SHARK_GW_DIE_I17L31O_`.

| Global | Value |
|---|---|
| `0x90BCB4` / `0x90BCB8` | Start / end |
| `0x90BCBC` / `C0` / `C4` | Start +12 / +23 / +33 |
| `0x90BCC8` / `0x90BCCC` | Start / end (second copy) |
| `0x90BCD0` / `0x90BCD4` | Start +5 / +11 |
| `0x90BCD8` / `0x90BCDC` | Start / end (third copy) |
| `0x90BCE0` / `0x90BCE4` | Start +5 / +11 |

**Playback:** `0x66B187` and `0x66B475` call `0x65E610` (play clip, speed from `0x5BEBC0`), set the sub-state `+0x248` = 6, and play `Jaws.Chew`.

**Damage, `0x65CB30`** (per tick, from `0x67003B`). In state 5 (prey in the mouth), `0x4DD1F0(frame)` returns 1 when the animation passed `frame` this tick. At each such frame the shark sends damage message `0x27` to the prey:

| Sub-state | Damage frames | Bites |
|---|---|---|
| 6 (full Pitbull04) | Start +12, +23, +33 (AQUARIUM: 1009, 1020, 1030) | 3 |
| 9 | Start +5, +11 | 2 |
| 0x16 (22) | Start +5, +11 | 2 |

- Damage = `(cfg[0xD74] × ctrl[0x730] + k1) × cfg[0x4AC]` (`k1` at `0x7CE0D8`). `ctrl+0x730` is the Power ability (×5 at max; `docs/speedrun_glitches.md` §5).
- After the hit, the action at `cfg[0x850]` is started on the target (`0x6C3010` → `0x5525C0`).
- **Sub-state 0xF** doesn't use Pitbull04: damage comes from how far the shark moved (`|dx| + |dz|` against `0x90BEA4`/`0x90BEA8`, × `cfg[0x46C]`, above `cfg[0x474]`). It plays `Jaws.Tear` and prints `Razas damage!` (*rázás* = shaking): the thrashing tear-apart.

**Open:** what puts the shark into state 5 and sub-states 9 / 22; whether "04" means earlier Pitbull clips existed (the exe names only this one).

### Tick, input, water height and the animation runtime

Found 2026-10-21 while porting Ecco's dolphin controller (`docs/ecco_dolphin_controller.md`). The mod's Ecco mode uses all of it and is user-confirmed, so it's tested in-game unless marked.

**The tick.**
- `MLSharkCtrl`'s tick = vtable `0x7F28FC` slot `0x48` (address `0x7F2944`) = **`0x667FB0`** (thiscall, no args). All of the shark's own movement happens inside it.
- Replacing the slot (mod `ecco.cpp`) replaces the movement while the rest keeps working: the camera follows, and F8 and terrain push-out still apply afterwards. So collision is resolved outside the movement code.
- **To move the brick yourself:** write its world matrix (`+0x84`) and local matrix (`+0x50`, solved through the parent's world matrix), and set flag `0x20` at `+0x0C`. Call `0x696EA0` first if the flag is already set, as the stock tick does.

**The pad.**
- `[[0x920E24]+0x88]+8` → `[buttons][previous buttons][stick X][stick Y]`.
- Swim = bit `2` or `0x800000`. D-pad: `0x100`/`0x200` (left/right), `0x40`/`0x80` (up/down).
- The stock stick reader `0x65EAE0` uses a `0x1000` deadzone rescaled to ±`0x4000`, and flips Y unless the invert option byte `0x8D1DC1` is set. It prints "Nem Invert" (emptied in release) on every call.

#### Water height

Three function pointers, all `float cdecl f(const float* pos)`, all returning `-2147483648.0` (`0x7D388C`) where there's no water. The water action (`0x630DC0`/`0x630E70`/`0x631A..`) sets them together.

| Pointer | What | Call sites |
|---|---|---|
| `0x8B2E94` | **Wave surface** height (`0x6331E0`/`0x633280`/`0x6331D0`) | 197 |
| `0x8B2E98` | Not identified (`0x633390`/`0x633400`/`0x633370`) | 3 |
| `0x8B2E9C` | **Flat water level** (`0x633260`/`0x633320`: the water brick's world Y, `[0x902EA4]+0xAC`) | 107 |

Every call site is `call [ptr]`, so a wrapper can tell the caller from its return address (site + 6).

**Users of the wave surface:**
- **Shark airborne physics:** `0x66D6FB`/`0x66D70E` test two body points.
  - Both above → `ctrl+0x4A0` = 1 (airborne; jump states 2/0x18/0x1B/0x29/10).
  - One above → the fraction out of water blends air and water physics.
- `0x66D762` sets the near-surface flag `ctrl+0x828`.
- `0x66D2E4` clears `ctrl+0x5A8` (on-ground) once Y ≤ surface.
- `0x6703A7`/`0x6703EB`: the surface wake.
- `0x66E4A7` adds `SharkConfig.m_felszineny` ("surface Y").

**Users of the flat level:**
- `0x67031E`/`0x67033C` set bit `0x40000` in the previous-buttons word (`[ctrl+0x58]+0x38`) when out of the water, blocking the charge/jump press in the air.
- **Max depth:** `0x66DDC5`/`0x66DDFB`. When `SharkConfig.m_depthvizsg` (`+0xE4C`) is on, the brick's local Y is kept at least `water − m_maxdepth` (`+0xE54`).
- `0x669CA2` gates a wave-surface snap that didn't run in testing.
- `0x6607DC` (state setter) places a splash at the surface.
- **The follow camera** (global `0x90BC10`, vtable `0x7F29E4`, ctor `0x6752A0`, created at `0x55ABE4`, tick `0x678230`):
  - Nearly all its code (`0x675000`–`0x680000`, plus `0x6643D0`/`0x664520`) reads the flat level.
  - `cam+0xB4` = above/below-water mode.
  - Above water (`0x676AC0`) it sits at `water + camcfg[0xDC]` (site `0x676C3B`) and aims at `sharkY + camcfg[0xEC]` (at least `water + camcfg[0xE4]`). So in a jump the camera stays by the waves looking up.
- Others: `0x48DF10` (vtable `0x7D7464`) puts an object on the wave surface above a brick (fin/wake marker). The `0x4F3920`–`0x5166F0` group are other swimmers and boats.

**The mod's F7 air swim** lifts the surface for the shark sites above (not the max-depth pair) and gives `0x676C3B` the camera's own height (`mod/src/noclip_guard.{h,cpp}`). User-tested 2026-11-25.

**Globals:** `0x90BC08` = shark brick, `0x90BC0C` = effects/message object (`0x694860(0x2E, …)` spawns splashes).

#### Animation runtime

**The clip animator at `ctrl+0xBC`:**
- `PlayClip` `0x65E610` → `0x4DCF70` (a two-slot cross-fader).
- Per-tick update **`0x4DD250`** (thiscall `(animator, int reset)`, `ret 4`), called from the tick at `0x66DF91`. Frame step = speed × `[engine+0xB4]`.
- Posing goes through `0x6F6150`, cross-fades through `0x6F6230`.
- Fields:

  | Offset | Field |
  |---|---|
  | `+0x10` | Skeleton model |
  | `+0x14` | Frame |
  | `+0x1C` / `+0x20` | Start / end |
  | `+0x24` / `+0x28` | Cross-fade length / remaining |
  | `+0x2C` / `+0x30` / `+0x34` | Slot B start / end / frame |
  | `+0x3C` | Weight |
  | `+0x44` / `+0x48` | Speeds |
  | `+0x58` | Reference frame |
  | `+0x60` | Flags: `8` = loop; `1`/`2`/`4` select per-bone paths (not decoded) |

- **It can be driven from outside:** save its first `0x80` bytes, write a clip range and frame (speed 0, no cross-fade, weight 1), call `0x4DD250(anim, 0)`, restore the bytes. The bones take the pose, and the shark logic's own clip timing is unaffected (mod `PoseDolphin`).
- **A second animator** at `ctrl+0x15C` runs while `ctrl+0x24C` is set. Not identified.
- **Clips are looked up by name only.** The controller never checks which skeleton it drives. A foreign 28-bone rig (padded to 40) whose `ANIM` lists the 73 `Shark_GW_*` names plays as the player (`DOLPHIN` level). Whether 40 bones are really needed wasn't tested.

**Other animation code:**
- The generic clip-player action `0x6F75A0` (start `+0x40`, end `+0x48`, speed `+0x50`, frame `+0x64`, loop count `+0x88`) serves other animated objects.
- `0x6F5EB0` (thiscall `(start, end, float frame)`) poses a skeleton at a fractional frame. It sums the per-frame root-motion deltas (`SKEL +0x1C`, 12 bytes per frame) into the model's `+0x1D8`, then interpolates every bone (`0x6E9E90`).
- **The `SKEL` resource object** (loader `0x6F47D0`, via the skeleton model's vtable `+0x84`): `+0x1C` root motion, `+0x20` frame count, `+0x24` morph frame count, `+0x40` vertex count, `+0x4C` morph data.
- **`ANIM`'s second header word** = the total byte length of the clip names (NULs included, padding excluded). Matches all 345 `ANIM` chunks in the 20 levels.

**Drawing from the d3d8 proxy:** the game sets the view matrix several times per frame (reflection and refraction render to textures). The last view and projection set while the back buffer is the target are the main camera; drawing with them places objects correctly (mod `sonar.cpp`).

### Other globals nearby

| Address | What |
|---|---|
| `0x920E24` | The engine object (`+0x80`, `+0x84`, `+0x88` sub-objects; `+0xB0` game clock) |
| `0x8DA1C0` | `DDGameState` (`+0x104` `m_angry`, `+0x12C` `m_koteldied`; §11) |
| `0x90BC08` | Shark brick; cleared at the end of `SharkRelPos` |
| `0x93BE68` | The debug-print object (`call 0x703BD0`) |
| `0x8D1EBC` / `0x8D1EC0` | Written from `ctrl+0x2A8..+0x2B4`; probably a HUD copy of health/hunger |

---

## 7. Other classes: SC17 mission, camera

**`MSMineAllMineMission` (SC17):**
- Name getter `0x52A1A0`; the constructor installs vtable `0x7DFFE0` at `0x52A4FC`.
- Fields: `m_WhaleID` (`0x08000AE5`), `m_SharksID` (`0x08000AE6`), `m_Easy/Medium/HardSharkNum` (`0x08000AE7–9`), `m_Easy/Medium/HardWhaleDeadHurt` (`0x08000AEA–C`).
- The code that moves the whale by the root's transform wasn't traced; the effect was verified in-game (`docs/scene_graph.md` §4).

**`MLSharkCamera`:**
- Descriptor `0x907120`, name getter `0x672440`.
- ~150 fields for the follow camera **and the minimap**: `m_target`, `m_distance`, `m_abovedistance`, `m_viewheight`, smoothing pairs, boss/charge/strafe/zlock modes, `m_mapsprite`, `m_maproot`, `m_mapdist`, `m_northsprite`, `m_northbrick`, map sprites.
- Not needed so far.

---

## 8. `GDControl`: level scripting

**In short:** most level scripting (cutscene sequencing, effects, killing or hiding objects, checkpoint clean-up, barriers) is done by `GDControl` actions. Each is a timeline of up to 8 steps; each step applies an operation to a list of node or action IDs. Across the 19 levels with a scene graph: 3,261 controls, 82 distinct action words.

Dump any level: **`scripts/dump_gdcontrol.py GAME_GDWs/<NAME>.GDW [REGEX]`**.

### Where it lives

| What | Address |
|---|---|
| Class name getter (`"GDControl"`, `0x8B9CB0`) | `0x6B6180`, slot 0 of `0x7F5780` |
| Reflection descriptor | `0x91FED0` (from `0x6B6280`): 17 fields, `m_Ctrl1`/`m_List1` … `m_Ctrl8`/`m_List8`, `m_DeactProps` |
| Props / runtime constructor | `0x6B6030` (0xC4 bytes) / `0x6B66F0` (0x130 bytes) |
| Property type `GDPropControl` (`0x8B9CA0`) | Vtable `0x7F5768`; 16 bytes = vtable + `[w0, w1, w2]`; copy `0x6B5FB0`, serialise `0x6B5FD0` |
| Start (schedule steps) | `0x6B68A0` |
| Per-tick executor | `0x6B6C00` |
| Step interpreter | `0x6B6DB0` (thiscall: control, `&Ctrl`, list) |
| Deactivate when finished | `0x68EB10` |

### In the level file

```
ACTN [size] [u32 class 0x0203B039] [u32 action ID] PRPS…
```

- **Every `ACTN` has its own ID.** START's boulder control is 2084; its node is 2083. List entries may be node or action IDs.
- `m_CtrlN` = `PROP 0x08001819 + 3(N−1)`: 12 bytes `[w0, w1, w2]`.
- `m_ListN` = `PROP 0x0800181A + 3(N−1)`: `[u32 n] + n IDs`.
- `m_DeactProps` = `PROP 0x08001831`. Instance name = `PROP 0x080017C3` (all action classes).

### Timing

- At start, step *i* gets a fire tick `w1 + rand(0 … w2 − w1)`, or exactly `w1` when `w2 ≤ w1` (`w1` is signed).
- The counter starts at −1 and the executor runs once at once. So **t = −1 fires the moment the control starts**; t = 0 fires one tick later.
- A step with `w0 & 0xFFFF` = 0 does nothing.
- After the last step the control deactivates itself.
- Common delays: 0, then 1, 15, 30, 20, 60, 120, and "300 to 400 random".

### Targets

Each list ID is looked up twice through the registry (`0x6B8A00`, §9):

- **`0x6C3010` → the live action instance.** It returns **registered object `+0x24`**: for an action ID, the action's runtime instance; for a node ID, the node's live object. **Null if there's none**, and the step skips that target. Live flags at `+0x0C` (`0x2` active, `0x8000000` started, `0x1` killed); children `+0x1C`, next `+0x10`.
- **`0x6C2F90` → the registered object itself** (for an action, its owner node). `m_nFlags` at **`+0x18`**; children `+0x28`, next sibling `+0x20`.

Null lookups are skipped. 9 to 72 IDs per level are defined nowhere (e.g. START's `SzetfroccsenoDarabokController3` still adds blood-splash pieces 639–642, which don't exist). Probably objects deleted during development; some might be created at runtime (not checked).

### The action word `w0`

**Operations (low 16 bits),** applied to every target:

| Bit | Effect in `0x6B6DB0` | Name in dump | Example |
|---|---|---|---|
| `0x0001` | Live flags \|= `0x2` (scope `0x01000000`), object `m_nFlags` \|= `0x2` (scope `0x10000000`); with `0x10000` also (re)start the target's action (`0x694C70`/`0x68EA80`) | start | `IntroStarter` → `IntroMovie` (1,936 uses) |
| `0x0002` | Clear those `0x2` bits (only when `0x1` isn't set) | stop | `PostStateControl` |
| `0x0004` | Add the target to the world (`0x6C2EB0` → `0x698720`) | add | `ArbocDestroyController` → debris + dust |
| `0x1000` | Same as `0x4`, using the list as stored in the file instead of the runtime copy | add(stored-list) | `MovieStarter_601` |
| `0x0008` | Live flags \|= `0x1` (the action ends and takes its object with it); with `0x200000` also `m_nFlags` \|= `0x20000` | kill | `PortalKinyiro` ("portal killer") |
| `0x0200` | Spawn a copy (`0x697BB0`, mode 3, or 4 with `0x20000`); with `0x200000` as a child of the controller's owner | spawn-copy | `FoamControl`, explosions |
| `0x0010` / `0x0020` / `0x0040` | `0x10`: set `0x40`, clear `0x10`. `0x20`: set `0x10`, clear `0x40`. `0x40`: clear both. On live flags (scope `0x04000000`) and/or `m_nFlags` (scope `0x40000000`) | flags… | `PalyavegiKizaroKiller` ("level-end barrier killer"): `0x40` |
| `0x0080` / `0x0100` | Clear / set `0x100` = **don't render** (live: scope `0x08000000`; object: `0x80000000`) | show / hide | `real_shark_norender` → `GWside` |
| `0x0400` / `0x0800` | `m_nFlags` set / clear `0x20000` (`0x6B71C0`, scope `0x40000000`) | suspend / resume | `FecsegesSzunetel` / `FecsegesUjra` ("chatter pauses / again") |
| `0x2000` / `0x4000` | `m_nFlags` set / clear `0x400000` (meaning unknown) | node±0x400000 | DEEPSEA `bummcontroll` (exploding tanks) |

**Scope and modifier bits (high 16 bits):**

| Bits | Meaning |
|---|---|
| `0x01000000` / `0x10000000` | Live-action / object enable bit |
| `0x04000000` / `0x40000000` | Live-action / object `0x10`–`0x40` group |
| `0x08000000` / `0x80000000` | Live-action / object render group |
| `0x00400000` / `0x00800000` | Also recurse into children (`0x10`–`0x40` group / render group) |
| `0x00010000` | Restart on start |
| `0x00020000` | Spawn mode 4 |
| `0x00200000` | "At self" / also suspend |
| `0x02000000` | Not tested by the interpreter |

`0x0F000000` with no modifiers is the default: 5,856 of 6,547 steps (89 %).

**Flag meanings:**
- `m_nFlags 0x100` = not rendered. Confirmed by the "norender" control and the invisible blocker plates (`Kizaro_Lap_Kozepes`, flags `0x15A`).
- `0x2` = enabled (on almost every node).
- `0x20000` = suspended.
- A live action's `0x1` = killed.
- `0x10`/`0x40`: barrier "killers" clear them and invisible walls have them. Clearing them at runtime removes visibility *and* collision, so they're more "in the world" than pure collision bits.

**Single steps on a plain model node** (user-confirmed 2026-10-03, one step per target):

| Step | Visible after | Solid after |
|---|---|---|
| `0x4B000400` suspend | no | no |
| `0x8F000100` hide | no | no |
| `0x4F000040` clear `0x10`/`0x40` | no | no |
| `0x0F000008` kill | no | **yes** |

Note: `0x100` set **in the level file** keeps collision (the blocker plates are invisible and solid), while setting it **at runtime** removed it. The engine probably only re-checks collision when a flag changes.

### Example: START's tunnel boulder

```
[node 2083 "TunnelBlockingDust"] SeaSeekerQuestEventControl  (act 2084)
  1: t=0  0x4b000400 suspend  -> TunnelBlockingDust
  2: t=0  0x0f000008 kill     -> TunnelBlockingDust
[node 677 "SecondPart"] CheckPointCleanUp
  3: t=0  0x0f000008 kill     -> TunnelBlockingDust
```

No other control starts `SeaSeekerQuestEventControl`, so the seeker quest code presumably starts it directly.

---

## 9. Object registry, live actions and destructibles

Found 2026-10-03 while getting a scripted trigger to work (`docs/brtr_editing.md` "Scripted triggers"). Confirmed with the mod's **F12 registry dump** (`mod/src/iddump.cpp`).

### Object registry

- **A hash map at `engine + 0x50`** (`engine = [0x920E24]`): `+4` bucket count (16,381 in FISH), `+8` bucket array. Entries are `[0] id, [1] ?, [2] object, [3] next`.
  - `0x6B8A00` looks up; `0x6B8450` inserts (fails if the key exists); `0x6B8600` inserts or overwrites.
- **Registration** (`0x692C10`, for every loaded node and action): with the loader's "keep file IDs" flag, an object is registered under its file ID if free. Otherwise it gets **`++engine+0x14`**, the runtime counter, and the old ID is mapped to the new one.
- **The runtime counter starts near `0x100000`** (`0x100324` after loading FISH, `0x1008B2` seconds later). Engine-created objects (reference copies, spawned effects) are numbered from there.
- **File IDs at or above `0x100000` collide and the objects vanish.** A rock at `0x10000A` never appeared; IDs up to `0xFFF00` work.
- **Registered objects are definitions**, with properties inline at the reflection `a` offsets. Common layout: `+0x04` own ID, `+0x08` runtime class ID, `+0x18` `m_nFlags`, `+0x1C` owner (actions), `+0x24` live instance.
- **Nodes** (e.g. vtable `0x7F68F0` for a plain model): `+0x18` `m_nFlags`, `+0x20` next sibling, `+0x24` live object, `+0x28` first child, `+0x2C` the node's `ACTN` definition.

### Live action instances

- An action **definition** (one per `ACTN`) only does something through a **live instance** at its `+0x24`.
  - `0x698700` creates it (`if !def->vt20(): def[9] = def->vt48()`); the instance's destructor (`0x68E770`) clears it.
  - `GDControl`: definition vtable `0x7F5804` (0x130 bytes), instance vtable `0x7F5798` (0xC4 bytes).
- **Who gets an instance at load:**
  - actions on **group-type nodes** (`0x010B10AA`, `0x010AA0A4`) do;
  - actions on **plain model nodes** (`0x0107402F`) don't. Live dumps: the pink post root had one; the monkey and FISH's `LoadingPredatorEffect` didn't.
  - All 132 shipped destructible-hook targets are on group-type nodes, all with `m_nFlags` = 0.
  - Step `0x4` ("add", `0x698720`) also creates one.
  - The load-time code wasn't traced; the rule is from observation.
- **Starting** an instance = `0x68EA80`: sets `0x2` (active), calls slot `+0x50`, sets `0x8000000` (started), then follows `+0x20` (`m_OnActivate`). Does nothing if already active and started. `0x68EB10` deactivates.
- **Start-pass timing:** delay −1 steps run in the same instant the control starts; delay 0 on the next tick. This matters when starting it deletes its owner (`m_killparent`).

### `MBRombolhato`, the destructible

- `ACTN` class `0x02169168`. Definition vtable `0x7D9998` (0x228 bytes, `0x4A4430`, getter `0x4A3990`); runtime vtable `0x7D99F8` (0xF8 bytes, `0x4A4C60`).
- **PROP = `0x08000661` + field index** (55 fields). Notable ones:

  | PROP | Field | Meaning |
  |---|---|---|
  | `0x0661` | `m_type` | |
  | `0x0662` | `m_darabokid` | Pieces node |
  | `0x0663` | `m_maxhitpoint` | Durability |
  | `0x0673` | **`m_robbcontrol`** | Control run when destroyed ("explosion control") |
  | `0x0679` | `m_killparent` | Delete the root when destroyed |
  | `0x067C` | **`m_megutcontrol`** | Control run on every non-fatal hit |
  | `0x0692` | `m_killotherrombolhato` | Kill other destructibles |

  Others: `m_felulrolcolli`, `m_toclone`, `m_maradclone` (remains), `m_szetroppen`, `m_megutclone`, `m_megutclonevegen`, `m_pusztulomessage`, `m_colliremains`, `m_tarsaivalpusztul`, `m_reborn`, `m_addpoint`. Full table: `dump_class_fields.py`. (PROP IDs shown without the `0x0800` prefix.)
- Runtime: `+0x48` = `m_robbcontrol`, `+0x50` = `m_megutcontrol`, `+0xE8` = hit points.
- **Hit/destroy handler `0x4A5080`** (mode 0/1/2):
  - hit points ≤ 0: sounds and messages, kill listed destructibles, spawn remains, **start `m_robbcontrol`** (`0x6C3010` → `0x68EA80`);
  - otherwise **start `m_megutcontrol`**.
  - The collision handler `0x4A5F10` subtracts damage and calls it in mode 2. `0x4A5E00` handles losing supports.
- **Shipped use:** 111 destructibles use `m_robbcontrol`, 21 `m_megutcontrol`. E.g. AQUARIUM's `ParavanTorik` screens open a portal and advance the quest; DEEPSEA's tanks start explosion chains; DEEPSEA2's lamps kill their light cones. FISH's pier posts have both empty.

---

## 10. Cut story mission Hot Pursuit

**In short:** the logic of the cut *Hot Pursuit* is fully compiled into the PC exe. `StagePursuitQuest2` is a complete mission: jet skis race through gates that open ahead of them and close behind; lose if the nearest jet ski gets too far away; a boss fight; completion. `StagePursuitQuest` is an earlier kill-driven draft. A playable restoration runs in-game. The mission story is in `docs/cut_content.md` §2.

Decoded 2026-10-10 with `CreateDecomp.java` over the vtable entries; code range `0x5FB300`–`0x5FD000`.

| | `StagePursuitQuest` | `StagePursuitQuest2` |
|---|---|---|
| Class descriptor | `0x8FE120` | `0x8FE418` |
| Object vtable | `0x7EDFE8` | `0x7EE180` |
| Tick (`+0x48`) | `0x5FBA00` | `0x5FC800` |
| Activate / deactivate (`+0x50` / `+0x54`) | `0x5FB960` / `0x5FB9F0` | `0x5FC730` / `0x5FC7F0` |
| Message handler (`+0x68`) | `0x5FBB80` | `0x5FCD10` |
| Advance to step N (`+0x6C`) | `0x5FBBF0` | `0x5FCDF0` |
| Object size | `0x1AC` | `0x24C` |

- Each has an event class (`StagePursuitQuestEvent`, `StagePursuitQuest2Event`): a plain `NAQuestEvent` subclass with no fields, the same base as the shipped `StageDocksQuest`, `StageDeepSeaQuest` and `NAQuestEventKatatama` events.
- On activation each quest stores itself in **`0x8FE494`** (the current quest; cleared on deactivate). Quest events send their message number to whatever that points at.

**Fields** (runtime offset; for ID lists the count is at +4 and the array pointer at +8; single values at +4):

| Field | Quest | Quest2 | Used as |
|---|---|---|---|
| `m_JetSkiIDList` | `0x174` | `0x174` | The jet skis being chased |
| `m_GateIDList` | `0x180` | – | Gate-opening actions |
| `m_GateOpenPosIDList` | – | `0x180` | Markers: open gate *i* when a jet ski nears marker *i* |
| `m_GateClosePosIDList` | – | `0x18C` | Markers: a jet ski within 100 units of marker *i* is "through gate *i*" |
| `m_GateOpenerIDList` | – | `0x198` | Actions that open each gate |
| `m_GateCloserIDList` | `0x18C` | `0x1A4` | Actions that close each gate |
| `m_JetSkiBossIDList` | – | `0x1B0` | Extra jet skis that only matter in the boss phase |
| `m_OnAccomplished` | – | `0x1BC` | Started on success |
| `m_OnBossFight` | – | `0x1C4` | Started when the boss phase begins |
| `m_PursuitLostDist` | – | `0x1CC` (float) | Lose distance |

- Inherited from the quest base (descriptor `0x8FE1D0`): `m_checkpoints`, `m_checkpointactions`, `m_events` (one action per state; "advance to step N" starts `m_events[N]` when the state is N−1), `m_missionbricks`.
- Quest state is at `+0x6C`.
- A jet ski counts as dead when its AI state (`ai+0xC28 + ai[+0xC24]*8`, `ai` = registered object `+0x20`) is 5.

### `StagePursuitQuest2`: how the mission plays

States: **0** chase, **8** boss fight, **5** accomplished, **6** failed, **7** inactive.

**State 0, every tick** (`0x5FC800`). The shark's position is the brick at `[0x90BC08]` (`+0xA8`). Two 1-based counters start at 1: next gate to open `g` (`+0x1DC`) and next to close `c` (`+0x1E0`). Each jet ski has a "passed gate" counter at `+0x1EC + 4i`.
- **Lose:** if the *nearest* live jet ski is farther than `m_PursuitLostDist`, show *"The jet skiers have escaped! Mission failed!"*, state 6.
- **Gates open ahead:** a live jet ski within **150** units of `m_GateOpenPosIDList[g−1]` → start `m_GateOpenerIDList[g−1]`, `g++`.
- **Gates close behind:** a jet ski within **100** units of `m_GateClosePosIDList[c−1]` is marked through gate `c`. Once `c < g` and every marked jet ski is more than **150** units past that marker, start `m_GateCloserIDList[c−1]`, `c++`.

So the shark has to keep up and get through before a gate shuts, or it's cut off. That fits the canal locks of MINEMSHA.

**Message 5 → boss fight** (`0x5FCD10`): only if not already in state 8 *and* every gate is closed (`c > count(m_GateCloserIDList)`). Shows *"Destroy all the jet skis!"*, starts `m_OnBossFight`, state 8. Presumably an area trigger at the canal's end was meant to send it, through a `StagePursuitQuest2Event`.

**State 8, every tick:** counts live, active (`flags & 2`) jet skis in both lists. At zero: `m_OnAccomplished`, state 5.

**State 6 (failed):** resets something in `[0x920E24]+0x88`, calls `0x69AC70(0x8000)`, then `RequestStage(2, "")`. Flag 2 restarts the current stage (seen in-game).

**Messages** (`+0x68`):

| Message | Effect |
|---|---|
| 0 or 4 | State 0 (start or resume) |
| 1 | 5 (accomplished) |
| 2 | 6 (fail) |
| 3 | 7 (stop) |
| 5 | Boss fight (above) |
| 10000–10063 | Increment counter `+0x70 + 4(n−10000)` |

**On-screen texts** go through `0x4928D0(text, 4, 0x98967F)` and only show when `[0x8DA1EC]` is non-zero. That global has 134 references, so it's a general mission-HUD flag, not a debug switch.

**`"NNNNNNZZZZZ"`** is set at `+0x1E8` (mask `0x2000` at `+0x1E4`) on activation but never read by Quest2: a leftover from the first version.

### `StagePursuitQuest` (first version): kill-driven gates

- No lose condition, boss phase or completion.
- The tick (`0x5FBA00`) counts live jet skis. Each time one dies:
  - it starts the next `m_GateIDList` action (opens the next gate);
  - it sets a new **waypoint-group mask** on every jet ski: `mask = 1 << (pattern[k] − 'A')`, with pattern **`"OOOOOOZZZZZ"`** and `k` = gates opened so far.
- The mask starts at `0x2000` = `'N'`, so the sequence is N, then O after kills 1–5, then Z. It goes to jet-ski AI `+0x318`.
- The code also ORs the group bits of each live jet ski's current waypoint (`ai+0xA80` → registered object `+0x108`). Once every jet ski is on an allowed waypoint, it starts the next closer.
- **So `OOOOOOZZZZZ` / `NNNNNNZZZZZ` are waypoint-group sequences** (A–Z = bits 0–25, matching `m_waypointgroups`), not cheat codes. Killing a jet skier sent the rest onto another route group.
- Messages: 0 → 0, 1 → 5, 2 → 6, 10045 (`0x273D`) → 7, 10062 (`0x274E`) → 0, else counters.

### Running it in-game

**Proof of concept, 2026-10-10, user-tested.** `scripts/build_pursuit_test.py` builds `edited_levels/PURSUIT.GDW` from stock MINEMSHA and installs it as the custom level `PURSUIT` (F9). **The gate opens, the lose condition fires (then the stage restarts), the end zone starts the boss phase, and killing the jet ski fires `m_OnAccomplished`.**

What the test builds taught:
- **The quest instance:** a root-level `ACTN` (class `0x0208D08C`, right after the root `PRPS`, like MINEMSHA's `Stage0Quest`), base fields `0x08001161`–`64` as empty lists, `0x080017C4` = 2. That runs from load. (The same quest on a group node with `0x080017C4` = 0, started by an area trigger, never ran, but that test also had the flags bug below.)
- **Jet skis are listed by their `ANPosition` marker** (`jetski 1`, node 2670), as shipped quests list boats.
  - `ANPosition`'s vtable (`0x7D0AEC`) slot `+0x24` = `0x69A210` looks up the object at `+0xF4` (the spawned copy, a runtime ID like `0x1001EF`) with `0x6C2FD0`.
  - So `0x6C3010(marker)` gives the moving jet ski.
- **`0x6C3010` on a node** returns registered object `+0x24`, its live brick, or null.
  - **A node only gets one when its `m_nFlags` has `0x10`.** The empty group node copied from MINEMSHA's `NorthBrick` (flags `0x2`) got none.
  - As a marker, the quest then compared against nothing (the gate never opened). As the holder of the controls and the quest event, none of its actions got a live instance.
  - Flags `0x12` (like `SHARRRK`) fixed both.
- **Area triggers copied from FISH's exit (`PRPS` only) fire in MINEMSHA**, with `m_target` set to the level's shark and `m_enter_act` listing actions on an in-world group node.
- **`[0x90BC08]`** is set to the shark's brick when the controller activates (`0x664EA9`). Before that it points at a placeholder brick made at `0x55AB90`; teardown clears it (`0x6711BE`).
- **The stock jet ski doesn't drive its route.** MINEMSHA's `jetski 1` only loiters near its start, probably because SC15's `UpACreekMission` drives the canal traffic. (Repointing its route, `0x080001F0`, changed nothing; its second route field `0x080001FC` = `JetskiChase`.) So the gate never closed; the early builds listed no closers ("all gates closed" is then true from the start). `m_GateClosePosIDList` must stay non-empty, since the tick reads entry `[c−1]` every frame.
- **Boss-phase quirk:** state 8 counts jet skis flagged active. Swimming far away deactivates the range-spawned copy, which counts as destroyed and completes the mission. The lose check only runs in state 0.

### Getting the jet ski to race

v6–v10, 2026-10-11, user-tested. **Result: the full sequence works through the real gate logic, with the jet ski driving the route on its own (v10).** It drives up the main canal through two gates; each opens as it approaches and shuts behind it. Only after both shut does the end zone start the boss phase. Killing the jet ski completes the mission.

What it took:
- **Boat markers** (`ANPosition`, descriptor `0x8CBB10`, 98 fields; PROP = `0x080001EE` + field index):

  | PROP | Field |
  |---|---|
  | `0x080001EF`, `0x080001F0` | Route (fields 1–2, a `GDPath` node). The canal sailboats set both and have no chase mode. |
  | `0x080001F4` | `m_lookdistance` |
  | `0x080001FB` / `FC` | `m_chase_proc` / `m_chase_area` (a `GDPath` used as an area) |
  | `0x08000212` | `m_speed` |
  | `0x08000213` / `14` | `m_crew` / `m_customcrew` (rider list) |
  | `0x08000218` / `19` | `m_turnd` / `m_stopd` |
  | `0x08000228` | `m_alarmer` |
  | `0x0800022D` | `m_runaway` |
  | `0x0800023B` | `m_targeting` |

  Tri-state values: 0 = inherit, 1 = off, 2 = on. Only names checked against values are listed; the dump's names drift.
- **Boats do follow routes.** The F12 boat probe showed `jetski 1` in state 2, sub-state 3 ("path mode") with its path found. Both stock jet-ski routes (`jetskipath`, `JetskiChase`) are small loops in the starting cove, which looks like loitering. A copy set up like ocean boats (`m_runaway` 2, `m_alarmer` 1) fled from the shark instead.
- **`ANShip` activation (`0x410DA0`):**
  - path ID at AI `+0xE20` → `0x692630` (lookup);
  - with a path: state 2/3 plus 0/3, starting from the nearest path point (`+0x2B4`);
  - without: state 2/1 plus the "no path" byte `+0xA78`; a flag at `+0xD8C` gives 2/7;
  - it also sets the waypoint mask `+0x318` = `0x2000` ('N'), the mask the first draft changes.
- **A spawned boat is removed when it leaves its marker's box.** `jetski 1`'s box covers only the cove (x −1662…−845, z −1195…−377), so the copy vanished ~500 units up the canal and respawned. A box around the whole route (+100) fixed it. SC15's other crew markers have similar ±300 boxes. The top-level sailboats have tiny boxes and still drive the whole canal, so the rule may only apply to some setups.
- **The route:** a reversed copy of the sailboats' `vitorlas_a1_a2 path` (node 2658: open, 24 points, ~1,230 units, all water), placed at the source path's world transform since points are local.
- **The loiterer removed:** the script cuts `jetski 1` and its rider out of `BRTR` (`remove_nodes`, fixing every ancestor's size) after copying them.
- **Speed (v10):** with `m_speed` 250 and turn/stop 0 (inherit), it rammed the bends (the route was made for slow sailboats). **`m_speed` 120, `m_turnd` 40, `m_stopd` 20 (the ocean boats' values) made it drive the route by itself.**
- **Still open:** the route ends in the canal's north-west corner, so the jet ski then drives into the bank. Close the route or end it in open water. Also several jet skis plus bosses, solid gates and goal text.

**Mod F12 boat probe:** for an `ANPosition` marker, F12 follows marker → spawned copy (`+0xF4`) → live object → `ANShip` AI (`+0x20`), and prints position, state stack, path and flags. Runtime-spawned copies are registered *as* the live object (vtable `+4` = "not a definition"); file nodes resolve through `+0x24`. Code: `mod/src/iddump.cpp`.

### Open

- **No level data instantiates the quest.** No GDW contains a `StagePursuitQuest*` instance (searched by class ID, 2026-10-10).
- `0x69AC70(0x8000)` on the fail path.
- The jet-ski AI is `ANShip` (definition `0x1264` bytes; only `0x410000`–`0x41D000` writes the state stack at `+0xC24`/`+0xC28`; state 5 at `0x41691A`). `+0xA80` (current waypoint), used by the first draft, is unexplored.

---

## 11. Cut Aurora rope

**In short:** the cut tutorial ending's tug-of-war (`NAAuroraRope`) is fully in the exe. How it played is in `docs/cut_content.md` §3 "How the rope fight worked"; this section is the engine side. Static analysis only (2026-11-02); nothing was run.

| Class | Address | What |
|---|---|---|
| `NAAuroraRope` | Descriptor vtable `0x7DA4C0`, getter `0x4BB630`, field descriptor `0x8DB828` (37 fields) | Subclass of `NARope` (getter `0x5AA050`) |
| | Runtime vtable `0x7DA4D4` | Slot 22 tick **`0x4BC670`**, 23 activate `0x4BC470`, 24 deactivate `0x4BD010` |
| | Props vtable `0x7DA56C` | Created at `0x4BB5B0` → ctor `0x4BBDC0` (0x374 bytes; `m_treshold` default 1.1) |
| | Runtime object `0x4BB530` (0x2B4 bytes) | Message hook `0x4BBD90` (at `+0x48`) handles **`0x29A`** → damage handler **`0x4BD100(float)`**; segment helper `0x4BC610` |
| `NAAuroraRopeExcluder` | Getter `0x4BD360`, descriptor `0x8DC8E0`, runtime vtable `0x7DA5E8`, tick `0x4BD780` | Subclass of `NARopeExcluder` (`0x5AC6F0`) |
| `NAAuroraRopeBuoyRopeInteractor` | Getter `0x574BD0`, vtable `0x7E69CC`, tick `0x574DC0` | Not decoded |
| `MBAurora` | Getter `0x4B77F0`, descriptor `0x8DCD00`, collision handler `0x4B9610` | Mask `0x4000` → push + rope damage (at most once per 30 ticks); mask `0x8` → `m_angry` |
| `MBShipRope` | Getter `0x4C0830`, descriptor `0x8DBD48` | A stripped copy of the tension core; placed once, in OPEN_S |

**Props fields** (value offsets):

| Offset | Field | Offset | Field |
|---|---|---|---|
| `0x238` | `m_maxhp` | `0x2B0` | `m_kotelalap` |
| `0x240` | `m_treshold` | `0x2B8`–`0x310` | HUD sprites: `keret`, `hudcapa`, `fazisok` (list `0x2C8`), `szinesfazisok` (list `0x2D4`), `hudhosszu`, `belseje`, `hudhajo`, sizes, positions |
| `0x250` | `m_capaszaja` | `0x318` | `m_maxscale` |
| `0x258` | `m_aurora` | `0x320` | `m_damagetime` |
| `0x260` | `m_kotelauroravege` | `0x328` / `0x330` | `m_minlen` / `m_maxlen` |
| `0x268` | `m_kotelforce` | `0x338` | `m_belsofeszulkotelkifele` |
| `0x270` | `m_halfdist` | `0x340` | `m_behuz` |
| `0x280` | `m_kotelsebzicapatfeszules` | `0x348` | `m_kienged` |
| `0x288` | `m_kotelsebez` | `0x350` | `m_nemhuztime` |
| `0x290` | `m_kotelhajothuzza` | `0x358` | `m_font` |
| `0x298` | `m_kotelhajothuzzacsaktol` | `0x360` | `m_kozelvantav` |
| `0x2A0` | `m_hajothuzfesz` | `0x368` | `m_kozelvansebez` |
| `0x2A8` | `m_feszulhpszorzo` | `0x370` | `m_finalmovie` |

**Runtime fields:**

| Offset | Field |
|---|---|
| `+0x18` | Props |
| `+0x1FC` | Segment count |
| `+0x260` | Segments (stride `0x3C`) |
| `+0x270` / `+0x274` | Rest / actual length |
| `+0x284` | Rope HP |
| `+0x298` | Last damage time |
| `+0x29C` | Flash |
| `+0x2A0` | Current line length L |
| `+0x2A4` | Last pull time |
| `+0x2AC` | HUD slide offset |
| `+0x2B0` | Frames held at `m_minlen` |

**Formulas:**
- Stretch `r = actual / L`.
- Tension `t = 1 − halfdist / (halfdist + r − treshold)`.
- HP `−= feszulhpszorzo · t` per tick.
- Shark damage goes out as message **`0x41`**, with a pull of `kotelforce` × the rope vector.
- HUD phase = `(maxhp − hp) · 4 / maxhp`; HUD x = `(640 − hudfulllen) / 2`. Hidden while `[0x920E24]+0xA8 & 8`.
- Rumble on rope damage: `0x6C9010(2, 30, 0, 30)`.

**Globals and calls:**
- `[0x8DA1C0]` = `DDGameState`. `+0x104` = `m_angry`; **`+0x12C` = `m_koteldied`**, set when the rope's HP reaches 0. It's the flag `MBStageTutorial` waits for.
- Final movie: `0x692630` / `0x698720`. Before it, a type check (`0x6927A0` against `0x8DE6F0`, class unknown) is followed by `[[0x8DA1C0]+0x20]+0x40 = 6`, meaning unknown.
- Float constants: `0x7DA5D0` = 160, `0x7D3894` = 4, `0x7CE0D8` = 1, `0x7CE024` = 0, `0x7CE7B8` = 0.8.

**Open:** `NARope`'s own fields (segment setup), the interactor, state 6, what collision mask `0x4000` is.

---

## 12. Draw distance and fog

**In short:** the short view distance is level data plus one water action, not a hardcoded limit. Underwater, the fog end *is* the camera's far plane.

- **Camera:** `GDCamera` fields `m_nFOV`, `m_nRatio`, `m_NearPlane`, `m_FarPlane` (`PROP 0x080017FD`–`0x08001800`); runtime near/far at `+0x114`/`+0x11C`.
  - `0x69B400` = point-vs-frustum test (near, far, four sides); `0x69B2A0` builds the frustum.
  - Every level's `SharkCamera` has far plane **600**.
- **Fog:** `GDFog`, `m_FogStart`/`m_FogEnd` = `PROP 0x0800184D`/`E`, runtime `+0x12C`/`+0x134`. Each level has `FogAbove`, `FogBelow`, `FogReflection`, `FogTransparentAbove/Below`.
- **`NAWaterYCamera`** switches between above- and underwater rendering. Action class `0x02071070`, live vtable `0x7F0120`; PROP = `0x08001330` + field index (`m_viewportabove` … `m_transparencyfarplanefrombelow`).

  | Runtime | Field |
  |---|---|
  | `+0x80` / `+0x88` | IDs of the above / below fog |
  | `+0x90` / `+0x98` | `m_fogbelowstartPC` / `EndPC` (stock 30/170 in OPEN_S) |
  | `+0xB0` / `+0xB8` | `m_fogstartbottom` / `endbottom` (deep water, below `m_fogbottomy` `+0xC0`; interpolated between) |
  | `+0x150` | 0 above / 1 below |

  - **Its tick `0x62B430`** runs every frame underwater. It writes those values into the below fog (`+0x12C`/`+0x134`, colour `+0x144..+0x14C`) **and sets the current camera's far plane (`+0x11C`) to the fog end.** So `FogBelow`'s own values (40/80) are overridden.
  - Crossing the surface calls `0x62AC40` (going above) or `0x62AEF0` (going below). They show and hide the viewports, set the far plane once from `*(lookup(cam+0x2E4 or +0x2EC) + 0x50)`, and set the music's underwater flag `0x8B2E7C`.
  - Init: `0x62B1B0`.
  - Helpers: `0x5519A0(mask)` (cdecl) = current camera; `0x6C3010` (thiscall on the engine, `(id, 0)`) = live object by ID.
- **Tests on OPEN_S** (`FAR_*` custom levels, user-tested):
  - far plane 3000 + above fog 1000–2900: distant objects fine;
  - underwater fog 800–2500: crashed on load;
  - 300–1200: the shipwreck flickers or appears only up close, barriers only when very close, NPCs culled more;
  - 100–400: no problems.
  - Why a longer underwater far plane breaks per-object visibility isn't traced.
- **Mod:** `Shift+F4` far view (`mod/src/farview.{h,cpp}`) applies these at runtime. Level-file edits: `docs/brtr_editing.md` §14.

---

## 13. Movie playback

- **`0x7221E0`** plays `movie\*.WMV` through DirectShow:
  1. `CoCreateInstance(CLSID_FilterGraph)` → `IGraphBuilder` (IID at `0x804CC4`);
  2. the path is built with `"%s.WMV"` (`0x8BD0E4`) and widened by hand;
  3. `IGraphBuilder::RenderFile` (vtable `+0x34`), then `IVideoWindow` (IID at `0x8053C4`) sized to the game window;
  4. it pumps window messages until the movie ends or a skip key is pressed.
- If `RenderFile` fails it returns silently, so a missing file just skips the movie.
- The movies are WMV2 + WMA2, 720×480.
- **Proton:** under Valve's Proton 10.0 they showed a "video not available" placeholder (no decoder for these formats in a non-Steam game). Under GE-Proton11-9 they play (user-confirmed). See `mod/README.md` "Deploy".

**Which movies are requested:** the names aren't in the exe. They're `PROP 0x080005E6` on movie-play actions in the levels, and all 12 match the 12 shipped files:

| Level | Action | Movies |
|---|---|---|
| TITLE | `PC MPEG Demo 1 Loader` / `… 1` | `INTRO`, `SHARK` |
| TITLE | `Movie Scene 1–6` (menu order) | `JAWSC4`, `JAWSC10`, `JAWSC7`, `JAWSC11`, `JAWSC8`, `JAWSC9` |
| TITLE | `Trailers Page 0` | `FLUX`, `PSYCHO`, `INF` |
| CHASE | `MPGPlay 3_pc` (the ending) | `OUTSCENE` |

The `JAWSC` gaps (1–3, 5, 6) aren't referenced anywhere. Maybe the film's scene numbers; unverified.

---

## 14. Push barriers

**In short:** both "Current's too strong." boundaries push the shark instead of blocking it: `ANTol` on buoys and `NAWhirl2000` currents. Strength tables and the DOCKS gaps are in `docs/speedrun_glitches.md` §13.

### `ANTol` (buoys)

- *Tol* = push. Descriptor `0x8CB868`, vtable `0x7D18D4`, on the buoy template `BolyaDef`.
- PROP `0x080002B2` + field index: `m_type`, `m_radius`, `m_fmul`, `m_delay`, `m_forcemax`.
- Runtime: `+0x100` next tick time, `+0x104` radius² (set by init `0x43F670` from `+0x114`), `+0x10C` type, `+0x11C` fmul, `+0x124` delay, `+0x12C` forcemax.
- **Tick `0x43F6A0`:**
  1. when the game clock (`[0x920E24]+0xB0`) passes `+0x100`, re-arm `m_delay` ticks ahead;
  2. take the shark brick (`[0x90BC08]`) and the buoy's world x, z (`+0xA8`/`+0xB0`; y ignored);
  3. if d² < r²: push = the buoy's world Z axis (`+0x9C`–`+0xA4`, through `0x7080C0`) × (1 − d²/r²) × fmul;
  4. if `m_type` ≠ 0, clamp to `m_forcemax`;
  5. `0x694860(0x5F, vec)` and a `MSG_WHIRL` broadcast through `0x6C6120`.
- `0x43F700` is the same test for a given (x, z).
- The push follows the buoy's facing, not away from it, so a line of overlapping buoys adds up.

### `NAWhirl2000` (currents)

- Descriptor `0x902FF8`, vtable `0x7F0A4C`. Force function `0x63BD80` at slot `+0x84` (`NAWhirl2000::CalculateDisplacement`).
- Push along the path direction = force × (1 − d/rad), d = 3D distance to the path line.
- Runtime: rad `+0x154`, grad `+0x15C`, force `+0x164`.
- **Tick `0x63D100`** (2026-11-25):
  - refreshes the shark brick `[0x90BC08]` and copies its position (`+0xA8`–`+0xB0`);
  - calls its force function (thiscall `(pos*, out*)`, `ret 8`; also slot `0x7D952C` of a second class);
  - only if that returns non-zero, it pushes the shark (`0x694860(0x5F, vec)`), broadcasts `MSG_WHIRL` and sends `0x65`. Out of range it returns 0 with `*out = 0`;
  - then the same for its other targets (`m_targets`).
  - The mod's no-clip returns 0 for the shark's position (`mod/src/noclip_guard.cpp`).

### Messages

- `0x63DD50` shows "Current's too strong." (string `0x8B2128`) and arms a timer.
- `MSG_WHIRL` = string `0x84F12C` (table `0x8D3FBC`); `MSG_ARAMLAT` (*áramlat* = current) `0x8D3F48`.
- **Not traced:** how the shark turns `MSG_WHIRL` into motion, so push units aren't converted to swim speed.

### Area trigger tick (`ANSphereCheck`)

- Vtable `0x7D128C`, tick `0x43BF60` (slot `+0x58`), init `0x43BF20`.
- Every `+0x144` ticks (next time `+0x104`) it calls `0x43BDE0`. That looks up the target `+0x11C` (`0x6C3010`) and returns 1 when it's **outside**: distance² (`+0x10C`) > radius² (`+0x108`).
- `m_type` (`+0x114`): 2 = also outside above `+0x14C` / below `+0x154`; 3 = never inside below `+0x154`.
- `+0x100` keeps the last result. Outside → inside runs the enter list (`+0x138` count, `+0x13C` IDs); inside → outside the leave list (`+0x12C`/`+0x130`); each through `0x552190`.
- The swim-out prompt (`MBSwimoutChecker`, vtable `0x7D8AB0`; `0x496B10` shows "Do you want to leave this stage?") is one of the actions such a trigger starts.

---

## 15. Control bindings and the profile

Found 2026-11-25 while adding the mod's `jaws_config.txt` control layout (`mod/src/config.cpp`).

**In short:** three live arrays hold the bindings; the save profile stores 19 entries per device. A new game copies the *live* arrays, so it inherits whatever layout is loaded.

### Live bindings

Three arrays of 31 dwords, indexed by action:

| Array | Device | Codes |
|---|---|---|
| `0x8A0094` | Keyboard | DirectInput scan codes (e.g. `0x11` W, `0x39` Space); built-in defaults carry a `0x1000` bit |
| `0x8A0208` | Second slot | Mouse buttons `0x103`–`0x10C`; −1 = unbound |
| `0x8A0300` | Gamepad | Button numbers |

- Default keyboard table: `0x8A0110` (or `0x89FF20` when `[0x8D681C]` ≠ 0).
- `0x8A018C` (or `0x89FF9C`) is a second keyboard table, registered next to the main one and never saved (fixed extra keys).
- `0x8A0284`/`0x8A037C` are referenced at `0x546A93` with the live arrays. Probably the controls menu's defaults; not traced.

### The input object

Static global `0x8D67F8` (vtable `0x7D6460`, built by the static initialiser `0x483C80`):
- **Slot `+4` `0x483CE0` = startup:** copies the default keyboard table into `0x8A0094`, creates the keyboard device `[0x8D6818]`, and the mouse `[0x8D6800]` or pad `[0x8D67FC]`.
- **Slot `+0xC` `0x483F30` = rebuild:**
  - `0x6C9450(-1)` and `0x6C9450(0)` clear the input manager's bindings (`[[0x920E24]+0x88]`);
  - then `0x4842E0(0, mask, action)` per action registers the keyboard, extra-key and mouse/pad codes through `0x6C8D40` (skipping −1).
  - Plain `ret`, no arguments. Slot `+0x10` `0x483F00` jumps to it.

### The profile

Global `0x8D0110`, 0x1DB4 bytes, written verbatim to `PROFILE<N>.sav`.
- `+0x5C`, `+0xA8`, `+0xF4` = 19 dwords each: keyboard (`& 0xFF`), second slot (`& 0x1FF`), gamepad (`& 0xFFFF`).
- Each entry = `action << 16 | code`. Actions in the order of the table at `0x7E07E0`: `2 5 6 7 8 A C 0 B 9 3 18 19 16 17 4 1B 1 D`.
- Unbound = `0x1FF` (second slot) / `0xFF` (pad).
- This corrects an older "`0x54`–`0x138`" guess in the save notes. On the user's saves, a fresh default profile and their own layout differ in exactly these entries.

**Load** (`0x539B30`): `fread` the save into `0x8D0110`, then for each of the 19 entries, `array[entry >> 16] = entry & 0xFFFF` in all three arrays.

**New game** (`0x537090`, from `0x536738`): zeroes the profile, sets the name `.....`, then fills the three tables **from the live arrays**. It never resets the arrays. So the stock game resets to the defaults only because each session starts with them; loading a save first, then quitting to the menu, carries its layout into a new game.

The controls menu (`0x539120`) and its binding list (`0x54EC90`) read the arrays.

### Action names

Built by the controls menu at `0x54E6E0` with `0x54EC90(label, action)`:

| Action | Name | Action | Name |
|---|---|---|---|
| `0` | SHARK VISION | `0xA` | CHARGE ATTACK |
| `1` | DODGE | `0xB` | STEALTH ATTACK |
| `2` | SWIM | `0xC` | BITE |
| `3` | TARGET LOCK | `0xD` | CAMERA MODE |
| `4` | MAP | `0x16` | NEXT BODY PART |
| `5` | TURN UP | `0x17` | PREVIOUS BODY PART |
| `6` | TURN DOWN | `0x18` | NEXT TARGET |
| `7` | TURN LEFT | `0x19` | PREVIOUS TARGET |
| `8` | TURN RIGHT | `0x1B` | PAUSE |
| `9` | TAIL WHIP | | |

### Code meanings

From the menu text (`0x539120`; key names via `0x537550` = `MapVirtualKeyEx` + `ToAsciiEx` + name tables):

| Device | Code | Meaning |
|---|---|---|
| Keyboard | any | DirectInput scan code |
| Second slot | `0x103` / `0x104` / `0x105` | Left / right / middle mouse button |
| Second slot | other | "Mouse button N" (code − `0x102`) |
| Second slot | `0x10B` / `0x10C` | Mouse wheel |
| Gamepad | `< 0x17` | "BUTTON N" (code − 5) |
| Gamepad | `0x17`–`0x1A` | D-pad up / right / down / left |
| Any | `0xFF` / `0x1FF` | Unbound |

**Gamepad mode:** `[0x8D681C]` = the launch option Gamepad (vs Mouse & Keyboard), written by the startup settings code `0x729630` from its field `+0x118` (probably `pcrt.ini` `KeyboardLayout`; unverified). When set, input init creates a pad device instead of the mouse, the rebuild registers the pad column instead of the mouse one, and the menu shows the pad column. **So mouse bindings are inactive in Gamepad mode.**

**Open:** what `0x1000` in the default keyboard codes means (save-loaded codes lack it and still work); which wheel direction `0x10B` is.

---

## 16. On-screen message tables

**In short:** the game's on-screen messages live in 5 language tables of 1,000 pointers each. Code asks for a message by its English text, through a hash built at startup. Repointing a slot changes the displayed text, which is how the mod's message overrides work (user-confirmed 2026-10-04).

- `[0x854D14 + 4*lang]` points at each table, in writable `.data`. English is `0x84FEF0`; the others follow at `0x850E94`, `0x851E34`, `0x852DD4`, `0x853D74`.
- **Startup** (`0x453AC0`): creates a hash (`0x6B8140(0x7F7, 0x18)`: flag `0x8` = case-insensitive, `0x10` = keys not copied) and adds every English message as key → number 1…1000 (`0x6B8300`).
- **Lookup** (`0x453D00(text)`): hashes the text (`0x6B8910`). If found, returns `tables[lang][n − 1]`, with `lang = [0x920E24]+0x38` clamped to 0…4. Otherwise returns the text unchanged.
- Example: `MBSwimoutChecker` pushes the mixed-case `"Do you want to leave this stage?…"` (`0x8A13E0`, at `0x496B4B`), which resolves case-insensitively to slot 201.
- Because the hash keys are the original strings, **repointing a slot doesn't break the lookup.** The mod does it per stage (`mod/src/messages.cpp`, file `jaws_messages.txt`).

**Exit-related slots:**

| Slot | Message |
|---|---|
| 598 | `\nDO YOU WANT TO ENTER THIS AREA?…` (the area-trigger prompt; the game puts the destination, e.g. `OPEN OCEAN - SOUTH`, in front) |
| 201 | Leave this stage (`MBSwimoutChecker`) |
| 199, 851 | Completed stage |
| 200 | Stage locked |

- In the game font, `[` and `]` draw the Esc and Enter key icons. `^OK^`, `^CANCEL^`, `^CONT^` are button tokens.
- Full numbered list: `docs/game_messages.txt` (`scripts/dump_messages.py`).

---

## 17. Stage loading and the F10 reload

- **The engine object** `[0x920E24]`, vtable `0x7F6018` (the base class's is `0x7D2810`; both share the slots below). Found by locating the dword `0x6C3FD0` in `.rdata`.
  - **Caution:** the tables at `0x7D2818`/`0x7F6020` are 8 bytes off; reading slots from them gives wrong functions.
- **`+0x78` = `0x6C3FD0`, the raw loader `(name)`:**
  - copies the name and appends `.GDW` if there's no extension;
  - records the file name at `0x920D20`;
  - checks already-loaded `FDIR` sub-archives by name first, otherwise opens the file and runs `GDLoadGame` (`0x693180`);
  - stores the argument at `engine+0xB8`.
  - It loads immediately, so it must only run from the engine's own tick.
- **`+0x80` = `0x6C3C50`, `RequestStage(flags, name)`:** thiscall, `ret 8`. Its whole body: `engine+0x40C |= flags; if (name) strcpy(engine+0x410, name)`.
- **The engine tick `0x6C7800`** (vtable `+0x50`) handles the request flags at `engine+0x40C`:

  | Flag | Does |
  |---|---|
  | `8` | Clear flags, unload (`vtbl+0x2C`) |
  | `1` | Clear flags, unload, `0x6B5CF0`, load `engine+0x410` (`vtbl+0x78`), re-init (`vtbl+0x28`) |
  | `0x20`, `4`, `2` | Other paths (pause/reset-style; not decoded). `2` restarts the current stage (§10). |

- **Callers:**
  - the leftover dev "Open Stage" window command (`0x99`, handler near `0x726457`) calls `+0x80(1, path)`;
  - `0x6C4AB0` calls `+0x80(0x20, 0)` when an async load completes;
  - startup (`0x726BE0`) calls `+0x78` directly with the first stage.
- **Async state machine** at `engine+0x510` (`[0x144]`: 0 idle, 1 load, 2/3 disc streaming), name at `+0x530`, progress at `+0x598`. Driven by `0x6C4610` (from `0x729CD0`) and `0x6C4AB0`. Not used by the mod.
- **Byte-scan trick:** calls through the engine's `+0x78` slot were found by scanning for the engine pointer's address followed within 40 bytes by `FF 5x 78` (`call [reg+0x78]`). Six sites, including `0x6C46F8` and `0x727055`.
- **Mod:** F10 calls `+0x80(1, <engine+0xB8>)` after checking the slot really holds `0x6C3C50` (`mod/src/stage.cpp`).

---

## 18. Open items

- **`GDControl`:** the `0x400000` flag (ops `0x2000`/`0x4000`); why kill hides but keeps collision; why `0x100` set in the file keeps collision but set at runtime doesn't; spawn modes 3 vs 4; the code that gives group-type nodes' actions a live instance at load.
- **Push barriers:** how the shark applies `MSG_WHIRL` (`0x5F`).
- **`dump_class_fields.py`:** complete the class-name resolution (132 of 691).
- **`SetState`:** the full list of ~40 states (only 7 = dead identified).
- **The engine object** `0x920E24`'s layout.
- **Animation:** the second animator (`ctrl+0x15C`, gated by `ctrl+0x24C`), the animator flag bits `1`/`2`/`4`, and whether a player skeleton needs exactly 40 bones.
- **Scripted deaths:** whether their side effects (model hide, mission notification) can be suppressed cleanly. Parked: the user doesn't want it (2026-10-01).

More in `docs/open_problems.md`.

---

## 19. Old mistakes

| Old claim | Now |
|---|---|
| `NAPredator` is the shark / predator AI | The predator-vision screen effect. The shark is `MLSharkCtrl` + `SharkConfig`. |
| `0x5BEB80` is the collision sweep | A getter returning `obj+0x24` (2026-10-12) |
| `0x8B2E94` is ground height | The wave surface height (2026-11-25) |
| The registration integers: the first is the runtime offset | `a` = props offset, `b` = runtime mirror offset, value at +4 (2026-10-03) |
| `0x6C3010` returns the object and `0x6C2F90` the live instance | The other way round (corrected from live dumps, 2026-10-03) |
| Collision is a per-frame overlap push-out, not a sweep | Swept from the start-of-frame position (`docs/speedrun_glitches.md` §13) |
| The old mod memory scans should find the shark | They only searched `.data` (`0x845000`–`0xE6C000`); the shark is heap-allocated at level load. The old `0x8CFC88` "position" was a static scratch variable written by several entities, and the old god-mode addresses (`0x8F11A8` etc.) were static copies, probably why that code crashed after level changes. |

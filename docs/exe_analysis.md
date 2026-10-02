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
  ```bash
  ~/tools/ghidra_12.1.4_PUBLIC/support/analyzeHeadless ~/tools/ghidra_projects JAWS \
      -process Jaws.exe -noanalysis -readOnly \
      -scriptPath ~/tools/ghidra_scripts -postScript DecompAt.java /tmp/out.c 0x65eda0
  ```
- **Limitation:** many small functions are reached only through vtables or static-initializer tables and are never recognized as functions by auto-analysis. Ghidra reports `ref from ... in <none>` for them. Read those with plain `i686-w64-mingw32-objdump -d -M intel --start-address=... --stop-address=...` instead. Plain byte-pattern scans in Python over the exe also worked well (all the field-registration, vtable and call-site searches below were done that way).

**Exe sections** (`objdump -h`): `.text` `0x401000`–`0x7CE000`, `.rdata` `0x7CE000`–`0x845000`, `.data` `0x845000`–`0xE6C000` (size `0x627000`), `.idata`, `.rsrc`. Imports include `d3d8.dll` (`Direct3DCreate8` only), `DINPUT8.dll`, `DSOUND.dll`, `WINMM.dll`. No D3DX, no packer.

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

**Unresolved: what the two integers mean.** One looks like an in-object offset, but the evidence is mixed:
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
| `+0x244` | secondary state value (initialized to `-1` alongside `+0x240`) | constructor `0x66693D` |
| `+0x2A8` | **max health** | ability setup `0x53AD50` |
| `+0x2AC` | **max hunger** | ability setup `0x53AD50` |
| `+0x2B0` | **current health** (float) | clamped to `+0x2A8`; is-dead check tests `<= 0` |
| `+0x2B4` | **current hunger** (float) | clamped to `+0x2AC`; user-verified in-game (refilling it keeps the hunger bar full) |
| `+0x72C`–`+0x73C` | five ability multipliers (floats) | ability setup: `= save_byte * const`, from save-state bytes `0x8D0124`–`0x8D0128` |
| `+0x704` | flag; when set and the requested state is `0`, the state setter substitutes state `0x1D` (and clears controller `+0x3C`) | state setter `0x65EDA0` |

**Ability setup `0x53AD50`** recomputes max health/hunger from the ability multipliers and `SharkConfig` tuning values, then clamps current to max: `max_hp = (cfg[0xD8C] * ability[0x73C] + k1) * k2` (constants `k1`/`k2` at `0x7CE0D8` / `0x7CEB90`), and the same shape for hunger with `cfg[0xD84]` / `ability[0x738]`.

### State setter and every death path

**`0x65EDA0`** is a `thiscall SetState(int state, int, int)` method, ~16 KB (a big switch), ending in `ret 0xC`. Its first instruction is a 6-byte `mov edx, [0x920E24]`, which is where the mod's hook patches in. It's called with ~40 distinct state values. State `7` (dead) is requested from exactly four places:

| Call site | Trigger |
|---|---|
| `0x65B871` | **Scripted kill message.** The message handler checks for the 4-byte ID `0x4449454D` (`"MEID"` read as a dword, i.e. bytes `D I E M`), and if not already dead, zeroes current health **and** hunger, then calls `SetState(7, -1, -1)`. This is how missions kill the shark directly. |
| `0x65D871` | Normal death: current health `<= 0` → zero health, `SetState(7)`. |
| `0x668CC6` | Timer-based: a game clock (`[world+0xB0]`) compared against an int limit at controller `+0x5B0`. |
| `0x66D4E9` | Timer-based: a similar comparison against controller `+0x5AC`. |

Blocking `SetState(7)` (the mod's F11 death block) stops all four. But scripted deaths also hide the model and tell the mission the shark died through other paths, so after a blocked scripted kill the shark stays alive, invisible, and the game otherwise behaves as if it died. Health/timer deaths block cleanly.

### Other globals seen nearby (unexplored)

- `0x920E24`: a top-level engine/world object referenced everywhere (`+0x80`, `+0x84`, `+0x88` sub-objects; `+0xB0` looks like a game clock).
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

## Open items

- Meaning of the two integers in each field registration (offset vs. property-header offset). See above.
- Complete the class-name resolution in `dump_class_fields.py` (132/691 named).
- The full state-value enumeration of `SetState` (~40 states; only `7` = dead identified).
- `0x920E24` engine object layout.
- Whether the scripted-death side effects (model hide, mission notification) can also be suppressed cleanly. The user said this isn't wanted (2026-10-01), so it's parked.

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


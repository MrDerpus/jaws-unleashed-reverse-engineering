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
| `+0x680` | **last / collision-resolved position** (3 floats): copied from the brick's world translation after the scene update (`0x666611`), set to the resolved position from `0x5BEB80` when alive (`0x670485`). The collision move sweeps from here to the brick's new position each frame, so a teleport must move it too (mod F8 fix, 2026-10-04). | code above; runtime scan |
| `+0x58` | object whose `+0xA8` also mirrors the shark's world position (also referenced from `+0xCC`, `+0x16C`) | runtime scan 2026-10-04 |
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

## Open items

- ~~Meaning of the two integers in each field registration~~: resolved 2026-10-03, see "`GDControl`… Registration integers, resolved".
- `GDControl` leftovers: the `0x400000` flag (`0x2000`/`0x4000`), why kill hides but keeps collision, why file-set `0x100` keeps collision but runtime-set `0x100` doesn't, spawn modes 3 vs 4, and the engine code that gives group-type nodes' actions a live instance at load.
- Complete the class-name resolution in `dump_class_fields.py` (132/691 named).
- The full state-value enumeration of `SetState` (~40 states; only `7` = dead identified).
- `0x920E24` engine object layout.
- Whether the scripted-death side effects (model hide, mission notification) can also be suppressed cleanly. The user said this isn't wanted (2026-10-01), so it's parked.

## On-screen message tables (2026-10-04)

The game's on-screen messages (prompts, hints, mission text) live in **5 language tables of 1,000 `char*` each**, in writable `.data`. `[0x854D14 + 4*lang]` points at each table; English is `0x84FEF0`, the other four follow at `0x850E94`, `0x851E34`, `0x852DD4`, `0x853D74`.

- **Startup** (`FUN_00453ac0`): creates a hash (`FUN_006b8140(0x7F7, 0x18)`: flag `0x8` = case-insensitive, `0x10` = keys aren't copied) and adds every English message as key → number 1…1000 (`FUN_006b8300`).
- **Lookup** (`FUN_00453d00(text)`): hashes the English text (`FUN_006b8910`), and if found returns `tables[lang][n − 1]`, with `lang = [0x920E24]+0x38` clamped to 0…4. Otherwise it returns the text unchanged.
- So code refers to messages by their English text, e.g. `MBSwimoutChecker` pushes the mixed-case `"Do you want to leave this stage?…"` (`0x8A13E0`, pushed at `0x496B4B`), which resolves case-insensitively to slot 201.
- Because the hash keys are the original strings, **repointing a table slot changes the displayed text without breaking the lookup**. The mod does this per stage (`mod/src/messages.cpp`, file `C:\jaws_messages.txt`). User-confirmed 2026-10-04.

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


# Jaws Unleashed — d3d8 Proxy Mod

A reverse-engineering / exploration mod for *Jaws Unleashed* (PC, 2006, Appaloosa Interactive).  
Runs under **GE-Proton11-9** on Linux (since 2026-10-16; earlier testing used Valve's Proton 10.0, see "Proton version" under Deploy). Targets DirectX 8 (`d3d8.dll`).

**Mod files** (settings `jaws_config.txt`, bookmarks, message overrides, logs, F12 dumps, screenshots, Ecco sonar assets) all live in the game folder next to `Jaws.exe` (since 2026-11-25; before that in `C:\`, i.e. the prefix's `drive_c`). Paths come from `src/modpath.h`.

---

## Controls

| Key | Action |
|-----|--------|
| `F1` | *(unbound by the mod — left free for the game's own map screen)* |
| `Shift+F2` | **Ecco mode** (2026-10-21, user-confirmed working): the shark moves with Ecco the Dolphin: Defender of the Future's swim physics and controls (ported `DolphCtrl` states 0–6). Swim button = swim (taps add speed), RMB charge, R brake, T/Y 180° turn, C circle, B cruise, Q/E roll, U turn up. Optional `jaws_ecco.txt` (`scale`, `invert_x`, `invert_y`, `skip_shark_tick`, `body_length`). Hooks the shark tick vtable slot `0x7F2944`. In the `DOLPHIN` custom level (`scripts/build_ecco_dolphin.py`) it also poses Ecco's model with the dolphin's own clips (2026-10-21, user-confirmed). **Sonar** (2026-10-21, user-confirmed): F or the middle mouse button underwater sends Ecco's sonar cone and wave from the head with the sonar sound, 1 s cooldown, visual only (stage the files with `python3 scripts/stage_ecco_sonar.py`; tuning `sonar_head`, `sonar_alpha`, `sonar_ztest` in `jaws_ecco.txt`; `src/sonar.{h,cpp}`). `src/ecco.{h,cpp}`; details `docs/ecco_dolphin_controller.md` "Step 2, Phase A". |
| `F2` | Toggle freecam on / off *(moved off F1 2026-08-12 so F1 stays free for the map; god-mode removed the same pass)* |
| `F3` | Screenshot — saves `jaws_screenshot_NNNN.bmp` |
| `F4` | Toggle fog on / off |
| `Shift+F4` | **Far view** (2026-10-17; user-confirmed working 2026-11-25, used in normal play): longer draw distance in every level, no level files edited. Above water: camera far plane 3000 (stock 600) and above-water fog 1000–2900; underwater: fog 100–400 (stock about 30–170). Underwater the game sets the camera far plane to the fog end every frame, so that's also the underwater draw distance; past ~400 objects flicker or vanish, and 2500 crashed (OPEN_S test levels, user-tested). Writes the live `NAWaterYCamera` action (found by vtable `0x7F0120` in the ID registry), the current camera (`0x5519A0(3)` `+0x11C`) and the above-water fog (`0x6C3010(id)` `+0x12C`/`+0x134`); turning it off restores the level's values. Values are constants at the top of `src/farview.cpp`. Details: `docs/exe_analysis.md` "Draw distance and fog". |
| `F5` | Toggle sim pause — slows physics, AI, and cutscene playback to ~25% speed |
| `F6` | Toggle foliage hide — makes alpha-tested geometry (seaweed, kelp, plants) invisible |
| `F7` | **No-clip** (2026-10-12, user-confirmed): swim through terrain, rocks and walls; the shark stays limited to the water, and F8 teleports into geometry now stay put. Holds the shark controller's own collision-off flag `ctrl+0x810` = 1, which makes the per-frame collision step (`0x65BFC0`) skip its push-out and its "SafePoint Teleport"; no code patch. Moving objects (boats, debris) still push back, since their contact handler (`0x671AB0`) ignores the flag. Turning it off clears the flag only if the mod set it. `Shift+F7` = debug write-watch trace: CPU hardware write breakpoints (main thread only) on the shark's position fields; press again or wait 30 s and every writing instruction plus its callers is logged (`HW trace` lines). Wine reports `Dr6` = 0, so the log can't say which of the 4 breakpoints fired (`DR-1`). `src/hwtrace.{h,cpp}`. (Replaced the legacy health scanner.) **No-clip guards (2026-11-25, user-confirmed working):** while no-clip is on, the shark also ignores area triggers (level entrances/exits and the enter/leave prompts they start), buoy pushes (`ANTol`) and currents (`NAWhirl2000`, "Current's too strong."). Area triggers aimed at the shark keep tracking inside/outside without firing, so switching no-clip off outside a zone doesn't fire it; triggers aimed at other objects keep working. Vtable slot hooks: trigger tick `0x43BF60` (slot `0x7D12E4`), buoy tick `0x43F6A0` (`0x7D18D4`), current force `0x63BD80` (`0x7F0AD0`, `0x7D952C`). `src/noclip_guard.{h,cpp}`. |
| `F8` | Teleport text box: type `X Y Z` (or `X Z` to keep current depth), or a lone slot number `1`–`9` to jump to that bookmark; `Enter` to go, `Esc` to cancel. While open: `Ctrl+1`…`Ctrl+9` saves the current position to that bookmark slot, and saved slots are listed. Bookmarks persist in `jaws_bookmarks.txt` (Linux: `<prefix>/drive_c/Program Files (x86)/Jaws Unleashed/jaws_bookmarks.txt`), meant to be hand-edited: one `<slot> <X> <Y> <Z> [name]` line per slot, `#` comment lines ignored, re-read automatically when the file changes (even mid-game, checked each time F8 opens). Named slots show their name in the list. Plain world coords — not tied to a level. Game keyboard input is blocked while the box is open. **Reliability fix (2026-10-04):** the teleport also moves the controller's stored collision start point (`ctrl+0x680`) and then holds the shark at the target for 45 frames (~0.75 s), re-writing every known position copy each frame. Before that, jumps with terrain in the way snapped back or stopped part-way (the collision move sweeps from the stored last position), and long jumps flung the shark into the sky or under the map (the physics reads the jump as a huge one-frame velocity). Still occasionally finicky when landing inside or right next to geometry (the game pushes the shark out after the hold). Each teleport logs readbacks at 0.5 s and 2 s (`TP readback`, `TP late readback`); a debug scan of memory still holding the old position can be switched on with `TP_DEBUG_SCAN` in `src/device_proxy.cpp` (`ScanSharkPositionCopies`, `src/shark.cpp`). |
| `F10` | **Reload the current stage from disk** (added 2026-10-03, user-confirmed working; for testing GDW edits without leaving the area). Calls the engine's own deferred stage request (`[0x920E24]` vtable `+0x80` = `0x6C3C50`, `thiscall (flags=1, name)`) with the name the current stage was loaded with (`engine+0xB8`). The engine tick (`0x6C7800`) then unloads the world and reloads the `.GDW` at a safe point in its loop, the same path as the leftover dev "Open Stage" menu. Shows `Reloading <name> ...` in the message line. Debounced process-wide with a 3 s cooldown; ignored while the F8 box is open. Code: `src/stage.{h,cpp}`. |
| `F11` | Invincibility + infinite hunger toggle: refills shark health (controller `+0x2B0`) to max (`+0x2A8`) and hunger (`+0x2B4`) to max (`+0x2AC`) every frame. Re-resolves the pointer chain each frame, so it survives level loads — unlike the old hardcoded-address god mode that crashed. Also blocks deaths that bypass health: while on, the shark controller's state setter (`0x65EDA0`, patched with a 6-byte entry jump) drops requests to enter state 7 (dead). All four death paths go through it — health ≤ 0 (`0x65D871`), the scripted `DIEM` kill message (`0x65B871`), and two timer-based deaths (`0x668CC6`, `0x66D4E9`). Blocked attempts are logged as `death block:` in `jaws_mod.log`. **Known limitation (user-tested 2026-10-01):** scripted deaths do more than set the state — blocking the state change leaves the shark alive but invisible, with the game otherwise behaving as if it died (buggy). Accepted as-is; health-based invincibility is the reliable part. |
| `F12` | **Object-ID registry dump** (added 2026-10-03, debug, read-only). For each ID in `jaws_ids.txt` (one per line, decimal or `0x` hex; a built-in list if the file is missing) it appends to `jaws_iddump.txt`: the registry entry, the registered object's first 64 dwords, and the objects its `+0x20`/`+0x24` point at (live instances). Registry = hash map at `engine+0x50` (`engine = [0x920E24]`), entry `[id, ?, object, next]`; the header line also shows the runtime ID counter (`engine+0x14`). Only memory reads, no game code called. Used to debug the scripted trigger (see `docs/brtr_editing.md` "Scripted triggers"). **Boat probe (2026-10-11):** for an `ANPosition` boat marker (vtable `0x7D0AEC`) it also follows marker → spawned copy (`+0xF4`) → live brick (`+0x24`) → `ANShip` AI (brick `+0x20`), as `StagePursuitQuest2` does, and prints the boat's position, its state stack (`+0xC24`/`+0xC28`), path ID (`+0xE20`) and path object (`+0x2A4`), the no-path byte (`+0xA78`), the `+0xD8C` flag and the waypoint-group mask (`+0x318`). Code: `src/iddump.{h,cpp}`. |
| *(file)* | **Game debug text** (added 2026-10-12): the game's own debug prints, emptied in the release exe, are written to `jaws_debug.log`. See [Game debug text](#game-debug-text-cjaws_debuglog-2026-10-12). Code: `src/debuglog.{h,cpp}`. |
| *(file)* | **Mod settings** (added 2026-11-25, user-confirmed working): `jaws_config.txt` (next to `Jaws.exe`) sets your control layout from a save file (so new games stop resetting to the default controls; user-confirmed) and/or single `key`/`mouse`/`pad` bindings by name (added later the same day; user-confirmed, `mouse` lines untestable in Gamepad mode) and which features start switched on (`farview on`). See [Mod settings](#mod-settings-jaws_configtxt-2026-11-25). Code: `src/config.{h,cpp}`; example `jaws_config.example.txt`. |
| *(file)* | **Message overrides** (added 2026-10-04, user-confirmed): `jaws_messages.txt` replaces on-screen messages per stage, re-read when saved. See [Message overrides](#message-overrides-cjaws_messagestxt-2026-10-04). Code: `src/messages.{h,cpp}`. |
| `F9` | **Custom level picker** (2026-10-04, user-confirmed): lists `custom_levels\*.GDW` next to `Jaws.exe`; Up/Down, Enter loads (engine `RequestStage(1, name)`, like F10), Esc/F9 closes; game keys blocked while open. See "Custom levels" below. (F9 used to be the old three-pass position scanner, removed.) |
| `I` / `K` | Freecam: move forward / backward |
| `J` / `L` | Freecam: strafe left / right |
| `U` / `O` | Freecam: move up / down |
| `Alt` | Hold for fast movement (45× speed) |
| Mouse | Freecam look (cursor captured and re-centred each frame) |

The **XYZ overlay** (top-left corner) shows the player shark's real world-space position (read directly from game memory — see [XYZ Overlay Accuracy](#xyz-overlay-accuracy--solved-2026-10-01) below) plus its facing (`Hdg` 0–360°: 0 = +Z, 90 = +X; `Pitch` + = nose up — from the world matrix's Z basis row, since the shark model faces local +Z), its **speed** (`Spd` = 3D, `H` = horizontal X/Z, `V` = vertical, + = rising; game units per second, worked out from how far the position moves in ~0.25 s windows, not read from a game field; a jump of over 100 units in one frame, like a teleport, restarts the measurement instead of showing a spike; added 2026-10-16, user-confirmed in-game), and all toggle states. The X line ends in `Shark` when showing the real position, or `Cam` when it falls back to the old camera-derived reading (menus, loading screens).

Screenshots land at:
```
~/.steam/steam/steamapps/compatdata/2342933845/pfx/drive_c/Program Files (x86)/Jaws Unleashed/jaws_screenshot_0000.bmp
```

---

### Mod settings (`jaws_config.txt`, 2026-11-25)

Lives in the game folder next to `Jaws.exe` (the mod falls back to `jaws_config.txt` if the game folder has none). A `key value` settings file (`#` starts a comment), read at startup and re-read within a second when saved. Example with comments: `mod/jaws_config.example.txt`. Log lines start `[jaws_mod] config:` in `jaws_mod.log`.

| Key | Values | Effect |
|---|---|---|
| `controls_from` | save file, or `none` | Control layout copied from this save (`PROFILE<N>.sav`). A bare name is looked up next to `Jaws.exe`; a full path (`C:\...`) also works. Must be a 7,604-byte save. |
| `controls_apply` | `new` (default) / `all` | `new`: the layout is set once at startup, so every **new game** gets it; loaded saves keep their own controls. `all`: also replaces the controls of every save you load and writes the layout into that profile (so saving keeps it). With `all`, change controls in this file, not in the game's controls menu (a menu change looks like a different layout and is undone). |
| `farview`, `fog_off`, `foliage_hide`, `noclip`, `invincible`, `ecco_mode` | `on` / `off` | Start states of `Shift+F4` far view, `F4` fog off, `F6` foliage hide, `F7` no-clip, `F11` invincible and `Shift+F2` Ecco mode. Set when the game starts and again whenever that line changes; the hotkeys still toggle freely in between. A missing line = the mod's default (off). (Added 2026-11-25; the fog/foliage/invincible states moved from `DeviceProxy` members to process-wide globals at the same time, per the device-recreation rule.) |
| `key` / `mouse` / `pad` | `<action> <button>` | One binding, applied on top of `controls_from` (or the game's startup defaults when that's `none`). Actions are the game's controls-menu names: `swim turn_up turn_down turn_left turn_right charge_attack bite shark_vision stealth_attack tail_whip target_lock next_target previous_target next_body_part previous_body_part map pause dodge camera_mode`. Keyboard: DirectInput key names (`w`, `space`, `lshift`, `up`, `numpad0`, … full list in the example file and `src/config.cpp`). Mouse: `left right middle button4`–`button8 wheel_up wheel_down`. Pad: `button0`–`button17`, `dpad_up/right/down/left`. `none` unbinds; `0xNN` is a raw code. Changes apply live when the file is saved. Removing a line doesn't undo it until the next start. |

**Mouse or gamepad, not both:** the launch option Mouse & Keyboard / Gamepad sets `[0x8D681C]` (startup settings code `0x729630`, field `+0x118`; probably `pcrt.ini` `KeyboardLayout`, unverified). With it set, input init creates a gamepad device instead of the mouse, and the rebuild (`0x4842E0`) registers the pad column instead of the mouse one. So `mouse` lines only work in Mouse & Keyboard mode, `pad` lines only in Gamepad mode, `key` lines in both (user-observed 2026-11-25: a `mouse` binding did nothing while playing with a gamepad).

**Live layout file:** the mod writes the current controls to `jaws_controls_current.txt` (next to `Jaws.exe`) in the same `key`/`mouse`/`pad` syntax whenever they change (including changes made in the game's controls menu), so you can copy lines from it into the config.

Code meanings (from the controls menu's text, `0x539120`): keyboard = DirectInput scan code (`0xFF` none); second slot `0x103`/`0x104`/`0x105` left/right/middle mouse button, `0x106`+ = "mouse button N" (code − `0x102`), `0x10B`/`0x10C` mouse wheel (which is up is a guess: the user's layout has `0x10B` on next target), `0x1FF` none; gamepad `5`–`0x16` = "BUTTON N" (code − 5), `0x17`–`0x1A` d-pad up/right/down/left, `0xFF` none.

**Why new games lost your controls, and how the mod fixes it** (`Jaws.exe`, decompiled 2026-11-25; full notes in `docs/exe_analysis.md` "Control bindings and the profile"): the live bindings are three arrays of 31 dwords indexed by action (`0x8A0094` keyboard, `0x8A0208` second slot/mouse, `0x8A0300` gamepad), filled with the built-in defaults at startup. Loading a save (`0x539B30`) copies the save's binding table into them; a new game (`0x537090`) clears the profile and copies the *arrays* into it without resetting them. So the stock game starts every session on the defaults, and the old "load your save, quit to menu, make a new save" trick worked because the arrays still held the loaded layout. The mod does the same copy from the chosen save as soon as the input devices exist (`[0x8D6818]` set), then calls the game's own rebuild (`0x483F30` on the input object `0x8D67F8`, which clears and re-registers every binding from the arrays).

Named bindings and the live layout file (plan B) added later on 2026-11-25; instead of a hotkey, the live layout file is updated automatically.

### Message overrides (`jaws_messages.txt`, 2026-10-04)

Replaces any of the game's on-screen messages while a given stage is loaded, without touching `Jaws.exe` on disk. One line per override: `<STAGE or *> <slot> <text>`. `\n` is a line break, `^OK^` / `^CANCEL^` / `^CONT^` are the game's button icons, and `#` starts a comment. Slot numbers: run `scripts/dump_messages.py`, which writes them to `docs/game_messages.txt` (generated locally from your `Jaws.exe`; not in the repo). The file is re-read when saved. Overrides apply when the named stage loads and are undone on the next stage without overrides. Example: `TEST 598 LEAVE THE CUSTOM LEVEL?\n\nPRESS ^OK^ TO LEAVE OR ^CANCEL^ TO STAY.`

How it works (`src/messages.{h,cpp}`): `[0x854D14 + 4*lang]` points at 5 language tables of 1,000 message pointers (English `0x84FEF0`, writable `.data`). Code asks for a message by its English text; `FUN_00453d00` hashes it (case-insensitive; hash built once at startup from the original strings) to a number and returns `tables[lang][number − 1]`. The mod repoints that slot in every language table each time the stage changes. **In-game notes (user-tested 2026-10-04):** FISH/TEST's exit zone shows **slot 598**, and the game puts the destination name (`OPEN OCEAN - SOUTH`) in front of it, so start the text with `\n` like the original. `[` and `]` draw the Esc and Enter key icons, so don't use square brackets as text. Exit prompts: 598 "enter this area" (`LoadChecker`), 201 "leave this stage" (`MBSwimoutChecker`), 199/851 "completed stage", 200 "locked".

### Game debug text (`jaws_debug.log`, 2026-10-12)

`Jaws.exe` calls a printf-style debug print (`0x4549D0`, cdecl: format + args) from 171 places, e.g. `Razas damage!`, `HP:%f`, `StoryMissionCompleted:%d`, `GlobalMessage type:%d range:%f`. The release build reduced it to a lone `ret`. When the mod loads (`Direct3DCreate8`) it checks for that `ret` plus padding, patches in a `jmp` to `DebugPrintHook`, and writes each message, with seconds since start, to `jaws_debug.log` (recreated each game start; on Linux/Proton: `<prefix>/drive_c/Program Files (x86)/Jaws Unleashed/jaws_debug.log`). Identical consecutive lines are collapsed into one "repeated N more times" line. `%s` arguments are checked before formatting (these prints were never run in the shipped build), and `%n` is refused. Watch it live:

```bash
tail -f ~/.steam/steam/steamapps/compatdata/2342933845/pfx/drive_c/Program Files (x86)/Jaws Unleashed/jaws_debug.log
```

### Custom levels (`custom_levels\`, F9)

Added 2026-10-04, user-confirmed: load custom levels without editing any game file. Put `NAME.GDW` in `custom_levels\` next to `Jaws.exe` (name: letters, digits, `_`, max 31, not a stock level's name), then press F9 in any level and pick it. `levels/custom_fish/build.sh` installs there.

How it works (`src/levels.{h,cpp}`): the mod patches `Jaws.exe`'s imports of `CreateFileA` and `GetFileAttributesA`. The engine opens levels by absolute path, `<install>\data\<NAME>.GDW` (each load opens it twice). When a requested `.GDW` doesn't exist and `custom_levels\<NAME>.GDW` does, the call is pointed there. Stock files always win, so nothing original can be replaced. The level is then loaded with the engine's own deferred stage request (`RequestStageLoad` in `src/stage.cpp`, same path as F10). F10 reload, message overrides (keyed by `NAME`) and the level's exits (back to Open Ocean South through its `FISH00` loading screen) work unchanged. The first 40 `.GDW` opens are logged to `jaws_mod.log`, with `->` for redirected ones.

## Build

**Requirements:** `i686-w64-mingw32-g++` (32-bit MinGW cross-compiler), `make`.

```bash
cd mod/
make              # build d3d8.dll
make clean        # remove build output
```

No external SDK needed — the DX8 interface is hand-rolled in `src/d3d8_iface.h`.

---

## Deploy

**Proton version (2026-10-16):** use **GE-Proton** (currently `GE-Proton11-9`, in `~/.steam/root/compatibilitytools.d/GE-Proton11-9-x86_64/`), selected under the game's Steam Properties → Compatibility. Valve's Proton can't play the pre-rendered `movie\*.WMV` cutscenes (WMV2 video + WMA2 audio): it has no decoder for them in a non-Steam game and shows its "video not available" placeholder instead. GE-Proton bundles FFmpeg (`wmv2`/`wmav2`) and plays them. The mod loads the same under both (user-confirmed). In-engine cutscenes never depended on this.

1. **Set the Steam launch option** for Jaws Unleashed:
   ```
   WINEDLLOVERRIDES="d3d8=native,builtin" %command%
   ```
   This tells Proton to prefer the game-directory `d3d8.dll` over DXVK's system copy.

2. **Copy the built DLL** into the game directory:
   ```bash
   cp d3d8.dll "/path/to/steamapps/compatdata/2342933845/pfx/drive_c/Program Files (x86)/Jaws Unleashed/"
   ```

3. **Optional settings:** copy `jaws_config.example.txt` into the same folder as `jaws_config.txt` and edit it (control layout from a save, single bindings, features on at start). All mod files live in that folder.

4. **Launch the game** via Steam. Check the log at:
   ```
   ~/.steam/steam/steamapps/compatdata/2342933845/pfx/drive_c/Program Files (x86)/Jaws Unleashed/jaws_mod.log
   ```
   A successful load shows `[jaws_mod] DeviceProxy created 1920x1080` and `[jaws_mod] time hooks: GTC=ok QPC=ok`.

---

## Source Layout

```
mod/
├── Makefile
└── src/
    ├── d3d8.def            # Forces undecorated Direct3DCreate8 export name
    ├── d3d8_iface.h        # Hand-rolled DX8 COM interface definitions
    ├── d3d8_proxy.cpp      # DllMain, Direct3DCreate8, D3D8Proxy, IAT time hooks
    ├── device_proxy.h      # DeviceProxy class declaration
    ├── device_proxy.cpp    # Freecam, view matrix injection, key toggles, EndScene hook
    ├── overlay.h / .cpp    # GDI → D3D texture HUD renderer
    ├── shark.h / .cpp      # Player shark position/facing read + teleport (decompiled pointer chain)
    ├── input_block.h / .cpp # DirectInput keyboard vtable patch — blocks game input while the F8 box is open
    ├── bookmarks.h / .cpp  # 9 teleport bookmark slots, persisted to jaws_bookmarks.txt
    ├── messages.h / .cpp   # per-stage on-screen message overrides from jaws_messages.txt
    ├── noclip_guard.h / .cpp # no-clip: skip area triggers, buoy pushes, currents
    ├── config.h / .cpp     # jaws_config.txt (game folder): control layout, named bindings, start-on features
    ├── debuglog.h / .cpp   # re-enables the game's emptied debug print -> jaws_debug.log
    ├── stage.h / .cpp      # F10 reload / F9 load through the engine's deferred stage request
    ├── levels.h / .cpp     # custom_levels\ folder: file-open redirect + level list for F9
    ├── iddump.h / .cpp     # F12 object-ID registry dump (debug)
    ├── dinput8_proxy.cpp   # Abandoned injection attempt (not built)
    └── winmm_proxy.cpp     # Abandoned injection attempt (not built)
```

---

## Architecture

```
Direct3DCreate8 (our export, undecorated via d3d8.def)
  ├─ installs IAT time hooks into Jaws.exe (GetTickCount, QueryPerformanceCounter)
  ├─ lazy-loads DXVK d3d8 from system32
  └─ returns D3D8Proxy wrapping the real IDirect3D8
       └─ CreateDevice → returns DeviceProxy wrapping the real IDirect3DDevice8

DeviceProxy intercepts:
  SetTransform(VIEW)  → extracts world-space camera pos/orientation;
                        injects freecam view matrix when F2 active
  SetRenderState      → suppresses D3DRS_FOGENABLE (F4);
                        forces alpha test impossible to hide foliage (F6)
  EndScene            → draws overlay HUD; polls F2–F6 keys; takes screenshots (F3)
  Reset               → releases and re-initialises overlay after device reset
  (everything else)   → forwarded directly to the real DXVK device
```

---

## How the Freecam Works

### View matrix injection

The game calls `SetTransform(D3DTS_VIEW, &viewMatrix)` each frame. We intercept this and, when freecam is active, substitute a matrix built from our own position + yaw/pitch.

### Seeding on activation

The game calls `SetTransform(VIEW)` multiple times per frame for several different camera identities, not just one secondary camera (see [XYZ Overlay Accuracy](#xyz-overlay-accuracy--solved-2026-10-01) below for the full investigation). `ExtractCamPos` filters out the one degenerate case that's cheap and reliable to detect — a secondary camera whose translation is exactly `(0,0,0)` — and maintains a 5-sample rolling median of what's left for freecam seeding. This is good enough for seeding (a one-time snapshot on F1 press, where being off by a bit doesn't matter) but is **not** sufficient for the continuous, precise position readout the XYZ overlay is meant to provide.

### Position extraction

Given the D3D row-vector view matrix V:
```
eye.x = −(V._11·V._41 + V._21·V._42 + V._31·V._43)
eye.y = −(V._12·V._41 + V._22·V._42 + V._32·V._43)
eye.z = −(V._13·V._41 + V._23·V._42 + V._33·V._43)

pitch = asin(V._23)
yaw   = atan2(V._13, V._33)
```

### View matrix construction

Standard D3D left-handed view matrix from position, yaw, and pitch.  
The up vector is `forward × right` — using `right × forward` gives the down vector in a left-handed system and flips the scene upside-down.

---

## Overlay Rendering Bug Fix (2026-07-16)

The XYZ/status overlay never rendered at all — F1 toggled freecam fine, but no HUD ever appeared. Root cause was a wrong D3D FVF (vertex format) constant in `overlay.cpp`:

```cpp
// Wrong — evaluates to D3DFVF_XYZB1 | D3DFVF_TEX1 (position + a blend
// weight, no diffuse color, and NOT pretransformed):
#define D3DFVF_TLVERTEX (0x002 | 0x004 | 0x100)

// Correct — D3DFVF_XYZRHW | D3DFVF_DIFFUSE | D3DFVF_TEX1:
#define D3DFVF_TLVERTEX (0x004 | 0x040 | 0x100)
```

`D3DFVF_XYZ` (`0x002`) and `D3DFVF_XYZRHW` (`0x004`) are alternatives in the FVF's position-type field, not combinable flags. OR-ing them together produced `0x006`, which happens to numerically equal `D3DFVF_XYZB1` (position + one blend weight) combined with `D3DFVF_TEX1` — a completely different vertex layout with no color component, and critically *not* pretransformed/screen-space. The overlay's quad vertices were being run back through the game's real 3D world/view/projection + lighting pipeline instead of being drawn as a fixed screen-space HUD, which is why nothing ever showed up.

Also fixed in the same pass: the overlay's texture was being locked with `D3DLOCK_DISCARD`, which is only valid for `DYNAMIC`-usage resources — this texture is `POOL_MANAGED` with no usage flags, so the flag was invalid and DXVK could fail the lock outright (old native D3D8 drivers tended to just ignore the invalid flag, masking the bug). Changed to a plain lock (`0`).

---

## XYZ Overlay Accuracy — Solved (2026-10-01)

> **SOLVED (2026-10-01) via decompilation — everything below this note is the historical investigation, kept so it isn't repeated.**
>
> Decompiled `Jaws.exe` with Ghidra 12.1.4 (headless, `~/tools/ghidra_12.1.4_PUBLIC`) and found the game's own pointer chain to the player shark:
>
> | Step | Address / offset | Evidence |
> |---|---|---|
> | Player shark controller (singleton) | global `0x90BC04` | constructor at `0x664BD8` stores `this` there, destructor at `0x664C20` clears it; ~194 code references; holds shark state machine (`+0x240`), health/hunger (`+0x2A8`/`+0x2AC`), save-file-ability-scaled config object (`+0x54`) |
> | Shark scene object ("brick") | `ctrl + 0x50` | the debug routine that prints `"SharkRelPos"` (`0x671060`, vtable `0x7F28FC` slot 21) reads the shark this way |
> | World position | `brick + 0xA8` (3 floats X/Y/Z) | the engine's world-matrix updater (`0x696EA0`) shows the brick layout: `+0x0C` flags (`0x20` = world matrix stale), `+0x14` parent pointer, `+0x50` local 4x3 transform, `+0x84` world 4x3 transform = local x parent world, translation at `+0xA8` |
>
> `ReadSharkPos()` in `device_proxy.cpp` follows this chain every `EndScene` via `ReadProcessMemory` (fails cleanly rather than crashing if a pointer is dangling mid-load). **Verified in-game on Fisherman's Isle:** spawn reads `(2000, -6.4, -3630.7)` vs. the shark's authored BRTR spawn (`GWside`/`SharkPosReal`) at `(1998, -7, -3628)`; X/Z change smoothly while swimming and return identical values at the same spot; Y ≈ 0 at the water surface.
>
> **Why the old memory scan failed:** the F9 scanner only searched `0x845000`–`0xE70000`, which is exactly the exe's static `.data` section. The shark object is heap-allocated at level load, so it was never in range. The `0x008CFC88` false positive was a static scratch variable.

The overlay renders correctly (see bug fix above) and shows *a* position, but it is **not a reliable readout of the player's actual position**. This was investigated extensively (2026-07-17) and is documented here so the investigation isn't repeated from scratch.

### The core problem

The game calls `SetTransform(D3DTS_VIEW, ...)` **multiple times per frame** for different camera identities — the real player camera, plus at least one water reflection/refraction camera, and evidence of more (see below). There is no reliable way found so far to tell them apart from data available in the D3D call stream:

- **A camera that's sometimes static, sometimes moving.** Logging near a fixed reflective surface showed the secondary camera sitting almost still (barely drifting over a 20s window). Logging in open water instead showed it actively moving in a pattern that roughly mirrors the real camera's own motion. Any approach that assumes "the secondary camera is the static/degenerate one" only works in the first case.
- **Exact-zero filtering (implemented, partial fix).** One specific secondary camera reliably has translation `(0,0,0)` exactly, and — because it happens to be called last in the frame, right before the overlay reads the position — dominates a naive "latest value" or even a 5-sample-median read every single frame (not by chance: the call order is fixed, so the zero sample is always the freshest). `ExtractCamPos()` filters this exact case out. This is the *only* part of the problem that's actually fixed.
- **Reflection determinant check (tried, failed).** A mirrored/reflected transform should mathematically have a negative determinant on its 3×3 rotation part, vs. positive for an ordinary camera. Logged determinants for both real and mirrored-looking samples: **always exactly `+1.0`**. This engine must implement reflections via a genuinely repositioned/reoriented second camera (still a proper rotation matrix), not a flipped-handedness matrix — so this check has no discriminating power here.
- **Render-target gating (tried, failed).** Reflections normally render to an off-screen texture, so the theory was: only trust the camera set while the primary back buffer is the active render target. Interleaved logging of `SetRenderTarget` + `SetTransform(VIEW)` calls (in true call order, via a shared sequence counter) showed the real camera's `SetTransform(VIEW)` is **never** called while the back buffer is active — this engine renders the whole scene to off-screen textures first and only briefly touches the back buffer for a final composite blit at the end of the frame, with no camera transform set during that moment. There is no "this call is the real one" signal anywhere in the D3D call stream that was found.

### Memory-scan pivot (unsuccessful — historical)

Bypassed the rendering pipeline entirely and tried reading the player's position directly from memory, the same technique used to find the existing god-mode health addresses (`0x8F11A8` etc., found via the `F7` two-pass scanner already in the codebase).

Built `F9`, a three-pass scanner (removed 2026-10-04; F9 is now the level picker) in `device_proxy.cpp`:
1. Snapshot every 4-byte-aligned XYZ float triplet in a plausible coordinate range (magnitude 0.5–6000) across `0x845000`–`0xE70000` (the same range `F7` already reads safely, and where all known god-mode addresses live).
2. After swimming, keep triplets that moved a meaningful amount.
3. After continuing to swim in the *same direction*, keep survivors whose two displacement vectors point in a consistent direction (cosine similarity > 0.5) — added specifically because a simpler 2-pass "did it move" version found a false positive: some oscillating/animation value that happened to differ between two snapshots by chance, without actually tracking real movement.

The best candidate found, `0x008CFC88`, passed the 3-pass test cleanly (cos=0.98 across two independent movement segments) but **failed live verification**. Per-frame logging of the raw value while swimming showed it cycling through several independently, slowly-drifting value clusters (roughly 645.x, 646.x, 666.x, then a jump to -461.x, then zeroed out entirely) rather than one continuously-moving value — consistent with a **shared/reused scratch address written by multiple different entities** (likely several nearby fish/NPCs, or a temp variable reused across position updates each frame), not a dedicated player-position field. Same fundamental class of problem as the D3D approach, just manifesting in memory instead of render calls.

### Recommended next approach (historical — superseded by decompilation)

Scan for the position field **near the already-confirmed player-specific god-mode addresses** (`0x8F11A8`, `0x8FB1B0`, `0x8FB1C0`, `0x9E907C`, `0x9E908C`, `0x9E909C`, `0x9E90AC`, `0x9E90FC`, `0xA14ED4`, `0xA16318`, `0xA59448`) instead of the broad `0x845000`–`0xE70000` range. Those addresses are known-good because toggling god mode reliably keeps *the player* alive, not some other entity — the position field is very likely a small fixed byte offset away in the *same* player object struct, not somewhere else in memory shared with other entities. The `F9` scanner's 3-pass structure is reusable as-is; it just needs its scan range narrowed to a tight window around one of those addresses instead of the whole `.data` range.

**Current state:** the overlay shows the D3D camera-transform reading (`cam_x_/y_/z_`) — imperfect (third-person camera orbits with rotation; occasional pollution from an unfiltered secondary camera identity) but not actively showing data known to be wrong, unlike the memory candidate.

---

## How Sim Pause Works (F5)

The game's simulation (physics, AI, animations, cutscene playback) advances based on a delta-time value derived from `QueryPerformanceCounter` (QPC) and `GetTickCount` (GTC). At startup, `InstallTimeHooks` walks the import address table (IAT) of `Jaws.exe` and replaces the function pointers for both with our hooks.

While sim pause is active, both hooks return fake time advancing at `1 / SIM_DIVISOR` of real speed (`SIM_DIVISOR = 4` → 25% speed). Both must be slowed together: the game uses QPC to gate its own render loop, so slowing only one causes the other to diverge and either stops rendering or causes a time jump on resume.

On unpause, accumulated offsets are adjusted so the game sees no time discontinuity — the fake dt on the first post-resume frame is approximately zero.

**Render rate tradeoff:** slowing both timers reduces the game's effective render rate to roughly `60fps / SIM_DIVISOR` (~15 fps at divisor=4). This causes mild visual choppiness in freecam during pause — unavoidable without a more invasive hook into the game's render loop. The freecam itself moves at a consistent real-time speed regardless of render rate (camera position is scaled by actual wall-clock dt via the saved real QPC pointer).

**Tuning:** `SIM_DIVISOR` in `src/d3d8_proxy.cpp`. Lower = smoother freecam, faster simulation. Higher = more frozen simulation, choppier freecam.

---

## Foliage Hide (F6)

Sea foliage (kelp, seaweed, plants) is rendered as flat billboard cards using `D3DRS_ALPHATESTENABLE` to punch transparent cutouts. When foliage hide is active, any `D3DRS_ALPHATESTENABLE = TRUE` call is intercepted and immediately followed by:
- `D3DRS_ALPHAREF = 255`
- `D3DRS_ALPHAFUNC = D3DCMP_GREATER` — "pass only if alpha > 255"

No pixel can satisfy this condition, so all alpha-tested draws discard every pixel. Solid geometry is unaffected. `alpha_test_enabled_` tracks state so subsequent `ALPHAREF`/`ALPHAFUNC` calls from the game are also overridden while a test pass is active.

---

## Screenshots (F3)

`TakeScreenshot()` (`device_proxy.cpp`) grabs the front buffer via `CreateImageSurface` + `GetFrontBuffer` + `LockRect` and writes an uncompressed 32bpp BMP to `jaws_screenshot_NNNN.bmp`. Every failure branch (`CreateImageSurface`, `GetFrontBuffer`, `LockRect`, `CreateFileA`) now logs its `HRESULT`/`GetLastError()` to `jaws_mod.log` — previously these failed silently, which made a screenshot going missing undiagnosable.

**Numbering bug fixed (2026-08-16) — screenshots were overwriting each other.** The `NNNN` index used to be a `DeviceProxy` member (`screenshot_idx_`), starting at 0 for each instance. Log analysis showed `IDirect3D8::CreateDevice` firing **366 times** in a single play session — a fresh `DeviceProxy` (and thus a fresh `screenshot_idx_ = 0`) roughly every 35–45 log lines, far more often than any real device-loss/alt-tab event should cause (see the "Frequent device recreation" note below). Every recreation reset the counter, so screenshots kept landing back on `jaws_screenshot_0000.bmp`/`0001.bmp` instead of incrementing indefinitely.

Fix: the counter is now `NextScreenshotIdx()`, a function-local `static int` — process-wide, not per-`DeviceProxy`, so it survives device recreation. On first call it also scans `C:\` for existing `jaws_screenshot_*.bmp` files and seeds itself past the highest index found, so it won't clobber screenshots from a previous game launch either.

**Frequent device recreation — real anomaly, not a mod bug, still unexplained.** `real_->CreateDevice(...)` genuinely succeeds each time (this isn't our proxy misfiring) — the game or DXVK is legitimately tearing down and rebuilding the D3D8 device far more often than expected for a title that isn't crashing or reloading levels that fast. Not yet investigated further; worth revisiting if other per-instance mod state (freecam toggle, render-state overrides, etc.) is ever seen resetting mid-session the same way the screenshot counter was.

---

## Render State Isolation

`Overlay::DrawQuad` saves and restores every device state it touches. D3D8 state blocks (`CreateStateBlock`) are unreliable under DXVK so all save/restore is done manually with explicit `Get`/`Set` calls.

States saved/restored: texture slot 0 (note: `GetTexture` adds a COM ref), texture stage state 0 (ColorOp/Arg1, AlphaOp/Arg1), render states (AlphaBlendEnable, SrcBlend, DestBlend, ZEnable, ZWriteEnable, CullMode, Lighting, ColorVertex), vertex shader/FVF, stream source 0, index buffer.

**Why stream source matters:** `DrawPrimitiveUP` rebinds stream source 0 to a temporary buffer. The game renders multiple `BeginScene`/`EndScene` passes per frame (opaque, then transparent/skinned). Without restoring stream source after the overlay draw, the second pass reads from the wrong buffer, making water, characters, and NPCs invisible.

---

## Known Limitations

- **Frustum culling follows the player.** The game culls geometry before calling `SetTransform`. Freecam only replaces the view matrix — objects outside the player's frustum are not rendered even if the freecam is pointed at them.
- **Multi-pass rendering artefacts.** The view injection fires for every `SetTransform(VIEW)` call, including shadow and reflection passes, causing some visual artefacts in freecam mode.
- **Map screen.** The map's 3D view is affected by freecam. Disable freecam (F2) before opening the map — freecam was moved off F1 specifically so F1 is left free for the game's own map key.
- **Sim pause choppiness.** At `SIM_DIVISOR=4`, the game renders at ~15 fps while paused. Increase the divisor for a stronger freeze at the cost of more choppiness.
- **Teleport bookmarks aren't per-level.** Slots store plain world coordinates; the same slot is a different place in each GDW.
- **Blocked scripted deaths leave the shark invisible.** See `F11` in Controls. Accepted as-is.
- **`CreateDevice` fires far more often than expected** (366 times in one session observed 2026-08-16) — cause unknown. Any mod state stored per-`DeviceProxy` instance (rather than as a process-wide `static`, like the screenshot counter used to be) is at risk of silently resetting mid-session. See [Screenshots](#screenshots-f3).

---

## Tuning

Speed and sensitivity constants in `src/device_proxy.cpp`:
```cpp
static const float FC_SPEED = 5.0f;    // units per second
static const float FC_SHIFT = 45.5f;   // multiplier when Alt held
static const float FC_SENS  = 0.003f;  // mouse look, radians per pixel
```

Sim pause strength in `src/d3d8_proxy.cpp`:
```cpp
static const DWORD SIM_DIVISOR = 4;    // 4 = 25% sim speed, ~15fps render
```

---

## Injection Approach — History

Getting the DLL to load under Proton required several attempts:

| Approach | Result |
|----------|--------|
| `winmm.dll` proxy in game dir | Never loaded — Wine uses winmm builtin-first |
| `dinput8.dll` proxy | Loaded, but forwarding `DirectInput8Create` hit `EXCEPTION_WINE_STUB (0x80000100)` in Wine's i386 stub PE |
| `d3d8.dll` without launch option | Never loaded — Proton's DXVK override takes priority |
| `d3d8.dll` + `WINEDLLOVERRIDES="d3d8=native,builtin"` | **Works** |

**Export name gotcha:** MinGW exports `__stdcall` functions with stdcall decoration by default (`Direct3DCreate8@4`). Wine's loader looks for the undecorated name `Direct3DCreate8`. Without `src/d3d8.def`, Wine creates a stub and crashes on the first call.

---

## Future Work — BRTR Node-Insertion Mystery (2026-07-17)

A file-level custom-map-import experiment (see CLAUDE.md's "Custom map feasibility" note and memory `project_custom_map_feasibility`) hit a wall this mod could help resolve. Summary:

- Injecting a new resource into `RSRC` and repointing/relocating existing `BRTR` nodes both work reliably in-game.
- Appending an entirely new `CHBR` sibling node to `BRTR` (structurally valid, verified 3 different ways including a byte-for-byte clone of a real working node) **never renders** — no crash, just silently absent.

Static file analysis is exhausted. The natural next step is **runtime instrumentation**: hook whatever code path parses `BRTR` during level load (or a nearby allocation/object-registration call) to observe how many nodes the game actually processes, and whether that count is read from somewhere other than the `BRTR` chunk's own byte content — e.g. a precomputed spatial/streaming index or a node count cached elsewhere in the file/executable. This would need:
- Locating the `BRTR`-parsing or scene-object-instantiation routine in `game_binary/Jaws.exe` (not yet done — no disassembly work has targeted this path specifically).
- A logging hook in `device_proxy.cpp`/`d3d8_proxy.cpp` (or a new hook point) to dump node counts/IDs during a level load, comparable to how the existing freecam/overlay hooks already intercept `SetTransform`/`EndScene`.

Not started — flagged here so a future session doesn't have to rediscover the dead end in static analysis before reaching for this.

---

## Moved from CLAUDE.md (2026-11-25)

The text below was moved word for word from the root `CLAUDE.md`. It is newer than earlier sections of this file where they disagree.

### Mod (`mod/`, d3d8 proxy) — current features

All user-tested 2026-10-01. Full controls and internals are in `mod/README.md`.

| Key | Feature |
|---|---|
| overlay | Shark world **X/Y/Z** (labeled `Shark`, or `Cam` fallback in menus) + **heading/pitch** + **speed** (2026-10-16, user-confirmed: `Spd`/`H`/`V` in units/s from position change over ~0.25 s, `UpdateSharkSpeed` in `src/shark.cpp`; jumps > 100 units/frame restart it) |
| `F8` | **Teleport box**: type `X Y Z` / `X Z` / a bookmark slot number. `Ctrl+1..9` saves the current spot. Bookmarks live in hand-editable `jaws_bookmarks.txt` (`slot x y z [name]`, `#` comments; reloaded when F8 opens if the file changed; plain coords, not tied to a level). Game keyboard input is blocked while the box is open (DirectInput device vtable patch). Teleport writes the brick's local translation (solved through the parent's world matrix) and world translation, sets the stale flag, **moves the controller's collision start point `ctrl+0x680`, and holds the target for 45 frames** (2026-10-04 fix: without these, jumps through terrain snapped back and long jumps flung the shark into the sky or under the map). Still occasionally finicky right next to geometry. |
| `F11` | **Invincible + infinite hunger**: refills health and hunger to max every frame, and hooks `SetState` to drop state-7 (dead) requests. Known limitation: a blocked *scripted* death leaves the shark alive but invisible and the game confused. The user has accepted this; don't chase it. |
| `F10` | **Reload current stage from disk** (2026-10-03): calls engine vtable `+0x80` `RequestStage(1, engine+0xB8 name)`; the engine tick unloads and re-reads the `.GDW` at a safe point. For testing GDW edits in place. `src/stage.{h,cpp}`. **User-confirmed working 2026-10-03.** |
| file | **Message overrides** (2026-10-04): `jaws_messages.txt` lines `<STAGE or *> <slot> <text>` replace on-screen messages per stage by repointing the exe's language tables (`[0x854D14+4*lang]`, 1,000 slots, list in `docs/game_messages.txt` via `scripts/dump_messages.py`). `src/messages.{h,cpp}`. No exe patch. |
| `F9` | **Custom level loader** (2026-10-04, user-confirmed): picker for `custom_levels\*.GDW` next to `Jaws.exe`, loads via `RequestStage(1, name)`. The mod hooks `Jaws.exe`'s `CreateFileA`/`GetFileAttributesA` imports: the engine opens `<install>\data\NAME.GDW` by absolute path, and a missing `.GDW` is pointed at `custom_levels\NAME.GDW` (stock files always win). No game file edited; F10, message overrides and the level's exits work unchanged. `src/levels.{h,cpp}`. Replaced the old F9 position scanner. |
| `F12` | **Object-ID registry dump** (2026-10-03, debug, read-only): registry entries + objects for the IDs in `jaws_ids.txt` → `jaws_iddump.txt`. **Boat probe (2026-10-11):** for an `ANPosition` boat marker it follows the spawned copy to its `ANShip` AI and prints position, state stack, path and flags. `src/iddump.{h,cpp}`. |
| file | **Game debug text** (2026-10-12, not yet tested in-game): the exe's printf-style debug print `0x4549D0` (171 call sites, e.g. `Razas damage!`, `HP:%f`) was emptied to `ret` in the release build; the mod jumps it into `DebugPrintHook`, which writes timestamped lines to `jaws_debug.log` (`tail -f` it in `<prefix>/drive_c/`). `src/debuglog.{h,cpp}`. |
| `F7` | **No-clip** (2026-10-12, user-confirmed): holds the controller's collision-off flag `ctrl+0x810` = 1, so the collision step `0x65BFC0` skips its push-out and its "SafePoint Teleport" (the cause of F8 landing behind walls). Passes through terrain and most solid objects, still limited to the water, F8 into geometry stays put; moving objects (handler `0x671AB0`) still collide. `Shift+F7` = hardware write-watch trace of the shark's position fields (`src/hwtrace.{h,cpp}`; Wine reports `Dr6` = 0). Details: `docs/exe_analysis.md` "Collision step and no-clip". |
| `Shift+F4` | **Far view** (2026-10-17; user-confirmed working 2026-11-25, used in normal play): camera far plane 600 → 3000, above-water fog 1000–2900, underwater fog 100–400, in every level at runtime, restored when off. Underwater the water action `NAWaterYCamera` (live vtable `0x7F0120`, tick `0x62B430`) sets the camera far plane (`+0x11C`) to its fog end every frame, so that's the underwater draw distance; past ~400 objects flicker/vanish, 2500 crashed (OPEN_S tests, user-tested). `src/farview.{h,cpp}`; details `docs/exe_analysis.md` "Draw distance and fog". |
| `Shift+F2` | **Ecco mode** (2026-10-21, user-confirmed working): Ecco: Defender's `DolphCtrl` movement (states 0–6, water physics, steering, idle routine; 120NORTH `DolphConfig`) ported to C++ and driving the shark brick via the shark tick vtable slot `0x7F2944`; water height from fn ptr `0x8B2E9C`; `jaws_ecco.txt` tuning. Phase A of the Ecco port (B1 = DOLPHIN level with Ecco's model, user-confirmed; B2 2026-10-21, user-confirmed: on that model Ecco mode plays the simulated dolphin clip through the shark's animator `ctrl+0xBC` / update `0x4DD250`; C = shark→dolphin handover). **Sonar (2026-10-21, user-confirmed):** F / middle mouse underwater draws Ecco's cone + wave meshes from the head with the sonar sound (`src/sonar.{h,cpp}`, D3D8-drawn at `EndScene`; files staged by `scripts/stage_ecco_sonar.py`), visual + sound only. `src/ecco.{h,cpp}`; `docs/ecco_dolphin_controller.md` "Step 2, Phase A", "Step 3, sonar in the mod" |
| `F2`/`F3`/`F4`/`F5`/`F6` | Freecam / screenshot / fog / sim pause / foliage hide (unchanged) |

New source files: `src/shark.{h,cpp}` (position/facing/teleport/health/death hook), `src/input_block.{h,cpp}`, `src/bookmarks.{h,cpp}`. **Process-wide state rule:** the game recreates its D3D device hundreds of times per session, so anything that must persist (like bookmarks) can't live on `DeviceProxy`.

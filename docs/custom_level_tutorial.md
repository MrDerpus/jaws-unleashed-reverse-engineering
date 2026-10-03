# Making a Custom Level — Tutorial

Build your own underwater level for *Jaws Unleashed* in Blender, and swim around in it in the real game.

Your level replaces **Fisherman's Isle**: when you swim into Fisherman's Isle from Open Ocean South, the game loads your level instead. Everything from the original level is gone except the ocean itself (water, sky and sun), the shark, and the HUD. What's left is your own seabed, your objects and your exits.

---

## What you need

- *Jaws Unleashed* (PC), with the project's mod (`d3d8.dll`) installed in the game folder.
- **Blender** 4.0 or newer.
- This project folder, with the level kit in **`levels/custom_fish/`**:

| File | What it is |
|---|---|
| `custom_fish.blend` | **Your level.** Open this in Blender. |
| `build.sh` | Turns the `.blend` into a game level and installs it. |
| `jaws_messages.txt` | A copy of your level's custom on-screen text (see Part 4). |
| `FISH_minimal_base.GDW` | The empty base level the build starts from. Don't edit it. |
| `README.txt` | A short version of this tutorial. |

Only `build.sh`, `README.txt` and `jaws_messages.txt` come with the project. The other two contain game data, so you create them yourself from your own copy of the game (Part 0). If they're already in the folder, skip to Part 1.

---

## Part 0 — One-time setup

You need your own game files in the project folder: the 20 `.GDW` files in `GAME_GDWs/` (copied from the game's `data` folder).

1. **Extract FISH's textures** (the material palette uses them):
   ```bash
   cd scripts
   python3 rip_textures.py      # FISH is the default level in both scripts
   python3 rip_gtex.py
   cd ..
   ```
2. **Create the level kit** (base level + starter `.blend`; needs Blender on the PATH):
   ```bash
   python3 scripts/make_level_kit.py
   ```
   It never overwrites an existing `custom_fish.blend` unless you add `--force`.
3. **Point Fisherman's Isle at your level.** The game's Open Ocean South level has an entrance to Fisherman's Isle; this makes it load `TEST.GDW` (your level) instead. In the game's `data` folder, keep a backup first:
   ```bash
   cp OPEN_S.GDW OPEN_S.GDW.orig
   python3 <project>/scripts/redirect_stage.py OPEN_S.GDW.orig OPEN_S.GDW FISH TEST
   ```
4. **Install the mod** (`mod/d3d8.dll` into the game folder; see `mod/README.md`). It gives you F10 reload, F8 teleport and the custom text.
5. **Tell the build where the game is.** `scripts/build_scene.py` installs into the folder named by `LIVE_DATA` near its top (the game's `data` folder inside its Wine/Proton prefix). Change it if your game lives elsewhere.

## Part 1 — The Blender file

Open `custom_fish.blend`. There are two collections:

- **`JAWS`**: everything in here goes into the game. It starts with a sandy **Seafloor**.
- **`REFERENCE (not exported)`**: helpers that never go into the game:
  - **Water surface**: a wireframe plane showing where the sea surface is.
  - **Shark**: a cone the size of the shark, placed where it appears when the level loads (its nose points at −Y).
  - **Palette**: a row of textured cubes south of the play area, one per ready-made material (see Part 2).

### Size and position

| Blender | Game |
|---|---|
| 1 unit | 15 game units |
| The shark | about 1.1 long × 0.6 wide × 0.4 tall |
| Z (up) | height (game Y) |
| Water surface | Z = 1.67 |
| Seafloor | Z = −3 |
| Play area | 100 × 100 units around the origin |

To find a Blender spot in the game (for the F8 teleport):
**game X = 2160 + 15·x  game Y = −25 + 15·z  game Z = −3650 + 15·y**
(x, y, z are the Blender coordinates). Example: Blender (10, 0, −2) → game `2310 -55 -3650`.

---

## Part 2 — Building your level

Put everything you want in the game into the **`JAWS`** collection. Model as you normally would: modifiers are fine, and big objects are fine (the build cuts anything large into tiles automatically).

### Textures

**Easiest: the palette.** The cubes south of the play area each carry a material named `mat_<number>` (`mat_272` is the green seafloor sand, `mat_193` mossy rock, `mat_209` wooden planks, and so on). Give your object one of these materials and the game uses its own built-in version of it, so nothing extra is added to the level.

- Keep the name: `mat_272` must stay `mat_272`. (Blender's copies, like `mat_272.001`, are fine.)
- The texture repeats along with your UVs. The seafloor repeats every 4 units.

**Your own images work too.** Use any material with an **Image Texture** node, and the build turns the image into a game texture.

- Images are resized to a power of two (max 1024 × 1024).
- **See-through:** set the material's *Blend Mode* (Material Properties → Settings) to *Alpha Blend* (smooth fading) or *Alpha Clip* (hard on/off edges, like seaweed). The image needs an alpha channel.
- **Both sides visible:** turn *Backface Culling* off (only matters for see-through materials).

### Object settings (custom properties)

Select an object → **Object Properties** → **Custom Properties** → **New**, then rename the property and set its value:

| Property | Value | What it does |
|---|---|---|
| `jaws_collision` | `0` | The shark swims straight through it. (Without this, everything is solid.) |
| `jaws_exit` | `1` | Makes the object an **exit zone** instead of a visible object (see below). |

### Exits

An exit zone is a circle: when the shark swims into it, the game asks whether to leave to Open Ocean South. It works at any depth, from the seabed to above the surface. The exit object itself is never shown in the game.

**Adding an exit, step by step:**

1. **Pick the collection.** In the Outliner (top right), click the **`JAWS`** collection, so new objects go into it.
2. **Add a cylinder.** Put the 3D cursor where you want the exit (Shift + right-click on the spot), then **Add → Mesh → Cylinder** (Shift+A in the viewport).
3. **Size it.** Scale it (**S**) until it's as wide as you want the zone; the zone's radius is half the cylinder's width. The shark is about 1.1 units long, so 4–6 units wide is easy to swim into. Height doesn't matter.
4. **Mark it as an exit.** With the cylinder selected, open the **Object Properties** tab (the orange square in the Properties panel on the right). Under **Custom Properties**, click **New**. A property called `prop` appears: click the **gear icon** next to it, change **Property Name** to `jaws_exit`, click OK, and make sure the value is **1**.
5. **Save, build with `--show-exits`, and test** (see Part 3). The zone shows up as a coloured column; swim into it and the exit question appears.

**More exits:** select an exit and press **Shift+D** to duplicate it. The copy keeps `jaws_exit`, so just move it.

**An Empty works too** (Add → Empty, then the same custom property). Its radius is its *Size* (Object Data Properties) × its scale. A cylinder is easier, because you can see exactly how big the zone is.

**Colour of the test column:** with `--show-exits`, each exit shows as a see-through column in its **material's colour**. Give the exit object a material and set its **Base Color** (or the material's *Viewport Display* colour if its Base Color comes from a texture). Without a material, the column is bright pink. The column is always see-through: lowering the material's **Alpha** makes it more transparent. This is only for testing; the colour does nothing in a normal build.

> **Add at least one exit.** If your level has none, the game falls back to the original Fisherman's Isle exit: an invisible circle with a radius of about 53 Blender units, centred near Blender (−10, −24). Swimming out of it takes you out of the level.

---

## Part 3 — Putting it in the game

1. **Save** the `.blend` in Blender (Ctrl+S). The build reads the saved file.
2. In a terminal:
   ```bash
   cd ~/Projects/JAWS/levels/custom_fish
   ./build.sh
   ```
   It prints each object it built, then `deployed to …`. Takes about a minute.
3. In the game:
   - **Already in your level?** Press **F10** to reload it.
   - Otherwise, swim into **Fisherman's Isle** from Open Ocean South.

**Options:**

| Command | Does |
|---|---|
| `./build.sh` | Build and install. |
| `./build.sh --show-exits` | Same, plus a see-through **column** at every exit zone (its material's colour, or pink), so you can see where they are. For testing. |
| `./build.sh --no-deploy` | Build only (`custom_fish.GDW` in the folder), don't touch the game. |

If something goes wrong, the script stops and shows the end of `build.log` (in the same folder).

### Handy keys in the game (from the mod)

| Key | Does |
|---|---|
| **F10** | Reload the level from disk (after a build). |
| **F8** | Teleport: type `X Y Z` (game coordinates, see Part 1) and press Enter. |
| **F11** | Invincible and never hungry. |
| **F2** | Free camera. |
| **F3** | Screenshot. |

The top-left corner always shows the shark's game position.

---

## Part 4 — Changing the game's text

You can replace any message the game shows, for example the exit question, just for your level. The text lives in a plain text file the mod reads:

- **The live file** (what the game uses): `C:\jaws_messages.txt` inside the game's Wine prefix. On Linux:
  `~/.steam/debian-installation/steamapps/compatdata/2342933845/pfx/drive_c/jaws_messages.txt`
- **The copy in your level folder:** `levels/custom_fish/jaws_messages.txt`. After editing the copy, put it in place with:
  ```bash
  cp ~/Projects/JAWS/levels/custom_fish/jaws_messages.txt ~/.steam/debian-installation/steamapps/compatdata/2342933845/pfx/drive_c/
  ```

Changes apply as soon as the file is saved, even while the game is running.

### How a line works

```
TEST 598 \nLEAVE THE CUSTOM LEVEL?\n\nPRESS ^OK^ TO SWIM BACK TO THE OPEN OCEAN OR ^CANCEL^ TO STAY.
```

| Part | Meaning |
|---|---|
| `TEST` | The level it applies to (`TEST` = your level; `*` = every level). |
| `598` | Which message to replace. **598 is the exit question.** To see all 1,000 messages and their numbers, run `python3 scripts/dump_messages.py` from the project folder (needs `game_binary/Jaws.exe`); it writes `docs/game_messages.txt`. |
| the rest | Your text. |

Rules for the text:

- `\n` starts a new line.
- `^OK^`, `^CANCEL^` and `^CONT^` show the matching button icons.
- **Don't use `[` or `]`**: the game draws them as the Esc and Enter key icons.
- For the exit question, **start with `\n`**: the game puts the destination's name (OPEN OCEAN - SOUTH) in front of your text.
- Lines starting with `#` are notes and are ignored.

---

## Tips and limits

- **Huge objects are fine.** The game fades out single very large objects when it thinks you're not looking at them, so the build cuts anything bigger than 20 Blender units into tiles automatically. You won't notice the cuts.
- **Very dense small objects:** one object under 20 units across can have at most about 21,000 triangles.
- **Linked duplicates** (Alt+D) share one model in the game, which keeps the level small.
- **Negative scale (mirroring) isn't supported.** Apply it first (Ctrl+A → Scale).
- **Beyond the edge of your floor** there's nothing, and the shark can swim into the void. Build walls or cliffs if you want the area closed in.
- **Where things go wrong:**

| Problem | Likely cause |
|---|---|
| Object missing in-game | It isn't in the `JAWS` collection, or the `.blend` wasn't saved before building. |
| Object has the wrong texture | Its material was renamed (it must start with `mat_<number>`), or it has no image. |
| Swim through a wall | `jaws_collision` is set to `0` on it. |
| Can't leave the level | No object with `jaws_exit` = `1`, or it's somewhere you can't reach. Use `--show-exits` to see it. |
| Text change doesn't show | The live file wasn't updated (Part 4), or the line's level name isn't `TEST`. |
| Build stops with an error | Read the last lines it prints (or `build.log`). |

---

## Going back to the original game

- Copy `OPEN_S.GDW.orig` (your backup from Part 0) over `OPEN_S.GDW` in the game's `data` folder to make Fisherman's Isle normal again.
- Your level only lives in `TEST.GDW`, which the original game never uses.

To turn off the custom text, empty (or delete) `C:\jaws_messages.txt`.

---

*How it works under the hood (for the curious): `docs/brtr_editing.md` (building levels), `mod/README.md` (the mod and message overrides).*

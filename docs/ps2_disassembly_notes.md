# PS2 exe: disassembly notes

**In short:** how `GAME_GDWs/ps2/SLUS_210.62` was disassembled without Ghidra, using Python and Capstone, and what that approach could and couldn't do.
- It found the stage-name table by following a pointer.
- It could not find which code uses that table: tracing addresses through MIPS code needs real function analysis.

For the PS2 *Ecco: Defender* exe, a Ghidra project was used instead (`docs/ecco_dolphin_controller.md`). Findings from this exe: `docs/ps2_cut_content_findings.md`.

Rewritten for readability on 2026-11-27. Old version: `docs/archive/ps2_disassembly_notes_old_2026-11-27.md`.

---

## Contents

1. [Tools](#1-tools)
2. [ELF sections](#2-elf-sections)
3. [Capstone settings](#3-capstone-settings)
4. [Proof the decode works](#4-proof-the-decode-works)
5. [Finding the stage-name table](#5-finding-the-stage-name-table)
6. [What didn't work: finding the table's user](#6-what-didnt-work-finding-the-tables-user)
7. [String sweep](#7-string-sweep)

---

## 1. Tools

- No MIPS disassembler was installed: `objdump` lacked MIPS, and there was no `capstone` Python module.
- System pip can't install packages (externally managed Python; `sudo apt-get` needs a password).
- **Workaround:** a user-space virtual environment.

```bash
python3 -m venv <scratchpad>/venv
<scratchpad>/venv/bin/pip install capstone      # 5.0.7, no sudo needed
```

---

## 2. ELF sections

From `readelf -h` / `-S`:

| Section | Address | File offset | Size |
|---|---|---|---|
| `.text` | `0x00100000` | `0x001000` | `0x3C1258` |
| `.data` | `0x004C1500` | `0x3C2500` | `0x1AD410` |
| `.rodata` | `0x00675E00` | `0x576E00` | `0x02BCD8` |
| `.sdata` | `0x006A4E00` | `0x5A5E00` | `0x0043B8` |

- Entry point `0x00100008`.
- `readelf` says "MIPS R3000", a generic label. The flags (`5900`, `eabi64`, `mips3`) mean the Emotion Engine (R5900). The real R3000 in a PS2 is the I/O processor, which doesn't run this program.

---

## 3. Capstone settings

Three modes tested on the first 500,000 bytes of `.text` (with `skipdata` on):

| Mode | Decoded | Not recognised |
|---|---|---|
| `CS_MODE_MIPS32` | 382,258 | 117,742 (23.5 %) |
| `CS_MODE_MIPS3` | 1,028 | 498,972 (99.8 %, broken) |
| **`CS_MODE_MIPS64`** | **492,279** | **7,721 (1.5 %)** |

- **Use `CS_MODE_MIPS64 + CS_MODE_LITTLE_ENDIAN`.** It matches the `eabi64` flag.
- Over the whole `.text`, 984,214 of ~992 K words decode. The rest are R5900 multimedia (MMI) instructions that generic MIPS decoders don't know. Expected.
- **Set both `md.detail = True` and `md.skipdata = True`.** With only one, `md.disasm()` silently stops at the first unknown opcode. That first looked like total failure (2 instructions returned).

---

## 4. Proof the decode works

```
0x00100008 – 0x0010007c   raw R5900 boot code, not recognised (.byte)
                          probably cache/scratchpad setup, standard PS2 startup
0x0010007c   mthi   $zero
0x00100080   v3mulu $zero, $zero, $zero     an R5900 MMI instruction, decoded correctly
0x00100084   mtlo   $zero
0x00100090   mtc1   $zero, $f0
0x00100094   mtc1   $zero, $f1
   … through $f15
```

The 16 × `mtc1 $zero, $fN` block zeroes the FPU registers before `main()`, standard C startup.

---

## 5. Finding the stage-name table

1. The string `"Hot Pursuit"` is in `.rodata` at file offset `0x57FD70` → address `0x0067ED70`.
2. Searching the whole file for that address as a little-endian uint32 gives **exactly one hit**, at file offset `0x4CD95C` (in `.data`).
3. Walking back and forward from there in 12-byte steps, reading each step's first word as a string pointer, until one no longer resolves, recovers the whole table.

The table's contents: `docs/ps2_cut_content_findings.md` §1.

---

## 6. What didn't work: finding the table's user

**The attempt:** find the code that loads the table's base (`0x004CD8D8`) through the usual MIPS `lui` + `addiu` pair.
- Track each register's last `lui` value while scanning linearly.
- Flag any `addiu`/`ori`/`daddiu` that combines with it into the target address (adjusting for `addiu`'s sign extension).

**Result: no hits**, for either the table's base or the string's address.

**Probable reason:** "last `lui` per register in scan order" breaks with real control flow. The same register is reloaded by unrelated `lui`s elsewhere, and branches mean the last one in file order isn't necessarily the one that runs before the `addiu`. Doing it properly needs function and basic-block analysis (Ghidra or IDA). Not attempted.

---

## 7. String sweep

- A full `strings -n 5 -t x` dump (12,917 lines) was searched for developer markers (`debug`, `todo`, `unused`, `removed`, `placeholder`…), on top of targeted keyword searches.
- That's what found the developer-only strings in `docs/ps2_cut_content_findings.md` §5.
- Not exhaustive. Worth repeating with other keywords.

# PS2 Executable Disassembly Notes

Documents the disassembly toolchain setup and findings for `GAME_GDWs/ps2/SLUS_210.62`, and what did/didn't work when trying to trace data cross-references. Read alongside `ps2_cut_content_findings.md`, which documents what the string-level and struct-level analysis found.

---

## Toolchain

No MIPS-capable disassembler was preinstalled (`objdump` had no MIPS support compiled in; no `capstone` module). `python3-pip` isn't usable directly on this system (externally-managed Python, `sudo apt-get install` needs an interactive password not available in this environment). Worked around with a user-space venv:

```bash
python3 -m venv <scratchpad>/venv
<scratchpad>/venv/bin/pip install capstone   # installed 5.0.7, no sudo needed
```

## ELF Details (`readelf -h` / `-S`)

```
Class: ELF32, Machine: "MIPS R3000" (generic readelf label; actual target below)
Flags: 0x20924001 -- noreorder, 5900, eabi64, mips3
Entry point: 0x00100008
.text:   vaddr 0x00100000  file-off 0x001000  size 0x3c1258
.data:   vaddr 0x004c1500  file-off 0x3c2500  size 0x1ad410
.rodata: vaddr 0x00675e00  file-off 0x576e00  size 0x02bcd8
.sdata:  vaddr 0x006a4e00  file-off 0x5a5e00  size 0x0043b8
```

The `5900`/`eabi64`/`mips3` flags confirm this targets the PS2 Emotion Engine (R5900), not literal MIPS R3000 (that's the PS2's I/O co-processor, not the main CPU that runs this binary) — `readelf`'s machine-type string is just a generic fallback label for an ISA it doesn't specifically recognize.

## Capstone Mode Selection

Tested three MIPS modes on the first 500,000 bytes of `.text` (with `md.skipdata = True` to push through unrecognized opcodes):

| Mode | Decoded as instructions | Decoded as `.byte` (unrecognized) |
|---|---|---|
| `CS_MODE_MIPS32` | 382,258 | 117,742 (23.5%) |
| `CS_MODE_MIPS3` | 1,028 | 498,972 (99.8% — effectively broken) |
| `CS_MODE_MIPS64` | 492,279 | 7,721 (1.5%) |

**`CS_MODE_MIPS64 + CS_MODE_LITTLE_ENDIAN` is the correct mode** — matches the ELF's `eabi64` flag. Full `.text` section: 984,214 of ~992K possible instruction words decode cleanly. The remaining ~1.5% are R5900-specific multimedia (MMI) instructions no generic MIPS decoder models — expected, not a bug in the setup.

**Both `md.detail = True` and `md.skipdata = True` must be set together** — with only one, `md.disasm()` silently stops at the first unrecognized opcode instead of skipping past it, which looked like total decode failure (2 instructions returned) before this was caught.

## Entry Point Disassembly (Proof of Correct Decode)

```
0x00100008 - 0x0010007c:  raw R5900 boot instructions, unrecognized by capstone (shown as .byte)
                            -- almost certainly EE cache/scratchpad setup, standard for PS2 crt0
0x0010007c:  mthi   $zero
0x00100080:  v3mulu $zero, $zero, $zero      -- R5900 MMI instruction, decoded correctly
0x00100084:  mtlo   $zero
0x00100090:  mtc1   $zero, $f0
0x00100094:  mtc1   $zero, $f1
   ... (repeats through $f15)
```

The `mtc1 $zero, $fN` ×16 sequence is the standard FPU-register-zeroing block that runs in C runtime startup before `main()` — correctly decoded, confirming the toolchain works.

## Locating and Decoding the Mission-Name Table

Full method documented here since it doesn't fit `ps2_cut_content_findings.md`'s findings-focused format:

1. Found the string `"Hot Pursuit"` in `.rodata` at file offset `0x57fd70` → vaddr `0x0067ed70`.
2. Searched the whole file for that vaddr as a raw little-endian `uint32` (a pointer-table entry referencing it) → found exactly one hit, at file offset `0x4cd95c` (which sits inside `.data`).
3. Walked backward/forward from that offset in fixed 12-byte strides, resolving each stride's first field as a `.rodata` string pointer, until hitting an unresolvable entry (table boundary) → recovered the full table (see `ps2_cut_content_findings.md` for the decoded contents and the `flag`-field finding).

## What Didn't Work: Tracing the Table's Caller

Tried to find what function loads the table's base address (`0x004cd8d8`) via the standard MIPS `lui`/`addiu` address-formation idiom: track each register's `lui` immediate as instructions are scanned linearly, and flag any `addiu`/`ori`/`daddiu` that combines with a tracked register to reconstruct the target address (handling the sign-extension adjustment `addiu` requires when combining with `lui`).

**Result: zero hits**, both for the table's exact string address and for its base address. Likely cause: a simple linear "last `lui` per register name" model breaks down across real MIPS control flow — the same physical register gets reloaded by unrelated `lui`s at other call sites, and branches mean the "last `lui` seen in linear scan order" isn't necessarily the one that executes before the paired `addiu` at runtime. Reliably finding this would need actual function-boundary/basic-block analysis (e.g. a real CFG, or a tool like Ghidra/IDA that does this natively) rather than a flat linear scan — not attempted this pass.

## Other Strings-Sweep Method Note

A full `strings -n 5 -t x` dump (12,917 lines) was taken and grepped for dev/debug-marker patterns (`debug`, `todo`, `unused`, `removed`, `placeholder`, etc.) in addition to the targeted keyword searches used in earlier sessions — this is what surfaced the dev-only strings catalogued in `ps2_cut_content_findings.md`. Worth repeating with different keyword sets if more cut-content investigation is done later; this pass wasn't exhaustive.

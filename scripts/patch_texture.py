#!/usr/bin/env python3
"""Replace a GTEXT or GTEX texture in-place across GDWs.

Finds every GTEXT/GTEX block whose pixel payload is byte-identical to ORIGINAL
(an extracted PNG from rip_textures.py) and overwrites it with REPLACEMENT.
Matching on pixel content instead of texture ID is needed because the same
image has different IDs in different GDWs, and IDs collide across GDWs.

Same size/bpp only: nothing in the file moves, so no offsets need patching.

Usage (from project root):
    python3 scripts/patch_texture.py ORIGINAL.png REPLACEMENT.png OUT_DIR [GDW ...]
Reads GAME_GDWs/<NAME>.GDW (never written), writes OUT_DIR/<NAME>.GDW.
With no GDW names, all GDWs in GAME_GDWs/ are scanned.
"""
import struct
import sys
from pathlib import Path

from PIL import Image

PIXEL_OFFSET = 0x42  # pixel payload start inside a GTEXT block (see CLAUDE.md)


def to_gtext_pixels(path, w, h, bpp):
	"""PNG -> raw GTEXT payload: bottom-up rows, BGR / BGRA byte order."""
	img = Image.open(path)
	if img.size != (w, h):
		sys.exit(f'{path}: size {img.size} != texture size {(w, h)}')
	mode = {24: 'RGB', 32: 'RGBA'}[bpp]
	img = img.convert(mode).transpose(Image.FLIP_TOP_BOTTOM)
	return img.tobytes('raw', 'BGR' if bpp == 24 else 'BGRA')


def locate_block(data, pos, w, h, bpp):
	"""Confirm pixel data at pos belongs to a GTEXT or GTEX texture of the
	expected size; return a description, or None for a coincidental match.
	Both formats put the 18-byte TGA header directly before the pixels."""
	tga = pos - 18
	if struct.unpack_from('<HHB', data, tga + 12) != (w, h, bpp):
		return None
	blk = pos - PIXEL_OFFSET
	if data[blk:blk + 5] == b'GTEXT':
		tex_id = struct.unpack_from('<I', data, blk + 8)[0]
		return f'GTEXT id 0x{tex_id:x} @ 0x{blk:x}'
	tgan = pos - 8 - 22  # GTEX: [TGAN][size][4-byte prefix][TGA header][pixels]
	if data[tgan:tgan + 4] == b'TGAN':
		blk = data.rfind(b'GTEX', max(0, tgan - 4096), tgan)
		if blk != -1:
			tex_id = struct.unpack_from('<I', data, blk + 8)[0]
			return f'GTEX id 0x{tex_id:x} @ 0x{blk:x}'
	return None


def main():
	if len(sys.argv) < 4:
		sys.exit(__doc__)
	orig_png, new_png, out_dir = sys.argv[1:4]
	names = sys.argv[4:] or [p.stem for p in sorted(Path('GAME_GDWs').glob('*.GDW'))]
	out_dir = Path(out_dir)
	out_dir.mkdir(parents=True, exist_ok=True)

	w, h = Image.open(orig_png).size
	bpp = 32 if Image.open(orig_png).mode == 'RGBA' else 24
	old_px = to_gtext_pixels(orig_png, w, h, bpp)
	new_px = to_gtext_pixels(new_png, w, h, bpp)

	for name in names:
		data = bytearray(Path(f'GAME_GDWs/{name}.GDW').read_bytes())
		hits = []
		pos = 0
		while (pos := data.find(old_px, pos)) != -1:
			hit = locate_block(data, pos, w, h, bpp)
			if hit:
				data[pos:pos + len(new_px)] = new_px
				hits.append(hit)
			pos += 1
		if hits:
			(out_dir / f'{name}.GDW').write_bytes(data)
			print(f'{name}: patched {len(hits)} ({", ".join(hits)})')


if __name__ == '__main__':
	main()

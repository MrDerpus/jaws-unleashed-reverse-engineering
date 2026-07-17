import struct
from pathlib import Path

from PIL import Image



# =====================================
# CONFIG
# =====================================

INPUT_FILE = 'unknown_0215_1347375696x12_67108912bpp.raw'

OUTPUT_DIR = Path('./format_tests')



# =====================================
# MANUAL DIMENSIONS
# =====================================

# Since failed textures may contain
# invalid header values, we manually
# experiment with dimensions.

WIDTH = 64
HEIGHT = 64



# =====================================
# HELPERS
# =====================================

def ensure_dir(path):

	if not path.exists():

		path.mkdir(
			parents=True,
			exist_ok=True
		)



def save_image(img, name):

	out_path = OUTPUT_DIR / name

	img.save(out_path)

	print(f'Wrote: {out_path}')



# =====================================
# RGB565
# =====================================

def decode_rgb565(raw):

	pixels = []

	for i in range(0, len(raw), 2):

		if i + 1 >= len(raw):
			break

		value = struct.unpack(
			'<H',
			raw[i:i + 2]
		)[0]

		r = ((value >> 11) & 0x1F) << 3
		g = ((value >> 5) & 0x3F) << 2
		b = (value & 0x1F) << 3

		pixels.extend([r, g, b])

	img = Image.frombytes(

		'RGB',

		(WIDTH, HEIGHT),

		bytes(pixels[:WIDTH * HEIGHT * 3])

	)

	save_image(
		img,
		'test_rgb565.png'
	)



# =====================================
# ARGB1555
# =====================================

def decode_argb1555(raw):

	pixels = []

	for i in range(0, len(raw), 2):

		if i + 1 >= len(raw):
			break

		value = struct.unpack(
			'<H',
			raw[i:i + 2]
		)[0]

		a = 255 if (value & 0x8000) else 0

		r = ((value >> 10) & 0x1F) << 3
		g = ((value >> 5) & 0x1F) << 3
		b = (value & 0x1F) << 3

		pixels.extend([r, g, b, a])

	img = Image.frombytes(

		'RGBA',

		(WIDTH, HEIGHT),

		bytes(pixels[:WIDTH * HEIGHT * 4])

	)

	save_image(
		img,
		'test_argb1555.png'
	)



# =====================================
# ARGB4444
# =====================================

def decode_argb4444(raw):

	pixels = []

	for i in range(0, len(raw), 2):

		if i + 1 >= len(raw):
			break

		value = struct.unpack(
			'<H',
			raw[i:i + 2]
		)[0]

		a = ((value >> 12) & 0x0F) * 17
		r = ((value >> 8) & 0x0F) * 17
		g = ((value >> 4) & 0x0F) * 17
		b = (value & 0x0F) * 17

		pixels.extend([r, g, b, a])

	img = Image.frombytes(

		'RGBA',

		(WIDTH, HEIGHT),

		bytes(pixels[:WIDTH * HEIGHT * 4])

	)

	save_image(
		img,
		'test_argb4444.png'
	)



# =====================================
# RGB24
# =====================================

def decode_rgb24(raw):

	expected = WIDTH * HEIGHT * 3

	img = Image.frombytes(

		'RGB',

		(WIDTH, HEIGHT),

		raw[:expected]
	)

	save_image(
		img,
		'test_rgb24.png'
	)



# =====================================
# BGR24
# =====================================

def decode_bgr24(raw):

	expected = WIDTH * HEIGHT * 3

	img = Image.frombytes(

		'RGB',

		(WIDTH, HEIGHT),

		raw[:expected],

		'raw',

		'BGR'
	)

	save_image(
		img,
		'test_bgr24.png'
	)



# =====================================
# RGBA32
# =====================================

def decode_rgba32(raw):

	expected = WIDTH * HEIGHT * 4

	img = Image.frombytes(

		'RGBA',

		(WIDTH, HEIGHT),

		raw[:expected]
	)

	save_image(
		img,
		'test_rgba32.png'
	)



# =====================================
# ARGB8888
# =====================================

def decode_argb8888(raw):

	expected = WIDTH * HEIGHT * 4

	img = Image.frombytes(

		'RGBA',

		(WIDTH, HEIGHT),

		raw[:expected],

		'raw',

		'ARGB'
	)

	save_image(
		img,
		'test_argb8888.png'
	)



# =====================================
# MAIN
# =====================================

def main():

	ensure_dir(OUTPUT_DIR)

	with open(INPUT_FILE, 'rb') as f:

		raw = f.read()

	print(
		f'Loaded {len(raw)} bytes'
	)

	try:
		decode_rgb565(raw)
	except Exception as e:
		print(f'RGB565 failed: {e}')

	try:
		decode_argb1555(raw)
	except Exception as e:
		print(f'ARGB1555 failed: {e}')

	try:
		decode_argb4444(raw)
	except Exception as e:
		print(f'ARGB4444 failed: {e}')

	try:
		decode_rgb24(raw)
	except Exception as e:
		print(f'RGB24 failed: {e}')

	try:
		decode_bgr24(raw)
	except Exception as e:
		print(f'BGR24 failed: {e}')

	try:
		decode_rgba32(raw)
	except Exception as e:
		print(f'RGBA32 failed: {e}')

	try:
		decode_argb8888(raw)
	except Exception as e:
		print(f'ARGB8888 failed: {e}')

	print('\nDone.')



if __name__ == '__main__':

	main()
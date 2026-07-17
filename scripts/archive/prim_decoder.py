import struct
from pathlib import Path



# =====================================
# CONFIG
# =====================================

INPUT_FILE = 'FISH.GDW'

OUTPUT_DIR = Path('./prim_decoder')



# Runtime region near Hammerhead

START_OFFSET = 113221000
END_OFFSET   = 113240000



# =====================================
# HELPERS
# =====================================

def ensure_dir(path):

	if not path.exists():

		path.mkdir(
			parents=True,
			exist_ok=True
		)



def u32(data, offset):

	try:

		return struct.unpack(
			'<I',
			data[offset:offset + 4]
		)[0]

	except:

		return None



def u16(data, offset):

	try:

		return struct.unpack(
			'<H',
			data[offset:offset + 2]
		)[0]

	except:

		return None



def f32(data, offset):

	try:

		return struct.unpack(
			'<f',
			data[offset:offset + 4]
		)[0]

	except:

		return None



def ascii_clean(data):

	result = ''

	for b in data:

		if 32 <= b <= 126:

			result += chr(b)

		else:

			result += '.'

	return result



# =====================================
# PRIM ANALYSIS
# =====================================

def analyze_prim(full_data, offset):

	lines = []

	lines.append(
		f'\n==== PRIM @ 0x{offset:X} ===='
	)



	# ---------------------------------
	# RAW BLOCK
	# ---------------------------------

	block = full_data[
		offset:offset + 256
	]



	lines.append(
		'\n-- HEX DUMP --'
	)

	for i in range(0, len(block), 16):

		chunk = block[i:i + 16]

		hex_bytes = chunk.hex(' ')

		ascii_part = ascii_clean(chunk)

		lines.append(

			f'{offset + i:08X}  '
			f'{hex_bytes:<48}  '
			f'{ascii_part}'

		)



	# ---------------------------------
	# U32 VIEW
	# ---------------------------------

	lines.append(
		'\n-- U32 VALUES --'
	)

	for i in range(0, 128, 4):

		value = u32(block, i)

		if value is None:
			continue

		ptr_hint = ''

		if (
			0 < value < len(full_data)
		):

			ptr_hint = ' <-- POSSIBLE OFFSET'

		lines.append(

			f'+0x{i:02X}  '
			f'{value:<12} '
			f'0x{value:08X}'
			f'{ptr_hint}'

		)



	# ---------------------------------
	# FLOAT VIEW
	# ---------------------------------

	lines.append(
		'\n-- FLOAT VALUES --'
	)

	for i in range(0, 128, 4):

		value = f32(block, i)

		if value is None:
			continue

		if (
			-10000 < value < 10000
		):

			lines.append(

				f'+0x{i:02X}  '
				f'{value:.6f}'

			)



	# ---------------------------------
	# POSSIBLE VERTEX TRIPLETS
	# ---------------------------------

	lines.append(
		'\n-- POSSIBLE XYZ VERTICES --'
	)

	for i in range(0, 128, 12):

		x = f32(block, i)
		y = f32(block, i + 4)
		z = f32(block, i + 8)

		if (
			x is None or
			y is None or
			z is None
		):

			continue

		if (

			-1000 < x < 1000 and
			-1000 < y < 1000 and
			-1000 < z < 1000

		):

			lines.append(

				f'+0x{i:02X}  '
				f'XYZ: '
				f'{x:.4f}, '
				f'{y:.4f}, '
				f'{z:.4f}'

			)



	# ---------------------------------
	# POSSIBLE INDEX DATA
	# ---------------------------------

	lines.append(
		'\n-- POSSIBLE INDICES --'
	)

	for i in range(0, 64, 6):

		a = u16(block, i)
		b = u16(block, i + 2)
		c = u16(block, i + 4)

		if (
			a is None or
			b is None or
			c is None
		):

			continue

		lines.append(

			f'+0x{i:02X}  '
			f'TRI: {a}, {b}, {c}'

		)

	return lines



# =====================================
# MAIN
# =====================================

def main():

	ensure_dir(OUTPUT_DIR)

	with open(INPUT_FILE, 'rb') as f:

		full_data = f.read()

	print(
		f'Loaded {len(full_data)} bytes'
	)

	region = full_data[
		START_OFFSET:END_OFFSET
	]

	results = []

	offset = 0

	found = 0

	while True:

		pos = region.find(
			b'PRIM',
			offset
		)

		if pos == -1:
			break

		real_pos = START_OFFSET + pos

		print(
			f'Found PRIM at '
			f'0x{real_pos:X}'
		)

		lines = analyze_prim(
			full_data,
			real_pos
		)

		results.extend(lines)
		results.append('\n')

		offset = pos + 4

		found += 1



	out_path = (

		OUTPUT_DIR /

		'prim_analysis.txt'

	)

	with open(out_path, 'w') as out:

		out.write(
			'\n'.join(results)
		)

	print(
		f'\nFound {found} PRIM blocks'
	)

	print(
		f'Wrote: {out_path}'
	)



if __name__ == '__main__':

	main()
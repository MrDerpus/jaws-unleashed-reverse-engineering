import struct
from pathlib import Path



# =====================================
# CONFIG
# =====================================

INPUT_FILE = 'FISH.GDW'

OUTPUT_DIR = Path('./entity_region_dump')



# Hammerhead SkeletonModel offset

ENTITY_OFFSET = 113221972



# dump sizes

BEFORE_BYTES = 512
AFTER_BYTES = 4096



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



def f32(data, offset):

	try:

		return struct.unpack(
			'<f',
			data[offset:offset + 4]
		)[0]

	except:

		return None



def extract_ascii(chunk):

	result = ''

	for b in chunk:

		if 32 <= b <= 126:

			result += chr(b)

		else:

			result += '.'

	return result



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

	start = max(
		0,
		ENTITY_OFFSET - BEFORE_BYTES
	)

	end = min(
		len(full_data),
		ENTITY_OFFSET + AFTER_BYTES
	)

	data = full_data[start:end]



	# =================================
	# HEX DUMP
	# =================================

	lines = []

	lines.append(
		f'==== ENTITY REGION @ 0x{ENTITY_OFFSET:X} ====\n'
	)

	for i in range(0, len(data), 16):

		chunk = data[i:i + 16]

		hex_bytes = chunk.hex(' ')

		ascii_part = extract_ascii(chunk)

		lines.append(

			f'{start + i:08X}  '
			f'{hex_bytes:<48}  '
			f'{ascii_part}'

		)



	# =================================
	# POSSIBLE POINTERS
	# =================================

	lines.append(
		'\n==== POSSIBLE OFFSETS ====\n'
	)

	for i in range(0, len(data) - 4, 4):

		value = u32(data, i)

		if (
			value is not None and
			0 < value < len(full_data)
		):

			lines.append(

				f'0x{start + i:08X} -> '
				f'0x{value:X}'

			)



	# =================================
	# POSSIBLE FLOATS
	# =================================

	lines.append(
		'\n==== POSSIBLE FLOATS ====\n'
	)

	for i in range(0, len(data) - 12, 12):

		x = f32(data, i)
		y = f32(data, i + 4)
		z = f32(data, i + 8)

		if (
			x is not None and
			y is not None and
			z is not None
		):

			if (

				-10000 < x < 10000 and
				-10000 < y < 10000 and
				-10000 < z < 10000

			):

				lines.append(

					f'0x{start + i:08X}  '
					f'XYZ: '
					f'{x:.4f}, '
					f'{y:.4f}, '
					f'{z:.4f}'

				)



	# =================================
	# STRING SCAN
	# =================================

	lines.append(
		'\n==== STRINGS ====\n'
	)

	current = b''

	for b in data:

		if 32 <= b <= 126:

			current += bytes([b])

		else:

			if len(current) >= 4:

				lines.append(
					current.decode(
						errors='ignore'
					)
				)

			current = b''



	# =================================
	# WRITE OUTPUT
	# =================================

	out_path = (

		OUTPUT_DIR /

		'hammerhead_region.txt'

	)

	with open(out_path, 'w') as out:

		out.write(
			'\n'.join(lines)
		)

	print(
		f'Wrote: {out_path}'
	)



if __name__ == '__main__':

	main()
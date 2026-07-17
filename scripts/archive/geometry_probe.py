import struct
from pathlib import Path



# =====================================
# CONFIG
# =====================================

INPUT_FILE = 'FISH.GDW'

OUTPUT_DIR = Path('./geometry_probe')



# Start near interesting regions
# discovered earlier

OFFSETS = [

	47922,
	193065,
	193857,

]



# Bytes to inspect around offset

RANGE = 2048



# =====================================
# HELPERS
# =====================================

def ensure_dir(path):

	if not path.exists():

		path.mkdir(
			parents=True,
			exist_ok=True
		)



def safe_float(data, offset):

	try:

		return struct.unpack(
			'<f',
			data[offset:offset + 4]
		)[0]

	except:

		return None



def safe_u16(data, offset):

	try:

		return struct.unpack(
			'<H',
			data[offset:offset + 2]
		)[0]

	except:

		return None



# =====================================
# FLOAT ANALYSIS
# =====================================

def analyze_floats(data, base_offset):

	lines = []

	lines.append(
		'==== FLOAT ANALYSIS ====\n'
	)

	for i in range(0, len(data) - 12, 12):

		x = safe_float(data, i)
		y = safe_float(data, i + 4)
		z = safe_float(data, i + 8)

		if x is None:
			continue

		# Ignore absurd values

		if (
			-100000 < x < 100000 and
			-100000 < y < 100000 and
			-100000 < z < 100000
		):

			lines.append(

				f'0x{base_offset + i:08X}  '
				f'XYZ: '
				f'{x:.4f}, '
				f'{y:.4f}, '
				f'{z:.4f}'

			)

	return lines



# =====================================
# INDEX ANALYSIS
# =====================================

def analyze_indices(data, base_offset):

	lines = []

	lines.append(
		'\n==== INDEX ANALYSIS ====\n'
	)

	for i in range(0, len(data) - 6, 6):

		a = safe_u16(data, i)
		b = safe_u16(data, i + 2)
		c = safe_u16(data, i + 4)

		if a is None:
			continue

		# Typical index ranges

		if (
			0 <= a < 65535 and
			0 <= b < 65535 and
			0 <= c < 65535
		):

			lines.append(

				f'0x{base_offset + i:08X}  '
				f'TRI: '
				f'{a}, {b}, {c}'

			)

	return lines



# =====================================
# HEX DUMP
# =====================================

def dump_hex(data, base_offset):

	lines = []

	lines.append(
		'\n==== HEX DUMP ====\n'
	)

	for i in range(0, len(data), 16):

		chunk = data[i:i + 16]

		hex_bytes = chunk.hex(' ')

		ascii_part = ''

		for b in chunk:

			if 32 <= b <= 126:
				ascii_part += chr(b)
			else:
				ascii_part += '.'

		lines.append(

			f'{base_offset + i:08X}  '
			f'{hex_bytes:<48}  '
			f'{ascii_part}'

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

	for offset in OFFSETS:

		print(
			f'\nAnalyzing offset 0x{offset:X}'
		)

		start = max(
			0,
			offset - RANGE
		)

		end = min(
			len(full_data),
			offset + RANGE
		)

		data = full_data[start:end]

		lines = []

		lines.extend(
			analyze_floats(data, start)
		)

		lines.extend(
			analyze_indices(data, start)
		)

		lines.extend(
			dump_hex(data, start)
		)

		out_path = (

			OUTPUT_DIR /

			f'probe_0x{offset:X}.txt'

		)

		with open(out_path, 'w') as out:

			out.write(
				'\n'.join(lines)
			)

		print(
			f'Wrote: {out_path}'
		)

	print('\nDone.')



if __name__ == '__main__':

	main()
import struct
from pathlib import Path



# =====================================
# CONFIG
# =====================================

INPUT_FILE = 'FISH.GDW'

OUTPUT_DIR = Path('./gdmodel_scanner')



SEARCH_TERMS = [

	b'GDModel',
	b'GDStripModel'

]



BLOCK_SIZE = 4096



# =====================================
# HELPERS
# =====================================

def ensure_dir(path):

	if not path.exists():

		path.mkdir(
			parents=True,
			exist_ok=True
		)



def f32(data, offset):

	try:

		return struct.unpack(
			'<f',
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



def ascii_clean(data):

	result = ''

	for b in data:

		if 32 <= b <= 126:

			result += chr(b)

		else:

			result += '.'

	return result



# =====================================
# ANALYSIS
# =====================================

def analyze_region(data, offset):

	lines = []

	lines.append(
		f'\n==== REGION @ 0x{offset:X} ===='
	)



	block = data[
		offset:offset + BLOCK_SIZE
	]



	# ---------------------------------
	# HEX PREVIEW
	# ---------------------------------

	lines.append(
		'\n-- ASCII PREVIEW --'
	)

	for i in range(0, 512, 32):

		chunk = block[i:i + 32]

		ascii_part = ascii_clean(chunk)

		lines.append(

			f'+0x{i:04X}  '
			f'{ascii_part}'

		)



	# ---------------------------------
	# FLOAT SCAN
	# ---------------------------------

	lines.append(
		'\n-- POSSIBLE XYZ VERTICES --'
	)

	found_xyz = 0

	for i in range(0, len(block) - 12, 4):

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

			-10000 < x < 10000 and
			-10000 < y < 10000 and
			-10000 < z < 10000

		):

			# reject obvious garbage

			if (
				abs(x) < 0.00001 and
				abs(y) < 0.00001 and
				abs(z) < 0.00001
			):

				continue

			lines.append(

				f'+0x{i:04X}  '
				f'XYZ: '
				f'{x:.4f}, '
				f'{y:.4f}, '
				f'{z:.4f}'

			)

			found_xyz += 1

			if found_xyz > 64:
				break



	# ---------------------------------
	# UV SCAN
	# ---------------------------------

	lines.append(
		'\n-- POSSIBLE UVS --'
	)

	found_uv = 0

	for i in range(0, len(block) - 8, 4):

		u = f32(block, i)
		v = f32(block, i + 4)

		if (
			u is None or
			v is None
		):

			continue

		if (

			-2.0 <= u <= 2.0 and
			-2.0 <= v <= 2.0

		):

			lines.append(

				f'+0x{i:04X}  '
				f'UV: '
				f'{u:.4f}, '
				f'{v:.4f}'

			)

			found_uv += 1

			if found_uv > 64:
				break



	# ---------------------------------
	# STRIP SCAN
	# ---------------------------------

	lines.append(
		'\n-- POSSIBLE STRIPS --'
	)

	for i in range(0, 256, 2):

		values = []

		valid = True

		for j in range(0, 12, 2):

			v = u16(block, i + j)

			if v is None:

				valid = False
				break

			values.append(v)

		if valid:

			lines.append(

				f'+0x{i:04X}  '
				f'{values}'

			)

	return lines



# =====================================
# MAIN
# =====================================

def main():

	ensure_dir(OUTPUT_DIR)

	with open(INPUT_FILE, 'rb') as f:

		data = f.read()

	results = []

	for term in SEARCH_TERMS:

		offset = 0

		while True:

			pos = data.find(
				term,
				offset
			)

			if pos == -1:
				break

			print(
				f'Found {term.decode()} '
				f'at 0x{pos:X}'
			)

			start = max(
				0,
				pos - 512
			)

			lines = analyze_region(
				data,
				start
			)

			results.extend(lines)
			results.append('\n')

			offset = pos + 1



	out_path = (

		OUTPUT_DIR /

		'gdmodel_analysis.txt'

	)

	with open(out_path, 'w') as out:

		out.write(
			'\n'.join(results)
		)

	print(
		f'Wrote: {out_path}'
	)



if __name__ == '__main__':

	main()
import struct
from pathlib import Path



# =====================================
# CONFIG
# =====================================

INPUT_FILE = 'FISH.GDW'

OUTPUT_DIR = Path('./mesh_collection_hunter')

SEARCH_TERMS = [

	b'mcMeshCollection',
	b'm_3dModelID'

]



SCAN_SIZE = 32768



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



def ascii_ratio(block):

	printable = 0

	for b in block:

		if 32 <= b <= 126:

			printable += 1

	return printable / len(block)



# =====================================
# VERTEX DETECTOR
# =====================================

def detect_vertex_clusters(block):

	results = []

	run_start = None
	run_count = 0

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

			# reject near-zero garbage

			if (
				abs(x) < 0.00001 and
				abs(y) < 0.00001 and
				abs(z) < 0.00001
			):

				run_start = None
				run_count = 0
				continue

			if run_start is None:

				run_start = i

			run_count += 1

		else:

			if run_count >= 16:

				results.append(

					(run_start, run_count)

				)

			run_start = None
			run_count = 0

	return results



# =====================================
# STRIP DETECTOR
# =====================================

def detect_strip_regions(block):

	results = []

	for i in range(0, len(block) - 128, 2):

		valid = 0

		for j in range(0, 64, 2):

			v = u16(block, i + j)

			if v is None:
				continue

			if 0 <= v <= 10000:

				valid += 1

		if valid >= 24:

			results.append(i)

	return results



# =====================================
# ANALYSIS
# =====================================

def analyze_region(data, offset):

	lines = []

	lines.append(
		f'\n==== REGION @ 0x{offset:X} ===='
	)

	block = data[
		offset:offset + SCAN_SIZE
	]



	# ---------------------------------
	# ASCII DENSITY
	# ---------------------------------

	ratio = ascii_ratio(block)

	lines.append(
		f'\nASCII Ratio: {ratio:.3f}'
	)

	if ratio < 0.20:

		lines.append(
			'LIKELY BINARY REGION'
		)



	# ---------------------------------
	# VERTEX CLUSTERS
	# ---------------------------------

	lines.append(
		'\n-- VERTEX CLUSTERS --'
	)

	clusters = detect_vertex_clusters(block)

	for start, count in clusters[:32]:

		lines.append(

			f'0x{offset + start:X}  '
			f'count={count}'

		)



	# ---------------------------------
	# STRIP REGIONS
	# ---------------------------------

	lines.append(
		'\n-- STRIP REGIONS --'
	)

	strips = detect_strip_regions(block)

	for s in strips[:32]:

		lines.append(

			f'0x{offset + s:X}'

		)



	# ---------------------------------
	# FLOAT PREVIEW
	# ---------------------------------

	lines.append(
		'\n-- FLOAT PREVIEW --'
	)

	found = 0

	for i in range(0, len(block) - 12, 12):

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

				f'0x{offset + i:X}  '
				f'{x:.4f}, '
				f'{y:.4f}, '
				f'{z:.4f}'

			)

			found += 1

			if found >= 64:
				break

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
				pos - 4096
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

		'mesh_collection_analysis.txt'

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
import struct
from pathlib import Path
from collections import Counter



# =====================================
# CONFIG
# =====================================

INPUT_FILE = 'FISH.GDW'

OUTPUT_DIR = Path('./packet_layout_finder')



# suspicious region discovered earlier

PACKET_OFFSET = 0x6FB887C



# analyze one full packet

PACKET_SIZE = 0x800



# analysis chunk size

CHUNK_SIZE = 32



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



def s16(data, offset):

	try:

		return struct.unpack(
			'<h',
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



def entropy(block):

	if not block:
		return 0

	counter = Counter(block)

	total = len(block)

	ent = 0

	for count in counter.values():

		p = count / total

		ent -= p * (p.bit_length() if hasattr(p, 'bit_length') else 0)

	return ent



# =====================================
# ANALYSIS
# =====================================

def analyze_packet(packet):

	lines = []

	lines.append(
		f'Packet Size: {len(packet)} bytes\n'
	)



	# ---------------------------------
	# CHUNK ANALYSIS
	# ---------------------------------

	for chunk_offset in range(
		0,
		len(packet),
		CHUNK_SIZE
	):

		chunk = packet[
			chunk_offset:
			chunk_offset + CHUNK_SIZE
		]



		# ASCII ratio

		ascii_r = ascii_ratio(chunk)



		# zero count

		zero_count = chunk.count(0)



		# float count

		float_hits = 0

		for i in range(0, len(chunk) - 4, 4):

			v = f32(chunk, i)

			if v is None:
				continue

			if -10000 < v < 10000:

				float_hits += 1



		# int16 count

		int_hits = 0

		for i in range(0, len(chunk) - 2, 2):

			v = s16(chunk, i)

			if v is None:
				continue

			if -32768 <= v <= 32767:

				int_hits += 1



		# hex preview

		hex_preview = chunk[:16].hex(' ')



		lines.append(

			f'0x{chunk_offset:04X} | '
			f'ASCII={ascii_r:.2f} | '
			f'ZERO={zero_count:02d} | '
			f'F32={float_hits:02d} | '
			f'S16={int_hits:02d} | '
			f'{hex_preview}'

		)



	# ---------------------------------
	# FLOAT REGION DETECTION
	# ---------------------------------

	lines.append(
		'\n==== POSSIBLE FLOAT REGIONS ===='
	)

	for i in range(0, len(packet) - 12, 4):

		x = f32(packet, i)
		y = f32(packet, i + 4)
		z = f32(packet, i + 8)

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

			lines.append(

				f'0x{i:04X}  '
				f'{x:.4f}, '
				f'{y:.4f}, '
				f'{z:.4f}'

			)



	# ---------------------------------
	# INT16 REGION DETECTION
	# ---------------------------------

	lines.append(
		'\n==== POSSIBLE INT16 REGIONS ===='
	)

	for i in range(0, len(packet) - 12, 2):

		values = []

		valid = True

		for j in range(0, 12, 2):

			v = s16(packet, i + j)

			if v is None:

				valid = False
				break

			values.append(v)

		if valid:

			lines.append(

				f'0x{i:04X}  '
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

	packet = data[
		PACKET_OFFSET:
		PACKET_OFFSET + PACKET_SIZE
	]

	print(
		f'Loaded packet @ '
		f'0x{PACKET_OFFSET:X}'
	)

	lines = analyze_packet(packet)



	out_path = (

		OUTPUT_DIR /

		'packet_layout.txt'

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
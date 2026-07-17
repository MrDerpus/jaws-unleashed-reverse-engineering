import struct
from pathlib import Path



# =====================================
# CONFIG
# =====================================

INPUT_FILE = '../../GAME_GDWs/BEACHPST.GDW'

OUTPUT_DIR = Path('./failed_texture_regions')



# GTEXT OFFSET OF FAILED TEXTURE
# Replace with actual offset

GTEXT_OFFSET = 0x4323F38



# How much surrounding data to dump

BEFORE_BYTES = 4096
AFTER_BYTES = 16384



# =====================================
# HELPERS
# =====================================

def ensure_dir(path):

	if not path.exists():

		path.mkdir(
			parents=True,
			exist_ok=True
		)



def read_u32(data, offset):

	return struct.unpack(
		'<I',
		data[offset:offset + 4]
	)[0]



# =====================================
# MAIN
# =====================================

def main():

	ensure_dir(OUTPUT_DIR)

	with open(INPUT_FILE, 'rb') as f:

		data = f.read()

	print(
		f'Loaded {len(data)} bytes'
	)

	print(
		f'GTEXT offset: 0x{GTEXT_OFFSET:X}'
	)

	start = max(
		0,
		GTEXT_OFFSET - BEFORE_BYTES
	)

	end = min(
		len(data),
		GTEXT_OFFSET + AFTER_BYTES
	)

	region = data[start:end]



	# =================================
	# RAW DUMP
	# =================================

	raw_path = (

		OUTPUT_DIR /

		f'region_0x{GTEXT_OFFSET:X}.bin'

	)

	with open(raw_path, 'wb') as out:

		out.write(region)

	print(
		f'Wrote binary dump: {raw_path}'
	)



	# =================================
	# HEX DUMP
	# =================================

	hex_path = (

		OUTPUT_DIR /

		f'region_0x{GTEXT_OFFSET:X}.txt'

	)

	lines = []

	for i in range(0, len(region), 16):

		chunk = region[i:i + 16]

		hex_bytes = chunk.hex(' ')

		ascii_part = ''

		for b in chunk:

			if 32 <= b <= 126:
				ascii_part += chr(b)
			else:
				ascii_part += '.'

		lines.append(

			f'{start + i:08X}  '
			f'{hex_bytes:<48}  '
			f'{ascii_part}'

		)

	with open(hex_path, 'w') as out:

		out.write(
			'\n'.join(lines)
		)

	print(
		f'Wrote hex dump: {hex_path}'
	)



	# =================================
	# PALETTE HUNT
	# =================================

	print('\nSearching for possible palettes...\n')

	for i in range(0, len(region) - 1024, 4):

		block = region[i:i + 1024]

		unique_bytes = len(set(block))

		# crude heuristic:
		# palettes usually have
		# moderate diversity

		if 32 < unique_bytes < 220:

			print(
				f'Possible palette region near '
				f'0x{start + i:X} '
				f'(unique bytes: {unique_bytes})'
			)

	print('\nDone.')



if __name__ == '__main__':

	main()
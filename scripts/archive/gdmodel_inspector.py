import struct
from pathlib import Path



# =====================================
# CONFIG
# =====================================

INPUT_FILE = 'FISH.GDW'

OUTPUT_DIR = Path('./gdmodel_inspector')



# GDModel cluster discovered earlier

OFFSETS = [

	237960,
	237992,
	238024,
	238056,

]



# bytes per suspected object

ENTRY_SIZE = 32



# bytes to dump around object

SURROUNDING_BYTES = 128



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



def i32(data, offset):

	try:

		return struct.unpack(
			'<i',
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



# =====================================
# FIELD ANALYSIS
# =====================================

def analyze_entry(full_data, offset):

	lines = []

	lines.append(
		f'==== ENTRY @ 0x{offset:X} ====\n'
	)

	start = max(
		0,
		offset - SURROUNDING_BYTES
	)

	end = min(
		len(full_data),
		offset + ENTRY_SIZE + SURROUNDING_BYTES
	)

	data = full_data[start:end]



	# ---------------------------------
	# HEX DUMP
	# ---------------------------------

	lines.append(
		'---- HEX DUMP ----\n'
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

			f'{start + i:08X}  '
			f'{hex_bytes:<48}  '
			f'{ascii_part}'

		)



	# ---------------------------------
	# STRUCT VIEW
	# ---------------------------------

	lines.append(
		'\n---- STRUCT ANALYSIS ----\n'
	)

	entry_data = full_data[offset:offset + ENTRY_SIZE]

	for i in range(0, ENTRY_SIZE, 4):

		raw = entry_data[i:i + 4]

		val_u32 = u32(entry_data, i)
		val_i32 = i32(entry_data, i)
		val_f32 = f32(entry_data, i)

		ptr_hint = ''

		# check if value looks
		# like valid file offset

		if (
			val_u32 is not None and
			0 < val_u32 < len(full_data)
		):

			ptr_hint = ' <-- POSSIBLE OFFSET'

		lines.append(

			f'+0x{i:02X} | '
			f'HEX: {raw.hex()} | '
			f'U32: {val_u32:<12} | '
			f'I32: {val_i32:<12} | '
			f'F32: {val_f32:<15.6f}'
			f'{ptr_hint}'

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

	all_lines = []

	for offset in OFFSETS:

		print(
			f'Analyzing 0x{offset:X}'
		)

		lines = analyze_entry(
			full_data,
			offset
		)

		all_lines.extend(lines)
		all_lines.append('\n')



	out_path = (

		OUTPUT_DIR /

		'gdmodel_analysis.txt'

	)

	with open(out_path, 'w') as out:

		out.write(
			'\n'.join(all_lines)
		)

	print(
		f'\nWrote: {out_path}'
	)



if __name__ == '__main__':

	main()
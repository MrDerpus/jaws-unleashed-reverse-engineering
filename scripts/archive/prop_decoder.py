import struct
from pathlib import Path



# =====================================
# CONFIG
# =====================================

INPUT_FILE = 'FISH.GDW'

OUTPUT_DIR = Path('./prop_decoder_region')



# Runtime entity region discovered earlier

START_OFFSET = 113221000
END_OFFSET   = 113226000



# Maximum PROP blocks to parse

MAX_PROPS = 64



# Maximum payload bytes to display

MAX_PAYLOAD_DUMP = 64



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



def ascii_clean(data):

	result = ''

	for b in data:

		if 32 <= b <= 126:

			result += chr(b)

		else:

			result += '.'

	return result



# =====================================
# PROP PARSER
# =====================================

def parse_prop(full_data, offset):

	lines = []

	lines.append(
		f'\n==== PROP @ 0x{offset:X} ===='
	)

	try:

		# PROP
		# [4 bytes size]
		# [4 bytes property id]
		# [payload]

		size = u32(full_data, offset + 4)

		prop_id = u32(full_data, offset + 8)

		lines.append(
			f'Size       : {size}'
		)

		lines.append(
			f'PropertyID : 0x{prop_id:08X}'
		)



		# sanity checks

		if size is None:

			lines.append(
				'Invalid size'
			)

			return lines

		if size > 4096:

			lines.append(
				'Skipping huge payload'
			)

			return lines

		if size < 0:

			lines.append(
				'Invalid negative payload'
			)

			return lines



		payload_start = offset + 12
		payload_end = payload_start + size

		payload = full_data[
			payload_start:payload_end
		]

		lines.append(
			f'PayloadSize: {len(payload)}'
		)



		# ---------------------------------
		# HEX VIEW
		# ---------------------------------

		lines.append(
			'\n-- HEX VIEW --'
		)

		limited_payload = payload[
			:MAX_PAYLOAD_DUMP
		]

		for i in range(
			0,
			len(limited_payload),
			16
		):

			chunk = limited_payload[
				i:i + 16
			]

			hex_bytes = chunk.hex(' ')

			ascii_part = ascii_clean(chunk)

			lines.append(

				f'{payload_start + i:08X}  '
				f'{hex_bytes:<48}  '
				f'{ascii_part}'

			)



		# ---------------------------------
		# U32 VIEW
		# ---------------------------------

		lines.append(
			'\n-- U32 VIEW --'
		)

		for i in range(
			0,
			min(len(payload), 32),
			4
		):

			value = u32(payload, i)

			if value is None:
				continue

			ptr_hint = ''

			if (
				0 < value < len(full_data)
			):

				ptr_hint = ' <-- POSSIBLE OFFSET'

			lines.append(

				f'+0x{i:02X}  '
				f'U32: {value:<12} '
				f'HEX: 0x{value:08X}'
				f'{ptr_hint}'

			)



		# ---------------------------------
		# FLOAT VIEW
		# ---------------------------------

		lines.append(
			'\n-- FLOAT VIEW --'
		)

		for i in range(
			0,
			min(len(payload), 32),
			4
		):

			value = f32(payload, i)

			if value is None:
				continue

			if (
				-10000 < value < 10000
			):

				lines.append(

					f'+0x{i:02X}  '
					f'FLOAT: {value:.6f}'

				)



	except Exception as e:

		lines.append(
			f'ERROR: {e}'
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

	print(
		f'Scanning region: '
		f'0x{START_OFFSET:X} '
		f'-> '
		f'0x{END_OFFSET:X}'
	)

	region = full_data[
		START_OFFSET:END_OFFSET
	]

	prop_magic = b'PROP'

	results = []

	offset = 0

	found = 0

	while True:

		pos = region.find(
			prop_magic,
			offset
		)

		if pos == -1:
			break

		real_pos = START_OFFSET + pos

		found += 1

		print(
			f'Found PROP at '
			f'0x{real_pos:X}'
		)

		lines = parse_prop(
			full_data,
			real_pos
		)

		results.extend(lines)
		results.append('\n')

		offset = pos + 4

		if found >= MAX_PROPS:

			print(
				'Reached MAX_PROPS limit'
			)

			break



	out_path = (

		OUTPUT_DIR /

		'prop_analysis_region.txt'

	)

	with open(out_path, 'w') as out:

		out.write(
			'\n'.join(results)
		)

	print(
		f'\nFound {found} PROP blocks'
	)

	print(
		f'Wrote: {out_path}'
	)



if __name__ == '__main__':

	main()
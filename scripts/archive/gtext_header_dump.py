import struct
from pathlib import Path



INPUT_FILE = '../GAME_GDWs/FISH.GDW'

OUTPUT_FILE = '../gtext_report.txt'



def read_u32(data, offset):

	if offset + 4 > len(data):
		return None

	return struct.unpack(
		'<I',
		data[offset:offset + 4]
	)[0]



def main():

	with open(INPUT_FILE, 'rb') as f:

		data = f.read()

	print(
		f'Loaded {len(data)} bytes'
	)

	offset = 0
	texture_index = 0

	lines = []

	while True:

		gtext_offset = data.find(
			b'GTEXT',
			offset
		)

		if gtext_offset == -1:
			break

		lines.append(
			'=' * 60
		)

		lines.append(
			f'TEXTURE #{texture_index}'
		)

		lines.append(
			f'GTEXT Offset: 0x{gtext_offset:X}'
		)

		try:

			width = read_u32(
				data,
				gtext_offset + 0x18
			)

			height = read_u32(
				data,
				gtext_offset + 0x1C
			)

			bpp = read_u32(
				data,
				gtext_offset + 0x20
			)

			lines.append(
				f'Width : {width}'
			)

			lines.append(
				f'Height: {height}'
			)

			lines.append(
				f'BPP   : {bpp}'
			)

			# Dump nearby unknown fields
			lines.append('\nUnknown Fields:')

			for rel in range(0x00, 0x40, 4):

				value = read_u32(
					data,
					gtext_offset + rel
				)

				lines.append(
					f'  +0x{rel:02X} = '
					f'0x{value:08X}'
				)

			# Nearby tags
			lines.append('\nNearby ASCII:')

			ascii_region = data[
				gtext_offset:
				gtext_offset + 128
			]

			filtered = ''

			for b in ascii_region:

				if 32 <= b <= 126:
					filtered += chr(b)
				else:
					filtered += '.'

			lines.append(filtered)

			# Raw bytes
			lines.append('\nRaw Header Bytes:')

			raw = data[
				gtext_offset:
				gtext_offset + 96
			]

			hex_dump = raw.hex(' ')

			lines.append(hex_dump)

		except Exception as e:

			lines.append(
				f'ERROR: {e}'
			)

		lines.append('\n')

		texture_index += 1

		offset = gtext_offset + 1

	with open(OUTPUT_FILE, 'w') as out:

		out.write(
			'\n'.join(lines)
		)

	print(
		f'Wrote {OUTPUT_FILE}'
	)

	print(
		f'Dumped {texture_index} GTEXT headers.'
	)



if __name__ == '__main__':

	main()
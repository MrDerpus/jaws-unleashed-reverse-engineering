import struct
from pathlib import Path

from PIL import Image



INPUT_FILE = '../GAME_GDWs/OPEN_NE.GDW'

OUTPUT_DIR = Path('../textures')



HEADER_SIZE = 0x54



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



def save_texture(

	raw,
	width,
	height,
	bpp,
	texture_index,
	gtext_offset
):

	# =====================================
	# RGBA32
	# =====================================

	if bpp == 32:

		mode = 'RGBA'
		expected_size = width * height * 4

		if len(raw) < expected_size:

			print(
				f'  [!] RGBA payload too small'
			)

			return False

		raw = raw[:expected_size]

		img = Image.frombytes(

			'RGBA',

			(width, height),

			raw
		)

		filename = (
			f'texture_{texture_index:04}_'
			f'{width}x{height}_'
			f'rgba32.png'
		)

		out_path = OUTPUT_DIR / filename

		img.save(out_path)

		return True


	# =====================================
	# RGB24
	# =====================================

	elif bpp == 24:

		mode = 'RGB'
		expected_size = width * height * 3

		if len(raw) < expected_size:

			print(
				f'  [!] RGB payload too small'
			)

			return False

		raw = raw[:expected_size]

		img = Image.frombytes(

			'RGB',

			(width, height),

			raw
		)

		filename = (
			f'texture_{texture_index:04}_'
			f'{width}x{height}_'
			f'rgb24.png'
		)

		out_path = OUTPUT_DIR / filename

		img.save(out_path)

		return True


	# =====================================
	# UNKNOWN FORMAT
	# =====================================

	else:

		print(
			f'  [!] Unsupported BPP: {bpp}'
		)

		raw_name = (
			f'unknown_{texture_index:04}_'
			f'{width}x{height}_'
			f'{bpp}bpp.raw'
		)

		raw_path = OUTPUT_DIR / raw_name

		with open(raw_path, 'wb') as out:

			out.write(raw)

		print(
			f'  Wrote RAW: {raw_name}'
		)

		return False



def main():

	ensure_dir(OUTPUT_DIR)

	with open(INPUT_FILE, 'rb') as f:

		data = f.read()

	print(
		f'Loaded {len(data)} bytes'
	)

	offset = 0
	texture_index = 0
	successful = 0

	while True:

		gtext_offset = data.find(
			b'GTEXT',
			offset
		)

		if gtext_offset == -1:
			break

		print('\n' + '=' * 60)

		print(
			f'GTEXT @ 0x{gtext_offset:X}'
		)

		try:

			# =================================
			# HEADER FIELDS
			# =================================

			block_size = read_u32(
				data,
				gtext_offset + 0x04
			)

			texture_id = read_u32(
				data,
				gtext_offset + 0x08
			)

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

			print(
				f'  Texture ID : {texture_id}'
			)

			print(
				f'  Dimensions : '
				f'{width}x{height}'
			)

			print(
				f'  BPP        : {bpp}'
			)

			print(
				f'  Block Size : '
				f'0x{block_size:X}'
			)

			# =================================
			# PAYLOAD
			# =================================

			payload_offset = (
				gtext_offset +
				HEADER_SIZE
			)

			payload_size = (
				block_size -
				HEADER_SIZE
			)

			print(
				f'  Payload Offset: '
				f'0x{payload_offset:X}'
			)

			print(
				f'  Payload Size  : '
				f'0x{payload_size:X}'
			)

			if payload_size <= 0:

				print(
					'  [!] Invalid payload size'
				)

				offset = gtext_offset + 1
				continue

			raw = data[
				payload_offset:
				payload_offset + payload_size
			]

			ok = save_texture(

				raw,
				width,
				height,
				bpp,
				texture_index,
				gtext_offset
			)

			if ok:

				successful += 1

			texture_index += 1

		except Exception as e:

			print(
				f'  ERROR: {e}'
			)

		offset = (
			gtext_offset +
			block_size
		)

	print('\n' + '=' * 60)

	print(
		f'Successfully extracted '
		f'{successful} textures.'
	)

	print(
		f'Processed '
		f'{texture_index} texture entries.'
	)



if __name__ == '__main__':

	main()
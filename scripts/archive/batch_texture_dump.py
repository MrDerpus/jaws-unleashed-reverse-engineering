import os
import struct
from pathlib import Path

from PIL import Image



INPUT_FILE = '../GAME_GDWs/OPEN_NE.GDW'

OUTPUT_DIR = Path('../textures')



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



def main():

	ensure_dir(OUTPUT_DIR)

	with open(INPUT_FILE, 'rb') as f:
	
		data = f.read()

	print(f'File size: {len(data)} bytes')

	offset = 0
	texture_index = 0

	while True:

		gtext_offset = data.find(
			b'GTEXT',
			offset
		)

		if gtext_offset == -1:
			break

		print(
			f'\nGTEXT found at '
			f'0x{gtext_offset:X}'
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

			print(f'  Width : {width}')
			print(f'  Height: {height}')
			print(f'  BPP   : {bpp}')

			tgan_offset = data.find(

				b'TGAN0',

				gtext_offset,
				gtext_offset + 0x80
			)

			if tgan_offset == -1:

				print(
					'  No TGAN0 found nearby'
				)

				offset = gtext_offset + 1
				continue

			print(
				f'  TGAN0 at 0x{tgan_offset:X}'
			)

			# Experimental payload offset
			payload_offset = (
				tgan_offset +
				0x20 +
				44
			)

			# ==========================
			# RGBA32 TEXTURES
			# ==========================

			if bpp == 32:

				payload_size = (
					width *
					height *
					4
				)

				raw = data[
					payload_offset:
					payload_offset + payload_size
				]

				raw_path = (
					OUTPUT_DIR /
					f'texture_{texture_index:04}_{width}x{height}.raw'
				)

				with open(raw_path, 'wb') as out:
				
					out.write(raw)

				print(
					f'  Wrote RAW: '
					f'{raw_path.name}'
				)

				img = Image.frombytes(

					'RGBA',

					(width, height),

					raw
				)

				png_path = raw_path.with_suffix('.png')

				img.save(png_path)

				print(
					f'  Wrote PNG: '
					f'{png_path.name}'
				)

				texture_index += 1


			# ==========================
			# RGB24 TEXTURES
			# ==========================

			elif bpp == 24:

				payload_size = (
					width *
					height *
					3
				)

				raw = data[
					payload_offset:
					payload_offset + payload_size
				]

				raw_path = (
					OUTPUT_DIR /
					f'texture_{texture_index:04}_{width}x{height}_rgb24.raw'
				)

				with open(raw_path, 'wb') as out:
				
					out.write(raw)

				print(
					f'  Wrote RAW: '
					f'{raw_path.name}'
				)

				img = Image.frombytes(

					'RGB',

					(width, height),

					raw
				)

				png_path = raw_path.with_suffix('.png')

				img.save(png_path)

				print(
					f'  Wrote PNG: '
					f'{png_path.name}'
				)

				texture_index += 1


			# ==========================
			# UNKNOWN FORMATS
			# ==========================

			else:

				print(
					'  Unsupported format detected'
				)

				print(
					f'    Offset : '
					f'0x{gtext_offset:X}'
				)

				print(
					f'    Width  : {width}'
				)

				print(
					f'    Height : {height}'
				)

				print(
					f'    BPP    : {bpp}'
				)

				header_dump = data[
					gtext_offset:
					gtext_offset + 96
				]

				print(
					'    Header : '
					f'{header_dump.hex(" ")}'
				)

		except Exception as e:

			print(f'  ERROR: {e}')

		offset = gtext_offset + 1

	print('\nDone.')

	print(
		f'Extracted '
		f'{texture_index} textures.'
	)



if __name__ == '__main__':

	main()
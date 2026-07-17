import struct
from pathlib import Path



INPUT_FILE = '../GAME_GDWs/FISH.GDW'

OUTPUT_DIR = Path('../embedded_files')



SIGNATURES = {

	b'\x89PNG': 'png',

	b'DDS ': 'dds',

	b'BM': 'bmp'
}



PNG_END = b'IEND\xae\x42\x60\x82'



def ensure_dir(path):

	if not path.exists():

		path.mkdir(
			parents=True,
			exist_ok=True
		)



def carve_png(data, start_offset):

	end = data.find(
		PNG_END,
		start_offset
	)

	if end == -1:
		return None

	return data[
		start_offset:
		end + len(PNG_END)
	]



def carve_dds(data, start_offset):

	if start_offset + 128 > len(data):
		return None

	try:

		height = struct.unpack(
			'<I',
			data[start_offset + 12:start_offset + 16]
		)[0]

		width = struct.unpack(
			'<I',
			data[start_offset + 16:start_offset + 20]
		)[0]

		mipmap_count = struct.unpack(
			'<I',
			data[start_offset + 28:start_offset + 32]
		)[0]

		print(
			f'    DDS: {width}x{height} '
			f'mips={mipmap_count}'
		)

	except:

		pass

	# Temporary fixed-size carve
	# We improve this later
	size = 1024 * 1024

	return data[
		start_offset:
		start_offset + size
	]



def carve_bmp(data, start_offset):

	if start_offset + 6 > len(data):
		return None

	try:

		file_size = struct.unpack(
			'<I',
			data[start_offset + 2:start_offset + 6]
		)[0]

		if file_size <= 0:
			return None

		return data[
			start_offset:
			start_offset + file_size
		]

	except:

		return None



def main():

	with open(INPUT_FILE, 'rb') as f:

		data = f.read()

	print(
		f'Loaded {len(data)} bytes'
	)

	ensure_dir(OUTPUT_DIR)

	for signature, extension in SIGNATURES.items():

		print(f'\nSearching for {extension.upper()}')

		subdir = OUTPUT_DIR / extension

		ensure_dir(subdir)

		offset = 0
		file_index = 0

		while True:

			found = data.find(
				signature,
				offset
			)

			if found == -1:
				break

			print(
				f'  Found at 0x{found:X}'
			)

			blob = None

			if extension == 'png':

				blob = carve_png(
					data,
					found
				)

			elif extension == 'dds':

				blob = carve_dds(
					data,
					found
				)

			elif extension == 'bmp':

				blob = carve_bmp(
					data,
					found
				)

			if blob:

				out_path = (
					subdir /
					f'{extension}_{file_index:04}.{extension}'
				)

				with open(out_path, 'wb') as out:

					out.write(blob)

				print(
					f'    Wrote: '
					f'{out_path.name}'
				)

				file_index += 1

			offset = found + 1

	print('\nDone.')




if __name__ == '__main__':

	main()
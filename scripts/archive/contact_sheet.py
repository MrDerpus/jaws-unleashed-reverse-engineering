from pathlib import Path

from PIL import Image
from PIL import ImageDraw



INPUT_DIR = Path('../textures')

OUTPUT_FILE = 'contact_sheet.png'

THUMB_SIZE = 128
PADDING = 8
COLUMNS = 6



def main():

	files = sorted(
	
		INPUT_DIR.glob('*.png')
	)

	if not files:

		print('No PNG files found.')
		return

	print(
		f'Found {len(files)} textures.'
	)

	rows = (
		(len(files) + COLUMNS - 1)
		// COLUMNS
	)

	sheet_width = (
		COLUMNS *
		(THUMB_SIZE + PADDING)
		+ PADDING
	)

	sheet_height = (
		rows *
		(THUMB_SIZE + PADDING)
		+ PADDING
	)

	sheet = Image.new(

		'RGBA',

		(sheet_width, sheet_height),

		(30, 30, 30, 255)
	)

	draw = ImageDraw.Draw(sheet)

	for index, path in enumerate(files):

		try:

			img = Image.open(path).convert('RGBA')

			img.thumbnail(
				(THUMB_SIZE, THUMB_SIZE)
			)

			x = (
				index % COLUMNS
			) * (
				THUMB_SIZE + PADDING
			) + PADDING

			y = (
				index // COLUMNS
			) * (
				THUMB_SIZE + PADDING
			) + PADDING

			sheet.paste(
				img,
				(x, y)
			)

			draw.text(

				(x, y + THUMB_SIZE - 12),

				path.stem,

				fill=(255, 255, 255, 255)
			)

		except Exception as e:

			print(
				f'Failed loading '
				f'{path.name}: {e}'
			)

	sheet.save(OUTPUT_FILE)

	print(
		f'Wrote {OUTPUT_FILE}'
	)



if __name__ == '__main__':

	main()
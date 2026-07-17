import struct
from pathlib import Path



# =====================================
# CONFIG
# =====================================

INPUT_FILE = 'FISH.GDW'

OUTPUT_DIR = Path('./vertex_stride_tester')



# VERY promising region discovered earlier

START_OFFSET = 0x6FB887C



# amount to scan

SCAN_SIZE = 0x4000



# candidate strides

STRIDES = [

	12,
	16,
	20,
	24,
	28,
	32

]



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
			'<h',
			data[offset:offset + 4]
		)[0]

	except:

		return None



def valid_vertex(x, y, z):

	if (
		x is None or
		y is None or
		z is None
	):

		return False

	if (
		abs(x) > 10000 or
		abs(y) > 10000 or
		abs(z) > 10000
	):

		return False

	# reject NaN

	if (
		x != x or
		y != y or
		z != z
	):

		return False

	return True



# =====================================
# OBJ EXPORT
# =====================================

def export_obj(vertices, out_path):

	with open(out_path, 'w') as f:

		f.write(
			'# Generated OBJ\n'
		)

		for v in vertices:

			x, y, z = v

			f.write(

				f'v {x} {y} {z}\n'

			)

	print(
		f'Wrote: {out_path}'
	)



# =====================================
# STRIDE TESTING
# =====================================

def test_stride(block, stride):

	vertices = []

	for i in range(
		0,
		len(block) - stride,
		stride
	):

		x = f32(block, i)
		y = f32(block, i + 4)
		z = f32(block, i + 8)

		if not valid_vertex(x, y, z):
			continue



		# reject near-zero spam

		if (
			abs(x) < 0.00001 and
			abs(y) < 0.00001 and
			abs(z) < 0.00001
		):

			continue

		vertices.append(

			(x, y, z)

		)

	return vertices



# =====================================
# MAIN
# =====================================

def main():

	ensure_dir(OUTPUT_DIR)

	with open(INPUT_FILE, 'rb') as f:

		data = f.read()

	block = data[
		START_OFFSET:
		START_OFFSET + SCAN_SIZE
	]

	print(
		f'Loaded scan block '
		f'0x{START_OFFSET:X}'
	)

	for stride in STRIDES:

		print(
			f'\nTesting stride: {stride}'
		)

		vertices = test_stride(
			block,
			stride
		)

		print(
			f'Found '
			f'{len(vertices)} '
			f'candidate vertices'
		)



		# preview

		for v in vertices[:8]:

			print(v)



		# export OBJ

		out_path = (

			OUTPUT_DIR /

			f'stride_{stride}.obj'

		)

		export_obj(
			vertices,
			out_path
		)



if __name__ == '__main__':

	main()
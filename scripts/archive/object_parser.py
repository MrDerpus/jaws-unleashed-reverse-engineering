import struct
from pathlib import Path



# =====================================
# CONFIG
# =====================================

INPUT_FILE = 'FISH.GDW'

OUTPUT_DIR = Path('./object_parser')



# Runtime region

START_OFFSET = 113221000
END_OFFSET   = 113230000



# =====================================
# PROPERTY IDS
# =====================================

PROP_OBJECT_NAME = 0x080017D8
PROP_TRANSFORM   = 0x080017DA
PROP_BOUNDS      = 0x080017DF
PROP_CHILD       = 0x080018CB



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



def read_string(data):

	result = ''

	for b in data:

		if b == 0:
			break

		if 32 <= b <= 126:

			result += chr(b)

	return result



# =====================================
# PROP PARSER
# =====================================

def parse_prop(full_data, offset):

	try:

		if full_data[offset:offset + 4] != b'PROP':

			return None

		size = u32(full_data, offset + 4)

		prop_id = u32(full_data, offset + 8)

		payload_start = offset + 12
		payload_end = payload_start + size

		payload = full_data[
			payload_start:payload_end
		]

		return {

			'offset': offset,
			'size': size,
			'prop_id': prop_id,
			'payload': payload

		}

	except:

		return None



# =====================================
# OBJECT RECONSTRUCTION
# =====================================

def decode_object(props):

	obj = {

		'name': None,
		'transform': None,
		'bounds': None,
		'child_link': None,
		'raw_props': []

	}

	for prop in props:

		prop_id = prop['prop_id']
		payload = prop['payload']

		obj['raw_props'].append(
			f'0x{prop_id:08X}'
		)



		# ---------------------------------
		# OBJECT NAME
		# ---------------------------------

		if prop_id == PROP_OBJECT_NAME:

			if len(payload) >= 4:

				str_len = u32(payload, 0)

				name = read_string(
					payload[4:]
				)

				obj['name'] = name



		# ---------------------------------
		# TRANSFORM
		# ---------------------------------

		elif prop_id == PROP_TRANSFORM:

			floats = []

			for i in range(
				0,
				min(len(payload), 48),
				4
			):

				value = f32(payload, i)

				if value is not None:

					floats.append(
						round(value, 6)
					)

			obj['transform'] = floats



		# ---------------------------------
		# BOUNDS
		# ---------------------------------

		elif prop_id == PROP_BOUNDS:

			floats = []

			for i in range(
				0,
				min(len(payload), 24),
				4
			):

				value = f32(payload, i)

				if value is not None:

					floats.append(
						round(value, 6)
					)

			obj['bounds'] = floats



		# ---------------------------------
		# CHILD LINK
		# ---------------------------------

		elif prop_id == PROP_CHILD:

			if len(payload) >= 4:

				child_id = u32(payload, 0)

				obj['child_link'] = child_id

	return obj



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

	region = full_data[
		START_OFFSET:END_OFFSET
	]



	# ---------------------------------
	# FIND PROP BLOCKS
	# ---------------------------------

	props = []

	offset = 0

	while True:

		pos = region.find(
			b'PROP',
			offset
		)

		if pos == -1:
			break

		real_pos = START_OFFSET + pos

		prop = parse_prop(
			full_data,
			real_pos
		)

		if prop:

			props.append(prop)

		offset = pos + 4



	# ---------------------------------
	# GROUP OBJECTS
	# ---------------------------------

	objects = []

	current_group = []

	for prop in props:

		if prop['prop_id'] == PROP_OBJECT_NAME:

			if current_group:

				objects.append(
					decode_object(
						current_group
					)
				)

			current_group = []

		current_group.append(prop)



	if current_group:

		objects.append(
			decode_object(
				current_group
			)
		)



	# ---------------------------------
	# WRITE OUTPUT
	# ---------------------------------

	lines = []

	lines.append(
		'==== OBJECT RECONSTRUCTION ====\n'
	)

	for i, obj in enumerate(objects):

		lines.append(
			f'\n===== OBJECT {i} ====='
		)

		lines.append(
			f'Name: {obj["name"]}'
		)

		lines.append(
			f'ChildLink: {obj["child_link"]}'
		)

		lines.append(
			f'Properties: '
			f'{", ".join(obj["raw_props"])}'
		)

		lines.append(
			f'Transform: '
			f'{obj["transform"]}'
		)

		lines.append(
			f'Bounds: '
			f'{obj["bounds"]}'
		)



	out_path = (

		OUTPUT_DIR /

		'objects.txt'

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
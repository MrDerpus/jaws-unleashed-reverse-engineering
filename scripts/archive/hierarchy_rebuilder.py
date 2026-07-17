import re
from pathlib import Path



# =====================================
# CONFIG
# =====================================

INPUT_FILE = './object_parser/objects.txt'

OUTPUT_DIR = Path('./hierarchy_rebuilder')



# =====================================
# HELPERS
# =====================================

def ensure_dir(path):

	if not path.exists():

		path.mkdir(
			parents=True,
			exist_ok=True
		)



def parse_vector(text):

	if text == 'None':

		return None

	text = text.strip('[]')

	values = []

	for part in text.split(','):

		part = part.strip()

		try:

			values.append(
				float(part)
			)

		except:

			pass

	return values



# =====================================
# OBJECT PARSER
# =====================================

def parse_objects(text):

	objects = []

	chunks = text.split(
		'===== OBJECT'
	)

	for chunk in chunks:

		if 'Name:' not in chunk:
			continue

		obj = {

			'name': None,
			'child_link': None,
			'transform': None,
			'bounds': None,
			'properties': []

		}



		# ---------------------------------
		# NAME
		# ---------------------------------

		match = re.search(
			r'Name:\s*(.+)',
			chunk
		)

		if match:

			obj['name'] = (
				match.group(1)
				.strip()
			)



		# ---------------------------------
		# CHILD LINK
		# ---------------------------------

		match = re.search(
			r'ChildLink:\s*(.+)',
			chunk
		)

		if match:

			value = (
				match.group(1)
				.strip()
			)

			if value != 'None':

				try:

					obj['child_link'] = int(value)

				except:

					pass



		# ---------------------------------
		# TRANSFORM
		# ---------------------------------

		match = re.search(
			r'Transform:\s*(.+)',
			chunk
		)

		if match:

			obj['transform'] = parse_vector(
				match.group(1)
			)



		# ---------------------------------
		# BOUNDS
		# ---------------------------------

		match = re.search(
			r'Bounds:\s*(.+)',
			chunk
		)

		if match:

			obj['bounds'] = parse_vector(
				match.group(1)
			)



		# ---------------------------------
		# PROPERTIES
		# ---------------------------------

		match = re.search(
			r'Properties:\s*(.+)',
			chunk
		)

		if match:

			props = match.group(1)

			obj['properties'] = [

				p.strip()

				for p in props.split(',')

			]

		objects.append(obj)

	return objects



# =====================================
# HIERARCHY BUILDER
# =====================================

def build_groups(objects):

	groups = {}

	for obj in objects:

		link = obj['child_link']

		if link is None:

			continue

		if link not in groups:

			groups[link] = []

		groups[link].append(obj)

	return groups



# =====================================
# TREE PRINTER
# =====================================

def classify_object(name):

	if name is None:
		return 'Unknown'

	name_lower = name.lower()

	if 'bite' in name_lower:

		return 'BiteTarget'

	if 'tail' in name_lower:

		return 'Tail'

	if 'head' in name_lower:

		return 'Head'

	if 'mouth' in name_lower:

		return 'Mouth'

	if 'body' in name_lower:

		return 'Body'

	if 'skeletonmodel' in name_lower:

		return 'Root'

	return 'Other'



def print_group(link_id, objects):

	lines = []

	lines.append(
		f'\n===== HIERARCHY GROUP {link_id} ====='
	)

	root = None

	children = []



	# ---------------------------------
	# FIND ROOT
	# ---------------------------------

	for obj in objects:

		category = classify_object(
			obj['name']
		)

		if category == 'Root':

			root = obj

		else:

			children.append(obj)



	# ---------------------------------
	# PRINT ROOT
	# ---------------------------------

	if root:

		lines.append(
			f'\n{root["name"]}'
		)

	else:

		lines.append(
			'\n<NO ROOT FOUND>'
		)



	# ---------------------------------
	# PRINT CHILDREN
	# ---------------------------------

	for child in children:

		lines.append(

			f'├── {child["name"]}'

		)

		if child['transform']:

			pos = child['transform'][-3:]

			lines.append(

				f'│    Position: {pos}'

			)

		if child['bounds']:

			lines.append(

				f'│    Bounds: {child["bounds"]}'

			)

	return lines



# =====================================
# MAIN
# =====================================

def main():

	ensure_dir(OUTPUT_DIR)

	with open(INPUT_FILE, 'r') as f:

		text = f.read()

	objects = parse_objects(text)

	print(
		f'Parsed {len(objects)} objects'
	)

	groups = build_groups(objects)

	lines = []

	lines.append(
		'==== SCENE HIERARCHY ===='
	)

	for link_id, group_objects in groups.items():

		group_lines = print_group(
			link_id,
			group_objects
		)

		lines.extend(group_lines)



	out_path = (

		OUTPUT_DIR /

		'scene_hierarchy.txt'

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
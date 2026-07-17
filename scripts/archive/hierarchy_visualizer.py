import re
from pathlib import Path

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D



# =====================================
# CONFIG
# =====================================

INPUT_FILE = './object_parser/objects.txt'



# =====================================
# HELPERS
# =====================================

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
			'position': None,
			'bounds': None

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
		# TRANSFORM
		# ---------------------------------

		match = re.search(
			r'Transform:\s*(.+)',
			chunk
		)

		if match:

			transform = parse_vector(
				match.group(1)
			)

			# last 3 values
			# are likely translation

			if (
				transform and
				len(transform) >= 12
			):

				obj['position'] = (

					transform[-3],
					transform[-2],
					transform[-1]

				)



		# ---------------------------------
		# BOUNDS
		# ---------------------------------

		match = re.search(
			r'Bounds:\s*(.+)',
			chunk
		)

		if match:

			bounds = parse_vector(
				match.group(1)
			)

			obj['bounds'] = bounds

		objects.append(obj)

	return objects



# =====================================
# DRAW BOUNDS
# =====================================

def draw_bounds(ax, position, bounds):

	if not bounds:
		return

	if len(bounds) != 6:
		return

	min_x, min_y, min_z, max_x, max_y, max_z = bounds

	px, py, pz = position

	xs = [

		px + min_x,
		px + max_x

	]

	ys = [

		py + min_y,
		py + max_y

	]

	zs = [

		pz + min_z,
		pz + max_z

	]



	# draw wireframe corners

	for x in xs:
		for y in ys:

			ax.plot(
				[x, x],
				[y, y],
				[zs[0], zs[1]]
			)

	for x in xs:
		for z in zs:

			ax.plot(
				[x, x],
				[ys[0], ys[1]],
				[z, z]
			)

	for y in ys:
		for z in zs:

			ax.plot(
				[xs[0], xs[1]],
				[y, y],
				[z, z]
			)



# =====================================
# MAIN
# =====================================

def main():

	with open(INPUT_FILE, 'r') as f:

		text = f.read()

	objects = parse_objects(text)

	print(
		f'Loaded {len(objects)} objects'
	)



	# ---------------------------------
	# CREATE PLOT
	# ---------------------------------

	fig = plt.figure(
		figsize=(12, 10)
	)

	ax = fig.add_subplot(
		111,
		projection='3d'
	)



	# ---------------------------------
	# DRAW OBJECTS
	# ---------------------------------

	for obj in objects:

		name = obj['name']
		position = obj['position']
		bounds = obj['bounds']

		if not position:
			continue

		x, y, z = position



		# draw node

		ax.scatter(
			x,
			y,
			z,
			s=64
		)



		# label

		ax.text(
			x,
			y,
			z,
			name,
			size=8
		)



		# draw bounds

		draw_bounds(
			ax,
			position,
			bounds
		)



	# ---------------------------------
	# AXIS LABELS
	# ---------------------------------

	ax.set_xlabel('X')
	ax.set_ylabel('Y')
	ax.set_zlabel('Z')

	ax.set_title(
		'JAWS Entity Hierarchy Visualization'
	)

	plt.show()



if __name__ == '__main__':

	main()
import struct



INPUT_FILE  = '../GAME_GDWs/FISH.GDW'
OUTPUT_FILE = '../textures/texture_0.raw'



def main():

	with open(INPUT_FILE, 'rb') as f:

		data = f.read()

	# Find first GTEXT
	gtext_offset = data.find(b'GTEXT')

	if gtext_offset == -1:
		print('GTEXT not found')
		return

	print(f'GTEXT found at: 0x{gtext_offset:X}')

	# Find TGAN0 after GTEXT
	tgan_offset = data.find(b'TGAN0', gtext_offset)

	if tgan_offset == -1:
		print('TGAN0 not found')
		return

	print(f'TGAN0 found at: 0x{tgan_offset:X}')

	# Read payload size
	payload_size = struct.unpack(
		'<I',
		data[tgan_offset + 8:tgan_offset + 12]
	)[0]

	print(f'Payload size: {payload_size} bytes')

	# Payload begins after:
	# TGAN0 (6 bytes)
	# unknown fields/header
	#
	# Current experimental offset:
	payload_start = tgan_offset + 0x20 + 44

	print(f'Payload start: 0x{payload_start:X}')

	# Dump payload
	# Extract EXACT RGBA payload
	payload = data[
		payload_start:
		payload_start + (128 * 128 * 4)
	]

	with open(OUTPUT_FILE, 'wb') as out:
		out.write(payload)

	print(f'Wrote payload to: {OUTPUT_FILE}')



if __name__ == '__main__':

	main()
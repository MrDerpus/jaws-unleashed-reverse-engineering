import subprocess

filename = 'command-output.txt'
commands = [
    "grep -oba $'\xd9\x17\x00\x08' FISH.GDW | head",
	"grep -oba $'\xda\x17\x00\x08' FISH.GDW | head",
    "grep -oba $'\xdb\x17\x00\x08' FISH.GDW | head",

]

# clear file
open(filename, 'w').close()

# Write to file
with open(filename, 'a') as f:
    for command in commands:
        print(f'> Running:\n{command}')
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        f.write(f'$ {command}\n{result.stdout}{result.stderr}\n\n')

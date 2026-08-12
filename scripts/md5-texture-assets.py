# script always assumes argv[1] is json file
from colours import Colours as col
from json    import load as jLoad
from pathlib import Path
from hashlib import md5
from sys     import argv

# variable decleration
jsonFile:str   = ''
md5hash:str    = ''
base:object    = ()
jFile:object   = ()
arguments:dict = {}
gte:list = ['gtex', 'gtext']


# extract arguments from json file
jsonFile = argv[1].strip()
with open( jsonFile ) as jFile:
	arguments = jLoad(jFile)
	base = Path( arguments['file-location'] )

col.Print(f'{col.BRIGHT_WHITE}Searching for md5 hash: {col.RED}{arguments["hash-to-find"]}')

for folder in arguments['directories']:
	for asset_type in gte:
		for file in (base / folder / asset_type).glob('*'):

			if file.is_file():
				md5hash = md5(file.read_bytes()).hexdigest()

				if md5hash == arguments['hash-to-find']:
					col.Print(f'{col.BRIGHT_CYAN}{md5hash} {col.RED}{folder} {col.GREEN}{file}')
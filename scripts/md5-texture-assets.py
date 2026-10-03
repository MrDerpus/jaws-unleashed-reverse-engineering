# SPDX-License-Identifier: GPL-3.0-or-later
#
# Jaws Unleashed reverse engineering tools
# Copyright (C) 2026 MrDerpus and contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
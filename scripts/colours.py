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

# ANSI colour codes for Python3
class Colours:
	RESET = '\033[0m'
	
	# Regular colours
	BLACK   = '\033[30m'
	RED     = '\033[31m'
	GREEN   = '\033[32m'
	YELLOW  = '\033[33m'
	BLUE    = '\033[34m'
	MAGENTA = '\033[35m'
	CYAN    = '\033[36m'
	WHITE   = '\033[37m'
	
	# Bright colours
	BRIGHT_BLACK   = '\033[90m'
	BRIGHT_RED     = '\033[91m'
	BRIGHT_GREEN   = '\033[92m'
	BRIGHT_YELLOW  = '\033[93m'
	BRIGHT_BLUE    = '\033[94m'
	BRIGHT_MAGENTA = '\033[95m'
	BRIGHT_CYAN    = '\033[96m'
	BRIGHT_WHITE   = '\033[97m'
	
	# Styles
	BOLD      = '\033[1m'
	DIM       = '\033[2m'
	ITALIC    = '\033[3m'
	UNDERLINE = '\033[4m'
	REVERSED  = '\033[7m'
	
	def Print(user_input:str = '') -> None:
		print(user_input, Colours.RESET)

	# Example
	#Colours.Print(f'{Colours.GREEN}Success!{Colours.RESET}')
	#Colours.Print(f'{Colours.BOLD}{Colours.RED}Error!{Colours.RESET}')

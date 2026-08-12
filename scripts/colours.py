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

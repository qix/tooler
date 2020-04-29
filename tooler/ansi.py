from functools import partial
from typing import List

code_black = 0
code_red = 1
code_green = 2
code_yellow = 3
code_blue = 4
code_magenta = 5
code_cyan = 6
code_white = 7

def graphical(sequence: List[int]):
    return "\033[%sm" % ';'.join(map(str, sequence))

def colored(code, text, bold=False, dim=False, ansi=True):
    if not ansi:
        return text

    if dim:
        sequence = [2, 30 + code]
    elif bold:
        sequence = [1, 30 + code]
    else:
        sequence = [30 + code]
    return graphical(sequence)  + text + graphical([0])

black = partial(colored, code_black)
red = partial(colored, code_red)
green = partial(colored, code_green)
yellow = partial(colored, code_yellow)
blue = partial(colored, code_blue)
magenta = partial(colored, code_magenta)
cyan = partial(colored, code_cyan)
white = partial(colored, code_white)

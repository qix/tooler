# clide:
#   source: https://raw.githubusercontent.com/qix/clide/master/clide/ansi.py
#   version: 0.9.0
# License under the MIT License.
# See https://github.com/qix/clide/blob/master/LICENSE for details

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


def ansi_sgr(sequence: List[int]):
    "Select Graphic Rendition"
    return "\033[%sm" % ";".join(map(str, sequence))


def colored(
    text,
    *,
    foreground=None,
    background=None,
    bold=False,
    blink=False,
    dim=False,
    strike=False,
    bright=False,
    bright_background=False,
    underline=False,
    overline=False,
    ansi=True
):
    if not ansi:
        return text

    sequence = []
    if bold:
        sequence.append(1)
    if dim:
        sequence.append(2)
    if underline:
        sequence.append(4)
    if blink:
        sequence.append(5)
    if strike:
        sequence.append(9)
    if overline:
        sequence.append(53)
    if foreground is not None:
        sequence.append(30 + foreground + (60 if bright else 0))
    if background is not None:
        sequence.append(40 + background + (60 if bright_background else 0))
    return ansi_sgr(sequence) + text + ansi_sgr([0])


black = partial(colored, foreground=code_black)
red = partial(colored, foreground=code_red)
green = partial(colored, foreground=code_green)
yellow = partial(colored, foreground=code_yellow)
blue = partial(colored, foreground=code_blue)
magenta = partial(colored, foreground=code_magenta)
cyan = partial(colored, foreground=code_cyan)
white = partial(colored, foreground=code_white)

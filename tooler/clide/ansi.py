# clide:
#   source: https://raw.githubusercontent.com/qix/clide/master/clide/ansi.py
#   version: 0.9.0
# License under the MIT License.
# See https://github.com/qix/clide/blob/master/LICENSE for details

from functools import partial
import sys
from typing import List

default_sentinel = object()

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


reset = ansi_sgr([0])


def color(
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
):
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
    return ansi_sgr(sequence)


def build_color(c):
    def fn(
        text=None, *, ansi=True, **kv,
    ):
        if text is None:
            return color(foreground=c, **kv)
        elif not ansi:
            return text

        return color(foreground=c, **kv) + text + reset

    return fn


black = build_color(code_black)
red = build_color(code_red)
green = build_color(code_green)
yellow = build_color(code_yellow)
blue = build_color(code_blue)
magenta = build_color(code_magenta)
cyan = build_color(code_cyan)
white = build_color(code_white)


def ansi_message(color_escape, code, message):
    print(
        white(dim=True)
        + "["
        + color_escape
        + code
        + white(dim=True)
        + "]"
        + reset
        + " "
        + message,
        file=sys.stderr,
    )


def info(message: str):
    ansi_message(white(bold=True), "INFO", message)


def okay(message: str):
    ansi_message(green(bold=True), "OKAY", message)


def warn(message: str):
    ansi_message(yellow(bold=True), "WARN", message)


def error(message: str):
    ansi_message(red(bold=True), "ERR!", message)


def abort(message: str):
    ansi_message(red(bold=True), "ABORT", message)
    sys.exit(1)

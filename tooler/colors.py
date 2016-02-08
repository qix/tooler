from functools import partial


def colored(code, text, bold=False, ansi=True):
    if not ansi:
        return text
    if bold:
        code = '1;' + code
    return "\033[%sm%s\033[0m" % (code, text)

blue = partial(colored, '34')
cyan = partial(colored, '36')
green = partial(colored, '32')
magenta = partial(colored, '35')
red = partial(colored, '31')
white = partial(colored, '37')
yellow = partial(colored, '33')

grey = white

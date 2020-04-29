from functools import wraps
from shlex import quote as shell_quote

from .active import (
    get_active_tooler,
    set_active_tooler,
)
from .command import (
    default_parser,
    raw_parser,
    docopt_parser,
)
from .output import (
    write_status,
    write_error,
    write_warn,
    write_okay,
)
from .shell import bash
from .tooler import Tooler
from .version import (
    __author__,
    __author_email__,
    __url__,
    __version__,
)


def _tooler():
    tooler = get_active_tooler()
    if not tooler:
        tooler = Tooler()
        set_active_tooler(tooler)
    return tooler


def _not_implemented():
    raise Exception('not implemented yet')


def _not_implemented_decorator(fn):
    def decorated(*args, **kv):
        raise Exception('not implemented yet')
    return decorated

# Convenience methods run on the active tooler


def abort(*a, **k):
    return _tooler().abort(*a, **k)


def bash(*a, **k):
    return _tooler().bash(*a, **k)


def command(*a, **k):
    return _tooler().command(*a, **k)


def proceed(*a, **k):
    return _tooler().proceed(*a, **k)


def proceed_or_abort(*a, **k):
    return _tooler().proceed_or_abort(*a, **k)


def prompt(*a, **k):
    return _tooler().prompt(*a, **k)


# Add some compatability helpers for fabric migrations

def sudo(*a, **k):
    return _tooler().bash(*a, user='root', **k)


def cd(path):
    return settings(directory=path)

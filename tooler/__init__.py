from functools import wraps

from .command import (
    default_parser,
    raw_parser,
)
from .tooler import Tooler
from .version import (
    __author__,
    __author_email__,
    __url__,
    __version__,
)


def cd(path):
    return settings(directory=path)

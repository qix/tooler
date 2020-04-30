import shlex
from functools import partial

from tooler.command import (
    default_parser,
    raw_parser,
)

def parse(fn, command, parser=default_parser):
    return parser(fn, shlex.split(command))

def check(fn, command, *args, parser=default_parser, **kv):
    assert parse(fn, command, parser=parser) == (args, kv)


class TestDefaultParser:

    def test_var_args(self):
        def fn(*args, **va):
            pass
        _assert = partial(check, fn)

        _assert('')
        _assert(
            'one two three',
            'one', 'two', 'three',
        )
        _assert(
            'abc def --hij jkl --roar=now',
            'abc', 'def', hij='jkl', roar='now',
        )
        _assert(
            '--hij=jkl',
            hij='jkl'
        )
        _assert(
            'one',
            'one'
        )
        _assert(
            'one',
            'one'
        )

    def test_boolean(self):

        def simple(good=True):
            pass

        def negated(no_good=True):
            pass

        assert parse(simple, '') == ((), dict(good=True))
        assert parse(simple, '--good') == ((), dict(good=True))
        assert parse(simple, '--no-good') == ((), dict(good=False))

        assert parse(negated, '') == ((), dict(no_good=True))
        assert parse(negated, '--good') == ((), dict(no_good=False))
        assert parse(negated, '--no-good') == ((), dict(no_good=True))

class TestRawParser:

    def test_basic(self):
        def fn():
            pass


        assert parse(fn, 'first --second third', parser=raw_parser) == (('first', '--second', 'third'), {})

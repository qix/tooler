import shlex
from functools import partial

from tooler import DefaultParser, RawParser

def parse(fn, command, parser=None, parser_factory=DefaultParser):
    if parser is None:
        parser = parser_factory()
    return parser.parse(fn, 'sample command', None, shlex.split(command))

def check(
    fn, 
    command,
    *args,
    parser=DefaultParser(),
    throws=None,
    **kv
):
    if throws:
        assert not args and not kv
        try:
            parse(fn, command, parser=parser)
        except Exception as e:
            assert str(e) == throws
        raise Exception('Expected function to throw an exception')

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


    def test_boolean(self):

        def simple(good=True):
            pass

        def negated(no_good=True):
            pass

        assert parse(simple, '') == ((), dict(good=True))
        assert parse(simple, '--good') == ((), dict(good=True))
        assert parse(simple, '--no-good') == ((), dict(good=False))

        assert parse(negated, '') == ((), dict(no_good=True))
        #assert parse(negated, '--good') == ((), dict(no_good=False))
        assert parse(negated, '--no-good') == ((), dict(no_good=True))

class TestRawParser:

    def test_basic(self):
        def fn():
            pass


        assert parse(fn, 'first --second third', parser=RawParser()) == ([['first', '--second', 'third']], {})

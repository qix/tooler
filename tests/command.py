import shlex
from functools import partial
from nose.tools import (
  assert_equal,
)

from tooler.command import (
  default_parser,
  docopt_parser,
  raw_parser,
)


def _assert_parsed(parser, fn, selector, command, *args, **kv):
    assert_equal(
      parser(fn, fn.__doc__, selector, shlex.split(command)),
      (args, kv)
    )

class TestDefaultParser(object):
    def test_var_args(self):
        def fn(*args, **va):
            pass
        _assert = partial(_assert_parsed, default_parser, fn, '')

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

class TestDocoptParser(object):
    def test_basic(self):
        '''
        Only some super basic tests for docopt. They have their own tests.
        '''
        def fn():
            '''
            DocOpt Test

            Usage:
              test_basic <name> [--simple=<arg>]
            '''
            pass

        _assert_parsed(
          docopt_parser, fn, None,
          'first',
          { '<name>': 'first', '--simple': None }
        )

        _assert_parsed(
          docopt_parser, fn, None,
          'first --simple=second',
          { '<name>': 'first', '--simple': 'second' }
        )

class TestRawParser(object):
    def test_basic(self):
        def fn():
            pass

        _assert_parsed(
          raw_parser, fn, 'selector',
          'first --second third',
          'selector', ('first', '--second', 'third'),
        )

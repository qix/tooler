import io
from typing import Dict, Optional

from .exceptions import CommandHelpException
from .parser import DefaultParser


class Command:
  def __init__(self):
    pass

  def run(self, selector, argv):
    raise Exception("not implemented")


class DecoratorCommand(Command):
  def __init__(self, fn, doc=None, parser=None, shorthands: Optional[Dict[str, str]] = None):
    # @todo: Should just take an actual `parser` object, but need to do a large
    # refactor to fix that.
    if parser:
      assert not shorthands, "Shorthands option is not compatible with custom parser"
      self.parser = parser()
    else:
      self.parser = DefaultParser(shorthands=shorthands)

    self.fn = fn
    self.doc = doc

  def run(self, selector, argv):
    try:
      (args, vargs) = self.parser.parse(
          self.fn,
          self.doc,
          selector,
          argv
        )
    except CommandHelpException as e:
      print(e.usage)
      return

    try:
      return self.fn(*args, **vargs)
    finally:
      # Close any files that were opened as arguments
      for value in [*args, *vargs.values()]:
        # Skip as linter is not aware of `file` type
        if isinstance(value, io.IOBase):
          value.close()

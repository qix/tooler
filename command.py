import argparse
import inspect
from docopt import docopt

class ToolerCommand(object):
  def __init__(self, name, fn, doc=None, docopt=False):
    self.name = name
    self.fn = fn
    self.doc = doc

    if docopt:
      self.parser = lambda args: ((docopt(doc.strip(), argv=args),), {})
    else:
      signature = inspect.signature(fn)
      parser = argparse.ArgumentParser()
      for key, param in signature.parameters.items():
        if param.default == inspect._empty:
          parser.add_argument(key)
        else:
          parser.add_argument('--%s' % key, default=param.default)

    self.parser = lambda argv: ([], vars(parser.parse_args(argv)))


  def run(self, argv):
    (args, vargs) = self.parser(argv)
    return self.fn(*args, **vargs)

import argparse
import inspect
import re
from docopt import docopt as _docopt
from inspect import Parameter

ARG_REGEX = re.compile(r'^--([a-z]+(-[a-z]+)*)$')

def default_parser(fn, doc, selector, args):
  signature = inspect.signature(fn)
  parser = argparse.ArgumentParser()

  idx = 0

  positional = []
  keyword = {}

  while idx < len(args):
    if not args[idx].startswith('-'):
      if len(keyword):
        raise Exception('Positional arguments not valid after a keyword')
      positional.append(args[idx])
      idx += 1
    else:
      match = re.match(ARG_REGEX, args[idx])
      if not match:
        raise Exception('Could not identify argument: %s', args[idx])
      elif idx + 1 >= len(args):
        raise Exception('No value for argument: %s', args[idx])

      key = match.groups(1)
      if key in keyword:
        raise Exception('Value already set: ' + key)
      keyword[key] = args[idx + 1]
      idx += 2

  output = {}
  for key, param in signature.parameters.items():
    if positional:
      output[key] = positional.pop(0)
    elif param.kind == Parameter.VAR_KEYWORD:
      # **kv, take rest of keyword arguments
      for key, value in keyword.items():
        if key in output:
          raise Exception('Multiple values for key: ' + key)
        output[key] = value
      keyword = {}
    else:
      if key in keyword:
        output[key] = keyword.pop(key)
      elif param.default != inspect._empty:
        output[key] = param.default
      else:
        raise Exception('No default set for: ' + key)
  return ([], output)

def docopt_parser(fn, doc, selector, args):
  assert selector is None, 'selector not valid with docopt'
  return ((_docopt(doc.strip(), argv=args),), {})

def raw_parser(fn, doc, selector, args):
  return ((selector, args), {})

class ToolerCommand(object):
  def __init__(self, name, fn, doc=None, parser=None):
    self.name = name
    self.fn = fn
    self.doc = doc
    self.parser = default_parser if parser is None else parser

  def run(self, selector, argv):
    (args, vargs) = self.parser(self.fn, self.doc, selector, argv)
    return self.fn(*args, **vargs)

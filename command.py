from docopt import docopt

class ToolerCommand(object):
  def __init__(self, name, fn, doc=None, docopt=False):
    self.name = name
    self.fn = fn
    self.doc = doc
    self.docopt = docopt

  def run(self, args):
    if self.docopt:
      arguments = docopt(self.doc.strip(), argv=args)
      return self.fn(arguments)
    else:
      self.fn()

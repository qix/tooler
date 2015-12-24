import sys

from .output import write_error

def abort(message):
  write_error(message, code='ABORT')
  sys.exit(1)

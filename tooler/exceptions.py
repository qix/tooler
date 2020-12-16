import sys

from .clide.ansi import error


class CommandParseException(Exception):
  def __init__(self, message, usage=None):
    super().__init__(message)
    self.usage = usage

  def set_usage(self, usage):
    self.usage = usage

  def print_help(self):
    error(str(self))
    if self.usage:
      # Since usage information can get very long, write the error both
      # at the top and at the bottom.
      sys.stderr.write("\n" + self.usage + "\n")
      error(str(self))


class CommandHelpException(CommandParseException):
  pass

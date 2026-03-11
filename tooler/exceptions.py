import sys

from .clide.ansi import error


class ExceptionWithHelp(Exception):
  def __init__(self, message, help_string=None):
    super().__init__(message)
    self.help_string = help_string

  def set_usage(self, help_string):
    self.help_string = help_string

  def print_help(self):
    error(str(self))
    if self.help_string:
      # Since exception information can get very long, write the error both
      # at the top and at the bottom.
      sys.stderr.write("\n" + self.help_string + "\n")
      error(str(self))

class CommandParseException(ExceptionWithHelp):
  def __init__(self, message, usage=None):
    super().__init__(message, help_string=usage)

class CommandHelpException(CommandParseException):
  pass

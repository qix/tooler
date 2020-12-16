import asyncio
from dataclasses import dataclass
import functools
import os
import sys
from typing import Any, Dict, List, Optional, Union

from .clide.english import and_join
from .command import Command, DecoratorCommand
from .exceptions import CommandParseException
from .output import output_default
from .parser import ARG_REGEX


@dataclass
class ToolerOptionConfig:
  description: str
  default: Any


class UsageCommand(Command):
  def __init__(self, tooler):
    self.tooler = tooler

  def run(self, selector, argv):
    self.tooler.usage()


def _is_similar(command, search_command):
  return search_command in command


class Tooler:
  def __init__(self, help: Optional[str] = None):
    self.root = self
    self.parent = None

    self.default_command = None
    self.commands = {}
    self.namespace = set()

    self.help = help
    self.options = {}
    self.arguments = {}

    self.add_argument(
        "assume-defaults",
        description="Assume the default answer for proceed questions",
        default=False,
    )
    self.add_argument(
        "help", description="Display usage information for the tool", default=False
    )

  def _set_parent(self, parent):
    self.parent = parent
    self.root = parent.root

  def add_argument(self, arg, description=None, default=None):
    self.root.arguments[arg] = ToolerOptionConfig(description=description, default=default)
    if arg not in self.root.options:
      self.root.options[arg] = default

  def command(
      self,
      fn=None,
      *,
      name=None,
      default: bool = False,
      shorthands: Optional[Dict[str, str]] = None,
      parser=None,
  ):
    # This function creates a decorator. If we were passed a function here then
    # we need to first create the decorator and then pass the function to
    # it.
    if fn is not None:
      return self.command(
          name=name,
          default=default,
          shorthands=shorthands,
          parser=parser,
      )(fn)

    def decorator(fn):
      @functools.wraps(fn)
      def decorated(*args, **kv):
        return fn(*args, **kv)

      self.add_command(
          fn.__name__.replace("_", "-") if name is None else name,
          DecoratorCommand(fn, doc=fn.__doc__, parser=parser, shorthands=shorthands),
          default=default,
      )

      return decorated

    return decorator

  def conflicts(self, *groups: List[Union[str, List[str]]]):
    """
Refuse to run the command if conflicting parameters are provided.
"""

    def decorator(fn):
      @functools.wraps(fn)
      def decorated(*args, **kv):
        seen = []
        for group in groups:
          if isinstance(group, str):
            group = [group]
          for entry in group:
            if kv.get(entry):
              seen.append(entry)
              break

        if len(seen) > 1:
          raise CommandParseException(
              "Arguments are conflicting %s"
              % and_join(['"--%s"' % arg.replace("_", "-") for arg in seen])
          )

        return fn(*args, **kv)

      return decorated

    return decorator

  def add_command(self, name, command, default=False):
    if name in self.namespace:
      raise Exception("Second definition of %s" % name)
    self.namespace.add(name)

    if default:
      assert self.default_command is None, "Only one default option is allowed."
      self.default_command = command

    self.commands[name] = command

  def has_default(self):
    return True if self.default_command else False

  def parse_command(self, args=None, script_name=None):
    if args is None:
      args = sys.argv[:]
      script_name = args.pop(0)

    if type(args) in (bytes, str):
      raise Exception("Tooler args cannot be bytes/string, use an array")

    options = {}
    idx = 0
    command = None
    selector = None
    while idx < len(args):
      # If we have a default command set, and this command doesn't exist
      # We don't use it as a command and rather keep it as the first argument
      # This is done before parsing `--<x>` style arguments so they are passed
      # on to the default command as well.
      if self.default_command:
        if args[idx] not in self.commands:
          break

      arg_match = ARG_REGEX.match(args[idx])
      if arg_match:
        (arg_name, value) = arg_match.groups()
        if arg_name not in self.root.arguments:
          raise CommandParseException('Unknown tooler argument "%s"' % arg_name)
        idx += 1

        arg_config = self.root.arguments[arg_name]
        if isinstance(arg_config.default, bool):
          if value is not None:
            raise CommandParseException(
                'Value is not valid for bool arg "%s"' % arg_name
            )
          options[arg_name] = True
        elif value is not None:
          options[arg_name] = value
        else:
          if idx >= len(args):
            raise CommandParseException(
                'No value provided for argument "%s"' % arg_name
            )
            return False
          options[arg_name] = args[idx]
          idx += 1
      else:
        # If we have a default command set, and this command doesn't exist
        # We don't use it as a command and rather keep it as the first argument
        if self.default_command:
          if args[idx] not in self.commands:
            break

        command = args[idx]
        if ":" in command:
          (command, selector) = command.split(":", 1)
        args = args[idx + 1:]
        break

    # If no command was in the command line, use our default
    if command is None and self.default_command:
      command = self.default_command

    # Default to help, or overwrite if --help is set
    if command is None or "help" in options:
      command = UsageCommand(self)

    if isinstance(command, Command):
      return (options, command, selector, args)

    if command in self.commands:
      return (options, self.commands[command], selector, args)

    raise CommandParseException(
        "Invalid command: %s" % command,
        usage=self.usage(script_name, search_command=command, output=False),
    )

  def run(self, args=None, script_name=None, output=output_default):
    try:
      (options, command, selector, args) = self.parse_command(args, script_name)
      self.root.options.update(options)
      result = command.run(selector, args)
    except CommandParseException as e:
      e.print_help()
      return False

    if asyncio.iscoroutine(result):
      loop = asyncio.get_event_loop()
      result = loop.run_until_complete(result)

    if result is not None and output is not None:
      output(result)
    return result

  def main(self, argv=None):
    if argv is None:
      argv = sys.argv
    script_name = argv[0]
    args = argv[1:]

    if args == ["--bash-completion"]:
      words = os.environ["COMP_WORDS"].split("\n")
      word = int(os.environ["COMP_CWORD"])
      if word == 1 and len(words) >= 1:
        for command in self.commands.keys():
          if command.startswith(words[1]):
            print(command)
      sys.exit(0)

    rv = self.run(args, script_name=script_name)
    sys.exit(0 if rv in (True, None) else 1)

  def usage(self, script_name="t", search_command=None, output=True):
    prefix = script_name + " " if script_name else ""

    usage = "Usage: %s<command> [options...]\n\n" % prefix

    list_commands = list(self.commands.keys())

    if search_command is None:
      usage += "Available commands:\n" if list_commands else "No commands available.\n"
    else:
      list_commands = [cmd for cmd in list_commands if _is_similar(cmd, search_command)]
      usage += "Similar commands:\n" if list_commands else "No similar commands.\n"

    if list_commands:
      for command in sorted(list_commands):
        usage += "  %s\n" % command

    usage += "\n"

    if search_command is not None:
      usage += "Use '%s--help' to see the full list of all commands.\n" % prefix
    usage += "Use '%s<command> --help' for help on a single command.\n" % prefix

    if self.help:
      usage += "\n" + self.help + "\n"
    if output:
      sys.stderr.write(usage)
    return usage

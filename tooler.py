import asyncio
import sys
from functools import wraps

from .active import set_active_tooler
from .colors import (
  red,
  yellow,
)
from .command import (
  CommandParseException,
  ToolerCommand,
)
from .env import ToolerEnv
from .output import (
  output_json,
  write_error,
)
from .shell import (
  ShellException,
  bash,
)

class Tooler(object):

  def __init__(self):
    self.env = ToolerEnv()

    self.aliases = {}
    self.commands = {}
    self.submodules = {}
    self.failed_submodules = {}

    self.default_proceed_message = 'Are you sure you want to proceed?'
    self.assume_defaults = False
    self.default = None
    self.root = self
    self.parent = None

    self.loop = asyncio.get_event_loop()

    self.namespace = set()

  def _set_parent(self, parent):
    self.parent = parent
    self.env = parent.env
    self.root = parent.root

  def command(self, fn=None, name=None, alias=[], default=False, parser=None):
    # This function creates a decorator. If we were passed a function here then
    # we need to first create the decorator and then pass the function to it.
    if fn is not None:
      return self.command()(fn)

    def decorator(fn):
      @wraps(fn)
      def decorated(*args, **kv):
        return fn(*args, **kv)

      self.add_command(fn.__name__ if name is None else name, ToolerCommand(
        fn.__name__,
        fn,
        doc=fn.__doc__,
        parser=parser,
      ), default=default)

      return decorated

    return decorator

  def add_command(self, name, command, default=False):
    if name in self.namespace:
      raise Exception('Second definition of %s' % name)
    self.namespace.add(name)

    if default:
      assert self.default is None, 'Only one default option is allowed.'
      self.default = command

    self.commands[name] = command

  def add_submodule(self, name, tooler):
    if name in self.namespace:
      raise Exception('Second definition of %s' % name)

    if tooler.has_default():
      self.add_command(name, tooler.default)
    else:
      self.namespace.add(name)

    for subname, command in tooler.commands.items():
      self.add_command('%s.%s' % (name, subname), command)

    tooler._set_parent(self)

  def add_failed_submodule(self, name, reason):
    if name in self.namespace:
      raise Exception('Second definition of %s' % name)
    self.namespace.add(name)

    self.failed_submodules[name] = reason

  def alias(self, command, alias):
    if alias in self.namespace:
      raise Exception('Second definition of %s' % alias)
    self.namespace.add(alias)
    self.aliases[alias] = command

  def has_default(self):
    return True if self.default else False

  def run(self, args=None, script_name=None, output=output_json):
    set_active_tooler(self)

    if args is None:
      args = sys.argv[:]
      script_name = args.pop(0)

    if type(args) in (bytes, str):
      raise Exception('Tooler args cannot be bytes/string, use an array')

    # Super simple parser for tooler options
    toggles = {
      '--assume-defaults': False,
    }

    # Check for basic bash command. If there are multiple arguments treat them
    # as arguments to bash, but a single argument run as one large bash string.
    # This allows for: -- 'echo "hi" && echo "ho"' conveniently.
    if args and args[0] == '--':
      if len(args) == 2:
        self.bash(args[1])
      else:
        self.bash(args[1:])
      return

    idx = 0
    command = None
    while idx < len(args):
      if args[idx] in toggles:
        # If it's a toggle switch to true if it was used once
        if toggles[args[idx]]:
          print('Error argument', args[idx])
          return
        else:
          toggles[args[idx]] = True
        idx += 1
      elif args[idx].startswith('-'):
        print('Error argument', args[idx])
        return
      else:
        command = args[idx]
        if ':' in command:
          (command, selector) = command.split(':', 1)
        else:
          selector = None
        args = args[idx + 1:]
        break

    self.assume_defaults = toggles['--assume-defaults']

    # Follow aliases but throw on infinite loop
    seen = set()
    while command in self.aliases:
      if command in seen:
        raise Exception('Infinite loop in aliases: %s' % (', '.join(seen)))
      seen.add(command)
      command = self.aliases[command]

    if command in self.commands:
      try:
        result = self.commands[command].run(selector, args)
      except CommandParseException as e:
        write_error(str(e))
        return False

      if result is not None and output is not None:
        output(result)
      return result
    elif command is None:
      self.usage(script_name)
      return False

    splits = command.split('.')
    for length in range(1, 1 + len(splits)):
      submodule_name = '.'.join(splits[:length])
      if submodule_name in self.failed_submodules:
        write_error('Failed to load submodule %s: %s' % (
          submodule_name, self.failed_submodules[submodule_name]
        ))
        return False

    write_error('Invalid command: %s' % command)
    self.usage(script_name)
    return False

  def main(self, argv=None):
    if argv is None:
      argv = sys.argv
    script_name = argv[0]
    args = argv[1:]

    try:
      result = self.run(args, script_name=script_name)
    except ShellException as e:
      self.abort('Shell command raised exception: %s' % str(e))
    self.loop.close()
    sys.exit(1 if result is False else 0)

  def usage(self, script_name='./script'):
    prefix = script_name + ' '  if script_name else ''

    print('Usage: %s<command> [options...]' % prefix)
    print('')
    print('Available commands:')

    available_commands = (
      list(self.commands.keys()) +
      list(self.failed_submodules.keys())
    )
    for command in sorted(available_commands):
      print('  %s' % (red(command) if command in self.failed_submodules else command))

    print('')
    print('Use \'%s<command> --help\' for help on a single command' % prefix)

  def abort(self, message):
    write_error(message, code='ABORT')
    self.loop.close()
    sys.exit(1)

  def prompt(
    self, message,
    options=None,
    default=None,
    strip=True,
    lower=False,
    suggestion=None,
  ):
    # Sanity check
    if options is not None:
      assert default is None or default in options, (
        'The default value must be an option'
      )

    if default is not None and self.assume_defaults:
      print(message)
      print(yellow('Assuming default option:'), yellow(default, bold=True))
      return default


    if default is not None and suggestion is None:
      suggestion = default
    if default:
      message += ' [%s]' % suggestion

    try:
      # Loop if the answer is not one of the listed options
      while True:
        result = input(message + ' ')
        result = result.strip() if strip else result
        result = result.lower() if lower else result
        if result == '' and default is not None:
          return default
        elif options is None or result in options:
          return result
        else:
          print(red('Could not interpret answer: '), repr(result))

    except EOFError:
      sys.stdout.write('\n')
      self.abort('Could not read prompt from stdin.')
    except KeyboardInterrupt:
      sys.stdout.write('\n')
      sys.exit(1)

  def proceed(self, message=None, default=True):
    if message is None:
      message = self.default_proceed_message

    answers = {
      'y': True,
      'yes': True,
      'n': False,
      'no': False,
    }

    suggestion = ' [y/n]'
    result = self.prompt(
      message,
      options=answers.keys(),
      default='y' if default else 'n',
      suggestion='Y/n' if default else 'y/N',
      lower=True,
    )
    return answers[result]

  def proceed_or_abort(self, message=None, default=False):
    if not self.proceed(message, default=default):
      self.abort('User requested not to proceed.')

  def bash(self, *args, **kv):
    return bash(self.env, *args, **kv)

  def settings(self, *args, **kv):
    return self.env.settings(*args, **kv)

import sys
from functools import wraps

from .active import set_active_tooler
from .colors import yellow
from .command import ToolerCommand
from .env import ToolerEnv
from .output import output_json
from .shell import bash
from .util import (
  abort,
)

class Tooler(object):

  def __init__(self):
    self.commands = {}
    self.env = ToolerEnv()
    self.submodules = {}

    self.default_proceed_message = 'Are you sure you want to proceed?'
    self.assume_defaults = False
    self.default = None
    self.root = self
    self.parent = None

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
    if name in self.commands:
      raise Exception('Second definition of command: %s' % name)
    if name in self.submodules:
      raise Exception('Command was defined as a submodule: %s' % name)
    if default:
      assert self.default is None, 'Only one default option is allowed.'
      self.default = command

    self.commands[name] = command

  def add_submodule(self, name, tooler):
    tooler._set_parent(self)
    if tooler.has_default():
      self.add_command(name, tooler.default)
    for subname, command in tooler.commands.items():
      self.add_command('%s.%s' % (name, subname), command)

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

    # Check for basic bash command
    if args and args[0] == '--':
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

    if command in self.commands:
      result = self.commands[command].run(selector, args)
      if result is not None and output is not None:
        output(result)
      return result
    elif command is None:
      self.usage()
      return False
    else:
      print('Invalid command:', command)
      self.usage()
      return False

  def main(self):
    args = sys.argv[:]
    script_name = args.pop(0)
    result = self.run(args, script_name=script_name)
    sys.exit(1 if result is False else 0)

  def usage(self, script_name='./script'):
    print('Usage: %s <command> [options...]')
    print('')
    print('Available commands:')
    for command in sorted(self.commands.keys()):
      print('  %s' % command)
    print('')
    print('Use \'%s <command> --help\' for help on a singe command')

  def prompt(self, message):
    try:
      return input(message + ' ')
    except EOFError:
      sys.stdout.write('\n')
      abort('Could not read prompt from stdin.')
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
      '': default,
    }
    default_text = {False: 'n', True: 'y'}[default]

    if self.assume_defaults:
      print(message)
      print(yellow('Assuming default option:'), yellow(default_text, bold=True))
      return default

    suggestion = ' [y/n]'
    result = self.prompt(message + suggestion).strip().lower()
    while not result in answers:
      print(red('Could not interpret answer: '), repr(result))
      result = self.prompt(message + suggestion).strip().lower()
    return answers[result]

  def proceed_or_abort(self, message=None, default=False):
    if not self.proceed(message, default=default):
      abort('User requested not to proceed.')

  def bash(self, *args, **kv):
    return bash(self.env, *args, **kv)

  def settings(self, *args, **kv):
    return self.env.settings(*args, **kv)

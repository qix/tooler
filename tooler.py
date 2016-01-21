import sys
from functools import wraps

from .active import set_active_tooler
from .colors import yellow
from .command import ToolerCommand
from .util import (
  abort,
)

class Tooler(object):

  def __init__(self):
    self.commands = {}
    self.submodules = {}

    self.default_proceed_message = 'Are you sure you want to proceed?'
    self.assume_defaults = False

  def command(self, fn=None, docopt=False):
    # This function creates a decorator. If we were passed a function here then
    # we need to first create the decorator and then pass the function to it.
    if fn is not None:
      return self.command()(fn)

    def decorator(fn):
      @wraps(fn)
      def decorated(*args, **kv):
        return fn(*args, **kv)

      self.add_command(fn.__name__, ToolerCommand(
        fn.__name__,
        fn,
        doc=fn.__doc__,
        docopt=docopt,
      ))

      return decorated

    return decorator

  def add_command(self, name, command):
    if name in self.commands:
      raise Exception('Second definition of command: %s' % name)
    if name in self.submodules:
      raise Exception('Command was defined as a submodule: %s' % name)

    self.commands[name] = command

  def add_submodule(self, name, tooler):
    if tooler.has_default():
      self.add_command(name, tooler)
    for subname, command in tooler.commands.items():
      self.add_command('%s.%s' % (name, subname), command)

  def has_default(self):
    return False

  def run(self, args=None):
    set_active_tooler(self)

    if not args:
      args = sys.argv

    script_name = args.pop(0)

    # Super simple parser for tooler options
    toggles = {
      '--assume-defaults': False,
    }

    idx = 0
    command = None
    while idx < len(args):
      if args[idx] in toggles:
        # If it's a toggle switch to true if it was used once
        if toggles[args[idx]]:
          return self.usage()
        else:
          toggles[args[idx]] = True
        idx += 1
      elif args[idx].startswith('-'):
        return self.usage()
      else:
        command = args[idx]
        args = args[idx + 1:]
        break

    self.assume_defaults = toggles['--assume-defaults']

    if command in self.commands:
      self.commands[command].run(args)
    else:
      self.usage()


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

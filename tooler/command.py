import argparse
import inspect
import re
import shlex
from inspect import Parameter
from typing import List

from .output import write_error

ARG_REGEX = re.compile(r'^--([a-z]+(?:-[a-z]+)*)(?:=(.*))?$')


class CommandParseException(Exception):
    pass


class UsageException(Exception):
    def __init__(self, command: 'ToolerCommand', message):
        super().__init__(message)
        self.command = command


def default_parser(fn, args):
    signature = inspect.signature(fn)
    parser = argparse.ArgumentParser()

    idx = 0

    positional = []
    keyword = {}

    boolean = {
        name for name, param in signature.parameters.items()
        if param.default in (True, False)
        or param.annotation == bool
    }

    while idx < len(args):
        if not args[idx].startswith('-'):
            if len(keyword):
                raise CommandParseException( 
                    'Positional arguments not valid after a keyword')
            positional.append(args[idx])
            idx += 1
        else:
            match = re.match(ARG_REGEX, args[idx])
            idx += 1

            if not match:
                raise CommandParseException( 'Could not identify argument: %s' % args[idx])
            
            # Read the parameter out, automatic swap `-` for `_` in keyword arguments
            (key, value) = match.groups()
            key = key.replace('-', '_')

            if key in boolean:
                if value is not None:
                    raise CommandParseException( f'Expected boolean value for parameter: {key}')
                value = True
            elif key.startswith('no_') and key[3:] in boolean:
                if value is not None:
                    raise CommandParseException( f'Expected boolean value for parameter: {key}')
                key = key[3:]
                value = False
            elif ('no_' + key) in boolean:
                if value is not None:
                    raise CommandParseException( f'Expected boolean value for parameter: {key}')
                key = 'no_' + key
                value = False
            else:
                if key in keyword:
                    raise CommandParseException( 'Value already set: ' + key)

                # "--arg <value>" style; read value out of next argument
                if value is None:
                    if idx >= len(args):
                        raise CommandParseException( 'No value for argument: %s' % key)
                    value = args[idx]
                    idx += 1

            keyword[key] = value

    args = []
    kv = {}

    for key, param in signature.parameters.items():
        if param.kind == Parameter.VAR_POSITIONAL:
            # *args, take reset of positional arguments
            args.extend(positional)
            positional = []
        elif positional:
            # If there is anything left in positional; send it as a normal
            # argument
            args.append(positional.pop(0))
        elif param.kind == Parameter.VAR_KEYWORD:
            # **kv, take rest of keyword arguments
            for key, value in keyword.items():
                if key in kv:
                    raise CommandParseException( 'Multiple values for key: ' + key)
                kv[key] = value
            keyword = {}
        else:
            if key in keyword:
                kv[key] = keyword.pop(key)
            elif param.default != inspect._empty:
                kv[key] = param.default
            else:
                raise CommandParseException( 'No default set for: ' + key)

    if positional or keyword:
        raise CommandParseException(
            'Unused arguments: %s' % ' '.join(
                positional + list(keyword.keys()))
        )

    return (tuple(args), kv)


def raw_parser(fn, args):
    return (tuple(args), {})


class ToolerCommand:

    def __init__(self, name, fn, parser=None):
        self.name = name
        self.fn = fn
        self.parser = default_parser if parser is None else parser

    def run(self, selector, argv):
        try:
            (args, vargs) = self.parser(self.fn, argv)
        except CommandParseException as e:
            raise UsageException(self, str(e))
        return self.fn(*args, **vargs)

    def usage(self, command: List[str]):
        sig = inspect.signature(self.fn)
        params = sig.parameters

        lines = []
        longest_param = max((len(k) for k in params.keys()), default=0)

        for key, param in params.items():
            options = []
            if param.default == inspect._empty:
                options.append("required")
            elif isinstance(param.default, bool):
                options.append("default %s" % str(param.default).lower())
            elif param.default != "":
                options.append("default %s" % repr(param.default))

            key_dashed = key.replace('_', '-')
            padding = " " * (longest_param - len(key) + 4)
            description = ", ".join(options)
            lines.append(f"  --{key_dashed}{padding}{description}")

        full_command = ' '.join(shlex.quote(arg) for arg in command)

        if not lines:
            return full_command + '\n    No parameters available.\n'
    
        return (
            full_command + '\n' +           '\n'.join(lines) + '\n'
        )
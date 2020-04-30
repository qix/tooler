import argparse
import inspect
import re
from inspect import Parameter

from .output import write_error

ARG_REGEX = re.compile(r'^--([a-z]+(?:-[a-z]+)*)(?:=(.*))?$')


class CommandParseException(Exception):

    def __init__(self, message):
        super().__init__(message)


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
                raise CommandParseException('Could not identify argument: %s', args[idx])
            
            # Read the parameter out, automatic swap `-` for `_` in keyword arguments
            (key, value) = match.groups()
            key = key.replace('-', '_')

            if key in boolean:
                if value is not None:
                    raise CommandParseException(f'Expected boolean value for parameter: {key}')
                value = True
            elif key.startswith('no_') and key[3:] in boolean:
                if value is not None:
                    raise CommandParseException(f'Expected boolean value for parameter: {key}')
                key = key[3:]
                value = False
            elif ('no_' + key) in boolean:
                if value is not None:
                    raise CommandParseException(f'Expected boolean value for parameter: {key}')
                key = 'no_' + key
                value = False
            else:
                if key in keyword:
                    raise CommandParseException('Value already set: ' + key)

                # "--arg <value>" style; read value out of next argument
                if value is None:
                    if idx >= len(args):
                        raise CommandParseException('No value for argument: %s' % key)
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
                    raise Exception('Multiple values for key: ' + key)
                kv[key] = value
            keyword = {}
        else:
            if key in keyword:
                kv[key] = keyword.pop(key)
            elif param.default != inspect._empty:
                kv[key] = param.default
            else:
                raise Exception('No default set for: ' + key)

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
        (args, vargs) = self.parser(self.fn, argv)
        return self.fn(*args, **vargs)

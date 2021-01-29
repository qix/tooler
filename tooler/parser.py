import inspect
import io
from pathlib import Path
import re
from string import ascii_letters
import sys
from typing import List, Optional, Union

from .exceptions import CommandHelpException, CommandParseException


# Try import from `typing_extensions` if this command has it
try:
    from typing_extensions import Literal
except ModuleNotFoundError:
    pass


ARG_REGEX = re.compile(r"^--([a-z0-9]+(?:[-_][a-z0-9]+)*)(?:=(.*))?$")


def _is_literal(annotation):
    """
    Since `Literal` is in an extension for now, best effort compare or return false"""
    try:
        origin = getattr(annotation, "__origin__", None)
        return origin == Literal
    except NameError:
        return False


def _match_annotation_type(fn, annotation, value):
    if annotation in (Path, Optional[Path]):
        return Path(value)
    elif annotation in (io.BytesIO, Optional[io.BytesIO]):
        # BytesIO will automatically open a file stream
        if value == "-":
            return sys.stdin.buffer
        else:
            # lint is upset that this file isn't used in a contextmanager, but it is
            # closed as part of the run
            return open(value, "rb")  # noqa
    elif _is_literal(annotation):
        if value not in annotation.__args__:
            options_str = ", ".join(repr(arg) for arg in annotation.__args__)
            raise CommandParseException(
                "Argument not valid: %s (allowed are %s)" % (repr(value), options_str)
            )
        return value
    else:
        return value


def _match_param_type(fn, param, value):
    # If they've set a default do some automatic type conversion
    if isinstance(param.default, float) or param.annotation == float:
        return float(value)
    elif isinstance(param.default, int) or param.annotation == int:
        return int(value)
    elif param.annotation:
        return _match_annotation_type(fn, param.annotation, value)
    else:
        return value


class Parser:
    def parse(self, fn, doc, selector, args):
        raise NotImplementedError()


class RawParser(Parser):
    def parse(self, fn, doc, selector, args):
        return ([args], {})


class DefaultParser(Parser):
    def __init__(self, shorthands=None):
        self.shorthands = shorthands or {}

        for key in self.shorthands.keys():
            assert (
                len(key) == 1 and key in ascii_letters
            ), "Shorthand keys must be single letters"

    def usage(self, fn):
        signature = inspect.signature(fn)

        key_strings = {}
        for key, param in signature.parameters.items():
            string = "--" + key.replace("_", "-")

            for shorthand, shorthand_key in self.shorthands.items():
                if shorthand_key == key:
                    string = f"-{shorthand}, {string}"

            key_strings[string] = param

        parameter_lengths = [len(key) for key in key_strings.keys()]
        key_length = max(parameter_lengths or [0])

        def _key_usage(key_string, param):
            props = []

            if param.default == inspect._empty:
                props.append("required")
            elif isinstance(param.default, bool):
                props.append("default %s" % ("yes" if param.default else "no"))
            elif param.default not in ("", None):
                props.append("default %s" % repr(param.default))

            suffix = ""
            if props:
                suffix += " " * (key_length - len(key_string) + 4)
                suffix += ", ".join(props)

            return "  %s%s" % (key_string, suffix)

        return "Usage:\n" + "\n".join(
            _key_usage(key_string, param) for key_string, param in key_strings.items()
        )

    def parse(self, fn, doc, selector, args):
        try:
            return self._parse(fn, doc, selector, args)
        except CommandParseException as e:
            e.set_usage(self.usage(fn))
            raise e

    def _parse(self, fn, doc, selector, args):
        if selector is not None:
            raise Exception("Command selector has not been enabled")

        signature = inspect.signature(fn)
        idx = 0

        positional = []
        keyword = {}
        boolean = {}

        for key, param in signature.parameters.items():
            if isinstance(param.default, bool):
                boolean[key] = param.default
            elif param.annotation == bool:
                boolean[key] = False
            elif param.annotation == Union[bool, None]:
                boolean[key] = None

        while idx < len(args):
            if args[idx] in ("-", "--") or not args[idx].startswith("-"):
                if len(keyword):
                    raise CommandParseException(
                        "Positional arguments not valid after a keyword"
                    )
                positional.append(args[idx])
                idx += 1
            else:
                match = re.match(ARG_REGEX, args[idx])

                if match:
                    (key, value) = match.groups()
                elif args[idx].startswith("-") and args[idx][1] in self.shorthands:
                    key = self.shorthands[args[idx][1]]
                    value = args[idx][2:] if len(args[idx]) > 2 else None
                else:
                    raise CommandParseException(
                        "Could not identify argument: %s" % args[idx]
                    )

                idx += 1

                # Since dash is not valid in variable name, automatically convert
                key = key.replace("-", "_")

                if key in keyword:
                    raise CommandParseException(
                        "Saw multiple values for an argument: " + key
                    )

                # Add support for --flag, and --no-flag
                if key in boolean:
                    if value is not None:
                        raise CommandParseException(
                            "Value provided to boolean key: %s" % key
                        )
                    boolean[key] = True
                    continue
                elif key.startswith("no_") and key[3:] in boolean:
                    if value is not None:
                        raise CommandParseException(
                            "Value provided to boolean key: %s" % key
                        )
                    boolean[key[3:]] = False
                    continue

                # "--arg <value>" style; read value out of next argument
                if value is None:
                    if key == "help":
                        raise CommandHelpException("Command help requested")

                    if idx >= len(args):
                        raise CommandParseException(
                            "No value provided for argument: %s" % key
                        )
                    value = args[idx]
                    idx += 1

                keyword[key] = value

        args = []
        kv = {}

        for key, param in signature.parameters.items():
            if key in boolean:
                kv[key] = boolean[key]
            elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                # *args, take reset of positional arguments
                if (
                    param.annotation and param.annotation != inspect.Parameter.empty
                ):  # noqa: W503
                    # Make sure the annotation is valid if there is one
                    try:
                        origin = param.annotation.__origin__
                    except AttributeError:
                        origin = None
                    assert origin in (
                        List,
                        list,
                    ), f"Expected `List[]` annotation for positional arguments"

                    single_annotation = param.annotation.__args__[0]
                    positional = [
                        _match_annotation_type(fn, single_annotation, value)
                        for value in positional
                    ]
                args.extend(positional)
                positional = []
            elif positional:
                # If there is anything left in positional; send it as a normal
                # argument
                args.append(_match_param_type(fn, param, positional.pop(0)))
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                # **kv, take rest of keyword arguments
                for key, value in keyword.items():
                    kv[key] = value
                keyword = {}
            else:
                if key in keyword:
                    kv[key] = _match_param_type(fn, param, keyword.pop(key))
                elif param.default != inspect._empty:
                    kv[key] = param.default
                else:
                    raise CommandParseException(
                        "No value provided for required argument: " + key
                    )

        if positional or keyword:
            raise CommandParseException(
                "Unused arguments: %s" % " ".join(positional + list(keyword.keys()))
            )

        return (tuple(args), kv)

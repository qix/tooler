import asyncio
import sys
from contextlib import contextmanager
from functools import wraps

from .active import set_active_tooler
from .ansi import (
    abort,
    error,
    red,
    yellow,
)
from .command import (
    CommandParseException,
    ToolerCommand,
    UsageException,
)
from .output import output_json


class Tooler:
    def __init__(self):
        self.env = None

        self.aliases = {}
        self.commands = {}
        self.submodules = {}
        self.failed_submodules = {}

        self.default_proceed_message = "Are you sure you want to proceed?"
        self.assume_defaults = False
        self.default = None

        self.loop = asyncio.get_event_loop()

        self.namespace = set()

    def command(self, fn=None, /, *, name=None, alias=[], default=False, parser=None):
        # This function creates a decorator. If we were passed a function here then
        # we need to first create the decorator and then pass the function to
        # it.
        if fn is not None:
            return self.command()(fn)

        def decorator(fn):
            @wraps(fn)
            def decorated(*args, **kv):
                return fn(*args, **kv)

            self._add_command(
                fn.__name__ if name is None else name,
                ToolerCommand(fn.__name__, fn, parser=parser),
                default=default,
            )

            return decorated

        return decorator

    def _add_command(self, name, command, default=False):
        if name in self.namespace:
            raise Exception("Second definition of %s" % name)
        self.namespace.add(name)

        if default:
            assert self.default is None, "Only one default option is allowed."
            self.default = command

        self.commands[name] = command

    def subcommand(self, name, tooler):
        assert isinstance(tooler, Tooler)

        self._add_command(name, tooler)

    def add_failed_submodule(self, name, reason):
        if name in self.namespace:
            raise Exception("Second definition of %s" % name)
        self.namespace.add(name)

        self.failed_submodules[name] = reason

    def alias(self, command, alias):
        if alias in self.namespace:
            raise Exception("Second definition of %s" % alias)
        self.namespace.add(alias)
        self.aliases[alias] = command

    def has_default(self):
        return True if self.default else False

    def run(self, argv=None, script_name=None, output=output_json):
        set_active_tooler(self)

        if argv is None:
            argv = sys.argv[:]
            argv_script = argv.pop(0)
            if not script_name:
                script_name = argv_script

        if type(argv) in (bytes, str):
            raise Exception("Tooler args cannot be bytes/string, use an array")

        # Super simple parser for tooler options
        toggles = {
            "--assume-defaults": False,
        }

        idx = 0
        command = None
        while idx < len(argv):
            if argv[idx] in toggles:
                # If it's a toggle switch to true if it was used once
                if toggles[argv[idx]]:
                    print("Error argument", argv[idx])
                    return
                else:
                    toggles[argv[idx]] = True
                idx += 1
            elif argv[idx].startswith("-"):
                print("Error argument", argv[idx])
                return
            else:
                command = argv[idx]
                argv = argv[idx + 1 :]
                break

        self.assume_defaults = toggles["--assume-defaults"]

        # Follow aliases but throw on infinite loop
        seen = set()
        while command in self.aliases:
            if command in seen:
                raise Exception("Infinite loop in aliases: %s" % (", ".join(seen)))
            seen.add(command)
            command = self.aliases[command]

        if command in self.commands:
            try:
                result = self.commands[command].run(argv)

            except UsageException as e:
                error(str(e))
                print(e.command.usage([command]), file=sys.stderr)
                return False
            except CommandParseException as e:
                error(str(e))
                return False

            if result is not None and output is not None:
                output(result)
            return result
        elif command is None:
            self.usage(script_name)
            return False

        splits = command.split(".")
        for length in range(1, 1 + len(splits)):
            submodule_name = ".".join(splits[:length])
            if submodule_name in self.failed_submodules:
                error(
                    "Failed to load submodule %s: %s"
                    % (submodule_name, self.failed_submodules[submodule_name])
                )
                return False

        error("Invalid command: %s" % command)
        self.usage(script_name)
        return False

    def main(self, argv=None, *, script_name=None, **kv):
        if argv is None:
            argv = sys.argv
        script_name = script_name if script_name is not None else argv[0]
        args = argv[1:]

        with self.settings(**kv):
            result = self.run(args, script_name=script_name)
        self.loop.close()
        sys.exit(1 if result is False else 0)

    def usage(self, script_name="./script"):
        prefix = script_name + " " if script_name else ""

        print("Usage: %s<command> [options...]" % prefix)
        print("")
        print("Available commands:")

        available_commands = list(self.commands.keys()) + list(
            self.failed_submodules.keys()
        )
        for command in sorted(available_commands):
            print(
                "  %s"
                % (red(command) if command in self.failed_submodules else command)
            )

        print("")
        print("Use '%s<command> --help' for help on a single command" % prefix)

    def prompt(
        self,
        message,
        options=None,
        default=None,
        strip=True,
        lower=False,
        suggestion=None,
    ):
        # Sanity check
        if options is not None:
            assert (
                default is None or default in options
            ), "The default value must be an option"

        if default is not None and self.assume_defaults:
            print(message)
            print(yellow("Assuming default option:"), yellow(default, bold=True))
            return default

        if default is not None and suggestion is None:
            suggestion = default
        if default:
            message += " [%s]" % suggestion

        try:
            # Loop if the answer is not one of the listed options
            while True:
                result = input(message + " ")
                result = result.strip() if strip else result
                result = result.lower() if lower else result
                if result == "" and default is not None:
                    return default
                elif options is None or result in options:
                    return result
                else:
                    print(red("Could not interpret answer: "), repr(result))

        except EOFError:
            sys.stdout.write("\n")
            abort("Could not read prompt from stdin.")
        except KeyboardInterrupt:
            sys.stdout.write("\n")
            sys.exit(1)

    @contextmanager
    def settings(self, *args, **kv):
        yield

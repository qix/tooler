import json
import sys


def output_json(json_string):
  if not sys.stdout.isatty():
    print(json_string)
    return

  try:
    # If we have pygments installed, we can pretty print with color
    from pygments import highlight
    from pygments.formatters import TerminalFormatter
    from pygments.lexers import JsonLexer

    print(highlight(json_string, JsonLexer(), TerminalFormatter()), end="")
  except ImportError:
    print(json_string)


def output_default(body):
  try:
    json_string = json.dumps(body, sort_keys=True, indent=2, ensure_ascii=False)
    output_json(json_string)
  except TypeError:
    # If we couldn't convert to json, just output the python str version
    print(str(body))

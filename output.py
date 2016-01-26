import json
import textwrap
import sys
from datetime import datetime
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer

from .colors import (
  blue,
  green,
  grey,
  red,
  yellow,
)

def human_filesize(value):
  for unit in ['', 'kb', 'mb', 'gb']:
    if abs(value) < 1024:
      return '%.1f%s' % (value, unit)
    value /= 1024.0
  return '%.1f%s' % (value, 'tb')

def _wrap(message, indent=0):
  lines = message.split('\n')
  return '\n'.join([
    '\n'.join(textwrap.wrap(
      lines[idx],
      width=100,
      initial_indent='' if idx == 0 else ' ' * indent,
      subsequent_indent=' ' * indent,
      break_on_hyphens=False,
      break_long_words=False,
    ))
    for idx in range(len(lines))
  ])

def output_json(body):
  json_string = json.dumps(
    body,
    sort_keys=True,
    indent=2,
    ensure_ascii=False
  )
  print(highlight(json_string, JsonLexer(), TerminalFormatter()), end='')

def write_message(prefix, message=None, wrap=True, prefix_length=None):
  if message is None:
    message = prefix
    prefix = ''
  if prefix_length is None:
    prefix_length = len(prefix)

  msg = prefix + message
  msg = _wrap(msg, prefix_length) if wrap else msg
  sys.stderr.write(msg + '\n')
  sys.stderr.flush()

def _write_coded(code, message, color=None, bold=False):
  prefix = '[%s]' % code
  prefix_length = len(prefix)
  if color:
    prefix = color(prefix, bold=bold)
  write_message(prefix + ' ', message, prefix_length=prefix_length+1)

def write_error(message, code='ERR!'):
  _write_coded(code, message, color=red, bold=True)

def write_status(message, code='STAT'):
  _write_coded(code, message, color=blue, bold=True)

def write_okay(message, code='OKAY'):
  _write_coded(code, message, color=green, bold=True)

def write_warn(message, code='WARN'):
  _write_coded(code, message, color=yellow, bold=True)

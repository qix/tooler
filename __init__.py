from functools import wraps
from shlex import quote as shell_quote

from .active import (
  get_active_tooler,
  set_active_tooler,
)
from .command import (
  default_parser,
  raw_parser,
  docopt_parser,
)
from .env import (
  LocalHost,
  SshHost,
  localhost,
)
from .output import (
  write_status,
  write_error,
  write_warn,
  write_okay,
)
from .shell import bash
from .tooler import Tooler

def _tooler():
  tooler = get_active_tooler()
  if not tooler:
    tooler = Tooler()
    set_active_tooler(tooler)
  return tooler

def _not_implemented():
  raise Exception('not implemented yet')
def _not_implemented_decorator(fn):
  def decorated(*args, **kv):
    raise Exception('not implemented yet')
  return decorated

# Convenience methods run on the active tooler
abort = lambda *a, **k: _tooler().abort(*a, **k)
bash = lambda *a, **k: _tooler().bash(*a, **k)
command = lambda *a, **k: _tooler().command(*a, **k)
proceed = lambda *a, **k: _tooler().proceed(*a, **k)
proceed_or_abort = lambda *a, **k: _tooler().proceed_or_abort(*a, **k)
prompt = lambda *a, **k: _tooler().prompt(*a, **k)
settings = lambda *a, **k: _tooler().settings(*a, **k)

# Add some compatability helpers for fabric migrations
local = lambda *a, **k: _tooler().bash(*a, hosts=[localhost], **k)[0]
sudo = lambda *a, **k: _tooler().bash(*a, user='root', **k)
task = command
execute = lambda func, *a, **k: func(*a, **k)
hide = _not_implemented
put = _not_implemented
show = _not_implemented
serial = _not_implemented_decorator


def cd(path):
  return settings(directory=path)

def runs_once(fn):
  results = {}
  @wraps(fn)
  def decorated(*a, **kv):
    key = (tuple(a), tuple(kv.items()))
    if not key in results:
      results[key] = fn(*a, **kv)
    return results[key]
  return decorated

from functools import wraps
from shlex import quote as bash_quote

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
from .shell import (
  bash,
)
from .tooler import Tooler
from .util import (
  abort,
)

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
add_submodule = lambda *a, **k: _tooler().add_submodule(*a, **k)
bash = lambda *a, **k: _tooler().bash(*a, **k)
command = lambda *a, **k: _tooler().command(*a, **k)
proceed = lambda *a, **k: _tooler().proceed(*a, **k)
proceed_or_abort = lambda *a, **k: _tooler().proceed_or_abort(*a, **k)
prompt = lambda *a, **k: _tooler().proceed_or_abort(*a, **k)
run = lambda *a, **k: _tooler().run(*a, **k)
settings = lambda *a, **k: _tooler().settings(*a, **k)

# Add some compatability helpers for fabric migrations
local = lambda *a, **k: _tooler().bash(*a, hosts=[LocalHost], **k)
sudo = lambda *a, **k: _tooler().bash(*a, user='root', **k)
task = command
execute = lambda func, *a, **k: func(*a, **k)
hide = _not_implemented
put = _not_implemented
show = _not_implemented
serial = _not_implemented_decorator


def cd(path):
  return settings(directory=path)

def local(*a, **k):
  with settings(hosts=[localhost]):
    return bash(*a, **k)[0]

def runs_once(fn):
  results = {}
  @wraps(fn)
  def decorated(*a, **kv):
    key = (tuple(a), tuple(kv.items()))
    if not key in results:
      results[key] = fn(*a, **kv)
    return results[key]
  return decorated

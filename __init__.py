from shlex import quote as bash_quote
from .active import (
  get_active_tooler,
  set_active_tooler,
)
from .local import (
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

# Convenience methods run on the active tooler
add_submodule = lambda *a, **k: _tooler().add_submodule(*a, **k)
command = lambda *a, **k: _tooler().command(*a, **k)
proceed_or_abort = lambda *a, **k: _tooler().proceed_or_abort(*a, **k)
run = lambda *a, **k: _tooler().run(*a, **k)

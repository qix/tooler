from contextlib import contextmanager

from .hosts import (
  Host,
  SshHost,
  LocalHost,
  localhost,
)
from .shell import (
  _local_bash,
  _ssh_bash
)


DEFAULTS = {
  'directory': None,
  'hosts': [localhost],
  'tty': True,
}

def _ensure_host(host):
  if isinstance(host, Host):
    return host
  return SshHost(host)

class ToolerEnv(object):
  def __init__(self):
    self._stack = [DEFAULTS, {}]

  def __getattr__(self, prop):
    if not prop in DEFAULTS:
      return self.__getattribute__(prop)
    for values in reversed(self._stack):
      if prop in values:
        return values[prop]
    raise Exception('Expected to find property: ' + prop)

  def __setattr__(self, prop, value):
    if prop == '_stack':
      self.__dict__[prop] = value
    else:
      self.set(prop, value)

  def add_hosts(self, hosts):
    self.set(
      'hosts',
      (self.hosts if self.hosts else []) + hosts
    )

  def set(self, prop, value):
    if prop == 'hosts':
      value = [_ensure_host(v) for v in value]
    self._stack[-1][prop] = value

  @contextmanager
  def settings(self, **kv):
    original = self._stack[:]
    self._stack.append({})
    for prop, value in kv.items():
      self.set(prop, value)
    yield
    self._stack.pop()

    assert self._stack == original, (
      'Expected original stack after call to settings'
    )

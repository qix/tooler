from collections import namedtuple
from contextlib import contextmanager

from .shell import (
  _local_bash,
  _ssh_bash
)

SshHost = namedtuple('SshHost', (
  'username',
  'hostname',
  'name',
))

class Host(object):
  pass

class SshHost(Host):
  def __init__(self, name, hostname=None, username=None):
    self.name = name
    self.hostname = hostname if hostname is not None else name
    self.username = username

  def bash(self, command, stdin=None):
    return _ssh_bash(self, command, stdin=stdin)

class LocalHost(Host):
  def __init__(self):
    self.name = 'localhost'
    self.hostname = 'localhost'
    self.username = None

  def bash(self, command, stdin=None):
    return _local_bash(command, stdin=stdin)

localhost = LocalHost()

DEFAULTS = {
  'directory': None,
  'hosts': [localhost],
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

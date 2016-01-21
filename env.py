from contextlib import contextmanager

DEFAULTS = {
  'hosts': None,
}

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

  def set(self, prop, value):
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

env = ToolerEnv()

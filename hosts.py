import getpass
import sys
from collections import namedtuple

from .colors import (
  grey,
)

SshHost = namedtuple('SshHost', (
  'username',
  'hostname',
  'name',
))

class Host(object):
  def print(self, message, symbol=':', user=None, **kv):
    # @TODO: Ideally this could take multiline messages, and similar print()
    # arguments.

    if user is None:
      user = self.user

    # Don't show the user if it is the same as the current logged in user
    if user == getpass.getuser():
      user = None

    full_host = self.name
    if user is not None:
      full_host = '%s@%s' % (self.user, full_host)

    sys.stderr.write(grey(full_host + symbol) + ' ' + message + '\n')


class SshHost(Host):
  def __init__(self, name, hostname=None, user=None, port=22, trust_host_key=False):
    self.name = name
    self.hostname = hostname if hostname is not None else name
    self.user = user
    self.trust_host_key = trust_host_key
    self.port = port

class LocalHost(Host):
  def __init__(self):
    self.name = 'local'
    self.hostname = 'localhost'
    self.user = getpass.getuser()

localhost = LocalHost()

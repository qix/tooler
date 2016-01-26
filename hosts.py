import getpass
from collections import namedtuple

SshHost = namedtuple('SshHost', (
  'username',
  'hostname',
  'name',
))

class Host(object):
  pass

class SshHost(Host):
  def __init__(self, name, hostname=None, user=None, trust_host_key=False):
    self.name = name
    self.hostname = hostname if hostname is not None else name
    self.user = user
    self.trust_host_key = trust_host_key

class LocalHost(Host):
  def __init__(self):
    self.name = 'localhost'
    self.hostname = 'localhost'
    self.user = getpass.getuser()

localhost = LocalHost()

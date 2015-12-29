from collections import namedtuple

import asyncio, asyncssh, sys

SshHost = namedtuple('SshHost', ('username', 'host', 'port', 'nickname'))

class SshSession(asyncssh.SSHClientSession):
    def data_received(self, data, datatype):
        print(data, end='')

    def connection_lost(self, exc):
        if exc:
            print('SSH session error: ' + str(exc), file=sys.stderr)

class SshClient(asyncssh.SSHClient):
    def connection_made(self, conn):
        print('Connection made to %s.' % conn.get_extra_info('peername')[0])

    def auth_completed(self):
        print('Authentication successful.')

class SshConnection(object):
  def __init__(self, host):
    self.promise = asyncssh.create_connection(SshClient, host.host)

  @asyncio.coroutine
  def create_session(self, command):
    conn, client = yield from self.promise
    chan, session = yield from conn.create_session(SshSession, command)
    yield from chan.wait_closed()

class SshConnectionPool(object):
  def __init__(self):
    self.connections = {}

  def get_client(self, host):
    if not host in self.connections:
      self.connections[host] = SshConnection(host)
    return self.connections[host]

  @asyncio.coroutine
  def _host_execute(self, host, command):
    yield from self.get_client(host).create_session('hostname')

  @asyncio.coroutine
  def _execute(self, hosts, command):
    for host in hosts:
      yield from self._host_execute(host, command)

  def execute(self, hosts, command):
    try:
      asyncio.get_event_loop().run_until_complete(self._execute(hosts, command))
    except (OSError, asyncssh.Error) as exc:
      sys.exit('SSH connection failed: ' + str(exc))

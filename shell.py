import asyncio
import asyncssh
import getpass
import sys
from asyncio import (
  shield,
  sleep,
  subprocess,
  wait_for,
)
from io import BytesIO
from shlex import quote

from .colors import (
  green,
  grey,
  red,
)
from .hosts import (
  LocalHost,
  SshHost,
  localhost,
)
from .output import write_error
from .result import BashResult

PIPE = object()

BOLD_CHECKMARK = "\u2714"
BOLD_CROSS = "\u2718"

class BashCommand(object):
  def __init__(self, command, user=None, directory=None):

    if type(command) is list:
      command = ' '.join([quote(arg) for arg in command])

    self.directory = directory
    self.user = user
    self.string = command

    self.full = command
    if directory:
      self.full = 'cd %s && (%s)' % (quote(directory), self.full)
    self.full = ['bash', '-c', self.full]
    if user is not None:
      self.full = ['sudo', '--user=%s' % user, '--login'] + self.full

    self.full_string = ' '.join([quote(arg) for arg in self.full])

class OutputHandler(object):
  def __init__(
    self, host, command,
    prefix=True, capture=True, display=True, quiet=False
  ):
    self.command = command
    self.user = command.user or host.user
    self.is_current_user = (self.user == getpass.getuser())

    self.capture = capture
    self.display = display
    self.prefix = prefix
    self.quiet = quiet

    full_host = host.name

    # Root is represented by a symbol
    if self.user not in (None, 'root'):
      full_host = '%s@%s' % (self.user, full_host)

    # Simple skip out the localhost unless it's an interesting user
    if isinstance(host, LocalHost):
      if self.user in (None, 'root', getpass.getuser()):
        full_host = 'local'
    self.full_host = full_host

  def open(self):
    if self.quiet:
      return
    symbol = '#' if self.user == 'root' else '$'
    sys.stderr.write(grey('%s%s %s\n' % (
      self.full_host, symbol, self.command.string
    )))

  @asyncio.coroutine
  def collect(self, stdout_stream, stderr_stream):
    if self.display:
      stdout_tailer = self._tail_stream(grey('%s> ' % (
        self.full_host,
      )) if self.prefix else '', stdout_stream)

      if stderr_stream:
        stderr_tailer = self._tail_stream(grey('%s! ' % (
          self.full_host
        )) if self.prefix else '', stderr_stream)

      stdout_data = yield from stdout_tailer
      if stderr_stream:
        stderr_data = yield from stderr_tailer
    else:
      stdout_data = yield from stdout_stream.read()
      stdout_data = stdout_data.decode('utf-8')
      if stderr_stream:
        stderr_data = yield from stderr_stream.read()
        stderr_data = stderr_data.decode('utf-8')
    return (stdout_data, stderr_data if stderr_stream else None)

  def close(self, return_code):
    if self.quiet:
      return
    symbol = grey('[' + (
      green(BOLD_CHECKMARK) if return_code == 0 else red(BOLD_CROSS)
    ) + ']')

    if return_code == 0:
      sys.stderr.write(grey(self.full_host + ':') + ' ' + symbol + '\n')
    else:
      sys.stderr.write(
        grey(self.full_host) + ': ' + symbol + ' ' +
        'exit with %d\n' % return_code
      )

  def exception(self, exc):
    write_error('%s failed: %s' % (self.full_host, str(exc)))

  @asyncio.coroutine
  def _tail_stream(self, prefix, stream):
    # Don't write blank lines at the end
    line = True
    captured = []
    empty_lines = 0

    while line:
      line_promise = stream.readline()
      line_data = yield from line_promise

      # @TODO: 
      # while True:
      #   try:
      #     line_data = yield from wait_for(shield(line_promise), 15)
      #     break
      #   except asyncio.TimeoutError:
      #     sys.stderr.write(prefix + red('no output after 15s'))

      line = line_data.decode('utf-8')
      if self.capture:
        captured.append(line)
      if not line.strip():
        empty_lines += 1
      else:
        sys.stderr.write((prefix + '\n') * empty_lines)
        sys.stderr.write(prefix + line.rstrip() + '\n')
        empty_lines = 0
    return ''.join(captured) if self.capture else None

@asyncio.coroutine
def _local_bash(env, host, command, output, tty=None, user=None, stdin=None):
  assert type(stdin) in (type(None), bytes, str), 'restrictions for now'

  if type(stdin) is str:
    stdin = stdin.encode('utf-8')

  output.open()
  proc = yield from asyncio.create_subprocess_shell(
    command.full_string,
    stdin=subprocess.PIPE if stdin else None,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
  )

  collect_promise = output.collect(proc.stdout, proc.stderr)

  if stdin:
    proc.stdin.write(stdin)
    yield from proc.stdin.drain()
    proc.stdin.close()

  (stdout, stderr) = yield from collect_promise
  yield from proc.wait()
  output.close(proc.returncode)

  return BashResult(proc.returncode, stdout, stderr)

@asyncio.coroutine
def _ssh_bash(env, host, command, output, tty=None, stdin=None):
  assert type(stdin) in (type(None), bytes, str), 'restrictions for now'

  connection_options = {
    'agent_forwarding': True,
  }

  if host.trust_host_key:
    connection_options['known_hosts'] = None

  if tty is None:
    tty = env.tty

  with (yield from asyncssh.connect(
    host.hostname,
    **connection_options
  )) as conn:
    output.open()

    (stdin_stream, stdout_stream, stderr_stream) = (
      yield from conn.open_session(
        command.full_string,
        term_type='xterm-color' if tty else None,
        encoding=None,
      )
    )

    if stdin:
      if type(stdin) is str:
        stdin = stdin.encode('utf-8')
      stdin_stream.write(stdin)
      stdin_stream.write_eof()

    (stdout_data, stderr_data) = yield from output.collect(
      stdout_stream, stderr_stream if not tty else None
    )

    yield from stdout_stream.channel.wait_closed()

    status = stdout_stream.channel.get_exit_status()

    if status is None:
      raise Exception('Received a null status from ssh channel')

    output.close(status)

    return BashResult(status, stdout_data, stderr_data)

def bash(
  env, command,
  hosts=None, directory=None, user=None,
  quiet=False, capture=True, display=True, prefix=True,
  **kv
):
  command = BashCommand(
    command,
    user=user,
    directory=directory or env.directory,
  )

  if hosts is None:
    hosts = env.hosts

  loop = asyncio.get_event_loop()
  tasks = []

  outputs = [
    OutputHandler(
      host, command,
      capture=capture, display=display, quiet=quiet, prefix=prefix,
    )
    for host in hosts
  ]

  for (host, output) in zip(hosts, outputs):
    if isinstance(host, LocalHost):
      tasks.append(_local_bash(env, host, command, output, **kv))
    elif isinstance(host, SshHost):
      tasks.append(_ssh_bash(env, host, command, output, **kv))
    else:
      raise Exception('Unknown host type: %s' % host)

  result = asyncio.gather(*tasks, return_exceptions=True)
  loop.run_until_complete(result)
  task_results = result.result()

  first_exception = None

  bash_results = []
  for task_result, output in zip(result.result(), outputs):
    # If we had a good bash result, append it to the list
    if isinstance(task_result, BashResult):
      if task_result.code == 0:
        bash_results.append(task_result)
        continue
      task_result = Exception('Task exited with non-zero code')

    assert isinstance(task_result, Exception), 'Expected exception'
    output.exception(task_result)
    first_exception = first_exception or task_result

  if first_exception:
    raise first_exception

  return bash_results

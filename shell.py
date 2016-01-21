import asyncio
import asyncssh
import sys
from asyncio import subprocess
from io import BytesIO
from shlex import quote

from .result import BashResult

PIPE = object()

@asyncio.coroutine
def tail_output(prefix, stream):
  line = True
  data = ''
  while line:
    line = (yield from stream.readline()).decode('utf-8')
    data += line
    sys.stderr.write(prefix + line.strip() + '\n')
  return data

@asyncio.coroutine
def _local_bash(command, stdin=None):
  assert type(stdin) in (type(None), bytes, str), 'restrictions for now'

  if type(command) is list:
    command = ' '.join([quote(arg) for arg in command])

  if type(stdin) is str:
    stdin = stdin.encode('utf-8')

  sys.stderr.write('# %s\n' % command)

  proc = yield from asyncio.create_subprocess_shell(
    command,
    stdin=subprocess.PIPE if stdin else None,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
  )

  stdout = tail_output('> ', proc.stdout)
  stderr = tail_output('! ', proc.stderr)

  if stdin:
    proc.stdin.write(stdin)
    yield from proc.stdin.drain()
    proc.stdin.close()

  stdout = yield from stdout
  stderr = yield from stderr
  yield from proc.wait()
  sys.stderr.write('~ exit with %d\n' % proc.returncode)

  if proc.returncode != 0:
    raise Exception('Command returned non-zero')
  return BashResult(stdout, stderr)

@asyncio.coroutine
def _ssh_bash(host, command, stdin=None):
  if type(command) is list:
    command = ' '.join([quote(arg) for arg in command])
  sys.stderr.write('%s# %s\n' % (host.name, command))
  with (yield from asyncssh.connect(host.hostname)) as conn:
    (stdin, stdout, stderr) = (
      yield from conn.open_session(command)
    )
    assert not stdin, 'Not implemented'

    stdout = tail_output('%s> ' % host.name, stdout),
    stderr = tail_output('%s! ' % host.name, stderr),
    stdout = yield from stdout
    stderr = yield from stderr

    sys.stderr.write('%s~ exit with %d\n' % (host.name, status))

    status = stdout.channel.get_exit_status()
    if status != 0:
      raise Exception('Command returned non-zero')
    return BashResult(stdout, stderr)

def bash(env, command, user=None):
  if type(command) is list:
    command = ' '.join([quote(arg) for arg in command])
  if env.directory:
    command = 'cd %s && (%s)' % (quote(env.directory), command)

  command = ['bash', '-c', command]
  if user is not None:
    command = ['sudo', '--user=%s' % user, '--login'] + command

  loop = asyncio.get_event_loop()
  tasks = [host.bash(command) for host in env.hosts]
  result = asyncio.gather(*tasks)
  loop.run_until_complete(result)
  return result.result()

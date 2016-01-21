import asyncio
import asyncssh
import subprocess
import sys
from shlex import quote

from .env import env

def bash(command):
  if env.hosts is None:
    sys.stderr.write('> %s\n' % command)
    subprocess.check_call(['bash', '-c', command])
  else:
    loop = asyncio.get_event_loop()
    print(env.hosts)
    tasks = [
      ssh_bash(host, command)
      for host in env.hosts
    ]
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()

@asyncio.coroutine
def ssh_bash(host, command):
  with (yield from asyncssh.connect(host)) as conn:
    (stdin, stdout, stderr) = (
      yield from conn.open_session('bash -c ' + quote(command))
    )
    output = yield from stdout.read()
    print(host, output, end='')

    status = stdout.channel.get_exit_status()
    if status:
      print('Program exited with status %d' % status, file=sys.stderr)
    else:
      print('Program exited successfully')

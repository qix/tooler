import subprocess
import sys
from collections import namedtuple
from io import BytesIO

BashResult = namedtuple('BashResult', ('stdout', 'stderr'))

PIPE = object()

def bash(command, stdin=None, stdout=None, stderr=None):
  assert type(stdin) in (type(None), bytes, str), 'restrictions for now'
  assert stdout in (PIPE, None), 'restrictions for now'
  assert stderr in (PIPE, None), 'restrictions for now'

  if type(stdin) is str:
    stdin = stdin.encode('utf-8')

  sys.stderr.write('> %s\n' % command)

  proc = subprocess.Popen(
    ['bash', '-c', command],
    stdin=subprocess.PIPE if stdin else None,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
  )

  if type(stdin) is bytes:
    stdout, stderr = proc.communicate(stdin)
  else:
    stdout, stderr = proc.communicate()

  # @TODO: Actually stream stdout/stderr
  if stdout is not PIPE:
    sys.stdout.write(stdout.decode('utf-8'))
  if stderr is not PIPE:
    sys.stdout.write(stderr.decode('utf-8'))

  if proc.returncode != 0:
    raise Exception('Command returned non-zero')

  return BashResult(stdout, stderr)

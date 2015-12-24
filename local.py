import subprocess
import sys

def bash(command):
  sys.stderr.write('> %s\n' % command)
  subprocess.check_call(['bash', '-c', command])

#!/usr/bin/env python3
import shlex
from tooler import (
  Tooler,
  bash,
  shell_quote,
)

tooler = Tooler()

@tooler.command
def free(mount='/'):
  for result in bash('df -mah | grep %s' % shell_quote(mount + '$')):
    fs, blocks, used, available, used_pct, mount = shlex.split(result.stdout)
    result.host.print('Used %s (%s) of %s [%s]' % (used, used_pct, mount, fs))

if __name__ == '__main__':
  tooler.main()

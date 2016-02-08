#!/usr/bin/env python3
import shlex
from tooler import Tooler

tooler = Tooler()


@tooler.command
def free(mount='/'):
    for result in tooler.bash('df -mah | grep %s' % shlex.quote(mount + '$')):
        fs, blocks, use, available, use_pct, mount = shlex.split(result.stdout)
        result.host.print('Used %s (%s) of %s [%s]' % (
            use, use_pct, mount, fs))

if __name__ == '__main__':
    tooler.main()

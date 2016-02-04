#!/usr/bin/env python3

from tooler import Tooler
from tooler.library import (named, SshConfig)

import disk

tooler = Tooler()

tooler.add_submodule('disk', disk.tooler)
tooler.add_submodule('named', named.tooler)

if __name__ == '__main__':
    named.add_hosts(SshConfig().get_hosts())
    tooler.main(hosts=[])

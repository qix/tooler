#!/usr/bin/env python3

from tooler import Tooler
from tooler.library import named

import disk

tooler = Tooler()

tooler.add_submodule('disk', disk.tooler)
tooler.add_submodule('named', named.tooler)

if __name__ == '__main__':
    named.load_ssh_config()
    tooler.main()

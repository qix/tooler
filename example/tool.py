#!/usr/bin/env python3

from tooler import (
  Tooler,
)

import disk

tooler = Tooler()

tooler.add_submodule('disk', disk.tooler)

if __name__ == '__main__':
  tooler.main()

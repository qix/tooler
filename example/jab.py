#!/usr/bin/env python3
from tooler import (
  Tooler,
  command,
  proceed_or_abort,
)

import photo

tooler = Tooler()

tooler.add_submodule('photo', photo.tooler)

@tooler.command
def off():
  proceed_or_abort()
  print('Called off!')

if __name__ == '__main__':
  tooler.main()

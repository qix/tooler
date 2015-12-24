#!/usr/bin/env python3
from tooler import (
  add_submodule,
  command,
  proceed_or_abort,
  run,
)

import photo
add_submodule('photo', photo.tooler)

@command
def off():
  proceed_or_abort()
  print('Called off!')


if __name__ == '__main__':
  run()

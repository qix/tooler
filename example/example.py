#!/usr/bin/env python3
import io
import json
from pathlib import Path
import sys
from typing import List, Optional

from tooler import Tooler


tooler = Tooler()


@tooler.command(name="json")
def return_json():
  """
Sample function that has been given a different name
"""
  print("Tooler should render out the JSON value returned")
  return {"one": 1, "deep": {"structure": ["example"]}}


@tooler.command(
    shorthands={"o": "one", "w": "two", "f": "four", "t": "three", "F": "example_false"}
)
def options(
    one,
    two,
    three=3,
    four=4,
    example_true=True,
    example_false=False,
    example_none: Optional[bool] = None,
):
  """
Try `t examples tooler options --example-false` or `--no-example-true`
`three`, `four` should automatically be converted to integers

"""
  print("Got the following arguments:", file=sys.stderr)
  print("one =", repr(one))
  print("two =", repr(two))
  print("three =", repr(three))
  print("four =", repr(four))
  print("example_true =", repr(example_true))
  print("example_false =", repr(example_false))
  print("example_none =", repr(example_none))


@tooler.command
def read_file(data: io.BytesIO):
  """
Reads a given file. Tooler will automatically open the given path (or `-`) if
the argument type is BytesIO
"""
  print("Reading file contents")
  sys.stdout.write(data.read().decode("utf8"))
  print("File contents read!")


@tooler.command
def path_exists(*paths: List[Path]):
  """
Function takes a path object and returns if it exists or not
"""
  for path in paths:
    print(str(path) + ": " + ("Yes!" if path.exists() else "No!"))


@tooler.command(default=True)
def default(*args):
  print("You ran the default command!")
  print(json.dumps(args))


if __name__ == "__main__":
  tooler.run()

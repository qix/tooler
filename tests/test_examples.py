import json
import os
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

def run_example(command, input=None, check=True):
    return subprocess.run([
        'python', '-m', 'example.example',
        *command
     ], input=input, check=check, stdout=subprocess.PIPE, encoding="utf-8") 


def test_paths():
  with NamedTemporaryFile() as tmp:
    with open(Path(tmp) / "abc", "w") as f:
      f.write("ho")

    rv = run_example(["path-exists", Path(tmp) / "abc", Path(tmp) / "def"])
    assert rv.stdout == ("%s: Yes!\n%s: No!\n" % (Path(tmp) / "abc", Path(tmp) / "def"))


def test_read_file():
  example_str = "This is an example file!\n"
  with NamedTemporaryFile() as tmp:
    with open(Path(tmp) / "abc", "w") as f:
      f.write(example_str)

    rv = run_example(["read-file", Path(tmp) / "abc"])
    assert rv.stdout == example_str

  rv = run_example(["read-file", "-"], input="Whoah")
  assert rv.stdout == "Whoah"


def test_default():
  rv = run_example(["tooler"])
  assert json.loads(rv.stdout) == []

  rv = run_example(["hello"])
  assert json.loads(rv.stdout) == ["hello"]


def run_tooler_options(*args):
  result = run_example(["options", *args])
  rv = {}
  for line in result.stdout.split("\n"):
    if line.strip():
      (k, v) = line.strip().split(" = ")
      rv[k] = v
  return rv


def test_bool():
  base = {"four": "4", "one": "'a'", "three": "3", "two": "'b'"}

  assert run_tooler_options("a", "b") == {
      **base,
      "example_false": "False",
      "example_none": "None",
      "example_true": "True",
  }
  assert run_tooler_options("a", "b", "--example-true", "--example-false", "--example-none") == {
      **base,
      "example_false": "True",
      "example_none": "True",
      "example_true": "True",
  }
  assert run_tooler_options(
      "a", "b", "--no-example-true", "--no-example-false", "--no-example-none"
  ) == {**base, "example_false": "False", "example_none": "False", "example_true": "False"}


def test_shorthands():
  help_stderr = run_example(["options", "--help"]).stdout
  assert (
      help_stderr
      == """
Usage:
  -o, --one              required
  -w, --two              required
  -t, --three            default 3
  -f, --four             default 4
  --example-true         default yes
  -F, --example-false    default no
  --example-none
""".strip()
      + "\n"
  )

  assert run_tooler_options("1", "2", "--three=4", "-f3") == {
      "example_false": "False",
      "example_true": "True",
      "example_none": "None",
      "four": "3",
      "one": "'1'",
      "three": "4",
      "two": "'2'",
  }

  assert run_tooler_options("-oA", "-wB", "-F", "-f4444", "-t333") == {
      "example_false": "True",
      "example_true": "True",
      "example_none": "None",
      "four": "4444",
      "one": "'A'",
      "three": "333",
      "two": "'B'",
  }

# clide:
#   source: https://raw.githubusercontent.com/qix/clide/master/clide/english.py
#   version: 0.9.0
# License under the MIT License.
# See https://github.com/qix/clide/blob/master/LICENSE for details
'''
English language helper functions
'''

from typing import List


def and_join(strings: List[str]) -> str:
  assert len(strings) > 0
  if len(strings) == 1:
    return strings[0]
  else:
    return ", ".join(strings[:-1]) + " and " + strings[-1]

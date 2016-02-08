import fnmatch
import re
from tooler.command import raw_parser
from tooler.tooler import Tooler

tooler = Tooler()

hostlist = []


def _expand(name):
    'Expand x{a,b} => xa, xb;; x{1..3} => x1, x2, x3'
    match = re.match(r'^(.*?)\{(.*)\}(.*?)$', name)
    if not match:
        return [name]
    (pre, curly, post) = match.groups()
    if re.match(r'.+(\|.+)+', curly):
        expansion = curly.split('|')
    elif re.match(r'\d+\.\.\d+', curly):
        (first, last) = list(map(int, curly.split('..')))
        expansion = list(map(str, list(range(first, last + 1))))
    else:
        raise Exception('Could not run brace expansion on: %s' % name)
    return [pre + x + post for x in expansion]


def _expand_names(names):
    output = set()
    for name in names:
        output.update(_expand(name))
    return sorted(list(output), key=natural_key)


def _does_match(name, test):
    expanded = _expand(test)
    return any([fnmatch.fnmatch(name, option) for option in expanded])


def add_hosts(hosts):
    hostlist.extend(hosts)


@tooler.command(default=True, parser=raw_parser)
def named(selector, args):
    hosts = [
        host for host in hostlist
        if _does_match(host.name, selector)
    ]

    if not len(hosts):
        tooler.abort('Did not find any hosts matching: %s' % selector)
    with tooler.settings():
        tooler.env.add_hosts(hosts)
        return tooler.root.run(args)

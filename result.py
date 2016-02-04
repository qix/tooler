from collections import namedtuple

BashResult = namedtuple('BashResult', ('host', 'code', 'stdout', 'stderr'))

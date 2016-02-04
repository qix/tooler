# Tooler: Easier, better, faster python devops scripts

Features:

 * Simple access to local or remote (via asyncssh) shells
 * Neat legible output from multiple hosts


### Simple access to bash:

```python
import shlex
from tooler import Tooler

tooler = Tooler()

@tooler.command
def free(mount='/'):
    for result in tooler.bash('df -mah | grep %s' % shell_quote(mount + '$')):
        fs, blocks, use, available, use_pct, mnt = shlex.split(result.stdout)
        result.host.print('Used %s (%s) of %s [%s]' % (use, use_pct, mnt, fs))

if __name__ == '__main__':
    tooler.main()
```

```bash
$ ./disk.py free --mount=/
local$ df -mah | grep '/$'
local> /dev/mapper/ubuntu--vg-root  102G   69G   28G  72% /
local: [✔]
local: Used 69G (72%) of / [/dev/mapper/ubuntu--vg-root]
```

### Subcommands made easy

```python
from tooler import Tooler
from tooler.library import (named, SshConfig)

import disk

tooler = Tooler()

tooler.add_submodule('disk', disk.tooler)
tooler.add_submodule('named', named.tooler)

if __name__ == '__main__':
    named.add_hosts(SshConfig().get_hosts())
    tooler.main(hosts=[])
```

### Library of awesome sauce

```bash
$ ./tool.py named:nginx* disk.free
$ s named:nginx* free
nginx1$ df -mah | grep '/$'
nginx2$ df -mah | grep '/$'
nginx3$ df -mah | grep '/$'
nginx3> /dev/sda1        59G   37G   22G  64% /
nginx3: [✔]
nginx1> /dev/sda1        59G   37G   22G  64% /
nginx1: [✔]
nginx2> /dev/sda1        59G   37G   22G  64% /
nginx2: [✔]
nginx1: Used 37G (64%) of / [/dev/sda1]
nginx2: Used 37G (64%) of / [/dev/sda1]
nginx3: Used 37G (64%) of / [/dev/sda1]
```

### Thanks required:

 * [asyncssh](https://github.com/ronf/asyncssh) for an easy to use ssh client
 * [fabric](https://github.com/fabric/fabric) & [baker](https://bitbucket.org/mchaput/baker) as inspiration

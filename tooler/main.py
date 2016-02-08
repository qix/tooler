from .tooler import Tooler
from .library import (named, SshConfig)

tooler = Tooler()

tooler.add_submodule('named', named.tooler)


def ssh():
    named.add_hosts(SshConfig().get_hosts())

    # @TODO: This is due to a speed issue within asyncssh
    tooler.env.set('trust_host_key', True)

    tooler.main(hosts=[])


if __name__ == '__main__':
    ssh()

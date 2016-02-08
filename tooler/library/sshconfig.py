import os
import re
from collections import defaultdict

from tooler.hosts import SshHost


class SshConfig(object):

    def __init__(self):
        self.hosts = defaultdict(dict)
        for filename in ['/etc/ssh/config', '~/.ssh/config']:
            path = os.path.expanduser(filename)
            if os.path.exists(path):
                self.load_file(path)

    def load_file(self, filename):
        with open(filename, 'r') as file:
            return self.load(file)

    def load(self, stream):
        '''
        Load hosts from a ssh config file.
        @TODO: This needs a ton of work
        '''
        current_host = None

        for line in stream:
            match = re.match(r'^([a-zA-Z]+)\w*([^#]+)\w*(?:#.*)?$', line)
            if not match:
                continue
            (key, value) = [group.strip() for group in match.groups()]

            if key.lower() == 'host':
                current_host = value

            self.hosts[current_host][key.lower()] = value

    def get_hosts(self):
        return [
            SshHost(
                name=name,
                user=host.get('user'),
                port=int(host.get('port', 22)),
                hostname=host.get('hostname', host.get('host')),
            ) for name, host in self.hosts.items()
        ]

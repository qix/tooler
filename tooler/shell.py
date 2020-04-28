import asyncio
import getpass
import sys
from asyncio import (
    shield,
    sleep,
    subprocess,
    wait_for,
)
from io import BytesIO
from shlex import quote

from .colors import (
    green,
    grey,
    red,
)
from .hosts import (
    LocalHost,
    SshHost,
    localhost,
)
from .output import write_error
from .result import ShellResult

PIPE = object()

BOLD_CHECKMARK = "\u2714"
BOLD_CROSS = "\u2718"


class ShellException(Exception):
    pass


class BashCommand(object):

    def __init__(self, command, user=None, directory=None):
        if type(command) in (list, tuple):
            command = ' '.join([quote(arg) for arg in command])

        self.directory = directory
        self.user = user
        self.string = command

        self.full = command
        if directory:
            self.full = 'cd %s && (%s)' % (quote(directory), self.full)
        self.full = ['bash', '-c', self.full]
        if user is not None:
            self.full = ['sudo', '--user=%s' % user, '--login'] + self.full

        self.full_string = ' '.join([quote(arg) for arg in self.full])


class OutputHandler(object):

    def __init__(
        self, host, command,
        prefix=True, capture=True, display=True, quiet=False
    ):
        self.command = command
        self.host = host
        self.user = command.user or host.user
        self.is_current_user = (self.user == getpass.getuser())

        self.capture = capture
        self.display = display
        self.prefix = prefix
        self.quiet = quiet

    def open(self):
        if self.quiet:
            return
        self.host.print(
            grey(self.command.string),
            symbol='#' if self.user == 'root' else '$'
        )

    @asyncio.coroutine
    def _read_encoded(self, stream):
        if stream is None:
            return None
        data = yield from stream.read()
        return data.decode('utf-8')

    @asyncio.coroutine
    def collect(self, stdout_stream, stderr_stream):
        if not self.display:
            return (yield from asyncio.gather(
                self._read_encoded(stdout_stream),
                self._read_encoded(stderr_stream)
            ))

        return (yield from asyncio.gather(
            self._tail_stream('>', stdout_stream),
            self._tail_stream('>', stderr_stream),
        ))

    def close(self, return_code):
        if self.quiet:
            return
        symbol = grey('[' + (
            green(BOLD_CHECKMARK) if return_code == 0 else red(BOLD_CROSS)
        ) + ']')

        if return_code == 0:
            self.host.print(symbol)
        else:
            self.host.print('%s exit with %d' % (symbol, return_code))

    def exception(self, exc):
        self.host.print(red('[ERR!]', bold=True) + ' ' + str(exc))

    @asyncio.coroutine
    def _tail_stream(self, symbol, stream):
        if stream is None:
            return None

        # Don't write blank lines at the end
        line = True
        captured = []
        empty_lines = 0

        while line:
            line_promise = stream.readline()
            line_data = yield from line_promise

            # @TODO: give warnings if no data is coming in
            # while True:
            #   try:
            #     line_data = yield from wait_for(shield(line_promise), 15)
            #     break
            #   except asyncio.TimeoutError:
            #     sys.stderr.write(prefix + red('no output after 15s'))

            line = line_data.decode('utf-8')
            if self.capture:
                captured.append(line)
            if not line.strip():
                empty_lines += 1
            else:
                for index in range(empty_lines):
                    self.host.print(symbol=symbol)
                self.host.print(line.rstrip(), symbol=symbol)
                empty_lines = 0
        return ''.join(captured) if self.capture else None


@asyncio.coroutine
def _local_bash(env, host, command, output, tty=None, user=None, stdin=None):
    assert type(stdin) in (type(None), bytes, str), 'restrictions for now'

    if type(stdin) is str:
        stdin = stdin.encode('utf-8')

    output.open()
    proc = yield from asyncio.create_subprocess_shell(
        command.full_string,
        stdin=subprocess.PIPE if stdin else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    collect_promise = output.collect(proc.stdout, proc.stderr)

    if stdin:
        proc.stdin.write(stdin)
        yield from proc.stdin.drain()
        proc.stdin.close()

    (stdout, stderr) = yield from collect_promise
    yield from proc.wait()
    output.close(proc.returncode)

    return ShellResult(host, proc.returncode, stdout, stderr)


@asyncio.coroutine
def _ssh_bash(env, host, command, output, tty=None, stdin=None):
    assert type(stdin) in (type(None), bytes, str), 'restrictions for now'

    connection_options = {
        'agent_forwarding': True,
    }

    trust_host_key = host.trust_host_key
    if trust_host_key is None:
        trust_host_key = env.trust_host_key

    if trust_host_key:
        connection_options['known_hosts'] = None

    if tty is None:
        tty = env.tty

    with (yield from asyncssh.connect(
        host.hostname,
        **connection_options
    )) as conn:
        output.open()

        (stdin_stream, stdout_stream, stderr_stream) = (
            yield from conn.open_session(
                command.full_string,
                term_type='xterm-color' if tty else None,
                encoding=None,
            )
        )

        if stdin:
            if type(stdin) is str:
                stdin = stdin.encode('utf-8')
            stdin_stream.write(stdin)
            stdin_stream.write_eof()

        (stdout_data, stderr_data) = yield from output.collect(
            stdout_stream, stderr_stream if not tty else None
        )

        yield from stdout_stream.channel.wait_closed()

        status = stdout_stream.channel.get_exit_status()

        if status is None:
            raise ShellException('Received a null status from ssh channel')

        output.close(status)

        return ShellResult(host, status, stdout_data, stderr_data)


def bash(
    env, command,
    hosts=None, directory=None, user=None,
    quiet=False, capture=True, display=True, prefix=True,
    **kv
):
    command = BashCommand(
        command,
        user=user,
        directory=directory or env.directory,
    )

    if hosts is None:
        hosts = env.hosts

    loop = asyncio.get_event_loop()
    tasks = []

    outputs = [
        OutputHandler(
            host, command,
            capture=capture, display=display, quiet=quiet, prefix=prefix,
        )
        for host in hosts
    ]

    for (host, output) in zip(hosts, outputs):
        if isinstance(host, LocalHost):
            tasks.append(_local_bash(env, host, command, output, **kv))
        elif isinstance(host, SshHost):
            tasks.append(_ssh_bash(env, host, command, output, **kv))
        else:
            raise ShellException('Unknown host type: %s' % host)

    result = asyncio.gather(*tasks, return_exceptions=True)
    loop.run_until_complete(result)
    task_results = result.result()

    first_exception = None

    bash_results = []
    for task_result, output in zip(result.result(), outputs):
        # If we had a good bash result, append it to the list
        if isinstance(task_result, ShellResult):
            if task_result.code == 0:
                bash_results.append(task_result)
                continue
            task_result = ShellException('Task exited with non-zero code')

        assert isinstance(task_result, Exception), (
            'Shell calls should either return an Exception or ShellResult'
        )
        output.exception(task_result)
        first_exception = first_exception or task_result

    if first_exception:
        raise first_exception

    return bash_results

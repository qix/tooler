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

from .ansi import (
    green,
    white,
    red,
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


class OutputHandler:

    def __init__(
        self, name: str, command,
        prefix=True, capture=True, display=True, quiet=False
    ):
        self.command = command
        self.name = name
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
            white(self.command.string),
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
        symbol = white('[' + (
            green(BOLD_CHECKMARK) if return_code == 0 else red(BOLD_CROSS)
        ) + ']')

        if return_code == 0:
            self.print('', symbol=symbol)
        else:
            self.print('exit with %d' % return_code)

    def exception(self, exc):
        self.print(red('[ERR!]', bold=True) + ' ' + str(exc))

    def print(self, string, symbol=':'):
        print('%s%s%s' % (self.name, symbol, string), file=sys.stderr)

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
                    self.print('', symbol=symbol)
                self.print(line.rstrip(), symbol=symbol)
                empty_lines = 0
        return ''.join(captured) if self.capture else None


@asyncio.coroutine
def _local_bash(env, name: str, command, output, tty=None, user=None, stdin=None):
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

def bash(
    env, command,
    name=None, directory=None, user=None,
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

    tasks.append(_local_bash(env, name, command, output, **kv))

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

# Copyright © 2012-2015 Jakub Wilk <jwilk@jwilk.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import difflib
import errno
import inspect
import io
import multiprocessing as mp
import os
import re
import shlex
import signal
import subprocess as ipc
import sys
import traceback
import unittest

import nose
import nose.plugins

from .. import tools

here = os.path.dirname(__file__)

# ----------------------------------------

def this():
    '''
    Return function that called this function. (Hopefully!)
    '''
    return globals()[inspect.stack()[1][0].f_code.co_name]

# ----------------------------------------

_parse_etag = re.compile(r'([A-Z]): (([\w-]+).*)').match

def parse_etag(contents, path):
    match = _parse_etag(contents)
    if match is None:
        return
    t = ETag(match.group(1), path, match.group(2))
    return t

def etags_from_tagstring(obj, path):
    try:
        docstring = obj.tagstring
    except AttributeError:
        return
    for line in docstring.splitlines():
        line = line.lstrip()
        t = parse_etag(line, path)
        if t is not None:
            yield t

def tagstring(s):
    def update(x):
        x.tagstring = s
        return x
    return update

# ----------------------------------------

class ETag(object):

    _ellipsis = '<...>'
    _split = re.compile('({})'.format(re.escape(_ellipsis))).split

    def __init__(self, code, path, rest):
        self._s = s = '{code}: {path}: {rest}'.format(
            code=code,
            path=path,
            rest=rest,
        )
        self.tag = rest.split(None, 1)[0]
        regexp = ''.join(
            '.*' if chunk == self._ellipsis else re.escape(chunk)
            for chunk in self._split(s)
        )
        self._regexp = re.compile('^{}$'.format(regexp))

    def __eq__(self, other):
        if isinstance(other, str):
            return self._regexp.match(other)
        else:
            return NotImplemented

    def __str__(self):
        return self._s

    def __repr__(self):
        return repr(self._s)

# ----------------------------------------

def _get_signal_names():
    data = dict(
        (name, getattr(signal, name))
        for name in dir(signal)
        if re.compile('^SIG[A-Z0-9]*$').match(name)
    )
    try:
        if data['SIGABRT'] == data['SIGIOT']:
            del data['SIGIOT']
    except KeyError:
        pass
    try:
        if data['SIGCHLD'] == data['SIGCLD']:
            del data['SIGCLD']
    except KeyError:
        pass
    for name, n in data.items():
        yield n, name

_signal_names = dict(_get_signal_names())

def get_signal_name(n):
    try:
        return _signal_names[n]
    except KeyError:
        return str(n)

# ----------------------------------------

test_file_extensions = ('.mo', '.po', '.pot', '.pop')
# .pop is a special extension to trigger unknown-file-type

class Plugin(nose.plugins.Plugin):

    name = 'po-plugin'
    enabled = True

    def options(self, parser, env):
        pass

    def wantFile(self, path):
        if path.endswith(test_file_extensions):
            if path.startswith(os.path.join(os.path.abspath(here), '')):
                return True

    def loadTestsFromFile(self, path):
        if self.wantFile(path):
            yield TestCase(path)

    def wantFunction(self, func):
        if getattr(func, 'redundant', False):
            return False

class TestCase(unittest.TestCase):

    def __init__(self, path):
        super().__init__('_test')
        self.path = os.path.relpath(path)

    def _test(self):
        _test_file(self.path, basedir=None)

    def __str__(self):
        return self.path

class SubprocessError(Exception):
    pass

def queue_get(queue, process):
    '''
    Remove and return an item from the queue.
    Block until the process terminates.
    '''
    while True:
        try:
            return queue.get(timeout=1)
            # This semi-active waiting is ugly, but there doesn't seem be any
            # obvious better way.
        except mp.queues.Empty:
            if process.exitcode is None:
                continue
            else:
                raise

def run_i18nspector(options, path):
    commandline = os.environ.get('I18NSPECTOR_COMMANDLINE')
    if commandline is None:
        # We cheat here a bit, because exec(3)ing is very expensive.
        # Let's load the needed Python modules, and use multiprocessing to
        # “emulate” the command execution.
        import lib.cli
        assert lib.cli  # make pyflakes happy
        prog = os.path.join(here, os.pardir, os.pardir, 'i18nspector')
        commandline = [sys.executable, prog]
        queue = mp.Queue()
        child = mp.Process(
            target=_mp_run_i18nspector,
            args=(prog, options, path, queue)
        )
        child.start()
        [stdout, stderr] = (
            s.splitlines()
            for s in queue_get(queue, child)
        )
        child.join()
        rc = child.exitcode
    else:
        commandline = shlex.split(commandline)
        commandline += options
        commandline += [path]
        fixed_env = dict(os.environ, PYTHONIOENCODING='UTF-8')
        child = ipc.Popen(commandline, stdout=ipc.PIPE, stderr=ipc.PIPE, env=fixed_env)
        stdout, stderr = (
            s.decode('UTF-8').splitlines()
            for s in child.communicate()
        )
        rc = child.poll()
    assert isinstance(rc, int)
    if rc == 0:
        return stdout
    if rc < 0:
        message = ['command was interrupted by signal {sig}'.format(sig=get_signal_name(-rc))]  # pylint: disable=invalid-unary-operand-type
    else:
        message = ['command exited with status {rc}'.format(rc=rc)]
    message += ['']
    if stdout:
        message += ['stdout:']
        message += ['| ' + s for s in stdout] + ['']
    else:
        message += ['stdout: (empty)']
    if stderr:
        message += ['stderr:']
        message += ['| ' + s for s in stderr]
    else:
        message += ['stderr: (empty)']
    raise SubprocessError('\n'.join(message))

def _mp_run_i18nspector(prog, options, path, queue):
    with open(prog, 'rt', encoding='UTF-8') as file:
        code = file.read()
    sys.argv = [prog] + list(options) + [path]
    orig_stdout = sys.stdout
    orig_stderr = sys.stderr
    code = compile(code, prog, 'exec')
    io_stdout = io.StringIO()
    io_stderr = io.StringIO()
    gvars = dict(
        __file__=prog,
    )
    (sys.stdout, sys.stderr) = (io_stdout, io_stderr)
    try:
        try:
            exec(code, gvars)  # pylint: disable=exec-used
        finally:
            (sys.stdout, sys.stderr) = (orig_stdout, orig_stderr)
            stdout = io_stdout.getvalue()
            stderr = io_stderr.getvalue()
    except SystemExit:
        queue.put([stdout, stderr])
        raise
    except:  # pylint: disable=bare-except
        exctp, exc, tb = sys.exc_info()
        stderr += ''.join(
            traceback.format_exception(exctp, exc, tb)
        )
        queue.put([stdout, stderr])
        sys.exit(1)
        raise  # hi, pydiatra!
    else:
        queue.put([stdout, stderr])
        sys.exit(0)

def assert_emit_tags(path, etags, *, options=()):
    etags = list(etags)
    stdout = run_i18nspector(options, path)
    expected_failure = os.path.basename(path).startswith('xfail-')
    if stdout != etags:
        if expected_failure:
            raise nose.SkipTest('expected failure')
        str_etags = [str(x) for x in etags]
        message = ['Tags differ:', '']
        diff = list(
            difflib.unified_diff(str_etags, stdout, n=9999)
        )
        message += diff[3:]
        raise AssertionError('\n'.join(message))
    elif expected_failure:
        raise AssertionError('unexpected success')

class TestFileSyntaxError(Exception):
    pass

def _parse_test_header_file(file, path, *, comments_only):
    etags = []
    options = []
    for n, line in enumerate(file):
        orig_line = line
        if comments_only:
            if n == 0 and line.startswith('#!'):
                continue
            if line.startswith('# '):
                line = line[2:]
            else:
                break
        if line.startswith('--'):
            options += shlex.split(line)
        else:
            etag = parse_etag(line, path)
            if etag is None:
                if comments_only:
                    break
                else:
                    raise TestFileSyntaxError(orig_line)
            etags += [etag]
    return etags, options

def _parse_test_headers(path):
    # <path>.tags:
    try:
        file = open(path + '.tags', encoding='UTF-8')
    except IOError as exc:
        if exc.errno != errno.ENOENT:
            raise
    else:
        with file:
            return _parse_test_header_file(file, path, comments_only=False)
    # <path>.gen:
    try:
        file = open(path + '.gen', encoding='UTF-8', errors='ignore')
    except IOError as exc:
        if exc.errno != errno.ENOENT:
            raise
    else:
        with file:
            return _parse_test_header_file(file, path, comments_only=True)
    # <path>:
    with open(path, 'rt', encoding='UTF-8', errors='ignore') as file:
        return _parse_test_header_file(file, path, comments_only=True)

def _test_file(path, basedir=here):
    if basedir is not None:
        path = os.path.relpath(os.path.join(basedir, path), start=os.getcwd())
    options = []
    etags, options = _parse_test_headers(path)
    assert_emit_tags(path, etags, options=options)

def get_coverage_for_file(path):
    etags, options = _parse_test_headers(path)
    del options
    return (t.tag for t in etags)

def get_coverage_for_function(fn):
    for etag in etags_from_tagstring(fn, ''):
        yield etag.tag

def _get_test_filenames():
    for root, dirnames, filenames in os.walk(here):
        del dirnames
        for filename in filenames:
            if not filename.endswith(test_file_extensions):
                continue
            yield os.path.join(root, filename)

def test_file():
    for filename in _get_test_filenames():
        path = os.path.relpath(filename, start=here)
        yield _test_file, path
test_file.redundant = True  # not needed if the plugin is enabled

@tagstring('''
E: os-error No such file or directory
''')
def test_os_error_no_such_file():
    with tools.temporary_directory() as tmpdir:
        path = os.path.join(tmpdir, 'nonexistent.po')
        expected = etags_from_tagstring(this(), path)
        assert_emit_tags(path, expected)

@tagstring('''
E: os-error Permission denied
''')
def test_os_error_permission_denied():
    if os.getuid() == 0:
        raise nose.SkipTest('this test must not be run as root')
    with tools.temporary_directory() as tmpdir:
        path = os.path.join(tmpdir, 'denied.po')
        with open(path, 'wb'):
            pass
        os.chmod(path, 0)
        expected = etags_from_tagstring(this(), path)
        assert_emit_tags(path, expected)

# ----------------------------------------

def get_coverage():
    coverage = set()
    for filename in _get_test_filenames():
        for tag in get_coverage_for_file(filename):
            coverage.add(tag)
    for objname, obj in globals().items():
        if not objname.startswith('test_'):
            continue
        for tag in get_coverage_for_function(obj):
            coverage.add(tag)
    return coverage

# vim:ts=4 sts=4 sw=4 et

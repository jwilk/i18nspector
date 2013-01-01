# Copyright © 2012 Jakub Wilk <jwilk@jwilk.net>
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
import inspect
import os
import re
import shlex
import subprocess as ipc
import sys

from .. import aux

here = os.path.dirname(__file__)

# ----------------------------------------

def this():
    '''
    Return function that called this fuction. (Hopefully!)
    '''
    return globals()[inspect.stack()[1][0].f_code.co_name]

# ----------------------------------------

_parse_etag = re.compile('# ([A-Z]): (([\w-]+).*)').match

def parse_etag(contents, path, multi_line=False):
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

def assert_emit_tags(path, etags, *, options=()):
    etags = list(etags)
    commandline = os.environ.get('I18NSPECTOR_COMMANDLINE')
    if commandline is None:
        prog = os.path.join(here, os.pardir, os.pardir, 'i18nspector')
        commandline = [sys.executable, prog]
    else:
        commandline = shlex.split(commandline)
    commandline += options
    commandline += [path]
    fixed_env = dict(os.environ, LC_ALL='C')
    stdout = ipc.check_output(commandline, env=fixed_env)
    stdout = stdout.decode('ASCII').splitlines()
    if stdout != etags:
        str_etags = [str(x) for x in etags]
        message = ['Tags differ:', '']
        diff = list(
            difflib.unified_diff(str_etags, stdout, n=9999)
        )
        message += diff[3:]
        raise AssertionError('\n'.join(message))

def _test_file(path):
    path = os.path.relpath(os.path.join(here, path), start=os.getcwd())
    options = []
    etags = []
    with open(path, 'rt', encoding='ASCII', errors='ignore') as file:
        for line in file:
            if not line.startswith('# '):
                break
            etag = parse_etag(line, path)
            if etag is None:
                if line.startswith('# --'):
                    options += shlex.split(line[2:])
                    continue
                break
            etags += [etag]
    assert_emit_tags(path, etags, options=options)

def get_coverage_for_file(path):
    with open(path, 'rt', encoding='ASCII', errors='ignore') as file:
        for line in file:
            if not line.startswith('# '):
                break
            etag = parse_etag(line, '')
            if etag is None:
                continue
            yield etag.tag

def get_coverage_for_function(fn):
    for etag in etags_from_tagstring(fn, ''):
        yield etag.tag

def _get_test_filenames():
    for root, dirnames, filenames in os.walk(here):
        for filename in filenames:
            if not filename.endswith(('.mo', '.po', '.pot', '.pop')):
                # .pop is a special extension to trigger unknown-file-type
                continue
            yield os.path.join(root, filename)

def test_file():
    for filename in _get_test_filenames():
        path = os.path.relpath(filename, start=here)
        yield _test_file, path

@tagstring('''
# E: os-error No such file or directory
''')
def test_os_error_no_such_file():
    with aux.temporary_directory() as tmpdir:
        path = os.path.join(tmpdir, 'nonexistent.po')
        expected = etags_from_tagstring(this(), path)
        assert_emit_tags(path, expected)

@tagstring('''
# E: os-error Permission denied
''')
def test_os_error_permission_denied():
    with aux.temporary_directory() as tmpdir:
        path = os.path.join(tmpdir, 'denied.po')
        with open(path, 'wb'):
            pass
        os.chmod(path, 0)
        expected = etags_from_tagstring(this(), path)
        assert_emit_tags(path, expected)

@tagstring('''
# E: invalid-mo-file
''')
def test_empty_mo_file():
    with aux.temporary_directory() as tmpdir:
        path = os.path.join(tmpdir, 'empty-mo-file.mo')
        with open(path, 'wb'):
            pass
        expected = etags_from_tagstring(this(), path)
        assert_emit_tags(path, expected)

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

# vim:ts=4 sw=4 et

# Copyright © 2012-2022 Jakub Wilk <jwilk@jwilk.net>
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

import functools
import os
import sys
import tempfile
import traceback
import unittest

tc = unittest.TestCase('__hash__')

assert_almost_equal = tc.assertAlmostEqual
assert_equal = tc.assertEqual
assert_false = tc.assertFalse
assert_greater = tc.assertGreater
assert_in = tc.assertIn
assert_is = tc.assertIs
assert_is_instance = tc.assertIsInstance
assert_is_none = tc.assertIsNone
assert_is_not_none = tc.assertIsNotNone
assert_less = tc.assertLess
assert_list_equal = tc.assertListEqual
assert_not_equal = tc.assertNotEqual
assert_not_in = tc.assertNotIn
assert_raises = tc.assertRaises
assert_sequence_equal = tc.assertSequenceEqual
assert_true = tc.assertTrue

del tc

def _collect_yielded(generator):
    # Convert test generator to something the test harness understands.
    # For nose, we don't need to do anything.
    # For pytest, see the tests.conftest module.
    return generator
collect_yielded = _collect_yielded

temporary_file = functools.partial(
    tempfile.NamedTemporaryFile,
    prefix='i18nspector.tests.',
)

temporary_directory = functools.partial(
    tempfile.TemporaryDirectory,
    prefix='i18nspector.tests.',
)

class IsolatedException(Exception):
    pass

def _n_relevant_tb_levels(tb):
    n = 0
    while tb and '__unittest' not in tb.tb_frame.f_globals:
        n += 1
        tb = tb.tb_next
    return n

def fork_isolation(f):

    EXIT_EXCEPTION = 101
    EXIT_SKIP_TEST = 102

    exit = os._exit  # pylint: disable=redefined-builtin,protected-access
    # sys.exit() can't be used here, because the test harness catches
    # all exceptions, including SystemExit

    # pylint:disable=consider-using-sys-exit

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        readfd, writefd = os.pipe()
        pid = os.fork()
        if pid == 0:
            # child:
            os.close(readfd)
            try:
                f(*args, **kwargs)
            except unittest.SkipTest as exc:
                s = str(exc).encode('UTF-8')
                with os.fdopen(writefd, 'wb') as fp:
                    fp.write(s)
                exit(EXIT_SKIP_TEST)
            except Exception:  # pylint: disable=broad-except
                exctp, exc, tb = sys.exc_info()
                s = traceback.format_exception(exctp, exc, tb, _n_relevant_tb_levels(tb))
                s = str.join('', s).encode('UTF-8')
                del tb
                with os.fdopen(writefd, 'wb') as fp:
                    fp.write(s)
                exit(EXIT_EXCEPTION)
            exit(0)
        else:
            # parent:
            os.close(writefd)
            with os.fdopen(readfd, 'rb') as fp:
                msg = fp.read()
            msg = msg.decode('UTF-8').rstrip('\n')
            pid, status = os.waitpid(pid, 0)
            if status == (EXIT_EXCEPTION << 8):
                raise IsolatedException() from Exception('\n\n' + msg)
            elif status == (EXIT_SKIP_TEST << 8):
                raise unittest.SkipTest(msg)
            elif status == 0 and msg == '':
                pass
            else:
                raise RuntimeError(f'unexpected isolated process status {status}')

    # pylint:enable=consider-using-sys-exit

    return wrapper

basedir = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
)
basedir = os.environ.get('I18NSPECTOR_BASEDIR', basedir)
basedir = os.path.join(basedir, '')
os.stat(basedir)
datadir = os.path.join(basedir, 'data')
os.stat(datadir)
sys.path[:0] = [basedir]

# vim:ts=4 sts=4 sw=4 et

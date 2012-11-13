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

import datetime
import os
import tempfile
import warnings

import lib.misc

from nose.tools import (
    assert_equal,
    assert_false,
    assert_is,
    assert_is_not_none,
    assert_is_instance,
    assert_raises,
    assert_true,
)

def sorted_iterable():
    yield 1
    yield 2
    yield 4

def unsorted_iterable():
    yield 1
    yield 4
    yield 2

class test_is_sorted:

    def test_sorted(self):
        iterable = sorted_iterable()
        is_sorted = lib.misc.is_sorted(iterable)
        assert_true(is_sorted)

    def test_not_sorted(self):
        iterable = unsorted_iterable()
        is_sorted = lib.misc.is_sorted(iterable)
        assert_false(is_sorted)

class test_check_sorted:

    def test_sorted(self):
        iterable = sorted_iterable()
        lib.misc.check_sorted(iterable)

    def test_not_sorted(self):
        iterable = unsorted_iterable()
        with assert_raises(lib.misc.DataIntegrityError):
            lib.misc.check_sorted(iterable)

class test_not_overriden:

    class B(object):
        @lib.misc.not_overridden
        def f(self, x, y):
            pass

    class C(B):
        def f(self, x, y):
            return x * y

    def test_not_overriden(self):
        def show(message, category, filename, lineno, file=None, line=None):
            with assert_raises(lib.misc.NotOverriddenWarning):
                raise message
        with warnings.catch_warnings():
            warnings.showwarning = show
            assert_is(self.B().f(6, 7), None)

    def test_overriden(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('error', category=lib.misc.NotOverriddenWarning)
            result = self.C().f(6, 7)
            assert_equal(result, 42)

class test_os_release:

    def _test(self, path, **like):
        os_release = lib.misc.OSRelease(path=path)
        for os, expected in like.items():
            if expected:
                assert_true(os_release.is_like(os))
            else:
                assert_false(os_release.is_like(os))

    def _tmpfile(self, contents):
        file = tempfile.NamedTemporaryFile(
            prefix='gettext-inspector.os-release.',
            mode='wt', encoding='ASCII'
        )
        file.write(contents)
        file.flush()
        return file

    def test_nonexistent(self):
        tmpdir = tempfile.mkdtemp()
        try:
            self._test(os.path.join(tmpdir, 'nonexistent'),
               debian=False,
               ubuntu=False,
               pld=False,
            )
        finally:
            os.rmdir(tmpdir)

    def test_io_error(self):
        with self._tmpfile('') as file:
            os.chmod(file.name, 0)
            with assert_raises(IOError):
                self._test(file.name)

    def test_syntax_error(self):
        with self._tmpfile('ID="debian\n') as file:
            self._test(file.name,
                debian=False,
                ubuntu=False,
                pld=False,
            )

    def test_empty(self):
        with self._tmpfile('') as file:
            self._test(file.name,
                debian=False,
                ubuntu=False,
                pld=False,
            )

    def test_debian(self):
        with self._tmpfile('ID="debian"\n') as file:
            self._test(file.name,
                debian=True,
                ubuntu=False,
                pld=False,
            )

    def test_debian_derivative(self):
        with self._tmpfile('ID="ubuntu"\nID_LIKE="debian"') as file:
            self._test(file.name,
                debian=True,
                ubuntu=True,
                pld=False,
            )

    def test_non_debian(self):
        with self._tmpfile('ID="pld"\n') as file:
            self._test(file.name,
                debian=False,
                ubuntu=False,
                pld=True,
            )

def test_utc_now():
    now = lib.misc.utc_now()
    assert_is_instance(now, datetime.datetime)
    assert_is_not_none(now.tzinfo)
    assert_equal(now.tzinfo.utcoffset(now), datetime.timedelta(0))

# vim:ts=4 sw=4 et

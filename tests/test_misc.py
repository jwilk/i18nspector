# Copyright © 2012-2016 Jakub Wilk <jwilk@jwilk.net>
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
import stat
import tempfile
import time

import lib.misc as M

from nose.tools import (
    assert_almost_equal,
    assert_equal,
    assert_is_instance,
    assert_is_not_none,
    assert_raises,
    assert_true,
)

from . import tools

class test_unsorted:

    def t(self, lst, expected):
        assert_is_instance(lst, list)
        r = M.unsorted(lst)
        assert_equal(r, expected)
        r = M.unsorted(x for x in lst)
        assert_equal(r, expected)

    def test_0(self):
        self.t([], None)

    def test_1(self):
        self.t([17], None)

    def test_2(self):
        self.t([17, 23], None)
        self.t([23, 17], (23, 17))

    def test_3(self):
        self.t([17, 23, 37], None)
        self.t([17, 37, 23], (37, 23))
        self.t([23, 17, 37], (23, 17))
        self.t([23, 37, 17], (37, 17))
        self.t([37, 17, 23], (37, 17))
        self.t([37, 23, 17], (37, 23))

    def test_inf(self):
        def iterable():
            yield 17
            yield 37
            while True:
                yield 23
        r = M.unsorted(iterable())
        assert_equal(r, (37, 23))

class test_check_sorted:

    def test_sorted(self):
        M.check_sorted([17, 23, 37])

    def test_unsorted(self):
        with assert_raises(M.DataIntegrityError) as cm:
            M.check_sorted([23, 37, 17])
        assert_equal(str(cm.exception), '37 > 17')

def test_sorted_vk():
    lst = ['eggs', 'spam', 'ham']
    d = dict(enumerate(lst))
    assert_equal(
        lst,
        list(M.sorted_vk(d))
    )

class test_utc_now:

    def test_types(self):
        now = M.utc_now()
        assert_is_instance(now, datetime.datetime)
        assert_is_not_none(now.tzinfo)
        assert_equal(now.tzinfo.utcoffset(now), datetime.timedelta(0))

    @tools.fork_isolation
    def test_tz_resistance(self):
        def t(tz):
            os.environ['TZ'] = tz
            time.tzset()
            return M.utc_now()
        now1 = t('Etc/GMT-4')
        now2 = t('Etc/GMT+2')
        tdelta = (now1 - now2).total_seconds()
        assert_almost_equal(tdelta, 0, places=1)

class test_format_range:

    def t(self, x, y, max, expected):  # pylint: disable=redefined-builtin
        assert_equal(
            M.format_range(range(x, y), max=max),
            expected
        )

    def test_max_is_lt_4(self):
        with assert_raises(ValueError):
            self.t(5, 10, 3, None)

    def test_len_lt_max(self):
        self.t(5, 10, 4, '5, 6, ..., 9')
        self.t(23, 43, 6, '23, 24, 25, 26, ..., 42')

    def test_len_eq_max(self):
        self.t(5, 10, 5, '5, 6, 7, 8, 9')

    def test_len_gt_max(self):
        self.t(5, 10, 6, '5, 6, 7, 8, 9')

    def test_huge(self):
        self.t(5, 42 ** 17, 5, '5, 6, 7, ..., 3937657486715347520027492351')

def test_namespace():
    ns = M.Namespace()
    with assert_raises(AttributeError):
        ns.eggs  # pylint: disable=pointless-statement
    ns.eggs = 37
    assert_equal(ns.eggs, 37)

def test_throwaway_tempdir():
    with M.throwaway_tempdir('test'):
        d = tempfile.gettempdir()
        st = os.stat(d)
        assert_equal(stat.S_IMODE(st.st_mode), 0o700)
        assert_true(stat.S_ISDIR(st.st_mode))

# vim:ts=4 sts=4 sw=4 et

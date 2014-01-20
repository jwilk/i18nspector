# Copyright © 2012, 2013, 2014 Jakub Wilk <jwilk@jwilk.net>
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

import nose
from nose.tools import (
    assert_equal,
    assert_false,
    assert_is_instance,
    assert_is_not_none,
    assert_raises,
    assert_true,
)

from . import aux

import lib.misc as M

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
        is_sorted = M.is_sorted(iterable)
        assert_true(is_sorted)

    def test_not_sorted(self):
        iterable = unsorted_iterable()
        is_sorted = M.is_sorted(iterable)
        assert_false(is_sorted)

class test_check_sorted:

    def test_sorted(self):
        iterable = sorted_iterable()
        M.check_sorted(iterable)

    def test_not_sorted(self):
        iterable = unsorted_iterable()
        with assert_raises(M.DataIntegrityError):
            M.check_sorted(iterable)

def test_utc_now():
    now = M.utc_now()
    assert_is_instance(now, datetime.datetime)
    assert_is_not_none(now.tzinfo)
    assert_equal(now.tzinfo.utcoffset(now), datetime.timedelta(0))

class test_format_range:

    def t(self, x, y, max, expected):
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

# vim:ts=4 sw=4 et

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

import lib.dates

from nose.tools import (
    assert_equal,
    assert_less,
    assert_raises,
    assert_true,
)

F = lib.dates.fix_date_format
P = lib.dates.parse_date

class test_fix_date_format:

    def test_boilerplace(self):
        assert_true(F('YEAR-MO-DA HO:MI+ZONE') is None)

    def test_okay(self):
        d = '2010-10-13 01:27+0200'
        assert_equal(F(d), d)

    def test_space_before_tz(self):
        assert_equal(
            F('2010-05-12 18:36 -0400'),
              '2010-05-12 18:36-0400'
        )

    def test_seconds(self):
        assert_equal(
            F('2010-03-27 12:44:19+0100'),
              '2010-03-27 12:44+0100'
        )

    def test_colon_in_tz(self):
        assert_equal(
            F('2001-06-25 18:55+02:00'),
              '2001-06-25 18:55+0200'
        )

    def test_nonnumeric_tz(self):
        assert_true(F('2004-04-20 13:24+CEST') is None)

    def test_only_date(self):
        assert_true(F('2008-01-09') is None)

    def test_nonexistent(self):
        assert_true(F('2010-02-29 19:49+0200') is None)

class test_parse_date:

    def test_nonexistent(self):
        with assert_raises(ValueError):
            P('2010-02-29 19:49+0200')

    def test_existent(self):
        d = P('2003-09-08 21:26+0200')
        assert_equal(d.second, 0)
        assert_true(isinstance(d, datetime.datetime))
        assert_equal(str(d), '2003-09-08 21:26:00+02:00')

def test_constants():
    d = P('2008-04-03 16:06+0300')
    assert_less(d, lib.dates.now)
    assert_less(lib.dates.gettext_epoch, d)

# vim:ts=4 sw=4 et

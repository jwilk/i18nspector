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

import lib.gettext

from nose.tools import (
    assert_equal,
    assert_false,
    assert_greater,
    assert_is_instance,
    assert_is_none,
    assert_less,
    assert_raises,
)

basedir = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
)
datadir = os.path.join(basedir, 'data')
info = lib.gettext.GettextInfo(datadir)

class test_gettext_info:

    def test_nonempty(self):
        # XXX Update this number after editing data/po-header-fields:
        expected = 12
        assert_equal(len(info.po_header_fields), expected)

    def test_no_x(self):
        for field in info.po_header_fields:
            assert_false(field.startswith('X-'))

class test_plurals:

    _error = lib.gettext.PluralFormsSyntaxError

    def _pf(self, s):
        return lib.gettext.parse_plural_forms(s)

    def _pe(self, s):
        return lib.gettext.parse_plural_expression(s)

    def test_plural_exp_c_operator(self):
        self._pe('6 * 7')

    def test_plural_exp_py_operator(self):
        self._pe('6 && 7')

    def test_plural_exp_conditional(self):
        self._pe('6 ? 7 : 42')

    def test_plural_exp_nested_conditional(self):
        self._pe('(2 ? 3 : 7) ? 23 : 37')

    def test_plural_exp_unbalanced_parentheses(self):
        with assert_raises(self._error):
            self._pe('(6 * 7')
        with assert_raises(self._error):
            self._pe('6 * 7)')

    def test_plural_exp_junk_token(self):
        with assert_raises(self._error):
            self._pe('6 # 7')

    def test_plural_forms_nplurals_0(self):
        with assert_raises(self._error):
            self._pf('nplurals=0; plural=0;')

    def test_plural_forms_nplurals_positive(self):
        for i in 1, 2, 10, 42:
            self._pf('nplurals={}; plural=0;'.format(i))

    def test_plural_forms_missing_trailing_semicolon(self):
        self._pf('nplurals=1; plural=0')


class test_fix_date_format:

    def _test(self, old, expected):
        new = lib.gettext.fix_date_format(old)
        if expected is None:
            assert_is_none(new)
        else:
            assert_equal(new, expected)


    def test_boilerplate(self):
        self._test('YEAR-MO-DA HO:MI+ZONE', None)

    def test_okay(self):
        d = '2010-10-13 01:27+0200'
        self._test(d, d)

    def test_space_before_tz(self):
        self._test(
            '2010-05-12 18:36 -0400',
            '2010-05-12 18:36-0400'
        )

    def test_seconds(self):
        self._test(
            '2010-03-27 12:44:19+0100',
            '2010-03-27 12:44+0100'
        )

    def test_colon_in_tz(self):
        self._test(
            '2001-06-25 18:55+02:00',
            '2001-06-25 18:55+0200'
        )

    def test_nonnumeric_tz(self):
        self._test('2004-04-20 13:24+CEST', None)

    def test_only_date(self):
        self._test('2008-01-09', None)

    def test_nonexistent(self):
        self._test('2010-02-29 19:49+0200', None)

class test_parse_date:

    _parse = staticmethod(lib.gettext.parse_date)

    def test_nonexistent(self):
        with assert_raises(lib.gettext.DateSyntaxError):
            self._parse('2010-02-29 19:49+0200')

    def test_existent(self):
        d = self._parse('2003-09-08 21:26+0200')
        assert_equal(d.second, 0)
        assert_is_instance(d, datetime.datetime)
        assert_equal(str(d), '2003-09-08 21:26:00+02:00')

    def test_epoch(self):
        d = self._parse('2008-04-03 16:06+0300')
        assert_less(lib.gettext.epoch, d)

# vim:ts=4 sw=4 et

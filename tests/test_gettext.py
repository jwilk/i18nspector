# Copyright © 2012, 2013 Jakub Wilk <jwilk@jwilk.net>
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

from nose.tools import (
    assert_equal,
    assert_false,
    assert_is_instance,
    assert_is_none,
    assert_is_not_none,
    assert_less,
    assert_raises,
)

from . import aux

import lib.gettext

info = lib.gettext.GettextInfo(aux.datadir)

class test_header_fields:

    def test_nonempty(self):
        # XXX Update this number after editing data/header-fields:
        expected = 12
        assert_equal(len(info.header_fields), expected)

    def test_no_x(self):
        for field in info.header_fields:
            assert_false(field.startswith('X-'))

class test_plurals:

    _error = lib.gettext.PluralFormsSyntaxError

    def _pf(self, s):
        return lib.gettext.parse_plural_forms(s)

    def _pe(self, s, n=None, fn=None):
        f = lib.gettext.parse_plural_expression(s)
        if n is not None:
            assert_is_not_none(fn)
            assert_equal(f(n), fn)

    def test_plural_exp_add(self):
        self._pe('17 + n', 6, 23)

    def test_plural_exp_unary_plus(self):
        self._pe('17 + (+ n)', 6, 23)

    def test_plural_exp_sub(self):
        self._pe('n - 23', 37, 14)

    def test_plural_exp_unary_minus(self):
        with assert_raises(OverflowError):
            self._pe('37 + (- n)', 23, 14)
        self._pe('37 + (- n)', 0, 37)

    def test_plural_exp_mul(self):
        self._pe('6 * n', 7, 42)

    def test_plural_exp_div(self):
        self._pe('105 / n', 17, 6)

    def test_plural_exp_div_by_0(self):
        with assert_raises(ZeroDivisionError):
            self._pe('105 / n', 0, False)

    def test_plural_exp_mod(self):
        self._pe('105 % n', 17, 3)

    def test_plural_exp_mod_by_0(self):
        with assert_raises(ZeroDivisionError):
            self._pe('105 % n', 0, False)

    def test_plural_exp_and(self):
        self._pe('n && 6', 7, 1)
        self._pe('n && 6', 0, 0)
        self._pe('n && (6 / 0)', 0, 0)  # no ZeroDivisionError
        self._pe('n && 0', 7, 0)
        self._pe('n && 0', 0, 0)

    def test_plural_exp_or(self):
        self._pe('n || 6', 7, 1)
        self._pe('n || (6 / 0)', 7, 1)  # no ZeroDivisionError
        self._pe('n || 6', 0, 1)
        self._pe('n || 0', 7, 1)
        self._pe('n || 0', 0, 0)

    def test_plural_exp_gt(self):
        self._pe('n > 37', 23, 0)
        self._pe('n > 37', 37, 0)
        self._pe('n > 37', 42, 1)

    def test_plural_exp_ge(self):
        self._pe('n >= 37', 23, 0)
        self._pe('n >= 37', 37, 1)
        self._pe('n >= 37', 42, 1)

    def test_plural_exp_lt(self):
        self._pe('n < 37', 23, 1)
        self._pe('n < 37', 37, 0)
        self._pe('n < 37', 42, 0)

    def test_plural_exp_le(self):
        self._pe('n <= 37', 23, 1)
        self._pe('n <= 37', 37, 1)
        self._pe('n <= 37', 42, 0)

    def test_plural_exp_eq(self):
        self._pe('n == 37', 23, 0)
        self._pe('n == 37', 37, 1)
        self._pe('n == 37', 42, 0)

    def test_plural_exp_ne(self):
        self._pe('n != 37', 23, 1)
        self._pe('n != 37', 37, 0)
        self._pe('n != 37', 42, 1)

    def test_plural_exp_multi_compare(self):
        self._pe('1 < n == 3 <= 4', 1, 0)  # False in Python
        self._pe('1 < n == 3 <= 4', 2, 1)  # False in Python
        self._pe('1 < n == 3 <= 4', 3, 1)  # True in Python
        self._pe('1 < n == 3 <= 4', 4, 1)  # False in Python
        self._pe('2 == 2 == n', 2, 0)  # True in Python
        self._pe('2 == 2 == n', 1, 1)  # False in Python

    def test_plural_exp_neg(self):
        self._pe('! n', 0, 1)
        self._pe('! n', 1, 0)
        self._pe('! n', 69, 0)

    def test_plural_exp_conditional(self):
        self._pe('6 ? 7 : 42')

    def test_plural_exp_nested_conditional(self):
        self._pe('(2 ? 3 : 7) ? 23 : 37')

    def test_plural_exp_unbalanced_parentheses(self):
        with assert_raises(self._error):
            self._pe('(6 * 7')
        with assert_raises(self._error):
            self._pe('6 * 7)')

    def test_plural_exp_dangling_binop(self):
        with assert_raises(self._error):
            self._pe('6 +')

    def test_plural_exp_junk_token(self):
        with assert_raises(self._error):
            self._pe('6 # 7')

    def test_plural_exp_exotic_whitespace(self):
        with assert_raises(self._error):
            self._pe('6 *\xa07')

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
        new = info.fix_date_format(old)
        if expected is None:
            assert_is_none(new)
        else:
            assert_equal(new, expected)

    def test_boilerplate(self):
        self._test('YEAR-MO-DA HO:MI+ZONE', None)

    def test_okay(self):
        d = '2010-10-13 01:27+0200'
        self._test(d, d)

    def test_double_space(self):
        d = '2011-11-08  16:49+0200'
        self._test(d, d.replace('  ', ' '))

    def test_space_before_tz(self):
        self._test(
            '2010-05-12 18:36 -0400',
            '2010-05-12 18:36-0400',
        )

    def test_seconds(self):
        self._test(
            '2010-03-27 12:44:19+0100',
            '2010-03-27 12:44+0100',
        )

    def test_colon_in_tz(self):
        self._test(
            '2001-06-25 18:55+02:00',
            '2001-06-25 18:55+0200',
        )

    def test_t_seperator(self):
        self._test(
            '2003-04-01T09:08+0500',
            '2003-04-01 09:08+0500',
        )

    def test_missing_tz(self):
        self._test('2002-01-01 03:05', None)

    def test_tz_hint(self):
        assert_equal(
            info.fix_date_format('2002-01-01 03:05', tz_hint='+0900'),
            '2002-01-01 03:05+0900',
        )

    def test_gmt_before_tz(self):
        self._test(
            '2001-07-28 11:19GMT+0200',
            '2001-07-28 11:19+0200',
        )
        self._test(
            '2001-12-20 17:22GMT+0100',
            '2001-12-20 17:22+0100',
        )

    def test_pygettext(self):
        self._test(
            '2004-04-20 13:24+CEST',
            '2004-04-20 13:24+0200',
        )
        self._test('2004-04-14 21:35+CDT', None)  # ambiguous
        self._test('2005-12-20 10:33+JEST', None)  # nonexistent

    def test_abbrev(self):
        self._test(
            '2010-02-17 13:11 PST',
            '2010-02-17 13:11-0800',
        )
        self._test(
            '2001-01-06 12:12GMT',
            '2001-01-06 12:12+0000',
        )

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

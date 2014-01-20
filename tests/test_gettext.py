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

from nose.tools import (
    assert_equal,
    assert_false,
    assert_is_instance,
    assert_is_none,
    assert_is_not_none,
    assert_less,
    assert_raises,
    assert_true,
)

import lib.gettext as M

class test_header_fields:

    def test_nonempty(self):
        # XXX Update this number after editing data/header-fields:
        expected = 12
        assert_equal(len(M.header_fields), expected)

    def test_no_x(self):
        for field in M.header_fields:
            assert_false(field.startswith('X-'))

    def test_valid(self):
        for field in M.header_fields:
            assert_true(M.is_valid_field_name(field))

class test_header_parser:

    def t(self, message, expected):
        parsed = list(M.parse_header(message))
        assert_equal(parsed, expected)

    def test_ok(self):
        self.t(
            'Menu: spam\nVikings: yes\n',
            [{'Menu': 'spam'}, {'Vikings': 'yes'}],
        )

    def test_invalid_field_name(self):
        self.t(
            'Menu :spam\nVikings: yes\n',
            ['Menu :spam', {'Vikings': 'yes'}],
        )

    def test_no_field(self):
        self.t(
            'Spam\nVikings: yes\n',
            ['Spam', {'Vikings': 'yes'}],
        )

    def test_continuation(self):
        self.t(
            'Menu: spam,\n eggs\nVikings: yes\n',
            [{'Menu': 'spam,'}, ' eggs', {'Vikings': 'yes'}],
        )

class test_plural_exp:

    error = M.PluralFormsSyntaxError

    def t(self, s, n=None, fn=None):
        f = M.parse_plural_expression(s)
        if n is not None:
            assert_is_not_none(fn)
            assert_equal(f(n), fn)

    def test_add(self):
        self.t('17 + n', 6, 23)

    def test_sub(self):
        self.t('n - 23', 37, 14)

    def test_mul(self):
        self.t('6 * n', 7, 42)

    def test_div(self):
        self.t('105 / n', 17, 6)

    def test_div_by_0(self):
        with assert_raises(ZeroDivisionError):
            self.t('105 / n', 0, False)

    def test_mod(self):
        self.t('105 % n', 17, 3)

    def test_mod_by_0(self):
        with assert_raises(ZeroDivisionError):
            self.t('105 % n', 0, False)

    def test_and(self):
        self.t('n && 6', 7, 1)
        self.t('n && 6', 0, 0)
        self.t('n && (6 / 0)', 0, 0)  # no ZeroDivisionError
        self.t('n && 0', 7, 0)
        self.t('n && 0', 0, 0)

    def test_or(self):
        self.t('n || 6', 7, 1)
        self.t('n || (6 / 0)', 7, 1)  # no ZeroDivisionError
        self.t('n || 6', 0, 1)
        self.t('n || 0', 7, 1)
        self.t('n || 0', 0, 0)

    def test_gt(self):
        self.t('n > 37', 23, 0)
        self.t('n > 37', 37, 0)
        self.t('n > 37', 42, 1)

    def test_ge(self):
        self.t('n >= 37', 23, 0)
        self.t('n >= 37', 37, 1)
        self.t('n >= 37', 42, 1)

    def test_lt(self):
        self.t('n < 37', 23, 1)
        self.t('n < 37', 37, 0)
        self.t('n < 37', 42, 0)

    def test_le(self):
        self.t('n <= 37', 23, 1)
        self.t('n <= 37', 37, 1)
        self.t('n <= 37', 42, 0)

    def test_eq(self):
        self.t('n == 37', 23, 0)
        self.t('n == 37', 37, 1)
        self.t('n == 37', 42, 0)

    def test_ne(self):
        self.t('n != 37', 23, 1)
        self.t('n != 37', 37, 0)
        self.t('n != 37', 42, 1)

    def test_multi_compare(self):
        self.t('1 < n == 3 <= 4', 1, 0)  # False in Python
        self.t('1 < n == 3 <= 4', 2, 1)  # False in Python
        self.t('1 < n == 3 <= 4', 3, 1)  # True in Python
        self.t('1 < n == 3 <= 4', 4, 1)  # False in Python
        self.t('2 == 2 == n', 2, 0)  # True in Python
        self.t('2 == 2 == n', 1, 1)  # False in Python

    def test_neg(self):
        self.t('! n', 0, 1)
        self.t('! n', 1, 0)
        self.t('! n', 69, 0)

    def test_neg_precedence(self):
        self.t('! 6 + 7', 0, 7)
        self.t('0 + ! 0')

    def test_conditional(self):
        s = 'n ? 3 : 7'
        self.t(s, 0, 7)
        self.t(s, 1, 3)

    def test_nested_conditional(self):
        self.t('(2 ? 3 : 7) ? 23 : 37')

    def test_unary_plus(self):
        with assert_raises(self.error):
            self.t('-37')
        with assert_raises(self.error):
            self.t('23 + (-37)')

    def test_unary_minus(self):
        with assert_raises(self.error):
            self.t('+42')
        with assert_raises(self.error):
            self.t('23 + (+37)')

    def test_unbalanced_parentheses(self):
        with assert_raises(self.error):
            self.t('(6 * 7')
        with assert_raises(self.error):
            self.t('6 * 7)')

    def test_dangling_binop(self):
        with assert_raises(self.error):
            self.t('6 +')

    def test_junk_token(self):
        with assert_raises(self.error):
            self.t('6 # 7')

    def test_exotic_whitespace(self):
        with assert_raises(self.error):
            self.t('6 *\xA07')

class test_codomain:

    def t(self, s, min_, max_=None):
        if max_ is None:
            max_ = min_
        f = M.parse_plural_expression(s)
        cd = f.codomain()
        if min_ is None:
            assert max_ is None
            assert_is_none(cd)
        else:
            assert_equal(cd, (min_, max_))

    def test_zero_div(self):
        self.t('n / 0', None)
        self.t('(n / 0) + 23', None)
        self.t('23 + (n / 0)', None)
        self.t('! (n / 0)', None)
        self.t('0 < n/0', None)
        self.t('n/0 < 0', None)
        self.t('0 < n/0 < 0', None)

    def test_mod(self):
        self.t('n % 42', 0, 41)

    def test_mod_mod(self):
        self.t('(23 + n%15) % 42', 23, 37)

    def test_add(self):
        self.t('(6 + n%37) + (7 + n%23)', (6 + 7), 6 + 7 + 36 + 22)

    def test_sub(self):
        self.t('(6 + n%37) - (7 + n%23)', 0, 6 + 36 - 7)
        self.t('(37 + n%6) - (23 + n%7)', 37 - 23 - 6, 37 + 5 - 23)

    def test_mul(self):
        self.t(
            '(6 + n%37) * (7 + n%23)',
            6 * 7,
            (6 + 37 - 1) * (7 + 23 - 1)
        )

    def test_div(self):
        self.t(
            '(42 + n%63) / (6 + n%7)',
            42 // (6 + 7),
            (42 + 63 - 1) // 6,
        )

class test_plural_forms:

    error = M.PluralFormsSyntaxError

    def t(self, s):
        return M.parse_plural_forms(s)

    def test_nplurals_0(self):
        with assert_raises(self.error):
            self.t('nplurals=0; plural=0;')

    def test_nplurals_positive(self):
        for i in 1, 2, 10, 42:
            self.t('nplurals={}; plural=0;'.format(i))

    def test_missing_trailing_semicolon(self):
        self.t('nplurals=1; plural=0')

class test_fix_date_format:

    def _test(self, old, expected):
        if expected is None:
            with assert_raises(M.DateSyntaxError):
                M.fix_date_format(old)
        else:
            new = M.fix_date_format(old)
            assert_is_not_none(new)
            assert_equal(new, expected)

    def _test_boilerplate(self, old):
        with assert_raises(M.BoilerplateDate):
            M.fix_date_format(old)

    def test_boilerplate(self):
        self._test_boilerplate('YEAR-MO-DA HO:MI+ZONE')
        self._test_boilerplate('YEAR-MO-DA HO:MI +ZONE')

    def test_partial_boilerplate(self):
        self._test_boilerplate('2000-05-15 22:MI+0200')
        self._test_boilerplate('2002-10-15 HO:MI+ZONE')
        self._test_boilerplate('2003-07-DA 11:31+0100')
        self._test_boilerplate('2004-MO-DA HO:MI+ZONE')
        self._test_boilerplate('2006-10-24 18:00+ZONE')
        self._test_boilerplate('2010-11-01 HO:MI+0000')

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
            M.fix_date_format('2002-01-01 03:05', tz_hint='+0900'),
            '2002-01-01 03:05+0900',
        )

    def test_gmt_before_tz(self):
        self._test(
            '2001-07-28 11:19GMT+0200',
            '2001-07-28 11:19+0200',
        )
        self._test(
            '2001-12-20 17:22UTC+0100',
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

    _parse = staticmethod(M.parse_date)

    def test_nonexistent(self):
        with assert_raises(M.DateSyntaxError):
            self._parse('2010-02-29 19:49+0200')

    def test_existent(self):
        d = self._parse('2003-09-08 21:26+0200')
        assert_equal(d.second, 0)
        assert_is_instance(d, datetime.datetime)
        assert_equal(str(d), '2003-09-08 21:26:00+02:00')

    def test_epoch(self):
        d = self._parse('2008-04-03 16:06+0300')
        assert_less(M.epoch, d)

class test_string_formats:

    def test_nonempty(self):
        # XXX Update this number after editing data/string-formats:
        expected = 27
        assert_equal(len(M.string_formats), expected)

    def test_lowercase(self):
        for s in M.string_formats:
            assert_is_instance(s, str)
            assert_true(s)
            assert_equal(s, s.lower())

# vim:ts=4 sw=4 et

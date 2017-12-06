# Copyright © 2014-2016 Jakub Wilk <jwilk@jwilk.net>
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

import os
import platform
import struct
import sys

try:
    import unittest.mock as mock
except ImportError:
    try:
        import mock
    except ImportError:
        mock = None

import nose
from nose.tools import (
    assert_equal,
    assert_greater,
    assert_is_instance,
    assert_raises,
    assert_sequence_equal,
)

import lib.strformat.c as M

def test_INT_MAX():
    struct.pack('=i', M.INT_MAX)
    with assert_raises(struct.error):
        struct.pack('=i', M.INT_MAX + 1)

def test_NL_ARGMAX():
    plat = sys.platform
    libc, _ = platform.libc_ver()
    if plat.startswith('linux') and libc == 'glibc':
        assert_equal(
            M.NL_ARGMAX,
            os.sysconf('SC_NL_ARGMAX')
        )
    else:
        raise nose.SkipTest('Test specific to Linux with glibc')

if mock is not None:
    small_NL_ARGMAX = mock.patch('lib.strformat.c.NL_ARGMAX', 42)
    # Setting NL_ARGMAX to a small number makes the *_index_out_of_range() tests
    # much faster.
else:
    def small_NL_ARGMAX(func):
        return func

def test_lone_percent():
    with assert_raises(M.Error):
        M.FormatString('%')

def test_invalid_conversion_spec():
    with assert_raises(M.Error):
        M.FormatString('%!')

def test_add_argument():
    fmt = M.FormatString('%s')
    with assert_raises(RuntimeError):
        fmt.add_argument(2, None)

def test_text():
    fmt = M.FormatString('eggs%dbacon%dspam')
    assert_equal(len(fmt), 5)
    fmt = list(fmt)
    assert_equal(fmt[0], 'eggs')
    assert_equal(fmt[2], 'bacon')
    assert_equal(fmt[4], 'spam')

class test_types:

    def t(self, s, tp, warn_type=None, integer=False):
        fmt = M.FormatString(s)
        [conv] = fmt
        assert_is_instance(conv, M.Conversion)
        assert_equal(conv.type, tp)
        if tp == 'void':
            assert_sequence_equal(fmt.arguments, [])
        else:
            [[arg]] = fmt.arguments
            assert_equal(arg.type, tp)
        if warn_type is None:
            assert_sequence_equal(fmt.warnings, [])
        else:
            [warning] = fmt.warnings
            assert_is_instance(warning, warn_type)
        assert_equal(conv.integer, integer)

    def test_integer(self):
        def t(s, tp, warn_type=None):
            integer = not suffix
            self.t(s, tp + suffix, warn_type, integer)
        for c in 'din':
            suffix = ''
            if c == 'n':
                suffix = ' *'
            yield t, ('%hh' + c), 'signed char'
            yield t, ('%h' + c), 'short int'
            yield t, ('%' + c), 'int'
            yield t, ('%l' + c), 'long int'
            yield t, ('%ll' + c), 'long long int'
            yield t, ('%L' + c), 'long long int', M.NonPortableConversion
            yield t, ('%q' + c), 'long long int', M.NonPortableConversion
            yield t, ('%j' + c), 'intmax_t'
            yield t, ('%z' + c), 'ssize_t'
            yield t, ('%Z' + c), 'ssize_t', M.NonPortableConversion
            yield t, ('%t' + c), 'ptrdiff_t'
        for c in 'ouxX':
            suffix = ''
            yield t, ('%hh' + c), 'unsigned char'
            yield t, ('%h' + c), 'unsigned short int'
            yield t, ('%' + c), 'unsigned int'
            yield t, ('%l' + c), 'unsigned long int'
            yield t, ('%ll' + c), 'unsigned long long int'
            yield t, ('%L' + c), 'unsigned long long int', M.NonPortableConversion
            yield t, ('%q' + c), 'unsigned long long int', M.NonPortableConversion
            yield t, ('%j' + c), 'uintmax_t'
            yield t, ('%z' + c), 'size_t'
            yield t, ('%Z' + c), 'size_t', M.NonPortableConversion
            yield t, ('%t' + c), '[unsigned ptrdiff_t]'

    def test_double(self):
        t = self.t
        for c in 'aefgAEFG':
            yield t, ('%' + c), 'double'
            yield t, ('%l' + c), 'double', M.NonPortableConversion
            yield t, ('%L' + c), 'long double'

    def test_char(self):
        t = self.t
        yield t, '%c', 'char'
        yield t, '%lc', 'wint_t'
        yield t, '%C', 'wint_t', M.NonPortableConversion
        yield t, '%s', 'const char *'
        yield t, '%ls', 'const wchar_t *'
        yield t, '%S', 'const wchar_t *', M.NonPortableConversion

    def test_void(self):
        t = self.t
        yield t, '%p', 'void *'
        yield t, '%m', 'void'
        yield t, '%%', 'void'

    def test_c99_macros(self):
        # pylint: disable=undefined-loop-variable
        def _t(s, tp):
            return self.t(s, tp, integer=True)
        def t(s, tp):
            return (
                _t,
                '%<{macro}>'.format(macro=s.format(c=c, n=n)),
                ('u' if unsigned else '') + tp.format(n=n)
            )
        # pylint: enable=undefined-loop-variable
        for c in 'diouxX':
            unsigned = c not in 'di'
            for n in {8, 16, 32, 64}:
                yield t('PRI{c}{n}', 'int{n}_t')
                yield t('PRI{c}LEAST{n}', 'int_least{n}_t')
                yield t('PRI{c}FAST{n}', 'int_fast{n}_t')
            yield t('PRI{c}MAX', 'intmax_t')
            yield t('PRI{c}PTR', 'intptr_t')

class test_invalid_length:
    def t(self, s):
        with assert_raises(M.LengthError):
            M.FormatString(s)

    _lengths = ['hh', 'h', 'l', 'll', 'q', 'j', 'z', 't', 'L']

    def test_double(self):
        t = self.t
        for c in 'aefgAEFG':
            for l in self._lengths:
                if l in 'lL':
                    continue
                yield t, ('%' + l + c)

    def test_char(self):
        t = self.t
        for c in 'cs':
            for l in self._lengths:
                if l != 'l':
                    yield t, '%' + l + c
                yield t, ('%' + l + c.upper())

    def test_void(self):
        t = self.t
        for c in 'pm%':
            for l in self._lengths:
                yield t, ('%' + l + c)

class test_numeration:

    def test_percent(self):
        with assert_raises(M.ForbiddenArgumentIndex):
            M.FormatString('%1$%')

    def test_errno(self):
        # FIXME?
        fmt = M.FormatString('%1$m')
        assert_equal(len(fmt), 1)
        assert_equal(len(fmt.arguments), 0)

    def test_swapped(self):
        fmt = M.FormatString('%2$s%1$d')
        assert_equal(len(fmt), 2)
        [a1], [a2] = fmt.arguments
        assert_equal(a1.type, 'int')
        assert_equal(a2.type, 'const char *')

    def test_numbering_mixture(self):
        def t(s):
            with assert_raises(M.ArgumentNumberingMixture):
                M.FormatString(s)
        t('%s%2$s')
        t('%2$s%s')

    @small_NL_ARGMAX
    def test_index_out_of_range(self):
        with assert_raises(M.ArgumentRangeError):
            M.FormatString('%0$d')
        def fs(n):
            s = ''.join(
                '%{0}$d'.format(i)
                for i in range(1, n + 1)
            )
            return M.FormatString(s)
        fmt = fs(M.NL_ARGMAX)
        assert_equal(len(fmt), M.NL_ARGMAX)
        assert_equal(len(fmt.arguments), M.NL_ARGMAX)
        with assert_raises(M.ArgumentRangeError):
            fs(M.NL_ARGMAX + 1)

    def test_initial_gap(self):
        with assert_raises(M.MissingArgument):
            M.FormatString('%2$d')

    def test_gap(self):
        with assert_raises(M.MissingArgument):
            M.FormatString('%3$d%1$d')

class test_redundant_flag:

    def t(self, s):
        fmt = M.FormatString(s)
        [exc] = fmt.warnings
        assert_is_instance(exc, M.RedundantFlag)

    def test_duplicate(self):
        self.t('%--17d')

    def test_minus_zero(self):
        self.t('%-017d')

    def test_plus_space(self):
        self.t('%+ d')

    # TODO: Check for other redundant flags, for example “%+s”.

class test_expected_flag:

    def t(self, s):
        fmt = M.FormatString(s)
        assert_equal(len(fmt), 1)

    def test_hash(self):
        for c in 'oxXaAeEfFgG':
            yield self.t, ('%#' + c)

    def test_zero(self):
        for c in 'diouxXaAeEfFgG':
            yield self.t, ('%0' + c)

    def test_apos(self):
        for c in 'diufFgG':
            yield self.t, ("%'" + c)

    def test_other(self):
        for flag in '- +I':
            for c in 'diouxXaAeEfFgGcCsSpm':
                yield self.t, ('%' + flag + c)

class test_unexpected_flag:

    def t(self, s):
        with assert_raises(M.FlagError):
            M.FormatString(s)

    def test_hash(self):
        for c in 'dicCsSnpm%':
            yield self.t, ('%#' + c)

    def test_zero(self):
        for c in 'cCsSnpm%':
            yield self.t, ('%0' + c)

    def test_apos(self):
        for c in 'oxXaAeEcCsSnpm%':
            yield self.t, ("%'" + c)

    def test_other(self):
        for c in '%n':
            for flag in '- +I':
                yield self.t, ('%' + flag + c)

class test_width:

    def test_ok(self):
        def t(s):
            fmt = M.FormatString(s)
            assert_equal(len(fmt), 1)
        for c in 'diouxXaAeEfFgGcCsSp':
            yield t, ('%1' + c)
        yield t, '%1m'  # FIXME?

    def test_invalid(self):
        for c in '%n':
            with assert_raises(M.WidthError):
                M.FormatString('%1' + c)

    def test_too_large(self):
        fmt = M.FormatString('%{0}d'.format(M.INT_MAX))
        assert_equal(len(fmt), 1)
        assert_equal(len(fmt.arguments), 1)
        with assert_raises(M.WidthRangeError):
            M.FormatString('%{0}d'.format(M.INT_MAX + 1))

    def test_variable(self):
        fmt = M.FormatString('%*s')
        assert_equal(len(fmt), 1)
        assert_equal(len(fmt.arguments), 2)
        [a1], [a2] = fmt.arguments
        assert_equal(a1.type, 'int')
        assert_equal(a2.type, 'const char *')

    def _test_index(self, i):
        fmt = M.FormatString('%2$*{0}$s'.format(i))
        assert_equal(len(fmt), 1)
        assert_equal(len(fmt.arguments), 2)
        [a1], [a2] = fmt.arguments
        assert_equal(a1.type, 'int')
        assert_equal(a2.type, 'const char *')

    def test_index(self):
        self._test_index(1)

    def test_leading_zero_index(self):
        self._test_index('01')
        self._test_index('001')

    @small_NL_ARGMAX
    def test_index_out_of_range(self):
        with assert_raises(M.ArgumentRangeError):
            M.FormatString('%1$*0$s')
        def fs(n):
            s = ''.join(
                '%{0}$d'.format(i)
                for i in range(2, n)
            ) + '%1$*{0}$s'.format(n)
            return M.FormatString(s)
        fmt = fs(M.NL_ARGMAX)
        assert_equal(len(fmt), M.NL_ARGMAX - 1)
        assert_equal(len(fmt.arguments), M.NL_ARGMAX)
        with assert_raises(M.ArgumentRangeError):
            fs(M.NL_ARGMAX + 1)

    def test_numbering_mixture(self):
        def t(s):
            with assert_raises(M.ArgumentNumberingMixture):
                M.FormatString(s)
        t('%1$*s')
        t('%*1$s')
        t('%s%1$*2$s')
        t('%1$*2$s%s')

class test_precision:

    def test_ok(self):
        def t(s):
            fmt = M.FormatString(s)
            assert_equal(len(fmt), 1)
        for c in 'diouxXaAeEfFgGsS':
            yield t, ('%.1' + c)

    def test_redundant_0(self):
        def t(s):
            fmt = M.FormatString(s)
            assert_equal(len(fmt), 1)
            [warning] = fmt.warnings
            assert_is_instance(warning, M.RedundantFlag)
        for c in 'diouxX':
            yield t, ('%0.1' + c)

    def test_non_redundant_0(self):
        def t(s):
            fmt = M.FormatString(s)
            assert_equal(len(fmt), 1)
            assert_sequence_equal(fmt.warnings, [])
        for c in 'aAeEfFgG':
            yield t, ('%0.1' + c)

    def test_unexpected(self):
        def t(s):
            with assert_raises(M.PrecisionError):
                M.FormatString(s)
        for c in 'cCpnm%':
            yield t, ('%.1' + c)

    def test_too_large(self):
        fmt = M.FormatString('%.{0}f'.format(M.INT_MAX))
        assert_equal(len(fmt), 1)
        with assert_raises(M.PrecisionRangeError):
            M.FormatString('%.{0}f'.format(M.INT_MAX + 1))

    def test_variable(self):
        fmt = M.FormatString('%.*f')
        assert_equal(len(fmt), 1)
        assert_equal(len(fmt.arguments), 2)
        [a1], [a2] = fmt.arguments
        assert_equal(a1.type, 'int')
        assert_equal(a2.type, 'double')

    def _test_index(self, i):
        fmt = M.FormatString('%2$.*{0}$f'.format(i))
        assert_equal(len(fmt), 1)
        assert_equal(len(fmt.arguments), 2)
        [a1], [a2] = fmt.arguments
        assert_equal(a1.type, 'int')
        assert_equal(a2.type, 'double')

    def test_index(self):
        self._test_index(1)

    def test_leading_zero_index(self):
        self._test_index('01')
        self._test_index('001')

    @small_NL_ARGMAX
    def test_index_out_of_range(self):
        with assert_raises(M.ArgumentRangeError):
            M.FormatString('%1$.*0$f')
        def fs(n):
            s = ''.join(
                '%{0}$d'.format(i)
                for i in range(2, n)
            ) + '%1$.*{0}$f'.format(n)
            return M.FormatString(s)
        fmt = fs(M.NL_ARGMAX)
        assert_equal(len(fmt), M.NL_ARGMAX - 1)
        assert_equal(len(fmt.arguments), M.NL_ARGMAX)
        with assert_raises(M.ArgumentRangeError):
            fs(M.NL_ARGMAX + 1)

    def test_numbering_mixture(self):
        def t(s):
            with assert_raises(M.ArgumentNumberingMixture):
                M.FormatString(s)
        t('%1$.*f')
        t('%.*1$f')
        t('%f%2$.*1$f')
        t('%2$.*1$f%f')

class test_type_compatibility:

    def test_okay(self):
        def t(s, tp):
            fmt = M.FormatString(s)
            [args] = fmt.arguments
            assert_greater(len(args), 1)
            for arg in args:
                assert_equal(arg.type, tp)
        t('%1$d%1$d', 'int')
        t('%1$d%1$i', 'int')

    def test_mismatch(self):
        def t(s):
            with assert_raises(M.ArgumentTypeMismatch):
                M.FormatString(s)
        t('%1$d%1$hd')
        t('%1$d%1$u')
        t('%1$d%1$s')

@small_NL_ARGMAX
def test_too_many_conversions():
    def t(s):
        with assert_raises(M.ArgumentRangeError):
            M.FormatString(s)
    s = M.NL_ARGMAX * '%d'
    fmt = M.FormatString(s)
    assert_equal(len(fmt), M.NL_ARGMAX)
    t(s + '%f')
    t(s + '%*f')
    t(s + '%.*f')

class test_get_last_integer_conversion:

    def test_overflow(self):
        fmt = M.FormatString('%s%d')
        for n in [-1, 0, 3]:
            with assert_raises(IndexError):
                fmt.get_last_integer_conversion(n=n)

    def t(self, s, n, tp=M.Conversion):
        fmt = M.FormatString(s)
        conv = fmt.get_last_integer_conversion(n=n)
        if tp is None:
            tp = type(tp)
        assert_is_instance(conv, tp)
        return conv

    def test_okay(self):
        self.t('%d', 1)
        self.t('%s%d', 1)

    def test_non_integer(self):
        self.t('%s', 1, None)
        self.t('%c', 1, None)

    def test_too_many(self):
        self.t('%s%d', 2, None)
        self.t('%d%d', 2, None)

    def test_var(self):
        self.t('%*d', 1)
        self.t('%*d', 2)
        self.t('%.*d', 2)
        self.t('%1$*2$d', 2)
        self.t('%2$*3$.*1$d', 3)

    def test_broken_var(self):
        self.t('%1$*2$d', 1, None)
        self.t('%1$*2$d%3$d', 2, None)
        self.t('%1$*3$d%2$d', 2, None)

# vim:ts=4 sts=4 sw=4 et

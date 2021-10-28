# Copyright © 2014-2018 Jakub Wilk <jwilk@jwilk.net>
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
import struct
import sys
import unittest
import unittest.mock

import pytest

import lib.strformat.c as M

from . import tools


# methods using the tools.collect_yielded decorator don't have a 'self'
# since they end up being run before 'self' exists. pylint doesn't
# understand this unusual situation
# pylint: disable=no-method-argument


def test_INT_MAX():
    struct.pack('=i', M.INT_MAX)
    with pytest.raises(struct.error):
        struct.pack('=i', M.INT_MAX + 1)

def is_glibc():
    try:
        os.confstr('CS_GNU_LIBC_VERSION')
    except (ValueError, OSError):
        return False
    return True

def test_NL_ARGMAX():
    plat = sys.platform
    if plat.startswith('linux') and is_glibc():
        assert (
            M.NL_ARGMAX ==
            os.sysconf('SC_NL_ARGMAX'))
    else:
        raise unittest.SkipTest('Test specific to Linux with glibc')

small_NL_ARGMAX = unittest.mock.patch('lib.strformat.c.NL_ARGMAX', 42)
# Setting NL_ARGMAX to a small number makes the *_index_out_of_range() tests
# much faster.

def test_lone_percent():
    with pytest.raises(M.Error):
        M.FormatString('%')

def test_invalid_conversion_spec():
    with pytest.raises(M.Error):
        M.FormatString('%!')

def test_add_argument():
    fmt = M.FormatString('%s')
    with pytest.raises(RuntimeError):
        fmt.add_argument(2, None)

def test_text():
    fmt = M.FormatString('eggs%dbacon%dspam')
    assert len(fmt) == 5
    fmt = list(fmt)
    assert fmt[0] == 'eggs'
    assert fmt[2] == 'bacon'
    assert fmt[4] == 'spam'

class test_types:

    @staticmethod
    def t(s, tp, warn_type=None, integer=False):
        fmt = M.FormatString(s)
        [conv] = fmt
        assert isinstance(conv, M.Conversion)
        assert conv.type == tp
        if tp == 'void':
            assert fmt.arguments == []
        else:
            [[arg]] = fmt.arguments
            assert arg.type == tp
        if warn_type is None:
            assert fmt.warnings == []
        else:
            [warning] = fmt.warnings
            assert isinstance(warning, warn_type)
        assert conv.integer == integer

    @tools.collect_yielded
    def test_integer():
        def t(s, tp, suffix, warn_type=None):
            integer = not suffix
            test_types.t(s, tp + suffix, warn_type, integer)
        for c in 'din':
            suffix = ''
            if c == 'n':
                suffix = ' *'
            yield t, (('%hh' + c), 'signed char', suffix)
            yield t, (('%h' + c), 'short int', suffix)
            yield t, (('%' + c), 'int', suffix)
            yield t, (('%l' + c), 'long int', suffix)
            yield t, (('%ll' + c), 'long long int', suffix)
            yield t, (('%L' + c), 'long long int', suffix, M.NonPortableConversion)
            yield t, (('%q' + c), 'long long int', suffix, M.NonPortableConversion)
            yield t, (('%j' + c), 'intmax_t', suffix)
            yield t, (('%z' + c), 'ssize_t', suffix)
            yield t, (('%Z' + c), 'ssize_t', suffix, M.NonPortableConversion)
            yield t, (('%t' + c), 'ptrdiff_t', suffix)
        for c in 'ouxX':
            suffix = ''
            yield t, (('%hh' + c), 'unsigned char', suffix)
            yield t, (('%h' + c), 'unsigned short int', suffix)
            yield t, (('%' + c), 'unsigned int', suffix)
            yield t, (('%l' + c), 'unsigned long int', suffix)
            yield t, (('%ll' + c), 'unsigned long long int', suffix)
            yield t, (('%L' + c), 'unsigned long long int', suffix, M.NonPortableConversion)
            yield t, (('%q' + c), 'unsigned long long int', suffix, M.NonPortableConversion)
            yield t, (('%j' + c), 'uintmax_t', suffix)
            yield t, (('%z' + c), 'size_t', suffix)
            yield t, (('%Z' + c), 'size_t', suffix, M.NonPortableConversion)
            yield t, (('%t' + c), '[unsigned ptrdiff_t]', suffix)

    @tools.collect_yielded
    def test_double():
        def t(*args):
            test_types.t(*args)

        for c in 'aefgAEFG':
            yield t, (('%' + c), 'double')
            yield t, (('%l' + c), 'double', M.NonPortableConversion)
            yield t, (('%L' + c), 'long double')

    @tools.collect_yielded
    def test_char():
        def t(*args):
            test_types.t(*args)

        yield t, ('%c', 'char')
        yield t, ('%lc', 'wint_t')
        yield t, ('%C', 'wint_t', M.NonPortableConversion)
        yield t, ('%s', 'const char *')
        yield t, ('%ls', 'const wchar_t *')
        yield t, ('%S', 'const wchar_t *', M.NonPortableConversion)

    @tools.collect_yielded
    def test_void():
        def t(*args):
            test_types.t(*args)

        yield t, ('%p', 'void *')
        yield t, ('%m', 'void')
        yield t, ('%%', 'void')

    @tools.collect_yielded
    def test_c99_macros():
        # pylint: disable=undefined-loop-variable
        def _t(s, tp):
            return test_types.t(s, tp, integer=True)
        def t(s, tp):
            return (
                _t,
                (
                    '%<{macro}>'.format(macro=s.format(c=c, n=n)),
                    ('u' if unsigned else '') + tp.format(n=n)
                )
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

_lengths = ['hh', 'h', 'l', 'll', 'q', 'j', 'z', 't', 'L']

class test_invalid_length:
    @staticmethod
    def t(s):
        with pytest.raises(M.LengthError):
            M.FormatString(s)

    @tools.collect_yielded
    def test_double():
        def t(*args):
            test_invalid_length.t(*args)
        for c in 'aefgAEFG':
            for l in _lengths:
                if l in 'lL':
                    continue
                yield t, ('%' + l + c)

    @tools.collect_yielded
    def test_char():
        def t(*args):
            test_invalid_length.t(*args)
        for c in 'cs':
            for l in _lengths:
                if l != 'l':
                    yield t, '%' + l + c
                yield t, ('%' + l + c.upper())

    @tools.collect_yielded
    def test_void():
        def t(*args):
            test_invalid_length.t(*args)
        for c in 'pm%':
            for l in _lengths:
                yield t, ('%' + l + c)

class test_numeration:

    def test_percent(self):
        with pytest.raises(M.ForbiddenArgumentIndex):
            M.FormatString('%1$%')

    def test_errno(self):
        # FIXME?
        fmt = M.FormatString('%1$m')
        assert len(fmt) == 1
        assert len(fmt.arguments) == 0

    def test_swapped(self):
        fmt = M.FormatString('%2$s%1$d')
        assert len(fmt) == 2
        [a1], [a2] = fmt.arguments
        assert a1.type == 'int'
        assert a2.type == 'const char *'

    def test_numbering_mixture(self):
        def t(s):
            with pytest.raises(M.ArgumentNumberingMixture):
                M.FormatString(s)
        t('%s%2$s')
        t('%2$s%s')

    @small_NL_ARGMAX
    def test_index_out_of_range(self):
        with pytest.raises(M.ArgumentRangeError):
            M.FormatString('%0$d')
        def fs(n):
            s = ''.join(
                '%{0}$d'.format(i)
                for i in range(1, n + 1)
            )
            return M.FormatString(s)
        fmt = fs(M.NL_ARGMAX)
        assert len(fmt) == M.NL_ARGMAX
        assert len(fmt.arguments) == M.NL_ARGMAX
        with pytest.raises(M.ArgumentRangeError):
            fs(M.NL_ARGMAX + 1)

    def test_initial_gap(self):
        with pytest.raises(M.MissingArgument):
            M.FormatString('%2$d')

    def test_gap(self):
        with pytest.raises(M.MissingArgument):
            M.FormatString('%3$d%1$d')

class test_redundant_flag:

    def t(self, s):
        fmt = M.FormatString(s)
        [exc] = fmt.warnings
        assert isinstance(exc, M.RedundantFlag)

    def test_duplicate(self):
        self.t('%--17d')

    def test_minus_zero(self):
        self.t('%-017d')

    def test_plus_space(self):
        self.t('%+ d')

    # TODO: Check for other redundant flags, for example “%+s”.

class test_expected_flag:

    @staticmethod
    def t(s):
        fmt = M.FormatString(s)
        assert len(fmt) == 1

    @tools.collect_yielded
    def test_hash():
        def t(*args):
            test_expected_flag.t(*args)
        for c in 'oxXaAeEfFgG':
            yield t, ('%#' + c)

    @tools.collect_yielded
    def test_zero():
        def t(*args):
            test_expected_flag.t(*args)
        for c in 'diouxXaAeEfFgG':
            yield t, ('%0' + c)

    @tools.collect_yielded
    def test_apos():
        def t(*args):
            test_expected_flag.t(*args)
        for c in 'diufFgG':
            yield t, ("%'" + c)

    @tools.collect_yielded
    def test_other():
        def t(*args):
            test_expected_flag.t(*args)
        for flag in '- +I':
            for c in 'diouxXaAeEfFgGcCsSpm':
                yield t, ('%' + flag + c)

class test_unexpected_flag:

    @staticmethod
    def t(s):
        with pytest.raises(M.FlagError):
            M.FormatString(s)

    @tools.collect_yielded
    def test_hash():
        def t(*args):
            test_unexpected_flag.t(*args)
        for c in 'dicCsSnpm%':
            yield t, ('%#' + c)

    @tools.collect_yielded
    def test_zero():
        def t(*args):
            test_unexpected_flag.t(*args)
        for c in 'cCsSnpm%':
            yield t, ('%0' + c)

    @tools.collect_yielded
    def test_apos():
        def t(*args):
            test_unexpected_flag.t(*args)
        for c in 'oxXaAeEcCsSnpm%':
            yield t, ("%'" + c)

    @tools.collect_yielded
    def test_other():
        def t(*args):
            test_unexpected_flag.t(*args)
        for c in '%n':
            for flag in '- +I':
                yield t, ('%' + flag + c)

class test_width:

    @tools.collect_yielded
    def test_ok():
        def t(s):
            fmt = M.FormatString(s)
            assert len(fmt) == 1
        for c in 'diouxXaAeEfFgGcCsSp':
            yield t, ('%1' + c)
        yield t, '%1m'  # FIXME?

    def test_invalid(self):
        for c in '%n':
            with pytest.raises(M.WidthError):
                M.FormatString('%1' + c)

    def test_too_large(self):
        fmt = M.FormatString('%{0}d'.format(M.INT_MAX))
        assert len(fmt) == 1
        assert len(fmt.arguments) == 1
        with pytest.raises(M.WidthRangeError):
            M.FormatString('%{0}d'.format(M.INT_MAX + 1))

    def test_variable(self):
        fmt = M.FormatString('%*s')
        assert len(fmt) == 1
        assert len(fmt.arguments) == 2
        [a1], [a2] = fmt.arguments
        assert a1.type == 'int'
        assert a2.type == 'const char *'

    def _test_index(self, i):
        fmt = M.FormatString('%2$*{0}$s'.format(i))
        assert len(fmt) == 1
        assert len(fmt.arguments) == 2
        [a1], [a2] = fmt.arguments
        assert a1.type == 'int'
        assert a2.type == 'const char *'

    def test_index(self):
        self._test_index(1)

    def test_leading_zero_index(self):
        self._test_index('01')
        self._test_index('001')

    @small_NL_ARGMAX
    def test_index_out_of_range(self):
        with pytest.raises(M.ArgumentRangeError):
            M.FormatString('%1$*0$s')
        def fs(n):
            s = ''.join(
                '%{0}$d'.format(i)
                for i in range(2, n)
            ) + '%1$*{0}$s'.format(n)
            return M.FormatString(s)
        fmt = fs(M.NL_ARGMAX)
        assert len(fmt) == M.NL_ARGMAX - 1
        assert len(fmt.arguments) == M.NL_ARGMAX
        with pytest.raises(M.ArgumentRangeError):
            fs(M.NL_ARGMAX + 1)

    def test_numbering_mixture(self):
        def t(s):
            with pytest.raises(M.ArgumentNumberingMixture):
                M.FormatString(s)
        t('%1$*s')
        t('%*1$s')
        t('%s%1$*2$s')
        t('%1$*2$s%s')

class test_precision:

    @tools.collect_yielded
    def test_ok():
        def t(s):
            fmt = M.FormatString(s)
            assert len(fmt) == 1
        for c in 'diouxXaAeEfFgGsS':
            yield t, ('%.1' + c)

    @tools.collect_yielded
    def test_redundant_0():
        def t(s):
            fmt = M.FormatString(s)
            assert len(fmt) == 1
            [warning] = fmt.warnings
            assert isinstance(warning, M.RedundantFlag)
        for c in 'diouxX':
            yield t, ('%0.1' + c)

    @tools.collect_yielded
    def test_non_redundant_0():
        def t(s):
            fmt = M.FormatString(s)
            assert len(fmt) == 1
            assert fmt.warnings == []
        for c in 'aAeEfFgG':
            yield t, ('%0.1' + c)

    @tools.collect_yielded
    def test_unexpected():
        def t(s):
            with pytest.raises(M.PrecisionError):
                M.FormatString(s)
        for c in 'cCpnm%':
            yield t, ('%.1' + c)

    def test_too_large(self):
        fmt = M.FormatString('%.{0}f'.format(M.INT_MAX))
        assert len(fmt) == 1
        with pytest.raises(M.PrecisionRangeError):
            M.FormatString('%.{0}f'.format(M.INT_MAX + 1))

    def test_variable(self):
        fmt = M.FormatString('%.*f')
        assert len(fmt) == 1
        assert len(fmt.arguments) == 2
        [a1], [a2] = fmt.arguments
        assert a1.type == 'int'
        assert a2.type == 'double'

    def _test_index(self, i):
        fmt = M.FormatString('%2$.*{0}$f'.format(i))
        assert len(fmt) == 1
        assert len(fmt.arguments) == 2
        [a1], [a2] = fmt.arguments
        assert a1.type == 'int'
        assert a2.type == 'double'

    def test_index(self):
        self._test_index(1)

    def test_leading_zero_index(self):
        self._test_index('01')
        self._test_index('001')

    @small_NL_ARGMAX
    def test_index_out_of_range(self):
        with pytest.raises(M.ArgumentRangeError):
            M.FormatString('%1$.*0$f')
        def fs(n):
            s = ''.join(
                '%{0}$d'.format(i)
                for i in range(2, n)
            ) + '%1$.*{0}$f'.format(n)
            return M.FormatString(s)
        fmt = fs(M.NL_ARGMAX)
        assert len(fmt) == M.NL_ARGMAX - 1
        assert len(fmt.arguments) == M.NL_ARGMAX
        with pytest.raises(M.ArgumentRangeError):
            fs(M.NL_ARGMAX + 1)

    def test_numbering_mixture(self):
        def t(s):
            with pytest.raises(M.ArgumentNumberingMixture):
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
            assert len(args) > 1
            for arg in args:
                assert arg.type == tp
        t('%1$d%1$d', 'int')
        t('%1$d%1$i', 'int')

    def test_mismatch(self):
        def t(s):
            with pytest.raises(M.ArgumentTypeMismatch):
                M.FormatString(s)
        t('%1$d%1$hd')
        t('%1$d%1$u')
        t('%1$d%1$s')

@small_NL_ARGMAX
def test_too_many_conversions():
    def t(s):
        with pytest.raises(M.ArgumentRangeError):
            M.FormatString(s)
    s = M.NL_ARGMAX * '%d'
    fmt = M.FormatString(s)
    assert len(fmt) == M.NL_ARGMAX
    t(s + '%f')
    t(s + '%*f')
    t(s + '%.*f')

class test_get_last_integer_conversion:

    def test_overflow(self):
        fmt = M.FormatString('%s%d')
        for n in [-1, 0, 3]:
            with pytest.raises(IndexError):
                fmt.get_last_integer_conversion(n=n)

    def t(self, s, n, tp=M.Conversion):
        fmt = M.FormatString(s)
        conv = fmt.get_last_integer_conversion(n=n)
        if tp is None:
            tp = type(tp)
        assert isinstance(conv, tp)
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

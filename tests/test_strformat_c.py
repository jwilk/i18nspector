# Copyright © 2014 Jakub Wilk <jwilk@jwilk.net>
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
    assert_is_instance,
    assert_raises,
)

from . import aux

import lib.strformat.c as M

def test_INT_MAX():
    struct.pack('=i', M.INT_MAX)
    with assert_raises(struct.error):
        struct.pack('=i', M.INT_MAX + 1)

def test_NL_ARGMAX():
    if sys.platform.startswith('linux'):
        assert_equal(
            M.NL_ARGMAX,
            os.sysconf('SC_NL_ARGMAX')
        )
    else:
        raise nose.SkipTest('Linux-specific test')

if mock is not None:
    small_NL_ARGMAX = mock.patch('lib.strformat.c.NL_ARGMAX', 42)
    # Setting NL_ARGMAX to a small number makes the *_index_out_of_range() tests
    # much faster.
else:
    def small_NL_ARGMAX(*args, **kwargs):
        def identity(x):
            return x
        return identity

def test_lone_percent():
    with assert_raises(M.FormatError):
        M.FormatString('%')

def test_invalid_conversion_spec():
    with assert_raises(M.FormatError):
        M.FormatString('%!')

def test_add_argument():
    fmt = M.FormatString('%s')
    with assert_raises(RuntimeError):
        fmt.add_argument(2, None)

def test_text():
    fmt = M.FormatString('eggs%dbacon%dspam')
    assert_equal(len(fmt), (5))
    fmt = list(fmt)
    assert_equal(fmt[0], 'eggs')
    assert_equal(fmt[2], 'bacon')
    assert_equal(fmt[4], 'spam')

class test_types:

    def t(self, s, type):
        fmt = M.FormatString(s)
        [conv] = fmt
        assert_is_instance(conv, M.Conversion)
        assert_equal(conv.type, type)
        if type == 'void':
            assert_equal(len(fmt.arguments), 0)
        else:
            [[arg]] = fmt.arguments
            assert_equal(arg.type, type)

    def test_integer(self):
        t = self.t
        for c in 'din':
            if c == 'n':
                suffix = ' *'
            else:
                suffix = ''
            yield t, ('%hh' + c), ('signed char' + suffix)
            yield t, ('%h' + c), ('short int' + suffix)
            yield t, ('%' + c), ('int' + suffix)
            yield t, ('%l' + c), ('long int' + suffix)
            yield t, ('%ll' + c), ('long long int' + suffix)
            yield t, ('%q' + c), ('long long int' + suffix)
            yield t, ('%j' + c), ('intmax_t' + suffix)
            yield t, ('%z' + c), ('ssize_t' + suffix)
            yield t, ('%t' + c), ('ptrdiff_t' + suffix)
        for c in 'ouxX':
            yield t, ('%hh' + c), 'unsigned char'
            yield t, ('%h' + c), 'unsigned short int'
            yield t, ('%' + c), 'unsigned int'
            yield t, ('%l' + c), 'unsigned long int'
            yield t, ('%ll' + c), 'unsigned long long int'
            yield t, ('%q' + c), 'unsigned long long int'
            yield t, ('%j' + c), 'uintmax_t'
            yield t, ('%z' + c), 'size_t'
            yield t, ('%t' + c), '[unsigned ptrdiff_t]'

    def test_double(self):
        t = self.t
        for c in 'aefgAEFG':
            yield t, ('%' + c), 'double'
            yield t, ('%L' + c), 'long double'

    def test_char(self):
        t = self.t
        yield t, '%c', '[int converted to unsigned char]'
        yield t, '%lc', 'wint_t'
        yield t, '%C', 'wint_t'
        yield t, '%s', 'const char *'
        yield t, '%ls', 'const wchar_t *'
        yield t, '%S', 'const wchar_t *'

    def test_void(self):
        t = self.t
        yield t, '%p', 'void *'
        yield t, '%m', 'void'
        yield t, '%%', 'void'

class test_invalid_length:
    def t(self, s):
        with assert_raises(M.FormatError):
            M.FormatString(s)

    _lengths = ['hh', 'h', 'l', 'll', 'q', 'j', 'z', 't', 'L']

    def test_integer(self):
        t = self.t
        for c in 'diouxXn':
            yield t, ('%L' + c)

    def test_double(self):
        t = self.t
        for c in 'aefgAEFG':
            for l in self._lengths:
                if l == 'L':
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
        with assert_raises(M.FormatError):
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

    def test_numbered_and_unnumbered_args(self):
        def t(s):
            with assert_raises(M.FormatError):
                M.FormatString(s)
        t('%s%2$s')
        t('%2$s%s')

    @small_NL_ARGMAX
    def test_index_out_of_range(self):
        with assert_raises(M.FormatError):
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
        with assert_raises(M.FormatError):
            fs(M.NL_ARGMAX + 1)

    def test_initial_gap(self):
        with assert_raises(M.FormatError):
            M.FormatString('%2$d')

    def test_gap(self):
        with assert_raises(M.FormatError):
            M.FormatString('%3$d%1$d')

def test_duplicate_flag():
    def t(s):
        with assert_raises(M.FormatError):
            M.FormatString(s)
    t('%007d')
    t('%-+-o')

class test_expected_flag():

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
            for c in 'diouxXaAeEfFgGcCsSpnm':
                yield self.t, ('%' + flag + c)

class test_unexpected_flag():

    def t(self, s):
        with assert_raises(M.FormatError):
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
        for flag in '- +I':
            yield self.t, ('%' + flag + '%')

class test_width():

    def test_ok(self):
        def t(s):
            fmt = M.FormatString(s)
            assert_equal(len(fmt), 1)
        for c in 'diouxXaAeEfFgGcCsSp':
            yield t, ('%1' + c)
        for c in 'nm':
            # FIXME?
            yield t, ('%1' + c)

    def test_invalid(self):
        with assert_raises(M.FormatError):
            M.FormatString('%1%')

    def test_too_large(self):
        fmt = M.FormatString('%{0}d'.format(M.INT_MAX))
        assert_equal(len(fmt), 1)
        assert_equal(len(fmt.arguments), 1)
        with assert_raises(M.FormatError):
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
        with assert_raises(M.FormatError):
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
        with assert_raises(M.FormatError):
            fs(M.NL_ARGMAX + 1)

    def test_numbered_and_unnumbered(self):
        def t(s):
            with assert_raises(M.FormatError):
                M.FormatString(s)
        t('%1$*s')
        t('%*1$s')

class test_precision():

    def test_ok(self):
        def t(s):
            fmt = M.FormatString(s)
            assert_equal(len(fmt), 1)
        for c in 'diouxXaAeEfFgGsS':
            yield t, ('%.1' + c)

    def test_unexpected(self):
        def t(s):
            with assert_raises(M.FormatError):
                M.FormatString(s)
        for c in 'cCpnm%':
            yield t, ('%.1' + c)

    def test_too_large(self):
        fmt = M.FormatString('%.{0}f'.format(M.INT_MAX))
        assert_equal(len(fmt), 1)
        with assert_raises(M.FormatError):
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
        with assert_raises(M.FormatError):
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
        with assert_raises(M.FormatError):
            fs(M.NL_ARGMAX + 1)

    def test_numbered_and_unnumbered(self):
        def t(s):
            with assert_raises(M.FormatError):
                M.FormatString(s)
        t('%1$.*f')
        t('%.*1$f')

# TODO: index out of range for unnumbered arguments

# vim:ts=4 sw=4 et

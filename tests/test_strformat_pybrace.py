# Copyright © 2016 Jakub Wilk <jwilk@jwilk.net>
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

import functools
import struct

try:
    from unittest import mock
except ImportError:
    try:
        import mock
    except ImportError:
        mock = None

import nose
from nose.tools import (
    assert_equal,
    assert_is,
    assert_is_instance,
    assert_raises,
)

import lib.strformat.pybrace as M

def test_SSIZE_MAX():
    struct.pack('=i', M.SSIZE_MAX)
    with assert_raises(struct.error):
        struct.pack('=i', M.SSIZE_MAX + 1)

if mock is not None:
    small_SSIZE_MAX = mock.patch('lib.strformat.pybrace.SSIZE_MAX', 42)
    # Setting SSIZE_ARGMAX to a small number makes it possible to test for
    # a very large number of arguments without running out of memory.
else:
    def small_SSIZE_MAX(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            del args, kwargs
            raise nose.SkipTest('mock module missing')
        return wrapper

def test_lone_lcb():
    with assert_raises(M.Error):
        M.FormatString('{')

def test_lone_rcb():
    with assert_raises(M.Error):
        M.FormatString('}')

def test_invalid_field():
    with assert_raises(M.Error):
        M.FormatString('{@}')

def test_add_argument():
    fmt = M.FormatString('{}')
    with assert_raises(RuntimeError):
        fmt.add_argument(None, None)
    with assert_raises(RuntimeError):
        fmt.add_argument('eggs', None)

def test_text():
    fmt = M.FormatString('eggs{}bacon{}spam')
    assert_equal(len(fmt), 5)
    fmt = list(fmt)
    assert_equal(fmt[0], 'eggs')
    assert_equal(fmt[2], 'bacon')
    assert_equal(fmt[4], 'spam')

class test_types:

    def t(self, k, *types):
        types = frozenset(tp.__name__ for tp in types)
        fmt = M.FormatString('{:' + k + '}')
        [fld] = fmt
        assert_is_instance(fld, M.Field)
        assert_equal(fld.types, types)
        assert_equal(len(fmt.argument_map), 1)
        [(key, [afld])] = fmt.argument_map.items()
        assert_equal(key, 0)
        assert_is(fld, afld)

    def test_default(self):
        self.t('', int, float, str)

    def test_s(self):
        self.t('s', str)

    def test_int(self):
        for k in 'bcdoxX':
            self.t(k, int)

    def test_n(self):
        self.t('n', int, float)

    def test_float(self):
        for k in 'eEfFgG':
            self.t(k, float)

class test_conversion:

    def t(self, c, k, *types):
        types = frozenset(tp.__name__ for tp in types)
        fmt = M.FormatString('{!' + c + ':' + k + '}')
        [fld] = fmt
        assert_is_instance(fld, M.Field)
        assert_equal(fld.types, types)
        assert_equal(len(fmt.argument_map), 1)
        [(key, [afld])] = fmt.argument_map.items()
        assert_equal(key, 0)
        assert_is(fld, afld)

    def test_default(self):
        for c in 'sra':
            self.t(c, '', int, float, str)

    def test_s(self):
        for c in 'sra':
            self.t(c, 's', str)

    def test_numeric(self):
        for c in 'sra':
            for k in 'bcdoxXneEfFgG':
                with assert_raises(M.FormatTypeMismatch):
                    self.t(c, k, int)

    def test_bad(self):
        with assert_raises(M.ConversionError):
            self.t('z', '')

class test_numbered_arguments:

    tp_int = frozenset({'int'})
    tp_float = frozenset({'float'})

    def t(self, s, *types):
        fmt = M.FormatString(s)
        assert_equal(len(fmt), len(types))
        assert_equal(len(fmt.argument_map), len(types))
        for (key, args), (xkey, xtype) in zip(sorted(fmt.argument_map.items()), enumerate(types)):
            [arg] = args
            assert_equal(key, xkey)
            assert_equal(arg.types, frozenset({xtype.__name__}))

    def test_unnumbered(self):
        self.t('{:d}{:f}', int, float)

    def test_numbered(self):
        self.t('{0:d}{1:f}', int, float)

    def test_swapped(self):
        self.t('{1:d}{0:f}', float, int)

    def test_mixed(self):
        with assert_raises(M.ArgumentNumberingMixture):
            self.t('{0:d}{:f}')
        with assert_raises(M.ArgumentNumberingMixture):
            self.t('{:d}{0:f}')

    def test_numbered_out_of_range(self):
        def t(i):
            s = ('{' + str(i) + '}')
            M.FormatString(s)
        t(M.SSIZE_MAX)
        with assert_raises(M.ArgumentRangeError):
            t(M.SSIZE_MAX + 1)

    @small_SSIZE_MAX
    def test_unnumbered_out_of_range(self):
        def t(i):
            s = '{}' * i
            M.FormatString(s)
        t(M.SSIZE_MAX + 1)
        with assert_raises(M.ArgumentRangeError):
            t(M.SSIZE_MAX + 2)

class test_named_arguments:

    def test_good(self):
        fmt = M.FormatString('{spam}')
        [fld] = fmt
        [(aname, [afld])] = fmt.argument_map.items()
        assert_equal(aname, 'spam')
        assert_is(fld, afld)

    def test_bad(self):
        with assert_raises(M.Error):
            M.FormatString('{3ggs}')

class test_format_spec:

    def test_bad_char(self):
        with assert_raises(M.Error):
            M.FormatString('{:@}')

    def test_bad_letter(self):
        with assert_raises(M.Error):
            M.FormatString('{:Z}')

    def test_comma(self):
        def t(k):
            M.FormatString('{:,' + k + '}')
        t('')
        for k in 'bcdoxXeEfFgG':
            t(k)
        for k in 'ns':
            with assert_raises(M.Error):
                t(k)

    def test_alt_sign(self):
        def t(c, k):
            M.FormatString('{:' + c + k + '}')
        for c in ' +-#':
            t(c, '')
            for k in 'bcdoxXneEfFgG':
                t(c, k)
            with assert_raises(M.Error):
                t(c, 's')

    def test_align(self):
        def t(c, k):
            M.FormatString('{:' + c + k + '}')
        for c in '<>^':
            t(c, '')
            for k in 'bcdoxXneEfFgGs':
                t(c, k)
                t(c + '0', k)
        for c in '=0':
            t(c, '')
            for k in 'bcdoxXneEfFgG':
                t(c, k)
            with assert_raises(M.Error):
                t(c, 's')

    def test_width(self):
        def t(w, k):
            if k == '\0':
                k = ''
            M.FormatString('{:' + str(w) + k + '}')
        for k in 'bcdoxXneEfFgGs\0':
            for i in 4, 37, M.SSIZE_MAX:
                t(i, k)
            with assert_raises(M.Error):
                t(M.SSIZE_MAX + 1, k)

    def test_precision(self):
        def t(w, k):
            if k == '\0':
                k = ''
            M.FormatString('{:.' + str(w) + k + '}')
        for k in 'neEfFgGs\0':
            for i in {4, 37, M.SSIZE_MAX}:
                t(i, k)
            with assert_raises(M.Error):
                t(M.SSIZE_MAX + 1, k)
        for k in 'bcdoxX':
            for i in {4, 37, M.SSIZE_MAX, M.SSIZE_MAX + 1}:
                with assert_raises(M.Error):
                    t(i, k)

    def test_type_compat(self):
        def t(k1, k2):
            s = '{0:' + k1 + '}{0:' + k2 + '}'
            M.FormatString(s)
        def e(k1, k2):
            with assert_raises(M.ArgumentTypeMismatch):
                t(k1, k2)
        ks = 'bcdoxXneEfFgGs'
        compat = [
            ('s', 's'),
            ('bcdoxX', 'bcdoxXn'),
            ('n', 'bcdoxXneEfFgG'),
            ('eEfFgG', 'neEfFgG'),
        ]
        for k in ks:
            t(k, '')
            t('', k)
        for (k1s, k2s) in compat:
            for k1 in k1s:
                for k2 in k2s:
                    t(k1, k2)
                for k2 in ks:
                    if k2 not in k2s:
                        e(k1, k2)

    def test_nested_fields(self):
        def t(v=None, f=None):
            if v is None:
                v = ''
            if f is None:
                f = ''
            s = '{' + str(v) + ':{' + str(f) + '}}'
            return M.FormatString(s)
        fmt = t()
        assert_equal(len(fmt.argument_map), 2)
        t(v=0, f=M.SSIZE_MAX)
        with assert_raises(M.ArgumentRangeError):
            t(v=0, f=(M.SSIZE_MAX + 1))
        with assert_raises(M.ArgumentNumberingMixture):
            t(v=0)
        with assert_raises(M.ArgumentNumberingMixture):
            t(f=0)

# vim:ts=4 sts=4 sw=4 et

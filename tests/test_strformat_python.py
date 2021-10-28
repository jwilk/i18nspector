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

import struct

import pytest

import lib.strformat.python as M
from . import tools

def test_SSIZE_MAX():
    struct.pack('=i', M.SSIZE_MAX)
    with pytest.raises(struct.error):
        struct.pack('=i', M.SSIZE_MAX + 1)

def test_lone_percent():
    with pytest.raises(M.Error):
        M.FormatString('%')

def test_invalid_conversion_spec():
    with pytest.raises(M.Error):
        M.FormatString('%!')

def test_add_argument():
    fmt = M.FormatString('%s')
    with pytest.raises(RuntimeError):
        fmt.add_argument(None, None)
    with pytest.raises(RuntimeError):
        fmt.add_argument('eggs', None)

def test_text():
    fmt = M.FormatString('eggs%dbacon%dspam')
    assert len(fmt) == 5
    fmt = list(fmt)
    assert fmt[0] == 'eggs'
    assert fmt[2] == 'bacon'
    assert fmt[4] == 'spam'

class test_map:

    def t(self, key):
        s = '%(' + key + ')s'
        fmt = M.FormatString(s)
        assert len(fmt) == 1
        assert fmt.seq_arguments == []
        [pkey] = fmt.map_arguments.keys()
        assert key == pkey

    def test_simple(self):
        self.t('eggs')

    def test_balanced_parens(self):
        self.t('eggs(ham)spam')

    def test_unbalanced_parens(self):
        with pytest.raises(M.Error):
            self.t('eggs(ham')

class test_types:

    @staticmethod
    def t( s, tp, warn_type=None):
        fmt = M.FormatString(s)
        [conv] = fmt
        assert isinstance(conv, M.Conversion)
        assert conv.type == tp
        assert len(fmt.map_arguments) == 0
        if tp == 'None':
            assert fmt.seq_arguments == []
        else:
            [arg] = fmt.seq_arguments
            assert arg.type == tp
        if warn_type is None:
            assert len(fmt.warnings) == 0
        else:
            [warning] = fmt.warnings
            assert isinstance(warning, warn_type)

    @tools.collect_yielded
    def test_integer():
        def t(*args):
            test_types.t(*args)
        for c in 'oxXdi':
            yield t, ('%' + c, 'int')
        yield t, ('%u', 'int', M.ObsoleteConversion)

    @tools.collect_yielded
    def test_float():
        def t(*args):
            test_types.t(*args)
        for c in 'eEfFgG':
            yield t, ('%' + c, 'float')

    @tools.collect_yielded
    def test_str():
        def t(*args):
            test_types.t(*args)
        yield t, ('%c', 'chr')
        yield t, ('%s', 'str')

    @tools.collect_yielded
    def test_repr():
        def t(*args):
            test_types.t(*args)
        for c in 'ra':
            yield t, ('%' + c, 'object')

    @tools.collect_yielded
    def test_void():
        def t(*args):
            test_types.t(*args)
        yield t, ('%%', 'None')

@tools.collect_yielded
def test_length():
    def t(l):
        fmt = M.FormatString('%' + l + 'd')
        [warning] = fmt.warnings
        assert isinstance(warning, M.RedundantLength)
    for l in 'hlL':
        yield t, l

class test_indexing:

    def test_percent(self):
        with pytest.raises(M.ForbiddenArgumentKey):
            M.FormatString('%(eggs)%')

    def test_indexing_mixture(self):
        def t(s):
            with pytest.raises(M.ArgumentIndexingMixture):
                M.FormatString(s)
        t('%s%(eggs)s')
        t('%(eggs)s%s')

# TODO: "u" should be everywhere, where "d" is

class test_multiple_flags:

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

@tools.collect_yielded
def test_single_flag():

    def t(s, expected):
        fmt = M.FormatString(s)
        assert len(fmt) == 1
        if expected:
            assert fmt.warnings == []
        else:
            [exc] = fmt.warnings
            assert isinstance(exc, M.RedundantFlag)

    for c in 'dioxXeEfFgGcrsa%':
        yield t, (('%#' + c), (c in 'oxXeEfFgG'))
        for flag in '0 +':
            yield t, (('%' + flag + c), (c in 'dioxXeEfFgG'))
        yield t, (('%-' + c), True)

class test_width:

    @tools.collect_yielded
    def test_ok():
        def t(s):
            fmt = M.FormatString(s)
            assert len(fmt) == 1
            assert fmt.warnings == []
        for c in 'dioxXeEfFgGcrsa%':
            yield t, ('%1' + c)

    def test_too_large(self):
        fmt = M.FormatString('%{0}d'.format(M.SSIZE_MAX))
        assert len(fmt) == 1
        assert len(fmt.seq_arguments) == 1
        assert len(fmt.map_arguments) == 0
        with pytest.raises(M.WidthRangeError):
            M.FormatString('%{0}d'.format(M.SSIZE_MAX + 1))

    def test_variable(self):
        fmt = M.FormatString('%*s')
        assert len(fmt) == 1
        assert len(fmt.map_arguments) == 0
        [a1, a2] = fmt.seq_arguments
        assert a1.type == 'int'
        assert a2.type == 'str'

    def test_indexing_mixture(self):
        def t(s):
            with pytest.raises(M.ArgumentIndexingMixture):
                M.FormatString(s)
        t('%*s%(eggs)s')
        t('%(eggs)s%*s')

class test_precision:

    @tools.collect_yielded
    def test_ok():
        def t(s):
            fmt = M.FormatString(s)
            assert len(fmt) == 1
        for c in 'dioxXeEfFgGrsa':
            yield t, ('%.1' + c)

    @tools.collect_yielded
    def test_redundant_0():
        def t(s):
            fmt = M.FormatString(s)
            assert len(fmt) == 1
            [warning] = fmt.warnings
            assert isinstance(warning, M.RedundantFlag)
        for c in 'dioxX':
            yield t, ('%0.1' + c)

    @tools.collect_yielded
    def test_non_redundant_0():
        def t(s):
            fmt = M.FormatString(s)
            assert len(fmt) == 1
            assert fmt.warnings == []
        for c in 'eEfFgG':
            yield t, ('%0.1' + c)

    @tools.collect_yielded
    def test_unexpected():
        def t(s):
            fmt = M.FormatString(s)
            assert len(fmt) == 1
            [warning] = fmt.warnings
            assert isinstance(warning, M.RedundantPrecision)
        for c in 'c%':
            yield t, ('%.1' + c)

    def test_too_large(self):
        fmt = M.FormatString('%.{0}f'.format(M.SSIZE_MAX))
        assert len(fmt) == 1
        with pytest.raises(M.PrecisionRangeError):
            M.FormatString('%.{0}f'.format(M.SSIZE_MAX + 1))

    def test_variable(self):
        fmt = M.FormatString('%.*f')
        assert len(fmt) == 1
        assert len(fmt.map_arguments) == 0
        [a1, a2] = fmt.seq_arguments
        assert a1.type == 'int'
        assert a2.type == 'float'

    def test_indexing_mixture(self):
        def t(s):
            with pytest.raises(M.ArgumentIndexingMixture):
                M.FormatString(s)
        t('%.*f%(eggs)f')
        t('%(eggs)f%.*f')

class test_type_compatibility:

    def test_okay(self):
        def t(s, tp):
            fmt = M.FormatString(s)
            assert len(fmt.seq_arguments) == 0
            [args] = fmt.map_arguments.values()
            assert len(args) > 1
            for arg in args:
                assert arg.type == tp
        t('%(eggs)d%(eggs)d', 'int')
        t('%(eggs)d%(eggs)i', 'int')

    def test_mismatch(self):
        def t(s):
            with pytest.raises(M.ArgumentTypeMismatch):
                M.FormatString(s)
        t('%(eggs)d%(eggs)s')

def test_seq_conversions():
    def t(s, n):
        fmt = M.FormatString(s)
        assert len(fmt.seq_conversions) == n
        for arg in fmt.seq_conversions:
            assert isinstance(arg, M.Conversion)
    t('%d', 1)
    t('%d%d', 2)
    t('eggs%dham', 1)
    t('%(eggs)d', 0)
    t('%*d', 1)
    t('%.*d', 1)

# vim:ts=4 sts=4 sw=4 et

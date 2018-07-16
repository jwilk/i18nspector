# Copyright © 2015-2018 Jakub Wilk <jwilk@jwilk.net>
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

'''
string format checks: Python's %-formatting
'''

import collections
import io

class _info:

    flags = '#0- +'
    lengths = 'hlL'

    oct_cvt = 'o'
    hex_cvt = 'xX'
    int_cvt = oct_cvt + hex_cvt + 'diu'

    float_cvt = 'eEfFgG'

    other_cvt = 'csra'

    all_cvt = int_cvt + float_cvt + other_cvt + '%'

SSIZE_MAX = (1 << 31) - 1  # on 32-bit architectures

# --------------------------------------------------------------------------

class Error(Exception):
    message = 'invalid conversion specification'

class ObsoleteConversion(Error):
    message = 'obsolete conversion specifier'

# errors in argument indexing:

class ForbiddenArgumentKey(Error):
    message = 'argument key not allowed'

class ArgumentIndexingMixture(Error):
    message = 'mixed named and unnamed argument specifications'

class ArgumentTypeMismatch(Error):
    message = 'argument type mismatch'

# errors is flags:

class RedundantFlag(Error):
    message = 'redundant flag character'

# errors in field width:

class WidthRangeError(Error):
    message = 'field width too large'

# errors in precision:

class RedundantPrecision(Error):
    message = 'redundant precision'

class PrecisionRangeError(Error):
    message = 'precision too large'

# errors in length modifiers:

class RedundantLength(Error):
    message = 'redundant length modifier'

# --------------------------------------------------------------------------

class VariableWidth():

    type = 'int'

    def __init__(self, parent):
        self.parent = parent

class VariablePrecision():

    type = 'int'

    def __init__(self, parent):
        self.parent = parent

# --------------------------------------------------------------------------

class FormatString():

    def __init__(self, s):
        self._items = items = []
        self._seq_arguments = []
        self._map_arguments = collections.defaultdict(list)
        self.warnings = []
        text = io.StringIO()
        si = enumerate(s)
        i = 0
        def next_si():
            try:
                return next(si)
            except StopIteration:
                raise Error(s[i:])
        while True:
            try:
                i, ch = next(si)
            except StopIteration:
                if text.tell():
                    items += [text.getvalue()]
                break
            if ch != '%':
                text.write(ch)
                continue
            j, ch = next_si()
            key = None
            if ch == '(':
                # XXX Python skips over balanced parentheses, but this is not documented.
                pcount = 1
                while True:
                    j, ch = next_si()
                    if ch == '(':
                        pcount += 1
                    elif ch == ')':
                        pcount -= 1
                        if pcount == 0:
                            j, ch = next_si()
                            break
                key = s[i+2:j-1]
            flags = collections.Counter()
            while ch in _info.flags:
                flags[ch] += 1
                j, ch = next_si()
            width = None
            var_width = False
            if ch == '*':
                var_width = True
                j, ch = next_si()
            else:
                width = 0
                while ch >= '0' and ch <= '9':
                    width *= 10
                    width += int(ch)
                    j, ch = next_si()
            prec = None
            var_prec = False
            if ch == '.':
                j, ch = next_si()
                if ch == '*':
                    var_prec = True
                    j, ch = next_si()
                else:
                    prec = 0
                    while ch >= '0' and ch <= '9':
                        prec *= 10
                        prec += int(ch)
                        j, ch = next_si()
            length = None
            if ch in _info.lengths:
                length = ch
                j, ch = next_si()
            if ch in _info.all_cvt:
                conv = ch
            else:
                raise Error(s[i:])
            if text.tell():
                items += [text.getvalue()]
                text.seek(0)
                text.truncate()
            items += [Conversion(self,
                s[i:j+1],
                key=key,
                flags=flags,
                width=width,
                var_width=var_width,
                prec=prec,
                var_prec=var_prec,
                length=length,
                conv=conv,
            )]
        self.seq_arguments = self._seq_arguments
        self.seq_conversions = [
            arg
            for arg in self._seq_arguments
            if isinstance(arg, Conversion)
        ]
        for key, args in self._map_arguments.items():
            types = frozenset(a.type for a in args)
            if len(types) > 1:
                raise ArgumentTypeMismatch(s, key, types)
        self.map_arguments = self._map_arguments
        self._map_arguments = self._seq_arguments = None

    def add_argument(self, key, arg):
        if self._map_arguments is None:
            raise RuntimeError('arguments already initialized')
        # Python accepts mixed named and unnamed arguments
        # in some corner cases:
        # https://bugs.python.org/issue1467929
        # We follow the documentation and reject such mixtures.
        if key is None:
            if self._map_arguments:
                raise IndexError
            self._seq_arguments += [arg]
        else:
            if self._seq_arguments:
                raise IndexError
            self._map_arguments[key] += [arg]

    def warn(self, exc_type, *args, **kwargs):
        self.warnings += [exc_type(*args, **kwargs)]

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

# --------------------------------------------------------------------------

class Conversion():

    def __init__(self, parent, s, *, key, flags, width, var_width, prec, var_prec, length, conv):
        assert s[-1] == conv, '{0} != {1}'.format(s[-1], conv)
        i = _info
        for flag, count in flags.items():
            if count != 1:
                parent.warn(RedundantFlag, s, flag, flag)
            if flag == '#':
                if conv not in i.oct_cvt + i.hex_cvt + i.float_cvt:
                    parent.warn(RedundantFlag, s, flag)
            elif flag == '-':
                pass
            else:
                assert flag in '0 +'
                if conv not in i.int_cvt + i.float_cvt:
                    parent.warn(RedundantFlag, s, flag)
        for f1, f2 in [('-', '0'), ('+', ' ')]:
            if (f1 in flags) and (f2 in flags):
                parent.warn(RedundantFlag, s, f1, f2)
        if var_width:
            assert width is None
            try:
                parent.add_argument(None, VariableWidth(self))
            except IndexError:
                raise ArgumentIndexingMixture(s)
            width = ...
        elif width > SSIZE_MAX:
            # The limit is INT_MAX in Python 2.X and SSIZE_MAX in Python 3.X;
            # but INT_MAX == SSIZE_MAX on mainstream 32-bit architectures.
            raise WidthRangeError(s, width)
        if var_prec:
            assert prec is None
            try:
                parent.add_argument(None, VariablePrecision(self))
            except IndexError:
                raise ArgumentIndexingMixture(s)
            prec = ...
        elif prec is not None:
            if prec > SSIZE_MAX:
                raise PrecisionRangeError(s, width)
        if prec is not None:
            if (conv in i.int_cvt) and ('0' in flags):
                parent.warn(RedundantFlag, s, '0')
            if conv in 'c%':
                parent.warn(RedundantPrecision, s, prec)
        if length is not None:
            parent.warn(RedundantLength, s, length)
        if conv in i.int_cvt:
            tp = 'int'
            if conv == 'u':
                parent.warn(ObsoleteConversion, s, '%u', '%d')
        elif conv in i.float_cvt:
            tp = 'float'
        elif conv == 'c':
            tp = 'chr'
        elif conv == 's':
            tp = 'str'
        elif conv in 'ra':
            tp = 'object'
        elif conv == '%':
            tp = 'None'
        else:
            assert False  # no coverage
        self.type = tp
        if tp == 'None':
            if key is not None:
                raise ForbiddenArgumentKey(s)
        else:
            try:
                parent.add_argument(key, self)
            except IndexError:
                raise ArgumentIndexingMixture(s)

# vim:ts=4 sts=4 sw=4 et

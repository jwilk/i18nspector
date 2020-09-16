# Copyright © 2016-2020 Jakub Wilk <jwilk@jwilk.net>
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
string format checks: Python's str.format()
'''

import collections
import functools
import re

_field_name_pattern = r'''
    (?: \d+ | [^\W\d]\w* )
    (?:
        [.] [^\W\d]\w* |
        \[ [^]]+ \]
    )*
'''

_simple_field_pattern = '[{] (?:' + _field_name_pattern + ') ? [}]'

_simple_field_re = re.compile(_simple_field_pattern, re.VERBOSE)

_field_re = re.compile(r'''
    (?P<literal> (?: [^{}] | [{]{2} | [}]{2} )+ ) |
    (?:
        [{]
            (?:
                (?P<name>''' + _field_name_pattern + r''') ?
                (?P<conversion> ! \w+ ) ?
                (?P<format> :
                    (?:
                        [^{}]* |
                        ''' + _simple_field_pattern + '''
                    )*
                ) ?
            )
        [}]
    )
''', re.VERBOSE)

_format_spec_re = re.compile(
# (this regex doesn't take nested fields into account)
r'''
    \A
    (?:
        (?P<fill> [^}] ) ?
        (?P<align> [<>=^] )
    ) ?
    (?P<sign> [ +-] ) ?
    (?P<alt> [#] ) ?
    (?P<zero> [0] ) ?
    (?P<width> [0-9]+ ) ?
    (?P<comma> [,] ) ?
    (?:
        [.]
        (?P<precision> \d+)
    ) ?
    (?P<type> [\w%]) ?
    \Z
''', re.VERBOSE)

def _printable_prefix(s, r=re.compile('[ -\x7E]+')):
    return r.match(s).group()

# --------------------------------------------------------------------------

SSIZE_MAX = (1 << 31) - 1  # on 32-bit architectures

# --------------------------------------------------------------------------

class Error(Exception):
    message = 'invalid replacement field specification'

class ConversionError(Error):
    message = 'invalid conversion flag'

class FormatError(Error):
    message = 'invalid format specification'

class FormatTypeMismatch(Error):
    message = 'type mismatch between conversion and format specifications'

# errors in argument indexing:

class ArgumentNumberingMixture(Error):
    message = 'mixed numbered and unnumbered argument specifications'

class ArgumentRangeError(Error):
    message = 'argument index too large'

class ArgumentTypeMismatch(Error):
    message = 'argument type mismatch'

# --------------------------------------------------------------------------

class FormatString():

    def __init__(self, s):
        self._argument_map = collections.defaultdict(list)
        self._next_arg_index = 0
        self._items = items = []
        last_pos = 0
        for match in _field_re.finditer(s):
            if match.start() != last_pos:
                raise Error(
                    _printable_prefix(s[last_pos:])
                )
            last_pos = match.end()
            literal = match.group('literal')
            if literal is not None:
                items += [literal]
            else:
                items += [Field(self, match)]
        if last_pos != len(s):
            raise Error(
                _printable_prefix(s[last_pos:])
            )
        for name, args in self._argument_map.items():
            common_types = functools.reduce(
                frozenset.__and__,
                (a.types for a in args)
            )
            if not common_types:
                raise ArgumentTypeMismatch(s, name)
            for arg in args:
                arg.types = common_types
        self.argument_map = dict(self._argument_map)
        self._argument_map = None

    def add_argument(self, name, field):
        if self._argument_map is None:
            raise RuntimeError('arguments already initialized')
        if name is None:
            if self._next_arg_index is None:
                raise IndexError
            n = self._next_arg_index
            if n > SSIZE_MAX:
                raise OverflowError(n)
            self._next_arg_index += 1
            self._argument_map[n] += [field]
        elif name.isdigit():
            n = int(name)
            if n > SSIZE_MAX:
                raise OverflowError(n)
            if self._next_arg_index is None:
                pass
            elif self._next_arg_index == 0:
                self._next_arg_index = None
            else:
                raise IndexError
            self._argument_map[n] += [field]
        else:
            self._argument_map[name] += [field]

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

# --------------------------------------------------------------------------

class Field():

    def __init__(self, parent, match):
        s = match.string[slice(*match.span())]
        name = match.group('name')
        try:
            parent.add_argument(name, self)
        except IndexError:
            raise ArgumentNumberingMixture(s)
        except OverflowError:
            raise ArgumentRangeError(s)
        fmt = match.group('format')
        tp = {'str', 'int', 'float'}
        if fmt is None:
            pass
        elif '{' in fmt:
            # Nested replacement fields are nasty. They make virtually
            # impossible to do any type checking. For example:
            #
            #     >>> '{:{}{}}'.format('m', 'o<2', 3)
            #     'moooooooooooooooooooooo'
            #     >>> '{:{}{}}'.format(23, '+', 'x')
            #     '+17'
            #
            for subfield in _simple_field_re.findall(fmt):
                assert subfield[0] == '{'
                assert subfield[-1] == '}'
                subfield_name = subfield[1:-1] or None
                subfield = NestedField(self)
                try:
                    parent.add_argument(subfield_name, subfield)
                except IndexError:
                    raise ArgumentNumberingMixture(subfield)
                except OverflowError:
                    raise ArgumentRangeError(s)
        else:
            assert fmt[0] == ':'
            fmatch = _format_spec_re.match(fmt[1:])
            if fmatch is None:
                raise FormatError(s)
            comma = fmatch.group('comma')
            ftype = fmatch.group('type')
            if ftype is None:
                pass
            elif ftype == 's':
                tp = {'str'}
            elif ftype in 'bcdoxX':
                tp = {'int'}
            elif ftype in 'eEfFgG%':
                tp = {'float'}
            elif ftype == 'n':
                if comma:
                    raise FormatError(s)
                tp = {'int', 'float'}
            else:
                raise Error(s)
            alt = fmatch.group('alt')
            sign = fmatch.group('sign')
            if alt or sign or comma:
                tp &= {'int', 'float'}
                if not tp:
                    raise FormatError(s)
            align = fmatch.group('align')
            zero = fmatch.group('zero')
            if (align is None) and (zero is not None):
                align = '='
            if align == '=':
                tp &= {'int', 'float'}
                if not tp:
                    raise FormatError(s)
            width = fmatch.group('width')
            if width is not None:
                width = int(width)
                if width > SSIZE_MAX:
                    raise FormatError(s)
            precision = fmatch.group('precision')
            if precision is not None:
                tp &= {'float', 'str'}
                if not tp:
                    raise FormatError(s)
                precision = int(precision)
                if precision > SSIZE_MAX:
                    raise FormatError(s)
        conversion = match.group('conversion')
        if conversion is None:
            pass
        elif conversion in {'!s', '!r', '!a'}:
            if 'str' not in tp:
                raise FormatTypeMismatch(s)
        else:
            raise ConversionError(s)
        self.types = frozenset(tp)

class NestedField():

    types = frozenset({'str', 'int', 'float'})

    def __init__(self, parent):
        self.parent = parent

# vim:ts=4 sts=4 sw=4 et

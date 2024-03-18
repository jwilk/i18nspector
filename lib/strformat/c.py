# Copyright © 2014-2022 Jakub Wilk <jwilk@jwilk.net>
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
string format checks: C
'''

import collections
import re

_directive_re = re.compile('''
    (?P<literal> [^%]+ ) |
    (
        %
        (?P<index> [0-9]+[$] )?
        (?P<flags> [#0 +'I-]* )
        (?:
            (?P<width> [1-9][0-9]* ) |
            (?P<varwidth> [*] ) (?P<varwidth_index> [0-9]+[$] )?
        )?
        (?:
            [.]
            (?:
                (?P<precision> [0-9]* ) |
                (?P<varprec> [*] ) (?P<varprec_index> [0-9]+[$] )?
            )
        )?
        (?:
            (?P<length>
                hh? | ll? | [qjzZt] | L
            )?
            (?P<conversion>
                [diouxXeEfFgGaAcsCSpnm%]
            ) |
            < (?: PRI (?P<c99conv>[diouxX]) (?P<c99len> (?:LEAST|FAST)?(?:8|16|32|64)|MAX|PTR) ) >
        )
    )
''', re.VERBOSE)

def _printable_prefix(s, r=re.compile('[ -\x7E]+')):
    return r.match(s).group()

class _info:

    oct_cvt = 'o'
    hex_cvt = 'xXaA'
    dec_cvt = 'diufFgG'
    float_cvt = 'aAeEfFgG'
    uint_cvt = 'ouxX'
    int_cvt = 'di' + uint_cvt
    str_cvt = 'sS'

    int_types = '''
    hh = signed char | unsigned char
    h = short int | unsigned short int
    l = long int | unsigned long int
    ll = long long int | unsigned long long int
    j = intmax_t | uintmax_t
    z = ssize_t | size_t
    t = ptrdiff_t | [unsigned ptrdiff_t]
    = int | unsigned int
    '''
    int_types = {
        key: tuple(str.strip(v) for v in values.split('|'))
        for line in int_types.strip().splitlines()
        for key, values in [map(str.strip, line.split('='))]
    }
    # FIXME: The printf(3) manpage says that the type for signed integer with
    # “z“ size is ssize_t.
    # But SUSv3 says it's a signed integer type corresponding to size_t,
    # which is not necessarily the same thing as ssize_t.

    # https://www.gnu.org/software/libc/manual/html_node/Integer-Conversions.html
    portable_int_lengths = dict(
        L='ll',
        q='ll',
        Z='z',
    )

INT_MAX = (1 << 31) - 1  # on most architectures
NL_ARGMAX = 4096  # on GNU/Linux

class Error(Exception):
    message = 'invalid conversion specification'

class NonPortableConversion(Error):
    message = 'non-portable conversion specifier or length modifier'

# errors in argument indexing:

class ForbiddenArgumentIndex(Error):
    message = 'argument index not allowed'

class ArgumentRangeError(Error):
    message = 'argument index too small or too large'

class MissingArgument(Error):
    message = 'missing argument'

class ArgumentTypeMismatch(Error):
    message = 'argument type mismatch'

class ArgumentNumberingMixture(Error):
    message = 'mixed numbered and unnumbered argument specifications'

# errors in length modifiers:

class LengthError(Error):
    message = 'invalid length modifier'

# errors in flag characters:

class FlagError(Error):
    message = 'unexpected format flag character'

class RedundantFlag(Error):
    message = 'redundant flag character'

# errors in field width:

class WidthError(Error):
    message = 'unexpected width'

class WidthRangeError(Error):
    message = 'field width too large'

# errors in precision:

class PrecisionError(Error):
    message = 'unexpected precision'

class PrecisionRangeError(Error):
    message = 'precision too large'


class VariableWidth:

    type = 'int'

    def __init__(self, parent):
        self.parent = parent

class VariablePrecision:

    type = 'int'

    def __init__(self, parent):
        self.parent = parent

class FormatString:

    def __init__(self, s):
        self._items = items = []
        self._argument_map = collections.defaultdict(list)
        self._next_arg_index = 1
        self.warnings = []
        last_pos = 0
        for match in _directive_re.finditer(s):
            if match.start() != last_pos:
                raise Error(
                    _printable_prefix(s[last_pos:])
                )
            last_pos = match.end()
            literal = match.group('literal')
            if literal is not None:
                items += [literal]
            else:
                items += [Conversion(self, match)]
        if last_pos != len(s):
            raise Error(
                _printable_prefix(s[last_pos:])
            )
        self.arguments = []
        for i in range(1, NL_ARGMAX + 1):
            if not self._argument_map:
                break
            try:
                args = self._argument_map.pop(i)
            except KeyError:
                raise MissingArgument(s, i)
            self.arguments += [args]
        assert not self._argument_map
        self._argument_map = None
        for i, args in enumerate(self.arguments, start=1):
            types = frozenset(a.type for a in args)
            if len(types) > 1:
                raise ArgumentTypeMismatch(s, i, types)

    def add_argument(self, n, value):
        if self._argument_map is None:
            raise RuntimeError('arguments already initialized')
        if n is None:
            if self._next_arg_index is None:
                raise IndexError
            else:
                n = self._next_arg_index
                self._next_arg_index += 1
        elif self._next_arg_index is None:
            pass
        elif self._next_arg_index == 1:
            assert not self._argument_map
            self._next_arg_index = None
        else:
            raise IndexError
        if n > NL_ARGMAX:
            raise OverflowError(n)
        self._argument_map[n] += [value]

    def warn(self, exc_type, *args, **kwargs):
        self.warnings += [exc_type(*args, **kwargs)]

    def get_last_integer_conversion(self, *, n):
        '''
        return the integer conversion that consumes the last n arguments,
        or None
        '''
        if n > len(self.arguments):
            raise IndexError
        if n <= 0:
            raise IndexError
        conv = vconv = None
        for i in range(len(self.arguments) - n, len(self.arguments)):
            assert i >= 0
            for arg in self.arguments[i]:
                if isinstance(arg, (VariableWidth, VariablePrecision)):
                    if vconv is None:
                        vconv = arg.parent
                    if vconv is not arg.parent:
                        return
                elif isinstance(arg, Conversion):
                    if vconv is None:
                        vconv = arg
                    if (conv is None) and (vconv is arg):
                        conv = arg
                    if conv is not arg:
                        return
                else:
                    assert False, f'type(arg) == {type(arg)!r}'  # no coverage
        if conv is None:
            return
        if not conv.integer:
            return
        return conv

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

class Conversion:

    type = None
    integer = None

    def __init__(self, parent, match):
        i = _info
        self._s = s = match.string[slice(*match.span())]
        # length and conversion:
        c99conversion = match.group('c99conv')
        c99length = match.group('c99len')
        length = match.group('length')
        conversion = match.group('conversion')
        tp = None
        self.integer = False
        if c99conversion is not None:
            assert c99length is not None
            if c99conversion in 'di':
                tp = 'int'
            elif c99conversion in 'ouxX':
                tp = 'uint'
            else:
                # should not happen
                assert False  # no coverage
            conversion = c99conversion
            if c99length.startswith(('LEAST', 'FAST')):
                tp += '_' + c99length.lower()
            else:
                tp += c99length.lower()
            tp += '_t'
            self.integer = True
        elif conversion in i.int_cvt + 'n':
            plength = i.portable_int_lengths.get(length, length)
            if plength != length:
                parent.warn(NonPortableConversion, s,
                    '%' + length + conversion,
                    '%' + plength + conversion
                )
            tp = i.int_types.get(plength or '')  # pylint: disable=no-member
            assert tp is not None
            tp = tp[conversion in i.uint_cvt]
            if conversion == 'n':
                tp += ' *'
            else:
                self.integer = True
        elif conversion in i.float_cvt:
            if length is None:
                tp = 'double'
            elif length == 'l':
                # XXX C99 says that the “l” length is no-op for floating-point
                # conversions, but this is not documented in the printf(3)
                # manpage.
                parent.warn(NonPortableConversion, s,
                    '%l' + conversion,
                    '%' + conversion
                )
                tp = 'double'
            elif length == 'L':
                tp = 'long double'
        elif conversion == 'c':
            if length is None:
                tp = 'char'
                # C99 says it's an int, which is then converted to unsigned char.
                # We don't want “int” here, so that %c and %d have distinct types.
                # Mere “char” is not very precise, but it should be good enough.
            elif length == 'l':
                tp = 'wint_t'
        elif conversion == 'C':
            if length is None:
                parent.warn(NonPortableConversion, s, '%C', '%lc')
                tp = 'wint_t'
        elif conversion == 's':
            if length is None:
                tp = 'const char *'
            elif length == 'l':
                tp = 'const wchar_t *'
        elif conversion == 'S':
            if length is None:
                parent.warn(NonPortableConversion, s, '%S', '%ls')
                tp = 'const wchar_t *'
        elif conversion == 'p':
            if length is None:
                tp = 'void *'
        elif conversion in {'m', '%'}:
            if length is None:
                tp = 'void'
        else:
            # should not happen
            assert False  # no coverage
        if tp is None:
            assert length is not None
            raise LengthError(s, length)
        self.type = tp
        # flags:
        flags = collections.Counter(match.group('flags'))
        for flag, count in flags.items():
            if count != 1:
                parent.warn(RedundantFlag, s, flag, flag)
            if conversion == 'n':
                raise FlagError(s, flag)
            if flag == '#':
                if conversion not in i.oct_cvt + i.hex_cvt + i.float_cvt:
                    raise FlagError(s, flag)
            elif flag == '0':
                if conversion not in i.int_cvt + i.float_cvt:
                    raise FlagError(s, flag)
            elif flag == "'":
                if conversion not in i.dec_cvt:
                    raise FlagError(s, flag)
            else:
                if conversion == '%':
                    raise FlagError(s, flag)
                assert flag in {'-', ' ', '+', 'I'}
        for f1, f2 in [('-', '0'), ('+', ' ')]:
            if (f1 in flags) and (f2 in flags):
                parent.warn(RedundantFlag, s, f1, f2)
        # width:
        width = match.group('width')
        if width is not None:
            width = int(width)
            if width > INT_MAX:
                raise WidthRangeError(s, width)
        elif match.group('varwidth'):
            varwidth_index = match.group('varwidth_index')
            if varwidth_index is not None:
                varwidth_index = int(varwidth_index.rstrip('$'))
                if not (0 < varwidth_index <= NL_ARGMAX):
                    raise ArgumentRangeError(s, varwidth_index)
            try:
                parent.add_argument(varwidth_index, VariableWidth(self))
            except IndexError:
                raise ArgumentNumberingMixture(s)
            except OverflowError as exc:
                raise ArgumentRangeError(s, f'{exc}$')
            width = ...
        if width is not None:
            if conversion in '%n':
                raise WidthError(s)
        # precision:
        precision = match.group('precision')
        if precision is not None:
            precision = int(precision or '0')
            if precision > INT_MAX:
                raise PrecisionRangeError(s)
        elif match.group('varprec'):
            varprec_index = match.group('varprec_index')
            if varprec_index is not None:
                varprec_index = int(varprec_index.rstrip('$'))
                if not (0 < varprec_index <= NL_ARGMAX):
                    raise ArgumentRangeError(s, varprec_index)
            try:
                parent.add_argument(varprec_index, VariablePrecision(self))
            except IndexError:
                raise ArgumentNumberingMixture(s)
            except OverflowError as exc:
                raise ArgumentRangeError(s, f'{exc}$')
            precision = ...
        if precision is not None:
            if conversion in i.int_cvt + i.float_cvt + i.str_cvt:
                pass
            else:
                # XXX C99 says that precision for the other conversion is
                # undefined behavior, but this is not documented in the
                # printf(3) manpage.
                raise PrecisionError(s)
            if (conversion in i.int_cvt) and ('0' in flags):
                parent.warn(RedundantFlag, s, '0')
        # index:
        index = match.group('index')
        if index is not None:
            index = int(index.rstrip('$'))
            if not (0 < index <= NL_ARGMAX):
                raise ArgumentRangeError(s, index)
        if tp == 'void':
            if index is not None:
                if conversion == '%':
                    raise ForbiddenArgumentIndex(s)
                else:
                    # Although not specifically forbidden, having an argument index
                    # for %m (which doesn't consume any argument) doesn't make any
                    # sense. TODO: Emit a warning.
                    pass
            # XXX The printf(3) manpage says that numbered arguments can be
            # mixed only with %%. But practically, mixing them with %m (which
            # also doesn't consume any argument) must be also allowed.
        else:
            try:
                parent.add_argument(index, self)
            except IndexError:
                raise ArgumentNumberingMixture(s)
            except OverflowError as exc:
                raise ArgumentRangeError(s, f'{exc}$')

# vim:ts=4 sts=4 sw=4 et

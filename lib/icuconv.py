# Copyright © 2013-2022 Jakub Wilk <jwilk@jwilk.net>
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
string encoding and decoding using PyICU
'''

import re
import sys

import icu

default_encoding = sys.getdefaultencoding()

_parse_decode_error = re.compile(r"^'\S+' codec can't decode byte 0x[0-9a-f]{2} in position ([0-9]+): [0-9]+ \((.+)\)$").match

IcuString = icu.UnicodeString  # pylint: disable=no-member

def encode(input: str, encoding=default_encoding, errors='strict'):
    if not isinstance(input, str):
        raise TypeError(f'input must be str, not {type(input).__name__}')
    if not isinstance(encoding, str):
        raise TypeError(f'encoding must be str, not {type(encoding).__name__}')
    if not isinstance(errors, str):
        raise TypeError(f'errors must be str, not {type(errors).__name__}')
    if len(input) == 0:
        return b''
    if errors != 'strict':
        raise NotImplementedError(f'error handler {errors!r} is not implemented')
    return _encode(input, encoding=encoding)

def _encode(input: str, *, encoding):
    s = IcuString(input).encode(encoding)
    try:
        _decode(s, encoding=encoding)
    except UnicodeDecodeError as exc:
        # PyICU uses the substitution error callback¹,
        # which is not what we want, and doesn't even guarantee
        # that the resulting string is correctly encoded.
        # As a work-around, try to decode.
        # ¹ https://unicode-org.github.io/icu/userguide/conversion/converters.html#error-callbacks
        raise UnicodeEncodeError(encoding, input, 0, len(input), exc.args[-1])
    return s

def decode(input: bytes, encoding=default_encoding, errors='strict'):
    if not isinstance(input, bytes):
        raise TypeError(f'input must be bytes, not {type(input).__name__}')
    if not isinstance(encoding, str):
        raise TypeError(f'encoding must be str, not {type(encoding).__name__}')
    if not isinstance(errors, str):
        raise TypeError(f'errors must be str, not {type(errors).__name__}')
    if len(input) == 0:
        return ''
    if errors != 'strict':
        raise NotImplementedError(f'error handler {errors!r} is not implemented')
    return _decode(input, encoding=encoding)

def _decode(input: bytes, *, encoding):
    try:
        s = IcuString(input, encoding)
    except ValueError as exc:
        begin = 0
        end = len(input)
        message = str(exc)
        match = _parse_decode_error(message)
        if match is not None:
            begin, message = match.groups()
            begin = int(begin)
            end = begin + 1
        raise UnicodeDecodeError(encoding, input, begin, end, message)
    else:
        return str(s)

__all__ = ['encode', 'decode']

# vim:ts=4 sw=4 et

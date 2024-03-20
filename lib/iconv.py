# Copyright © 2012-2024 Jakub Wilk <jwilk@jwilk.net>
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
string encoding and decoding using iconv(3), with a fallback to iconv(1)
'''

import ctypes
import errno
import os
import re
import subprocess as ipc
import sys

default_encoding = sys.getdefaultencoding()

_boring_iconv_stderr = re.compile('\nTry .+ for more information[.]$')

_libc = ctypes.CDLL(None, use_errno=True)
try:
    _iconv_open = _libc.iconv_open
    _iconv_close = _libc.iconv_close
    _iconv = _libc.iconv
except AttributeError:
    _iconv = _iconv_open = _iconv_close = None
else:
    _iconv_open.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    _iconv_open.restype = ctypes.c_void_p
    _iconv_close.argtypes = [ctypes.c_void_p]
    _iconv_close.restype = ctypes.c_int
    _iconv.argtypes = (
        [ctypes.c_void_p] +
        [ctypes.POINTER(ctypes.POINTER(ctypes.c_char)), ctypes.POINTER(ctypes.c_size_t)] * 2
    )
    _iconv.restype = ctypes.c_size_t

def _popen(*args):
    def set_lc_all_c():
        os.environ['LC_ALL'] = 'C'  # no coverage
    return ipc.Popen(args,  # pylint: disable=consider-using-with
        stdin=ipc.PIPE, stdout=ipc.PIPE, stderr=ipc.PIPE,
        preexec_fn=set_lc_all_c,
    )

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

def _encode_dl(input: str, *, encoding):
    uencoding = 'UTF-32LE'
    uwidth = 4
    binput = bytes(input, encoding=uencoding)
    assert len(binput) == len(input) * uwidth
    cd = _iconv_open(bytes(encoding, 'ASCII'), bytes(uencoding, 'ASCII'))
    assert isinstance(cd, int)
    if cd == ctypes.c_void_p(-1).value:
        rc = ctypes.get_errno()
        raise OSError(rc, os.strerror(rc))
    try:
        c_input = ctypes.c_char_p(binput)
        output_len = len(input)
        while True:
            inbuf = ctypes.cast(c_input, ctypes.POINTER(ctypes.c_char))
            inbytesleft = ctypes.c_size_t(len(binput))
            assert inbytesleft.value == len(binput)  # no overflow
            outbuf = ctypes.create_string_buffer(output_len)
            outbytesleft = ctypes.c_size_t(output_len)
            assert outbytesleft.value == output_len  # no overflow
            rc = _iconv(cd, None, None, None, None)
            if rc == ctypes.c_size_t(-1).value:
                rc = ctypes.get_errno()
                raise OSError(rc, os.strerror(rc))
            inbufptr = ctypes.pointer(ctypes.cast(inbuf, ctypes.POINTER(ctypes.c_char)))
            outbufptr = ctypes.pointer(ctypes.cast(outbuf, ctypes.POINTER(ctypes.c_char)))
            rc = _iconv(cd,
                inbufptr, ctypes.byref(inbytesleft),
                outbufptr, ctypes.byref(outbytesleft),
            )
            if rc != ctypes.c_size_t(-1).value:
                rc = _iconv(cd,
                    None, None,
                    outbufptr, ctypes.byref(outbytesleft),
                )
            if rc == ctypes.c_size_t(-1).value:
                rc = ctypes.get_errno()
                if rc == errno.E2BIG:
                    output_len *= 2
                    continue
                elif rc in {errno.EILSEQ, errno.EINVAL}:
                    begin = len(input) - inbytesleft.value // uwidth
                    raise UnicodeEncodeError(
                        encoding,
                        input,
                        begin, begin + 1,
                        os.strerror(errno.EILSEQ),
                    )
                raise OSError(rc, os.strerror(rc))
            assert inbytesleft.value == 0, f'{inbytesleft.value} bytes left'
            output_len -= outbytesleft.value
            return outbuf[:output_len]
    finally:
        rc = _iconv_close(cd)
        if rc != 0:
            rc = ctypes.get_errno()
            raise OSError(rc, os.strerror(rc))

def _encode_cli(input, *, encoding):
    child = _popen('iconv', '-f', 'UTF-8', '-t', encoding)
    (stdout, stderr) = child.communicate(input.encode('UTF-8'))
    if stderr != b'':
        stderr = stderr.decode('ASCII', 'replace')
        stderr = _boring_iconv_stderr.sub('', stderr)
        raise UnicodeEncodeError(encoding,
            input,  # .object
            0,  # .begin
            len(input),  # .end
            stderr.strip()  # .reason
        )
    return stdout

_encode = _encode_dl if _iconv is not None else _encode_cli

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

def _decode_dl(input: bytes, *, encoding):
    cd = _iconv_open(b'WCHAR_T', bytes(encoding, 'ASCII'))
    assert isinstance(cd, int)
    if cd == ctypes.c_void_p(-1).value:
        rc = ctypes.get_errno()
        raise OSError(rc, os.strerror(rc))
    try:
        c_input = ctypes.c_char_p(input)
        output_len = len(input)
        while True:
            inbuf = ctypes.cast(c_input, ctypes.POINTER(ctypes.c_char))
            inbytesleft = ctypes.c_size_t(len(input))
            assert inbytesleft.value == len(input)  # no overflow
            outbuf = ctypes.create_unicode_buffer(output_len)
            outbytesleft = ctypes.c_size_t(output_len)  # no overflow
            assert outbytesleft.value == output_len
            rc = _iconv(cd, None, None, None, None)
            if rc == ctypes.c_size_t(-1).value:
                rc = ctypes.get_errno()
                raise OSError(rc, os.strerror(rc))
            inbufptr = ctypes.pointer(ctypes.cast(inbuf, ctypes.POINTER(ctypes.c_char)))
            outbufptr = ctypes.pointer(ctypes.cast(outbuf, ctypes.POINTER(ctypes.c_char)))
            rc = _iconv(cd,
                inbufptr, ctypes.byref(inbytesleft),
                outbufptr, ctypes.byref(outbytesleft),
            )
            if rc != ctypes.c_size_t(-1).value:
                rc = _iconv(cd,
                    None, None,
                    outbufptr, ctypes.byref(outbytesleft),
                )
            if rc == ctypes.c_size_t(-1).value:
                rc = ctypes.get_errno()
                if rc == errno.E2BIG:
                    output_len *= 2
                    continue
                elif rc in {errno.EILSEQ, errno.EINVAL}:
                    begin = len(input) - inbytesleft.value
                    for end in range(begin + 1, len(input)):
                        # Assume that the encoding can be synchronized on ASCII characters.
                        # That's not necessarily true for _every_ encoding, but oh well.
                        if input[end] < 0x80:
                            break
                    else:
                        end = len(input)
                    raise UnicodeDecodeError(
                        encoding,
                        input,
                        begin, end,
                        os.strerror(errno.EILSEQ),
                    )
                raise OSError(rc, os.strerror(rc))
            assert inbytesleft.value == 0, f'{inbytesleft.value} bytes left'
            output_len -= outbytesleft.value
            assert output_len % ctypes.sizeof(ctypes.c_wchar) == 0
            unicode_output_len = output_len // ctypes.sizeof(ctypes.c_wchar)
            return outbuf[:unicode_output_len]
    finally:
        rc = _iconv_close(cd)
        if rc != 0:
            rc = ctypes.get_errno()
            raise OSError(rc, os.strerror(rc))

def _decode_cli(input, *, encoding):
    child = _popen('iconv', '-f', encoding, '-t', 'UTF-8')
    (stdout, stderr) = child.communicate(input)
    if stderr != b'':
        stderr = stderr.decode('ASCII', 'replace')
        stderr = _boring_iconv_stderr.sub('', stderr)
        raise UnicodeDecodeError(encoding,
            input,  # .object
            0,  # .begin
            len(input),  # .end
            stderr.strip()  # .reason
        )
    return stdout.decode('UTF-8')

_decode = _decode_dl if _iconv is not None else _decode_cli

__all__ = ['encode', 'decode']

# vim:ts=4 sts=4 sw=4 et

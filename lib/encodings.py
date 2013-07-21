# Copyright © 2012, 2013 Jakub Wilk <jwilk@jwilk.net>
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
- encoding information registry
- codecs for unusual encodings
'''

import codecs
import configparser
import contextlib
import errno
import itertools
import os
import unicodedata

from . import iconv
from . import misc
from . import paths

def charmap_encoding(encoding):

    def encode(input, errors='strict'):
        if not (_extra_encodings_installed > 0):
            # There doesn't seem to be a way to de-register a codec.
            # As a poor man's substitute, raise LookupError at decoding time.
            raise LookupError('unknown encoding: ' + encoding)
        return codecs.charmap_encode(input, errors, encoding_table)

    def decode(input, errors='strict'):
        if not (_extra_encodings_installed > 0):
            # There doesn't seem to be a way to de-register a codec.
            # As a poor man's substitute, raise LookupError at decoding time.
            raise LookupError('unknown encoding: ' + encoding)
        return codecs.charmap_decode(input, errors, decoding_table)

    def not_implemented(*args, **kwargs):
        raise NotImplementedError

    path = os.path.join(paths.datadir, 'charmaps', encoding.upper())
    try:
        file = open(path, 'rb')
    except IOError as exc:
        if exc.errno == errno.ENOENT:
            raise LookupError('unknown encoding: ' + encoding)
        raise
    with file:
        decoding_table = file.read()
    decoding_table = decoding_table.decode('UTF-8')
    encoding_table = codecs.charmap_build(decoding_table)

    return codecs.CodecInfo(
        encode=encode,
        decode=decode,
        streamreader=not_implemented,
        streamwriter=not_implemented,
        incrementalencoder=not_implemented,
        incrementaldecoder=not_implemented,
        name=encoding,
    )

def iconv_encoding(encoding):

    def encode(input, errors='strict'):
        if not (_extra_encodings_installed > 0):
            # There doesn't seem to be a way to de-register a codec.
            # As a poor man's substitute, raise LookupError at encoding time.
            raise LookupError('unknown encoding: ' + encoding)
        output = iconv.encode(input, encoding=encoding, errors=errors)
        return output, len(input)

    def decode(input, errors='strict'):
        if not (_extra_encodings_installed > 0):
            # There doesn't seem to be a way to de-register a codec.
            # As a poor man's substitute, raise LookupError at decoding time.
            raise LookupError('unknown encoding: ' + encoding)
        output = iconv.decode(bytes(input), encoding=encoding, errors=errors)
        return output, len(input)

    def not_implemented(*args, **kwargs):
        raise NotImplementedError

    return codecs.CodecInfo(
        encode=encode,
        decode=decode,
        streamreader=not_implemented,
        streamwriter=not_implemented,
        incrementalencoder=not_implemented,
        incrementaldecoder=not_implemented,
        name=encoding,
    )

_interesting_ascii_bytes = bytes(itertools.chain([
    0,  # NUL
    4,  # EOT
    7,  # BEL
    8,  # BS
    9,  # HT
    10,  # LF
    11,  # VT
    12,  # FF
    13,  # CR
    27,  # ESC
], range(32, 127)))
_interesting_ascii_str = _interesting_ascii_bytes.decode()

def _read_encodings():
    path = os.path.join(paths.datadir, 'encodings')
    cp = configparser.ConfigParser(interpolation=None, default_section='')
    cp.read(path, encoding='UTF-8')
    e2c = {}
    c2e = {}
    for encoding, extra in cp['portable-encodings'].items():
        e2c[encoding] = None
        if extra == '':
            pycodec = codecs.lookup(encoding)
            e2c[encoding] = pycodec
            c2e.setdefault(pycodec.name, encoding)
        elif extra == 'not-python':
            pass
        else:
            raise misc.DataIntegrityError
    extra_encodings = {
        key.lower()
        for key, value in cp['extra-encodings'].items()
    }
    return (e2c, c2e, extra_encodings)

[_portable_encodings, _pycodec_to_encoding, _extra_encodings] = _read_encodings()

def _read_control_characters():
    path = os.path.join(paths.datadir, 'control-characters')
    cp = configparser.ConfigParser(interpolation=None, default_section='')
    cp.read(path, encoding='UTF-8')
    for section in cp.values():
        if not section.name:
            continue
        misc.check_sorted(section)
        for code, name in section.items():
            if len(code) != 2:
                raise misc.DataIntegrityError
            code = chr(int(code, 16))
            if unicodedata.category(code) != 'Cc':
                raise misc.DataIntegrityError
            if name.upper() != name:
                raise misc.DataIntegrityError
            yield (code, name)

_control_character_names = dict(_read_control_characters())

_extra_encodings_installed = None

def get_portable_encodings(python=True):
    return (
        encoding
        for encoding, codec in _portable_encodings.items()
        if (not python) or (codec is not None)
    )

def is_portable_encoding(encoding, python=True):
    encoding = encoding.lower()
    if encoding.startswith('iso_'):
        encoding = 'iso-' + encoding[4:]
    if python:
        return _portable_encodings.get(encoding, None) is not None
    else:
        return encoding in _portable_encodings

def propose_portable_encoding(encoding, python=True):
    # Note that the "python" argument is never used.
    # Only encodings supported by Python are proposed.
    try:
        pycodec = codecs.lookup(encoding)
        new_encoding = _pycodec_to_encoding[pycodec.name]
    except LookupError:
        return
    assert is_portable_encoding(new_encoding, python=True)
    return new_encoding.upper()

def is_ascii_compatible_encoding(encoding):
    try:
        return (
            _interesting_ascii_bytes.decode(encoding) ==
            _interesting_ascii_str
        )
    except UnicodeError:
        return False

def _codec_search_function(encoding):
    if not (_extra_encodings_installed > 0):
        return
    if _portable_encodings.get(encoding, False) is None:
        # portable according to gettext documentation
        # but not supported directly by Python
        pass
    elif encoding in _extra_encodings:
        # non-portable, but used by real-world software
        pass
    else:
        return
    try:
        return charmap_encoding(encoding)
    except LookupError:
        return iconv_encoding(encoding)

def _install_extra_encodings():
    global _extra_encodings_installed
    if _extra_encodings_installed is None:
        codecs.register(_codec_search_function)
        _extra_encodings_installed = 1
    else:
        assert _extra_encodings_installed >= 0
        _extra_encodings_installed += 1

def _uninstall_extra_encodings():
    global _extra_encodings_installed
    assert _extra_encodings_installed > 0
    _extra_encodings_installed -= 1

@contextlib.contextmanager
def extra_encodings():
    _install_extra_encodings()
    try:
        yield
    finally:
        _uninstall_extra_encodings()

def get_character_name(ch):
    try:
        return unicodedata.name(ch)
    except ValueError:
        if unicodedata.category(ch) == 'Cn':
            return 'non-character'
        name = _control_character_names.get(ch)
        if name is None:
            raise
        return 'control character ' + name

# vim:ts=4 sw=4 et

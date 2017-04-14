# Copyright © 2012-2014 Jakub Wilk <jwilk@jwilk.net>
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

import curses.ascii
import sys

import lib.encodings as E

import nose
from nose.tools import (
    assert_equal,
    assert_false,
    assert_is_none,
    assert_not_in,
    assert_raises,
    assert_true,
)

from . import tools

class test_is_portable_encoding:

    def test_found(self):
        assert_true(E.is_portable_encoding('ISO-8859-2'))

    def test_found_(self):
        assert_true(E.is_portable_encoding('ISO_8859-2'))

    def test_found_nonpython(self):
        assert_false(E.is_portable_encoding('KOI8-T'))
        assert_true(E.is_portable_encoding('KOI8-T', python=False))

    def test_notfound(self):
        assert_false(E.is_portable_encoding('ISO-8859-16'))
        assert_false(E.is_portable_encoding('ISO-8859-16', python=False))

class test_propose_portable_encoding:

    def test_identity(self):
        encoding = 'ISO-8859-2'
        portable_encoding = E.propose_portable_encoding(encoding)
        assert_equal(portable_encoding, encoding)

    def test_found(self):
        def t(encoding, expected_portable_encoding):
            portable_encoding = E.propose_portable_encoding(encoding)
            assert_equal(portable_encoding, expected_portable_encoding)
        yield t, 'ISO8859-2', 'ISO-8859-2'
        yield t, 'ISO_8859-2', 'ISO-8859-2'
        yield t, 'Windows-1250', 'CP1250'

    def test_notfound(self):
        portable_encoding = E.propose_portable_encoding('ISO-8859-16')
        assert_is_none(portable_encoding)

class test_ascii_compatibility:

    def test_portable(self):
        def t(encoding):
            assert_true(E.is_ascii_compatible_encoding(encoding))
            assert_true(E.is_ascii_compatible_encoding(encoding, missing_ok=False))
        for encoding in E.get_portable_encodings():
            yield t, encoding

    def test_incompatible(self):
        def t(encoding):
            assert_false(E.is_ascii_compatible_encoding(encoding))
            assert_false(E.is_ascii_compatible_encoding(encoding, missing_ok=False))
        yield t, 'UTF-7'
        yield t, 'UTF-16'

    def _test_missing(self, encoding):
        assert_false(E.is_ascii_compatible_encoding(encoding))
        with assert_raises(E.EncodingLookupError):
            E.is_ascii_compatible_encoding(encoding, missing_ok=False)

    def test_non_text(self):
        t = self._test_missing
        yield t, 'base64_codec'
        yield t, 'bz2_codec'
        yield t, 'hex_codec'
        yield t, 'quopri_codec'
        yield t, 'rot_13'
        yield t, 'uu_codec'
        yield t, 'zlib_codec'

    def test_missing(self):
        self._test_missing('eggs')

class test_get_character_name:

    def test_latin(self):
        for i in range(ord('a'), ord('z')):
            u = chr(i)
            name = E.get_character_name(u)
            assert_equal(name, 'LATIN SMALL LETTER ' + u.upper())
            u = chr(i).upper()
            name = E.get_character_name(u)
            assert_equal(name, 'LATIN CAPITAL LETTER ' + u)

    def test_c0(self):
        for i, curses_name in zip(range(0, 0x20), curses.ascii.controlnames):
            u = chr(i)
            name = E.get_character_name(u)
            expected_name = 'control character ' + curses_name
            assert_equal(name, expected_name)

    def test_del(self):
        name = E.get_character_name('\x7F')
        assert_equal(name, 'control character DEL')

    def test_c1(self):
        for i in range(0x80, 0xA0):
            u = chr(i)
            name = E.get_character_name(u)
            assert_true(name.startswith('control character '))

    def test_uniqueness(self):
        names = set()
        for i in range(0, 0x100):
            u = chr(i)
            name = E.get_character_name(u)
            assert_not_in(name, names)
            names.add(name)

    def test_non_character(self):
        name = E.get_character_name('\uFFFE')
        assert_equal(name, 'non-character')
        name = E.get_character_name('\uFFFF')
        assert_equal(name, 'non-character')

    def test_lookup_error(self):
        with assert_raises(ValueError):
            E.get_character_name('\uE000')

class test_extra_encoding:

    @tools.fork_isolation
    def test_install(self):
        encoding = 'VISCII'
        def enc():
            ''.encode(encoding)
        def dec():
            b'.'.decode(encoding)
        try:
            enc()
        except LookupError:
            pass
        else:
            raise nose.SkipTest(
                'python{ver[0]}.{ver[1]} supports the {enc} encoding'.format(
                    ver=sys.version_info,
                    enc=encoding
                )
            )
        with assert_raises(LookupError):
            dec()
        E.install_extra_encodings()
        enc()
        dec()

    @tools.fork_isolation
    def test_8859(self):
        E.install_extra_encodings()
        encoding = '8859-2'
        portable_encoding = E.propose_portable_encoding(encoding)
        assert_equal('ISO-' + encoding, portable_encoding)

    @tools.fork_isolation
    def test_not_allowed(self):
        encoding = 'TSCII'
        def enc():
            ''.encode(encoding)
        try:
            enc()
        except LookupError:
            pass
        else:
            raise nose.SkipTest(
                'python{ver[0]}.{ver[1]} supports the {enc} encoding'.format(
                    ver=sys.version_info,
                    enc=encoding
                )
            )
        E.install_extra_encodings()
        with assert_raises(LookupError):
            enc()

    _viscii_unicode = 'Ti\u1EBFng Vi\u1EC7t'
    _viscii_bytes = b'Ti\xAAng Vi\xAEt'

    @tools.fork_isolation
    def test_8b_encode(self):
        E.install_extra_encodings()
        u = self._viscii_unicode
        b = u.encode('VISCII')
        assert_equal(b, self._viscii_bytes)

    @tools.fork_isolation
    def test_8b_encode_error(self):
        E.install_extra_encodings()
        u = self._viscii_unicode
        with assert_raises(UnicodeEncodeError):
            u.encode('KOI8-RU')

    @tools.fork_isolation
    def test_8b_decode(self):
        E.install_extra_encodings()
        b = self._viscii_bytes
        u = b.decode('VISCII')
        assert_equal(u, self._viscii_unicode)

    @tools.fork_isolation
    def test_8b_decode_error(self):
        E.install_extra_encodings()
        b = self._viscii_bytes
        with assert_raises(UnicodeDecodeError):
            b.decode('KOI8-T')

    _euc_tw_unicode = '\u4E2D\u6587'
    _euc_tw_bytes = b'\xC4\xE3\xC5\xC6'

    @tools.fork_isolation
    def test_mb_encode(self):
        E.install_extra_encodings()
        u = self._euc_tw_unicode
        b = u.encode('EUC-TW')
        assert_equal(b, self._euc_tw_bytes)

    @tools.fork_isolation
    def test_mb_encode_error(self):
        E.install_extra_encodings()
        u = self._viscii_unicode
        with assert_raises(UnicodeEncodeError):
            u.encode('EUC-TW')

    @tools.fork_isolation
    def test_mb_decode(self):
        E.install_extra_encodings()
        b = self._euc_tw_bytes
        u = b.decode('EUC-TW')
        assert_equal(u, self._euc_tw_unicode)

    @tools.fork_isolation
    def test_mb_decode_error(self):
        E.install_extra_encodings()
        b = self._viscii_bytes
        with assert_raises(UnicodeDecodeError):
            b.decode('EUC-TW')

# vim:ts=4 sts=4 sw=4 et

# Copyright © 2012 Jakub Wilk <jwilk@jwilk.net>
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

import codecs
import curses.ascii
import os
import lib.encodings

from nose.tools import (
    assert_equal,
    assert_false,
    assert_is_none,
    assert_not_in,
    assert_raises,
    assert_true,
)

basedir = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
)
datadir = os.path.join(basedir, 'data')
E = lib.encodings.EncodingInfo(datadir)

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
        def _test(encoding, expected_portable_encoding):
            portable_encoding = E.propose_portable_encoding(encoding)
            assert_equal(portable_encoding, expected_portable_encoding)
        yield _test, 'ISO8859-2', 'ISO-8859-2'
        yield _test, 'ISO_8859-2', 'ISO-8859-2'
        yield _test, 'Windows-1250', 'CP1250'

    def test_notfound(self):
        portable_encoding = E.propose_portable_encoding('ISO-8859-16')
        assert_is_none(portable_encoding)

class test_ascii_compatiblity:

    def test_portable(self):

        def _test(encoding):
            assert_true(E.is_ascii_compatible_encoding(encoding))

        for encoding in E.get_portable_encodings():
            yield _test, encoding

    def test_incompatible(self):

        def _test(encoding):
            assert_false(E.is_ascii_compatible_encoding(encoding))

        yield _test, 'UTF-7'
        yield _test, 'UTF-16'

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
        name = E.get_character_name('\ufffe')
        assert_equal(name, 'non-character')
        name = E.get_character_name('\uffff')
        assert_equal(name, 'non-character')

    def test_lookup_error(self):
        with assert_raises(ValueError):
            E.get_character_name('\ue000')

class test_extra_encoding:

    def test_install(self):
        def enc():
            ''.encode('VISCII')
        def dec():
            b'.'.decode('VISCII')
        with assert_raises(LookupError):
            enc()
        with assert_raises(LookupError):
            dec()
        with E.extra_encodings():
            enc()
            dec()
        with assert_raises(LookupError):
            enc()
        with assert_raises(LookupError):
            dec()

# vim:ts=4 sw=4 et

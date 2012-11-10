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

import os
import lib.encodings

from nose.tools import (
    assert_equal,
    assert_false,
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
        assert_equal(portable_encoding, encoding.lower())

    def test_found(self):
        portable_encoding = E.propose_portable_encoding('ISO8859-2')
        assert_equal(portable_encoding, 'iso-8859-2')

    def test_notfound(self):
        portable_encoding = E.propose_portable_encoding('ISO-8859-16')
        assert_true(portable_encoding is None)

# vim:ts=4 sw=4 et

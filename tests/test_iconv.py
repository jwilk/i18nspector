# Copyright © 2013-2019 Jakub Wilk <jwilk@jwilk.net>
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

from nose.tools import (
    assert_equal,
    assert_raises,
)

import lib.iconv as M

class _test:
    u = None
    b = None
    e = None

    def test_encode(self):
        b = M.encode(self.u, self.e)
        assert_equal(b, self.b)

    def test_decode(self):
        u = M.decode(self.b, self.e)
        assert_equal(u, self.u)

class test_iso2(_test):
    u = 'Żrą łódź? Część miń!'
    b = b'\xAFr\xB1 \xB3\xF3d\xBC? Cz\xEA\xB6\xE6 mi\xF1!'
    e = 'ISO-8859-2'

class test_tcvn(_test):
    u = 'Do bạch kim rất quý, sẽ để lắp vô xương'
    b = b'Do b\xB9ch kim r\xCAt qu\xFD, s\xCF \xAE\xD3 l\xBEp v\xAB x\xAD\xACng'
    e = 'TCVN-5712'

def test_incomplete_char():
    b = u'Ę'.encode('UTF-8')[:1]
    with assert_raises(UnicodeDecodeError):
        M.decode(b, 'UTF-8')

# vim:ts=4 sts=4 sw=4 et

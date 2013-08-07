# Copyright © 2013 Jakub Wilk <jwilk@jwilk.net>
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
)

import lib.iconv as M

_iso2_unicode = 'Żrą łódź? Część miń!'
_iso2_bytes = b'\xafr\xb1 \xb3\xf3d\xbc? Cz\xea\xb6\xe6 mi\xf1!'

def test_encode():
    b = M.encode(_iso2_unicode, 'ISO-8859-2')
    assert_equal(b, _iso2_bytes)

def test_decode():
    u = M.decode(_iso2_bytes, 'ISO-8859-2')
    assert_equal(u, _iso2_unicode)

# vim:ts=4 sw=4 et

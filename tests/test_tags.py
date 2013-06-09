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

import lib.tags

from nose.tools import (
    assert_equal,
)

class test_escape:

    _esc = staticmethod(lib.tags._escape)  # FIXME: _escape is private

    def _test(self, s, expected):
        assert_equal(
            self._esc(s),
            expected
        )

    def test_safe(self):
        s = 'fox'
        self._test(s, s)

    def test_trailing_newline(self):
        s = 'fox\n'
        self._test(s, repr(s))

    def test_colon(self):
        s = 'fox:'
        self._test(s, repr(s))

    def test_space(self):
        s = 'brown fox'
        self._test(s, repr(s))

# vim:ts=4 sw=4 et

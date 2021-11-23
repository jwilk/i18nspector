# Copyright © 2016-2020 Jakub Wilk <jwilk@jwilk.net>
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

import lib.strformat.perlbrace as M

from .tools import (
    assert_equal,
    assert_raises,
)

def test_lone_lcb():
    with assert_raises(M.Error):
        M.FormatString('{')

def test_lone_rcb():
    M.FormatString('}')

def test_invalid_field():
    with assert_raises(M.Error):
        M.FormatString('{@}')

def test_text():
    fmt = M.FormatString('bacon')
    assert_equal(len(fmt), 1)
    [fld] = fmt
    assert_equal(fld, 'bacon')

class test_named_arguments:

    def test_good(self):
        fmt = M.FormatString('{spam}')
        assert_equal(len(fmt), 1)
        [fld] = fmt
        assert_equal(fld, '{spam}')

    def test_bad(self):
        with assert_raises(M.Error):
            M.FormatString('{3ggs}')

# vim:ts=4 sts=4 sw=4 et

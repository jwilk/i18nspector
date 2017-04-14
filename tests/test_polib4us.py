# Copyright © 2013-2014 Jakub Wilk <jwilk@jwilk.net>
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

import polib

import lib.polib4us as M

from nose.tools import (
    assert_list_equal,
    assert_true,
)

from . import tools

minimal_header = r'''
msgid ""
msgstr "Content-Type: text/plain; charset=US-ASCII\n"
'''

class test_codecs:

    @tools.fork_isolation
    def test_trailing_obsolete_message(self):
        s = minimal_header + '''
msgid "a"
msgstr "b"

#~ msgid "b"
#~ msgstr "c"
'''
        def t():
            with tools.temporary_file(mode='wt', encoding='ASCII') as file:
                file.write(s)
                file.flush()
                po = polib.pofile(file.name)
                assert_true(po[-1].obsolete)
        t()
        M.install_patches()
        t()

@tools.fork_isolation
def test_flag_splitting():
    M.install_patches()
    e = polib.POEntry()
    e.flags = ['fuzzy,c-format']
    assert_list_equal(
        e.flags,
        ['fuzzy', 'c-format']
    )

# vim:ts=4 sts=4 sw=4 et

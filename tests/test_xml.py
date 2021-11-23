# Copyright © 2014-2022 Jakub Wilk <jwilk@jwilk.net>
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

import re
import xml.etree.ElementTree as etree

import lib.xml as M

from .tools import (
    assert_is_none,
    assert_is_not_none,
    assert_raises,
)

class test_well_formed:

    def t(self, s):
        M.check_fragment(s)

    def test_ok(self):
        self.t('eggs')
        self.t('<bacon>ham</bacon> spam')

    def test_unknown_entity(self):
        self.t('&eggs;')

class test_malformed:

    def t(self, s):
        with assert_raises(M.SyntaxError):
            M.check_fragment(s)

    def test_non_xml_character(self):
        self.t('\x01')

    def test_open_tag(self):
        self.t('<eggs>ham')

    def test_closed_tag(self):
        self.t('eggs</ham>')

    def test_broken_entity(self):
        self.t('&#eggs;')

    def test_entity_def(self):
        s = (
            '<!DOCTYPE spam [<!ENTITY eggs "ham">]>'
            '<spam>&eggs;</spam>'
        )
        etree.fromstring(s)
        self.t(s)

class test_name_re():
    regexp = re.compile(fr'\A{M.name_re}\Z')

    def test_good(self):
        def t(s):
            match = self.regexp.match(s)
            assert_is_not_none(match)
        t(':')
        t('_')
        t('e')
        t('e0')
        t('eggs')
        t('eggs-ham')
        t('eggs:ham')

    def test_bad(self):
        def t(s):
            match = self.regexp.match(s)
            assert_is_none(match)
        t('')
        t('0')
        t('-')
        t('e\N{GREEK QUESTION MARK}')

# vim:ts=4 sts=4 sw=4 et

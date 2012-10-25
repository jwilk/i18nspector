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
import lib.ling

from nose.tools import (
    assert_equal,
    assert_in,
    assert_not_in,
    assert_raises,
    assert_true,
)

basedir = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
)
datadir = os.path.join(basedir, 'data')
L = lib.ling.LingInfo(datadir)

class test_lookup_language_code:

    def test_found_3_to_3(self):
        lang = L.lookup_language_code('grc')
        assert_equal(lang, 'grc')

    def test_found_3_to_2(self):
        lang = L.lookup_language_code('ell')
        assert_equal(lang, 'el')

    def test_found_2_to_2(self):
        lang = L.lookup_language_code('el')
        assert_equal(lang, 'el')

    def test_not_found(self):
        lang = L.lookup_language_code('gre')
        assert_true(lang is None)

class test_lookup_country_code:

    def test_found(self):
        cc = L.lookup_country_code('GR')
        assert_equal(cc, 'GR')

    def test_not_found(self):
        cc = L.lookup_country_code('RG')
        assert_true(cc is None)

class test_get_language_for_name:

    def test_found(self):
        lang = L.get_language_for_name('Greek')
        assert_equal(lang, 'el')

    def test_not_found(self):
        with assert_raises(LookupError):
            lang = L.get_language_for_name('Terrx')

class test_get_primary_languages:

    def test_found(self):
        langs = L.get_primary_languages()
        assert_in('el', langs)

    def test_not_found(self):
        langs = L.get_primary_languages()
        assert_not_in('ry', langs)

    def test_iso_639(self):
        for lang in L.get_primary_languages():
            if '_' in lang:
                ll, cc = lang.split('_')
            else:
                ll = lang
                cc = None
            assert_equal(ll, L.lookup_language_code(ll))
            assert_equal(cc, L.lookup_country_code(cc))

# vim:ts=4 sw=4 et

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

import nose
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
T = lib.ling.Language
L = lib.ling.LingInfo(datadir)

class test_language_objects:

    # fix_codes(): grc(_GR) -> grc(_GR)

    def test_fix_codes_3c_to_3c(self):
        lang = T(L, 'grc', 'GR')
        assert_equal(lang.language_code, 'grc')
        assert_equal(lang.territory_code, 'GR')
        assert_true(lang.fix_codes() is None)
        assert_equal(lang.language_code, 'grc')
        assert_equal(lang.territory_code, 'GR')

    def test_fix_codes_3_to_3(self):
        lang = T(L, 'grc')
        assert_equal(lang.language_code, 'grc')
        assert_equal(lang.territory_code, None)
        assert_true(lang.fix_codes() is None)
        assert_equal(lang.language_code, 'grc')
        assert_equal(lang.territory_code, None)

    # fix_codes(): el(l)_GR -> el_GR

    def test_fix_codes_2c_to_2c(self):
        lang = T(L, 'el', 'GR')
        assert_equal(lang.language_code, 'el')
        assert_equal(lang.territory_code, 'GR')
        assert_true(lang.fix_codes() is None)
        assert_equal(lang.language_code, 'el')
        assert_equal(lang.territory_code, 'GR')

    def test_fix_codes_3c_to_2c(self):
        lang = T(L, 'ell', 'GR')
        assert_equal(lang.language_code, 'ell')
        assert_equal(lang.territory_code, 'GR')
        assert_true(lang.fix_codes() is True)
        assert_equal(lang.language_code, 'el')
        assert_equal(lang.territory_code, 'GR')

    # fix_codes(): el(l) -> el

    def test_fix_codes_2_to_2(self):
        lang = T(L, 'el')
        assert_equal(lang.language_code, 'el')
        assert_equal(lang.territory_code, None)
        assert_true(lang.fix_codes() is None)
        assert_equal(lang.language_code, 'el')
        assert_equal(lang.territory_code, None)

    def test_fix_codes_3_to_2(self):
        lang = T(L, 'ell')
        assert_equal(lang.language_code, 'ell')
        assert_equal(lang.territory_code, None)
        assert_true(lang.fix_codes() is True)
        assert_equal(lang.language_code, 'el')
        assert_equal(lang.territory_code, None)

    # *_principal_territory_code(): el_GR -> el

    def test_principal_territory_code(self):
        lang = T(L, 'el')
        cc = lang.get_principal_territory_code()
        assert_equal(cc, 'GR')

    def test_remove_principal_territory(self):
        lang = T(L, 'el', 'GR')
        assert_equal(lang.language_code, 'el')
        assert_equal(lang.territory_code, 'GR')
        lang.remove_principal_territory_code()
        assert_equal(lang.language_code, 'el')
        assert_true(lang.territory_code is None)

    # *_principal_territory_code(): en_US -> en_US

    def test_no_principal_territory_code(self):
        lang = T(L, 'en')
        cc = lang.get_principal_territory_code()
        assert_true(cc is None)

    def test_no_remove_principal_territory_code(self):
        lang = T(L, 'en', 'US')
        assert_equal(lang.language_code, 'en')
        assert_equal(lang.territory_code, 'US')
        lang.remove_principal_territory_code()
        assert_equal(lang.language_code, 'en')
        assert_equal(lang.territory_code, 'US')

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

class test_lookup_territory_code:

    def test_found(self):
        cc = L.lookup_territory_code('GR')
        assert_equal(cc, 'GR')

    def test_not_found(self):
        cc = L.lookup_territory_code('RG')
        assert_true(cc is None)

class test_get_language_for_name:

    def test_found(self):
        lang = L.get_language_for_name('Greek')
        assert_equal(lang, 'el')

    def test_found_multi(self):
        lang = L.get_language_for_name('Old Church Slavonic')
        assert_equal(lang, 'cu')

    def test_found_as_ascii(self):
        lang = L.get_language_for_name('Norwegian Bokmål')
        assert_equal(lang, 'nb')

    def test_found_semicolon(self):
        lang = L.get_language_for_name('Chichewa; Nyanja')
        assert_equal(lang, 'ny')

    def test_found_comma(self):
        lang = L.get_language_for_name('Ndebele, South')
        assert_equal(lang, 'nr')

    def test_found_comma_as_semicolon(self):
        lang = L.get_language_for_name('Pashto, Pushto')
        assert_equal(lang, 'ps')

    def test_not_found(self):
        with assert_raises(LookupError):
            lang = L.get_language_for_name('Nadsat')

class test_parse_language:

    def test_ll(self):
        lang = L.parse_language('el')
        assert_equal(lang.language_code, 'el')
        assert_true(lang.territory_code is None)
        assert_true(lang.encoding is None)
        assert_true(lang.modifier is None)

    def test_lll(self):
        lang = L.parse_language('ell')
        assert_equal(lang.language_code, 'ell')
        assert_true(lang.territory_code is None)
        assert_true(lang.encoding is None)
        assert_true(lang.modifier is None)

    def test_ll_cc(self):
        lang = L.parse_language('el_GR')
        assert_equal(lang.language_code, 'el')
        assert_equal(lang.territory_code, 'GR')
        assert_true(lang.encoding is None)
        assert_true(lang.modifier is None)

    def test_ll_cc_enc(self):
        lang = L.parse_language('el_GR.UTF-8')
        assert_equal(lang.language_code, 'el')
        assert_equal(lang.territory_code, 'GR')
        assert_equal(lang.encoding, 'UTF-8')
        assert_true(lang.modifier is None)

    def test_ll_cc_modifier(self):
        lang = L.parse_language('en_US@quot')
        assert_equal(lang.language_code, 'en')
        assert_equal(lang.territory_code, 'US')
        assert_true(lang.encoding is None)
        assert_equal(lang.modifier, 'quot')

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
            assert_equal(cc, L.lookup_territory_code(cc))

class test_get_plural_forms:

    def test_found(self):
        pf = L.get_plural_forms('el')
        assert_equal(pf, 'nplurals=2; plural=n != 1;')

    def test_not_known(self):
        pf = L.get_plural_forms('la')
        assert_true(pf is None)

    def test_not_found(self):
        with assert_raises(LookupError):
            L.get_plural_forms('ry')

class test_get_principal_territory:

    def test_found_2(self):
        cc = L.get_principal_territory('el')
        assert_equal(cc, 'GR')

    def test_found_3(self):
        cc = L.get_principal_territory('ang')
        assert_equal(cc, 'GB')

    def test_not_found(self):
        cc = L.get_principal_territory('en')
        assert_true(cc is None)

# vim:ts=4 sw=4 et

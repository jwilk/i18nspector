# Copyright © 2012, 2013 Jakub Wilk <jwilk@jwilk.net>
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
    assert_false,
    assert_in,
    assert_is,
    assert_is_instance,
    assert_is_none,
    assert_not_equal,
    assert_not_in,
    assert_raises,
    assert_true,
)

from . import aux

import lib.ling
import lib.encodings

L = lib.ling
T = lib.ling.Language
E = lib.encodings.EncodingInfo(aux.datadir)

class test_fix_codes:

    def _test(self, l1, l2):
        lang = L.parse_language(l1)
        assert_equal(str(lang), l1)
        if l1 == l2:
            assert_is_none(lang.fix_codes())
        else:
            assert_is(lang.fix_codes(), True)
        assert_equal(str(lang), l2)

    def test_2_to_2(self):
        self._test('grc', 'grc')
        self._test('grc_GR', 'grc_GR')

    def test_1_to_1(self):
        self._test('el', 'el')
        self._test('el_GR', 'el_GR')

    def test_2t_to_1(self):
        self._test('ell', 'el')
        self._test('ell_GR', 'el_GR')

    def test_2b_to_1(self):
        self._test('gre', 'el')
        self._test('gre_GR', 'el_GR')

    def test_ll_not_found(self):
        with assert_raises(lib.ling.FixingLanguageCodesFailed):
            self._test('ry', '')

    def test_cc_not_found(self):
        with assert_raises(lib.ling.FixingLanguageCodesFailed):
            self._test('el_RY', '')

class test_language_equality:

    # ==, !=, is_almost_equal()

    def test_eq(self):
        l1 = T('el', 'GR')
        l2 = T('el', 'GR')
        assert_equal(l1, l2)
        assert_equal(l2, l1)

    def test_ne(self):
        l1 = T('el')
        l2 = T('el', 'GR')
        assert_not_equal(l1, l2)
        assert_not_equal(l2, l1)

    def test_ne_other_type(self):
        l1 = T('el')
        assert_not_equal(l1, 42)
        assert_not_equal(42, l1)

    def test_almost_equal(self):
        l1 = T('el')
        l2 = T('el', 'GR')
        assert_true(l1.is_almost_equal(l2))
        assert_true(l2.is_almost_equal(l1))

    def test_not_almost_equal(self):
        l1 = T('el', 'GR')
        l2 = T('grc', 'GR')
        assert_false(l1.is_almost_equal(l2))
        assert_false(l2.is_almost_equal(l1))

    def test_not_almost_equal_other_type(self):
        l1 = T('el')
        with assert_raises(TypeError):
            l1.is_almost_equal(42)

class test_remove_encoding:

    def _test(self, l1, l2):
        lang = L.parse_language(l1)
        assert_equal(str(lang), l1)
        if l1 == l2:
            assert_is_none(lang.remove_encoding())
        else:
            assert_is(lang.remove_encoding(), True)
        assert_equal(str(lang), l2)

    def test_without_encoding(self):
        self._test('el', 'el')

    def test_with_encoding(self):
        self._test('el.UTF-8', 'el')

class test_remove_nonlinguistic_modifier:

    def _test(self, l1, l2):
        lang = L.parse_language(l1)
        assert_equal(str(lang), l1)
        if l1 == l2:
            assert_is_none(lang.remove_nonlinguistic_modifier())
        else:
            assert_is(lang.remove_nonlinguistic_modifier(), True)
        assert_equal(str(lang), l2)

    def test_quot(self):
        self._test('en@quot', 'en@quot')
        self._test('en@boldquot', 'en@boldquot')

    def test_latin(self):
        self._test('sr@latin', 'sr@latin')

    def test_euro(self):
        self._test('de_AT@euro', 'de_AT')

class test_lookup_territory_code:

    def test_found(self):
        cc = L.lookup_territory_code('GR')
        assert_equal(cc, 'GR')

    def test_not_found(self):
        cc = L.lookup_territory_code('RG')
        assert_is_none(cc)

class test_get_language_for_name:

    def _test(self, name, expected):
        lang = L.get_language_for_name(name)
        assert_is_instance(lang, T)
        assert_equal(str(lang), expected)

    def test_found(self):
        self._test('Greek', 'el')

    def test_found_multi(self):
        self._test('Old Church Slavonic', 'cu')

    def test_found_as_ascii(self):
        self._test('Norwegian Bokmål', 'nb')

    def test_found_semicolon(self):
        self._test('Chichewa; Nyanja', 'ny')

    def test_found_comma(self):
        self._test('Ndebele, South', 'nr')

    def test_found_comma_as_semicolon(self):
        self._test('Pashto, Pushto', 'ps')

    def test_not_found(self):
        with assert_raises(LookupError):
            self._test('Nadsat', None)

class test_parse_language:

    def test_ll(self):
        lang = L.parse_language('el')
        assert_equal(lang.language_code, 'el')
        assert_is_none(lang.territory_code)
        assert_is_none(lang.encoding)
        assert_is_none(lang.modifier)

    def test_lll(self):
        lang = L.parse_language('ell')
        assert_equal(lang.language_code, 'ell')
        assert_is_none(lang.territory_code)
        assert_is_none(lang.encoding)
        assert_is_none(lang.modifier)

    def test_ll_cc(self):
        lang = L.parse_language('el_GR')
        assert_equal(lang.language_code, 'el')
        assert_equal(lang.territory_code, 'GR')
        assert_is_none(lang.encoding)
        assert_is_none(lang.modifier)

    def test_ll_cc_enc(self):
        lang = L.parse_language('el_GR.UTF-8')
        assert_equal(lang.language_code, 'el')
        assert_equal(lang.territory_code, 'GR')
        assert_equal(lang.encoding, 'UTF-8')
        assert_is_none(lang.modifier)

    def test_ll_cc_modifier(self):
        lang = L.parse_language('en_US@quot')
        assert_equal(lang.language_code, 'en')
        assert_equal(lang.territory_code, 'US')
        assert_is_none(lang.encoding)
        assert_equal(lang.modifier, 'quot')

    def test_syntax_error(self):
        with assert_raises(lib.ling.LanguageSyntaxError):
            L.parse_language('GR')

class test_get_primary_languages:

    def test_found(self):
        langs = L.get_primary_languages()
        assert_in('el', langs)

    def test_not_found(self):
        langs = L.get_primary_languages()
        assert_not_in('ry', langs)

    def test_iso_639(self):
        def _test(lang_str):
            lang = L.parse_language(lang_str)
            assert_is_none(lang.fix_codes())
            assert_equal(str(lang), lang_str)
        for lang_str in L.get_primary_languages():
            yield _test, lang_str

class test_get_plural_forms:

    def _get(self, lang):
        lang = L.parse_language(lang)
        return lang.get_plural_forms()

    def test_found_ll(self):
        assert_equal(
            self._get('el'),
            ['nplurals=2; plural=n != 1;']
        )

    def test_found_ll_cc(self):
        assert_equal(
            self._get('el_GR'),
            ['nplurals=2; plural=n != 1;']
        )

    def test_en_ca(self):
        assert_equal(
            self._get('en'),
            self._get('en_CA'),
        )

    def test_pt_br(self):
        assert_not_equal(
            self._get('pt'),
            self._get('pt_BR'),
        )

    def test_not_known(self):
        assert_is_none(self._get('la'))

    def test_not_found(self):
        assert_is_none(self._get('ry'))

class test_principal_territory:

    def test_found_2(self):
        # el -> el_GR
        lang = L.parse_language('el')
        cc = lang.get_principal_territory_code()
        assert_equal(cc, 'GR')

    def test_remove_2(self):
        # el_GR -> el
        lang = L.parse_language('el_GR')
        assert_equal(str(lang), 'el_GR')
        rc = lang.remove_principal_territory_code()
        assert_is(rc, True)
        assert_equal(str(lang), 'el')

    def test_found_3(self):
        # ang -> ang_GB
        lang = L.parse_language('ang')
        cc = lang.get_principal_territory_code()
        assert_equal(cc, 'GB')

    def test_remove_3(self):
        # ang_GB -> ang
        lang = L.parse_language('ang_GB')
        assert_equal(str(lang), 'ang_GB')
        rc = lang.remove_principal_territory_code()
        assert_is(rc, True)
        assert_equal(str(lang), 'ang')

    def test_no_principal_territory_code(self):
        # en -/-> en_US
        lang = L.parse_language('en')
        cc = lang.get_principal_territory_code()
        assert_is_none(cc)

    def test_no_remove_principal_territory_code(self):
        # en_US -/-> en
        lang = L.parse_language('en_US')
        assert_equal(str(lang), 'en_US')
        rc = lang.remove_principal_territory_code()
        assert_is_none(rc)
        assert_equal(str(lang), 'en_US')

    def test_not_found(self):
        lang = L.parse_language('ry')
        cc = lang.get_principal_territory_code()
        assert_equal(cc, None)

class test_unrepresentable_characters:

    def test_ll_bad(self):
        lang = L.parse_language('pl')
        result = lang.get_unrepresentable_characters('ISO-8859-1')
        assert_not_equal(result, [])

    def test_ll_ok(self):
        lang = L.parse_language('pl')
        result = lang.get_unrepresentable_characters('ISO-8859-2')
        assert_equal(result, [])

    def test_ll_cc_bad(self):
        lang = L.parse_language('pl_PL')
        result = lang.get_unrepresentable_characters('ISO-8859-1')
        assert_not_equal(result, [])

    def test_ll_cc_ok(self):
        lang = L.parse_language('pl_PL')
        result = lang.get_unrepresentable_characters('ISO-8859-2')
        assert_equal(result, [])

    def test_ll_mod_bad(self):
        lang = L.parse_language('en@quot')
        result = lang.get_unrepresentable_characters('ISO-8859-1')
        assert_not_equal(result, [])

    def test_ll_mod_ok(self):
        lang = L.parse_language('en@quot')
        result = lang.get_unrepresentable_characters('UTF-8')
        assert_equal(result, [])

    def test_ll_cc_mod_bad(self):
        lang = L.parse_language('en_US@quot')
        result = lang.get_unrepresentable_characters('ISO-8859-1')
        assert_not_equal(result, [])

    def test_ll_cc_mod_ok(self):
        lang = L.parse_language('en_US@quot')
        result = lang.get_unrepresentable_characters('UTF-8')
        assert_equal(result, [])

    def test_ll_optional(self):
        # U+0178 (LATIN CAPITAL LETTER Y WITH DIAERESIS) is not representable
        # in ISO-8859-1, but we normally turn a blind eye to this.
        lang = L.parse_language('fr')
        result = lang.get_unrepresentable_characters('ISO-8859-1')
        assert_equal(result, [])
        result = lang.get_unrepresentable_characters('ISO-8859-1', strict=True)
        assert_not_equal(result, [])

    def test_ll_not_found(self):
        lang = L.parse_language('ry')
        result = lang.get_unrepresentable_characters('ISO-8859-1')
        assert_is_none(result)

    def test_extra_encoding(self):
        encoding = 'GEORGIAN-PS'
        lang = L.parse_language('pl')
        with assert_raises(LookupError):
            ''.encode(encoding)
        with E.extra_encodings():
            result = lang.get_unrepresentable_characters(encoding)
        assert_not_equal(result, [])

# vim:ts=4 sw=4 et

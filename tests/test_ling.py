# Copyright © 2012-2016 Jakub Wilk <jwilk@jwilk.net>
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

import lib.encodings
import lib.ling

import nose
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

from . import tools

L = lib.ling
T = lib.ling.Language
E = lib.encodings

class test_fix_codes:

    def t(self, l1, l2):
        lang = L.parse_language(l1)
        assert_equal(str(lang), l1)
        if l1 == l2:
            assert_is_none(lang.fix_codes())
        else:
            assert_is(lang.fix_codes(), True)
        assert_equal(str(lang), l2)

    def test_2_to_2(self):
        self.t('grc', 'grc')
        self.t('grc_GR', 'grc_GR')

    def test_1_to_1(self):
        self.t('el', 'el')
        self.t('el_GR', 'el_GR')

    def test_2t_to_1(self):
        self.t('ell', 'el')
        self.t('ell_GR', 'el_GR')

    def test_2b_to_1(self):
        self.t('gre', 'el')
        self.t('gre_GR', 'el_GR')

    def test_ll_not_found(self):
        with assert_raises(L.FixingLanguageCodesFailed):
            self.t('ry', '')

    def test_cc_not_found(self):
        with assert_raises(L.FixingLanguageCodesFailed):
            self.t('el_RY', '')

def test_language_repr():
    # Language.__repr__() is never used by i18nspector itself,
    # but it's useful for debugging test failures.
    lng = T('el')
    assert_equal(repr(lng), '<Language el>')

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

    def t(self, l1, l2):
        lang = L.parse_language(l1)
        assert_equal(str(lang), l1)
        if l1 == l2:
            assert_is_none(lang.remove_encoding())
        else:
            assert_is(lang.remove_encoding(), True)
        assert_equal(str(lang), l2)

    def test_without_encoding(self):
        self.t('el', 'el')

    def test_with_encoding(self):
        self.t('el.UTF-8', 'el')

class test_remove_nonlinguistic_modifier:

    def t(self, l1, l2):
        lang = L.parse_language(l1)
        assert_equal(str(lang), l1)
        if l1 == l2:
            assert_is_none(lang.remove_nonlinguistic_modifier())
        else:
            assert_is(lang.remove_nonlinguistic_modifier(), True)
        assert_equal(str(lang), l2)

    def test_quot(self):
        self.t('en@quot', 'en@quot')
        self.t('en@boldquot', 'en@boldquot')

    def test_latin(self):
        self.t('sr@latin', 'sr@latin')

    def test_euro(self):
        self.t('de_AT@euro', 'de_AT')

class test_lookup_territory_code:

    def test_found(self):
        cc = L.lookup_territory_code('GR')
        assert_equal(cc, 'GR')

    def test_not_found(self):
        cc = L.lookup_territory_code('RG')
        assert_is_none(cc)

class test_get_language_for_name:

    def t(self, name, expected):
        lang = L.get_language_for_name(name)
        assert_is_instance(lang, T)
        assert_equal(str(lang), expected)

    def test_found(self):
        self.t('Greek', 'el')

    def test_found_multi(self):
        self.t('Old Church Slavonic', 'cu')

    def test_found_as_ascii(self):
        self.t('Norwegian Bokmål', 'nb')

    def test_found_semicolon(self):
        self.t('Chichewa; Nyanja', 'ny')

    def test_found_comma(self):
        self.t('Ndebele, South', 'nr')

    def test_found_comma_as_semicolon(self):
        self.t('Pashto, Pushto', 'ps')

    def test_lone_comma(self):
        with assert_raises(LookupError):
            self.t(',', None)

    def test_not_found(self):
        with assert_raises(LookupError):
            self.t('Nadsat', None)

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
        with assert_raises(L.LanguageSyntaxError):
            L.parse_language('GR')

class test_get_primary_languages:

    def test_found(self):
        langs = L.get_primary_languages()
        assert_in('el', langs)

    def test_not_found(self):
        langs = L.get_primary_languages()
        assert_not_in('ry', langs)

    def test_iso_639(self):
        def t(lang_str):
            lang = L.parse_language(lang_str)
            assert_is_none(lang.fix_codes())
            assert_equal(str(lang), lang_str)
        for lang_str in L.get_primary_languages():
            yield t, lang_str

class test_get_plural_forms:

    def t(self, lang):
        lang = L.parse_language(lang)
        return lang.get_plural_forms()

    def test_found_ll(self):
        assert_equal(
            self.t('el'),
            ['nplurals=2; plural=n != 1;']
        )

    def test_found_ll_cc(self):
        assert_equal(
            self.t('el_GR'),
            ['nplurals=2; plural=n != 1;']
        )

    def test_en_ca(self):
        assert_equal(
            self.t('en'),
            self.t('en_CA'),
        )

    def test_pt_br(self):
        assert_not_equal(
            self.t('pt'),
            self.t('pt_BR'),
        )

    def test_not_known(self):
        assert_is_none(self.t('la'))

    def test_not_found(self):
        assert_is_none(self.t('ry'))

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

    @tools.fork_isolation
    def test_extra_encoding(self):
        encoding = 'GEORGIAN-PS'
        lang = L.parse_language('pl')
        with assert_raises(LookupError):
            ''.encode(encoding)
        E.install_extra_encodings()
        result = lang.get_unrepresentable_characters(encoding)
        assert_not_equal(result, [])

def test_glibc_supported():
    def t(l):
        lang = L.parse_language(l)
        try:
            lang.fix_codes()
        except L.FixingLanguageCodesFailed:
            # FIXME: some ISO-639-3 codes are not recognized yet
            if len(l.split('_')[0]) == 3:
                raise nose.SkipTest('expected failure')
            reason = locales_to_skip.get(l)
            if reason is not None:
                raise nose.SkipTest(reason)
            raise
        assert_equal(str(lang), l)
    try:
        file = open('/usr/share/i18n/SUPPORTED', encoding='ASCII')
    except IOError as exc:
        raise nose.SkipTest(exc)
    locales = set()
    with file:
        for line in file:
            if line[:1] in {'#', '\n'}:
                continue
            locale, *rest = line.split()
            del rest
            if (locale + '.').startswith('iw_IL.'):
                # iw_IL is obsolete
                continue
            locales.add(locale)
    misnamed_locales = {
        # glibc 2.21 had two misnamed locales:
        'bh_IN.UTF-8',  # should be bhb_IN
        'tu_IN.UTF-8',  # should be tcy_IN
    }
    locales_to_skip = {}
    if locales & misnamed_locales == misnamed_locales:
        for l in misnamed_locales:
            locales_to_skip[l] = 'https://sourceware.org/git/gitweb.cgi?p=glibc.git;a=commitdiff;h=032c510db06c'
    for l in sorted(locales):
        yield t, l

def test_poedit():
    # https://github.com/vslavik/poedit/blob/v1.8.1-oss/src/language_impl_legacy.h
    # There won't be any new names in this table,
    # so it's safe to hardcode them all here.
    def t(name, poedit_ll):
        poedit_ll = L.parse_language(poedit_ll)
        ll = L.get_language_for_name(name)
        assert_equal(ll, poedit_ll)
    def x(name, poedit_ll):
        poedit_ll = L.parse_language(poedit_ll)
        with assert_raises(LookupError):
            L.get_language_for_name(name)
        raise nose.SkipTest('expected failure')
    yield t, 'Abkhazian', 'ab'
    yield t, 'Afar', 'aa'
    yield t, 'Afrikaans', 'af'
    yield t, 'Albanian', 'sq'
    yield t, 'Amharic', 'am'
    yield t, 'Arabic', 'ar'
    yield t, 'Armenian', 'hy'
    yield t, 'Assamese', 'as'
    yield t, 'Avestan', 'ae'
    yield t, 'Aymara', 'ay'
    yield t, 'Azerbaijani', 'az'
    yield t, 'Bashkir', 'ba'
    yield t, 'Basque', 'eu'
    yield t, 'Belarusian', 'be'
    yield t, 'Bengali', 'bn'
    yield t, 'Bislama', 'bi'
    yield t, 'Bosnian', 'bs'
    yield t, 'Breton', 'br'
    yield t, 'Bulgarian', 'bg'
    yield t, 'Burmese', 'my'
    yield t, 'Catalan', 'ca'
    yield t, 'Chamorro', 'ch'
    yield t, 'Chechen', 'ce'
    yield t, 'Chichewa; Nyanja', 'ny'
    yield t, 'Chinese', 'zh'
    yield t, 'Church Slavic', 'cu'
    yield t, 'Chuvash', 'cv'
    yield t, 'Cornish', 'kw'
    yield t, 'Corsican', 'co'
    yield t, 'Croatian', 'hr'
    yield t, 'Czech', 'cs'
    yield t, 'Danish', 'da'
    yield t, 'Dutch', 'nl'
    yield t, 'Dzongkha', 'dz'
    yield t, 'English', 'en'
    yield t, 'Esperanto', 'eo'
    yield t, 'Estonian', 'et'
    yield t, 'Faroese', 'fo'
    yield t, 'Fijian', 'fj'
    yield t, 'Finnish', 'fi'
    yield t, 'French', 'fr'
    yield t, 'Frisian', 'fy'
    yield t, 'Friulian', 'fur'
    yield t, 'Gaelic', 'gd'
    yield t, 'Galician', 'gl'
    yield t, 'Georgian', 'ka'
    yield t, 'German', 'de'
    yield t, 'Greek', 'el'
    yield t, 'Guarani', 'gn'
    yield t, 'Gujarati', 'gu'
    yield t, 'Hausa', 'ha'
    yield t, 'Hebrew', 'he'
    yield t, 'Herero', 'hz'
    yield t, 'Hindi', 'hi'
    yield t, 'Hiri Motu', 'ho'
    yield t, 'Hungarian', 'hu'
    yield t, 'Icelandic', 'is'
    yield t, 'Indonesian', 'id'
    yield t, 'Interlingua', 'ia'
    yield t, 'Interlingue', 'ie'
    yield t, 'Inuktitut', 'iu'
    yield t, 'Inupiaq', 'ik'
    yield t, 'Irish', 'ga'
    yield t, 'Italian', 'it'
    yield t, 'Japanese', 'ja'
    yield t, 'Javanese', 'jv'  # https://github.com/vslavik/poedit/pull/193
    yield t, 'Kalaallisut', 'kl'
    yield t, 'Kannada', 'kn'
    yield t, 'Kashmiri', 'ks'
    yield t, 'Kazakh', 'kk'
    yield t, 'Khmer', 'km'
    yield t, 'Kikuyu', 'ki'
    yield t, 'Kinyarwanda', 'rw'
    yield t, 'Komi', 'kv'
    yield t, 'Korean', 'ko'
    yield t, 'Kuanyama', 'kj'
    yield t, 'Kurdish', 'ku'
    yield t, 'Kyrgyz', 'ky'
    yield t, 'Lao', 'lo'
    yield t, 'Latin', 'la'
    yield t, 'Latvian', 'lv'
    yield t, 'Letzeburgesch', 'lb'
    yield t, 'Lingala', 'ln'
    yield t, 'Lithuanian', 'lt'
    yield t, 'Macedonian', 'mk'
    yield t, 'Malagasy', 'mg'
    yield t, 'Malay', 'ms'
    yield t, 'Malayalam', 'ml'
    yield t, 'Maltese', 'mt'
    yield t, 'Maori', 'mi'
    yield t, 'Marathi', 'mr'
    yield t, 'Marshall', 'mh'
    yield t, 'Moldavian', 'ro_MD'  # XXX poedit uses deprecated "mo"
    yield t, 'Mongolian', 'mn'
    yield t, 'Nauru', 'na'
    yield t, 'Navajo', 'nv'
    yield t, 'Ndebele, South', 'nr'
    yield t, 'Ndonga', 'ng'
    yield t, 'Nepali', 'ne'
    yield t, 'Northern Sami', 'se'
    yield t, 'Norwegian Bokmal', 'nb'
    yield t, 'Norwegian Nynorsk', 'nn'
    yield t, 'Occitan', 'oc'
    yield t, 'Oriya', 'or'
    yield t, 'Ossetian; Ossetic', 'os'
    yield t, 'Pali', 'pi'
    yield t, 'Panjabi', 'pa'
    yield t, 'Pashto, Pushto', 'ps'
    yield t, 'Persian', 'fa'
    yield t, 'Polish', 'pl'
    yield t, 'Portuguese', 'pt'
    yield t, 'Quechua', 'qu'
    yield t, 'Rhaeto-Romance', 'rm'
    yield t, 'Romanian', 'ro'
    yield t, 'Rundi', 'rn'
    yield t, 'Russian', 'ru'
    yield t, 'Samoan', 'sm'
    yield t, 'Sangro', 'sg'
    yield t, 'Sanskrit', 'sa'
    yield t, 'Sardinian', 'sc'
    yield t, 'Serbian', 'sr'
    yield t, 'Sesotho', 'st'
    yield t, 'Setswana', 'tn'
    yield t, 'Shona', 'sn'
    yield t, 'Sindhi', 'sd'
    yield t, 'Sinhalese', 'si'
    yield t, 'Siswati', 'ss'
    yield t, 'Slovak', 'sk'
    yield t, 'Slovenian', 'sl'
    yield t, 'Somali', 'so'
    yield t, 'Spanish', 'es'
    yield t, 'Sundanese', 'su'
    yield t, 'Swahili', 'sw'
    yield t, 'Swedish', 'sv'
    yield t, 'Tagalog', 'tl'
    yield t, 'Tahitian', 'ty'
    yield t, 'Tajik', 'tg'
    yield t, 'Tamil', 'ta'
    yield t, 'Tatar', 'tt'
    yield t, 'Telugu', 'te'
    yield t, 'Thai', 'th'
    yield t, 'Tibetan', 'bo'
    yield t, 'Tigrinya', 'ti'
    yield t, 'Tonga', 'to'
    yield t, 'Tsonga', 'ts'
    yield t, 'Turkish', 'tr'
    yield t, 'Turkmen', 'tk'
    yield t, 'Twi', 'tw'
    yield t, 'Ukrainian', 'uk'
    yield t, 'Urdu', 'ur'
    yield t, 'Uyghur', 'ug'
    yield t, 'Uzbek', 'uz'
    yield t, 'Vietnamese', 'vi'
    yield t, 'Volapuk', 'vo'
    yield t, 'Walloon', 'wa'
    yield t, 'Welsh', 'cy'
    yield t, 'Wolof', 'wo'
    yield t, 'Xhosa', 'xh'
    yield t, 'Yiddish', 'yi'
    yield t, 'Yoruba', 'yo'
    yield t, 'Zhuang', 'za'
    yield t, 'Zulu', 'zu'
    # TODO:
    yield x, '(Afan) Oromo', 'om'
    yield x, 'Bihari', 'bh'  # "bh" is marked as collective in ISO-639-2
    yield x, 'Serbian (Latin)', 'sr_RS@latin'
    yield x, 'Serbo-Croatian', 'sh'  # "sh" is deprecated in favor of "sr", "hr", "bs"

# vim:ts=4 sts=4 sw=4 et

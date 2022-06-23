# Copyright © 2012-2022 Jakub Wilk <jwilk@jwilk.net>
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

'''
language information registry
'''

import configparser
import os
import re
import unicodedata

from lib import misc
from lib import paths

def _munch_language_name(s):
    # Normalize whitespace:
    s = str.join(' ', s.split())
    # Normalize capitalization:
    s = s.lower()
    # Strip accent marks etc.:
    s = unicodedata.normalize('NFD', s).encode('ASCII', 'ignore').decode()
    return s

class LanguageError(ValueError):
    pass

class LanguageSyntaxError(LanguageError):
    pass

class FixingLanguageCodesFailed(LanguageError):
    pass

class FixingLanguageEncodingFailed(LanguageError):
    pass

class Language():

    def __init__(self, language_code, territory_code=None, encoding=None, modifier=None):
        self.language_code = language_code
        if language_code is None:
            raise TypeError('language_code must not be None')  # no coverage
        self.territory_code = territory_code
        self.encoding = None
        if encoding is not None:
            self.encoding = encoding.upper()
        self.modifier = modifier

    def _get_tuple(self):
        return (
            self.language_code,
            self.territory_code,
            self.encoding,
            self.modifier
        )

    def clone(self):
        return Language(*self._get_tuple())

    def __eq__(self, other):
        if not isinstance(other, Language):
            return NotImplemented
        return self._get_tuple() == other._get_tuple()  # pylint: disable=protected-access

    def __ne__(self, other):
        return not self == other

    def is_almost_equal(self, other):
        if not isinstance(other, Language):
            raise TypeError
        self_clone = self.clone()
        self_clone.remove_principal_territory_code()
        other_clone = other.clone()
        other_clone.remove_principal_territory_code()
        return self_clone == other_clone

    def fix_codes(self):
        fixed = None
        ll = self.language_code
        ll = _lookup_language_code(ll)
        if ll is None:
            # TODO: Try to guess correct language code.
            raise FixingLanguageCodesFailed()
        elif ll != self.language_code:
            fixed = True
        cc = self.territory_code
        if cc is not None:
            cc = lookup_territory_code(cc)
            if cc is None:
                # TODO: Try to guess correct territory code.
                raise FixingLanguageCodesFailed()
            elif cc != self.territory_code:
                # This shouldn't really happen, but better safe than sorry.
                raise ValueError  # no coverage
            # TODO: ll_CC could be still incorrect, even when both ll and CC are
            # correct.
        self.language_code = ll
        self.territory_code = cc
        return fixed

    def get_principal_territory_code(self):
        ll = self.language_code
        assert ll is not None
        return _get_principal_territory_code(ll)

    def remove_principal_territory_code(self):
        cc = self.territory_code
        if cc is None:
            return
        default_cc = self.get_principal_territory_code()
        if cc == default_cc:
            self.territory_code = None
            return True

    def remove_encoding(self):
        if self.encoding is None:
            return
        self.encoding = None
        return True

    def remove_nonlinguistic_modifier(self):
        if self.modifier == 'euro':
            self.modifier = None
            return True
        return

    def get_plural_forms(self):
        result = None
        if self.territory_code is not None:
            code = self._simple_format()
            result = _get_plural_forms(code)
        if result is None:
            code = self._simple_format(territory=False)
            result = _get_plural_forms(code)
        return result

    def get_unrepresentable_characters(self, encoding, strict=False):
        characters = None
        if self.territory_code is not None:
            code = self._simple_format()
            characters = _get_characters(code, self.modifier, strict=strict)
        if characters is None:
            code = self._simple_format(territory=False)
            characters = _get_characters(code, self.modifier, strict=strict)
        if characters is None:
            return
        result = []
        try:
            # If iconv(1) is used to implement an encoding, there's a huge
            # overhead per encode() call. To reduce number of such calls,
            # optimize the common case of all characters being representable.
            str.join('', characters).encode(encoding)
        except UnicodeEncodeError:
            pass
        else:
            return result
        for character in characters:
            try:
                character.encode(encoding)
            except UnicodeEncodeError as exc:
                result += [character]
                if exc.reason.startswith('iconv:'):  # pylint: disable=no-member
                    # Avoid further calls to iconv(1):
                    break
        return result

    def _simple_format(self, territory=True):
        s = self.language_code
        if territory and self.territory_code is not None:
            s += '_' + self.territory_code
        return s

    def __str__(self):
        s = self.language_code
        if self.territory_code is not None:
            s += '_' + self.territory_code
        if self.encoding is not None:
            s += '.' + self.encoding
        if self.modifier is not None:
            s += '@' + self.modifier
        return s

    def __repr__(self):
        return f'<Language {self}>'

def _read_iso_codes():
    # ISO language/territory codes:
    path = os.path.join(paths.datadir, 'iso-codes')
    cp = configparser.ConfigParser(interpolation=None, default_section='')
    cp.read(path, encoding='UTF-8')
    cfg_iso_639 = cp['language-codes']
    misc.check_sorted(cfg_iso_639)
    iso_639 = {}
    for lll, ll in cfg_iso_639.items():
        if ll:
            iso_639[ll] = ll
            iso_639[lll] = ll
        else:
            iso_639[lll] = lll
    cfg_iso_3166 = cp['territory-codes']
    misc.check_sorted(cfg_iso_3166)
    iso_3166 = frozenset(cc.upper() for cc in cfg_iso_3166.keys())
    return (iso_639, iso_3166)

[_iso_639, _iso_3166] = _read_iso_codes()

def _read_primary_languages():
    # Hand-edited linguistic data:
    path = os.path.join(paths.datadir, 'languages')
    cp = configparser.ConfigParser(interpolation=None, default_section='')
    cp.read(path, encoding='UTF-8')
    primary_languages = {name: sect for name, sect in cp.items() if sect.name}
    name_to_code = {}
    misc.check_sorted(cp)
    for language, section in cp.items():
        if not language:
            continue
        for key in section.keys():
            if key in {'names', 'characters', 'macrolanguage', 'plural-forms', 'principal-territory'}:
                continue
            if key.startswith('characters@'):
                continue
            raise misc.DataIntegrityError(f'unknown key: {key}')
        for name in section['names'].splitlines():
            name = _munch_language_name(name)
            if name:
                if name in name_to_code:
                    raise misc.DataIntegrityError
                name_to_code[name] = language
    return primary_languages, name_to_code

def _check_primary_languages_coverage():
    # Check if primary languages have full ISO 639-1 coverage:
    for ll in _iso_639:
        if len(ll) > 2:
            continue
        try:
            _primary_languages[ll]
        except LookupError:  # no coverage
            raise misc.DataIntegrityError

[_primary_languages, _name_to_code] = _read_primary_languages()
_check_primary_languages_coverage()

def _lookup_language_code(language):
    return _iso_639.get(language)

def lookup_territory_code(cc):
    if cc in _iso_3166:
        return cc

def get_language_for_name(name):
    parse = parse_language
    _name = _munch_language_name(name)
    try:
        return parse(_name_to_code[_name])
    except KeyError:
        pass
    if ';' in _name:
        for subname in _name.split(';'):
            subname = subname.strip()
            try:
                return parse(_name_to_code[subname])
            except LookupError:
                pass
    if ',' in _name:
        subname = str.join(' ', map(str.strip, _name.split(',', 1)[::-1]))
        try:
            return parse(_name_to_code[subname])
        except LookupError:
            pass
        results = set()
        for subname in _name.split(','):
            subname = subname.strip()
            result = _name_to_code.get(subname)
            if result is not None:
                results.add(result)
        if len(results) == 1:
            return parse(results.pop())
    raise LookupError(name)

_language_regexp = re.compile(r'''
^       ( [a-z]{2,} )
(?:  _  ( [A-Z]{2,} ) )?
(?: [.] ( [a-zA-Z0-9+-]+ ) )?
(?:  @  ( [a-z]+) )?
$''', re.VERBOSE)

def parse_language(s):
    match = _language_regexp.match(s)
    if match is None:
        raise LanguageSyntaxError
    return Language(*match.groups())

def get_primary_languages():
    return iter(_primary_languages)

def _get_plural_forms(language):
    try:
        section = _primary_languages[language]
    except KeyError:
        return
    plural_forms = section.get('plural-forms')
    if plural_forms is None:
        return
    return [
        s.strip()
        for s in plural_forms.splitlines()
        if s and not s.isspace()
    ]

def _get_principal_territory_code(language):
    try:
        section = _primary_languages[language]
    except KeyError:
        return
    return section.get('principal-territory')

def _get_characters(language, modifier=None, strict=True):
    try:
        section = _primary_languages[language]
    except KeyError:
        return
    section_name = 'characters'
    if modifier is not None:
        section_name += f'@{modifier}'
    result = section.get(section_name)
    if result is None:
        return
    if strict:
        return [
            ch.strip('()')
            for ch in result.split()
        ]
    else:
        return [
            ch
            for ch in result.split()
            if not (ch.startswith('(') and ch.endswith(')'))
        ]

# vim:ts=4 sts=4 sw=4 et

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

import configparser
import os
import unicodedata

from . import misc

def _munch_language_name(s):
    # Normalize whitespace:
    s = ' '.join(s.split())
    # Normalize capitalization:
    s = s.lower()
    # Strip accent marks etc.:
    s = unicodedata.normalize('NFD', s).encode('ASCII', 'ignore').decode()
    return s

class FixingLanguageCodesFailed(Exception):
    pass

class FixingLanguageEncodingFailed(Exception):
    pass

class Language(object):

    def __init__(self, parent, language_code, territory_code=None, encoding=None, modifier=None):
        self._parent = parent
        self.language_code = language_code
        if self.language_code is None:
            raise ValueError('language_code must not be None')
        self.territory_code = territory_code
        self.encoding = None
        if encoding is not None:
            self.encoding = encoding.upper()
        self.modifier = modifier

    def fix_codes(self):
        fixed = None
        ll = self.language_code
        ll = self._parent.lookup_language_code(ll)
        if ll is None:
            # TODO: Try to guess correct language code.
            raise FixingLanguageCodesFailed()
        elif ll != self.language_code:
            fixed = True
        cc = self.territory_code
        if cc is not None:
            cc = self._parent.lookup_territory_code(cc)
            if cc is None:
                # TODO: Try to guess correct territory code.
                raise FixingLanguageCodesFailed()
            elif cc != self.territory_code:
                # This shouldn't really happen, but better safe than sorry.
                raise ValueError
            # TODO: ll_CC could be still incorrect, even when both ll and CC are
            # correct.
        self.language_code = ll
        self.territory_code = cc
        return fixed

    def get_principal_territory_code(self):
        ll = self.language_code
        assert ll is not None
        ll = self._parent.lookup_language_code(ll)
        if ll is None:
            return
        try:
            return self._parent.get_principal_territory(ll)
        except LookupError:
            return

    def remove_principal_territory_code(self):
        cc = self.territory_code
        if cc is None:
            return
        cc = self._parent.lookup_territory_code(cc)
        if cc is None:
            return
        if cc != self.territory_code:
            # This shouldn't really happen, but better safe than sorry.
            raise ValueError
        default_cc = self.get_principal_territory_code()
        if cc == default_cc:
            self.territory_code = None
            return True

    def fix_encoding(self):
        # TODO
        if self.encoding is None:
            return
        raise FixingLanguageEncodingFailed()

    def remove_encoding(self):
        if self.encoding == None:
            return
        self.encoding = None
        return True

    def remove_nonlinguistic_modifier(self):
        if self.modifier in {'quot', 'boldquot', 'euro'}:
            self.modifier = None
            return True
        return

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
        return '<Language {}>'.format(self)

class LingInfo(object):

    def __init__(self, datadir):
        # ISO language/territory codes:
        path = os.path.join(datadir, 'iso-codes')
        cp = configparser.ConfigParser(interpolation=None, default_section='')
        cp.read(path, encoding='UTF-8')
        iso_639 = cp['iso-639']
        misc.check_sorted(iso_639)
        self._iso_639 = {}
        for lll, ll in iso_639.items():
            if ll:
                self._iso_639[ll] = ll
                self._iso_639[lll] = ll
            else:
                self._iso_639[lll] = lll
        iso_3166 = cp['iso-3166']
        misc.check_sorted(iso_3166)
        self._iso_3166 = frozenset(cc.upper() for cc in iso_3166.keys())
        # Hand-edited linguistic data:
        path = os.path.join(datadir, 'languages')
        cp = configparser.ConfigParser(interpolation=None, default_section='')
        cp.read(path, encoding='UTF-8')
        self._primary_languages = {name: sect for name, sect in cp.items() if sect.name}
        self._name_to_code = {}
        misc.check_sorted(cp)
        for language, section in cp.items():
            if not language:
                continue
            for name in section['names'].splitlines():
                name = _munch_language_name(name)
                if name:
                    if name in self._name_to_code:
                        raise misc.DataIntegrityError
                    self._name_to_code[name] = language
        # Check if primary languages have full ISO 639-1 coverage:
        for lll, ll in iso_639.items():
            if ll:
                try:
                    self._primary_languages[ll]
                except LookupError:
                    raise misc.DataIntegrityError

    def lookup_language_code(self, language):
        return self._iso_639.get(language)

    def lookup_territory_code(self, cc):
        if cc in self._iso_3166:
            return cc

    def get_language_for_name(self, name):
        _name = _munch_language_name(name)
        try:
            return self._name_to_code[_name]
        except KeyError:
            pass
        if ';' in _name:
            for subname in _name.split(';'):
                subname = subname.strip()
                try:
                    return self._name_to_code[subname]
                except LookupError:
                    pass
        if ',' in _name:
            subname = ' '.join(map(str.strip, _name.split(',', 1)[::-1]))
            try:
                return self._name_to_code[subname]
            except LookupError:
                pass
            results = set()
            for subname in _name.split(','):
                subname = subname.strip()
                result = self._name_to_code.get(subname)
                results.add(result)
            if len(results) == 1:
                return results.pop()
        raise LookupError(name)

    def get_primary_languages(self):
        return list(self._primary_languages)

    def get_plural_forms(self, language):
        try:
            section = self._primary_languages[language]
        except KeyError:
            raise LookupError(language)
        return section.get('plural-forms')

    def get_principal_territory(self, language):
        try:
            section = self._primary_languages[language]
        except KeyError:
            raise LookupError(language)
        return section.get('principal-territory')

# vim:ts=4 sw=4 et

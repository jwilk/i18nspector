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

from . import misc

class LingInfo(object):

    def __init__(self, datadir):
        # ISO language/country codes:
        path = os.path.join(datadir, 'iso-codes')
        cp = configparser.ConfigParser(interpolation=None, default_section='')
        cp.read(path, encoding='UTF-8')
        self._iso_639 = cp['iso-639']
        misc.check_sorted(self._iso_639)
        iso_3166 = cp['iso-3166']
        misc.check_sorted(iso_3166)
        self._iso_3166 = frozenset(cc.upper() for cc in iso_3166.keys())
        # Hand-edited linguistic data:
        path = os.path.join(datadir, 'languages')
        cp = configparser.ConfigParser(interpolation=None, default_section='')
        cp.read(path, encoding='UTF-8')
        self._primary_languages = cp
        self._name_to_code = {}
        misc.check_sorted(cp)
        for language, section in cp.items():
            if not language:
                continue
            name = section['name']
            self._name_to_code[name] = language

    def lookup_language_code(self, language):
        try:
            return self._iso_639[language] or language
        except LookupError:
            return

    def lookup_country_code(self, cc):
        if cc in self._iso_3166:
            return cc

    def get_language_for_name(self, name):
        try:
            return self._name_to_code[name]
        except KeyError:
            raise LookupError(name)

    def get_primary_languages(self):
        return list(self._primary_languages)

    def get_plural_forms(self, language):
        return self._primary_languages[language]['plural-forms']

# vim:ts=4 sw=4 et

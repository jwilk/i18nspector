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
        path = os.path.join(datadir, 'languages')
        cp = configparser.ConfigParser(interpolation=None, default_section='')
        cp.read(path, encoding='UTF-8')
        self._path = path
        self._cp = cp
        self._name_to_code = {}
        if not misc.is_sorted(cp):
            raise configparser.ParsingError('sections are not sorted')
        for language, section in self._cp.items():
            if not language:
                continue
            name = section['name']
            self._name_to_code[name] = language

    def get_language_for_name(self, name):
        try:
            return self._name_to_code[name]
        except KeyError:
            raise LookupError(name)

    def get_primary_languages(self):
        return list(self._cp)

    def get_plural_forms(self, language):
        return self._cp[language]['plural-forms']

    def _set_plural_forms(self, language, s):
        self._cp[language]['plural-forms'] = s

    def _save(self):
        with open(self._path, 'wt', encoding='UTF-8') as file:
            self._cp.write(file)

# vim:ts=4 sw=4 et

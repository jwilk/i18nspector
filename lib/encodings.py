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

import codecs
import configparser
import encodings.aliases
import os

class EncodingInfo(object):

    def __init__(self, datadir):
        path = os.path.join(datadir, 'encodings')
        cp = configparser.ConfigParser(interpolation=None, default_section='')
        cp.read(path, encoding='UTF-8')
        self._portable_encodings = penc = {}
        for encoding, extra in cp['portable-encodings'].items():
            penc[encoding] = False
            if extra == '':
                ''.encode(encoding)
                penc[encoding] = True
            elif extra == 'not-python':
                pass
            else:
                raise ValueError
        self._extra_aliases = dict(
            (key.lower().replace('-', '_'), value.lower().replace('-', '_'))
            for key, value in cp['extra-aliases'].items()
        )

    def is_portable_encoding(self, encoding, python=True):
        encoding = encoding.lower()
        if encoding.startswith('iso_'):
            encoding = 'iso-' + encoding[4:]
        if python:
            return self._portable_encodings.get(encoding, False)
        else:
            return encoding in self._portable_encodings

    def propose_portable_encoding(self, encoding, python=True):
        try:
            new_encoding = codecs.lookup(encoding).name
        except LookupError:
            return
        if new_encoding.startswith('iso8859'):
            new_encoding = 'iso-' + new_encoding[3:]
        if self.is_portable_encoding(new_encoding, python=python):
            return new_encoding

    def install_extra_aliases(self):
        for key, value in self._extra_aliases.items():
            encodings.aliases.aliases[key] = value

# vim:ts=4 sw=4 et

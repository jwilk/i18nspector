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
        self._portable_encodings = e2c = {}
        self._pycodec_to_encoding = c2e = {}
        for encoding, extra in cp['portable-encodings'].items():
            e2c[encoding] = None
            if extra == '':
                pycodec = codecs.lookup(encoding)
                e2c[encoding] = pycodec
                c2e.setdefault(pycodec.name, encoding)
                assert self.propose_portable_encoding(encoding) is not None
            elif extra == 'not-python':
                pass
            else:
                raise ValueError
        self._extra_aliases = {
            key.lower().replace('-', '_'): value.lower().replace('-', '_')
            for key, value in cp['extra-aliases'].items()
        }

    def is_portable_encoding(self, encoding, python=True):
        encoding = encoding.lower()
        if encoding.startswith('iso_'):
            encoding = 'iso-' + encoding[4:]
        if python:
            return self._portable_encodings.get(encoding, None) is not None
        else:
            return encoding in self._portable_encodings

    def propose_portable_encoding(self, encoding, python=True):
        # Note that the "python" argument is never used.
        # Only encodings supported by Python are proposed.
        try:
            pycodec = codecs.lookup(encoding)
            new_encoding = self._pycodec_to_encoding[pycodec.name]
        except LookupError:
            return
        assert self.is_portable_encoding(new_encoding, python=True)
        return new_encoding

    def install_extra_aliases(self):
        for key, value in self._extra_aliases.items():
            encodings.aliases.aliases[key] = value

# vim:ts=4 sw=4 et

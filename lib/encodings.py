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
import functools
import os
import subprocess as ipc

from lib import misc

def iconv_encoding(encoding):

    # FIXME: This implementation is SLOW.

    def encode(input, errors='strict'):
        if len(input) == 0:
            return b'', 0
        if errors != 'strict':
            raise NotImplementedError
        child = ipc.Popen(['iconv', '-s', '-f', 'UTF-8', '-t', encoding],
            stdin=ipc.PIPE, stdout=ipc.PIPE, stderr=ipc.PIPE,
        )
        (stdout, stderr) = child.communicate(input.encode('UTF-8'))
        if stderr != b'':
            stderr = stderr.decode('ASCII', 'replace')
            raise UnicodeEncodeError(encoding, input, 0, len(input), stderr)
        return stdout, len(input)

    def decode(input, errors='strict'):
        if len(input) == 0:
            return '', 0
        if errors != 'strict':
            raise NotImplementedError
        child = ipc.Popen(['iconv', '-s', '-f', encoding, '-t', 'UTF-8'],
            stdin=ipc.PIPE, stdout=ipc.PIPE, stderr=ipc.PIPE,
        )
        (stdout, stderr) = child.communicate(input)
        if stderr != b'':
            stderr = stderr.decode('ASCII', 'replace')
            raise UnicodeDecodeError(encoding, input, 0, len(input), stderr)
        return stdout.decode('UTF-8'), len(input)

    class StreamReader(codecs.StreamReader):
        def decode(self, input, errors='strict'):
            return decode(input, errors)

        def read(self, size=-1, chars=-1, firstline=False):
            # Always read as much bytes as possible, limiting number of
            # required forks.
            return codecs.StreamReader.read(self, size=-1, chars=chars, firstline=False)

    class StreamWriter(codecs.StreamWriter):
        pass

    def not_implemented(*args, **kwargs):
        raise NotImplementedError

    return codecs.CodecInfo(
        encode=encode,
        decode=decode,
        streamreader=StreamReader,
        streamwriter=StreamWriter,
        incrementalencoder=not_implemented,
        incrementaldecoder=not_implemented,
        name=encoding,
    )

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
                raise misc.DataIntegrityError
        self._extra_encodings = {
            key.lower()
            for key, value in cp['extra-encodings'].items()
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

    def _codec_search_function(self, encoding):
        if self._portable_encodings.get(encoding, False) is None:
            pass
        elif encoding in self._extra_encodings:
            pass
        else:
            return
        return iconv_encoding(encoding)

    def install_extra_encodings(self):
        codecs.register(self._codec_search_function)

# vim:ts=4 sw=4 et

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

'''
polib monkey-patching
'''

import codecs
import contextlib
import inspect
import re

import polib

patches = []

@contextlib.contextmanager
def patched(*, patches=patches):
    '''
    with polib4us.patched():
        ...
    '''
    patches = tuple(patches)
    try:
        current_patch, *remaining_patches = patches
    except ValueError:
        yield
        return
    with current_patch():
        with patched(patches=remaining_patches):
            yield

__all__ = ['patched']

# polib.default_encoding
# ======================
# Do not allow broken/missing encoding declarations, unless the file is
# ASCII-only.

@contextlib.contextmanager
def default_encoding_patch():
    original = polib.default_encoding
    try:
        polib.default_encoding = 'ASCII'
        yield
    finally:
        polib.default_encoding = original

patches += [default_encoding_patch]

# polib.codecs
# ============
# Work around a newline decoding bug:
# <http://bugs.debian.org/692283>.

class Codecs(object):

    _iterlines = re.compile(r'[^\n]*(?:\n|\Z)').findall

    def __getattr__(self, attr):
        return getattr(codecs, attr)

    def open(self, path, mode, encoding):
        if mode != 'rU':
            raise NotImplementedError
        with open(path, 'rb') as file:
            contents = file.read()
        contents = contents.decode(encoding)
        for line in self._iterlines(contents):
            yield line

@contextlib.contextmanager
def codecs_patch():
    original = polib.codecs
    try:
        polib.codecs = Codecs()
        yield
    finally:
        polib.codecs = original

patches += [codecs_patch]

# polib._baseFile.__init__()
# ==========================
# Detect metadata duplicates.

class MetadataStr(str):
    def __iadd__(self, other):
        return MetadataStr(str.__add__(self, other))

class MetadataDict(dict):

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.duplicates = {}

    def __setitem__(self, key, value):
        if isinstance(value, MetadataStr):
            dict.__setitem__(self, key, value)
            return
        try:
            orig_value = self[key]
        except KeyError:
            dict.__setitem__(self, key, MetadataStr(value))
        else:
            try:
                self.duplicates[key] += value
            except KeyError:
                self.duplicates[key] = [orig_value, value]

@contextlib.contextmanager
def metadata_patch():
    original = polib._BaseFile.__init__
    def base_file_init(self, *args, **kwargs):
        original(self, *args, **kwargs)
        assert type(self.metadata) is dict
        assert len(self.metadata) == 0
        self.metadata = MetadataDict()
    try:
        polib._BaseFile.__init__ = base_file_init
        yield
    finally:
        polib._BaseFile.__init__ = original

patches += [metadata_patch]

# polib.unescape()
# ================
# Work around an escape sequence decoding bug
# <https://bitbucket.org/izi/polib/issue/31>.

_escapes_re = re.compile(r''' ( \\
(?: [ntbrfva]
  | \\
  | "
  | [0-9]{1,3}
  | x[0-9a-fA-F]{1,2}
  ))+
''', re.VERBOSE)

_short_x_escape_re = re.compile(r'''
    \\x ([0-9a-fA-F]) (?= \\ | $ )
''', re.VERBOSE)

def polib_unescape(s):
    def unescape(match):
        s = match.group()
        s = _short_x_escape_re.sub(r'\x0\1', s)
        result = eval("b'{}'".format(s))
        try:
            return result.decode('ASCII')
        except UnicodeDecodeError:
            # an ugly hack to discover encoding of the PO file:
            parser_stack_frame = inspect.stack()[2][0]
            parser = parser_stack_frame.f_locals['self']
            encoding = parser.instance.encoding
            return result.decode(encoding)
    return _escapes_re.sub(unescape, s)

@contextlib.contextmanager
def unescape_patch():
    original = polib.unescape
    try:
        polib.unescape = polib_unescape
        yield
    finally:
        polib.unescape = original

patches += [unescape_patch]

# vim:ts=4 sw=4 et

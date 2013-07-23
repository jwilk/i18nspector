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

'''
polib monkey-patching
'''

import ast
import codecs
import contextlib
import inspect
import re

import polib

from . import moparser

patches = []

def install_patches(patches=patches):
    for patch in patches:
        patch()

__all__ = ['install_patches']

def register_patch(patch):
    patches.append(contextlib.contextmanager(patch))

# polib.default_encoding
# ======================
# Do not allow broken/missing encoding declarations, unless the file is
# ASCII-only.

@register_patch
def default_encoding_patch():
    polib.default_encoding = 'ASCII'

# polib.codecs
# ============
# Work around a few PO parsing bugs:
# - newline decoding: http://bugs.debian.org/692283
# - atypical comment parsing

class Codecs(object):

    _iterlines = re.compile(r'[^\n]*(?:\n|\Z)').findall
    _atypical_comment = re.compile(r'#[^ .:,|~]').match

    def __getattr__(self, attr):
        return getattr(codecs, attr)

    def open(self, path, mode, encoding):
        if mode != 'rU':
            raise NotImplementedError
        with open(path, 'rb') as file:
            contents = file.read()
        contents = contents.decode(encoding)
        for line in self._iterlines(contents):
            if self._atypical_comment(line):
                yield '# ' + line[1:]
            else:
                yield line

@register_patch
def codecs_patch():
    polib.codecs = Codecs()

# polib.POFile.find()
# ===================
# Make POFile.find() always return None.
# That way the parser won't find the header entry, allowing us to parse it
# ourselves.

@register_patch
def pofile_find_patch():
    def pofile_find(self, *args, **kwargs):
        return
    polib.POFile.find = pofile_find

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
        result = ast.literal_eval("b'{}'".format(s))
        try:
            return result.decode('ASCII')
        except UnicodeDecodeError:
            # an ugly hack to discover encoding of the PO file:
            parser_stack_frame = inspect.stack()[2][0]
            parser = parser_stack_frame.f_locals['self']
            encoding = parser.instance.encoding
            return result.decode(encoding)
    return _escapes_re.sub(unescape, s)

@register_patch
def unescape_patch():
    polib.unescape = polib_unescape

# polib._MOFileParser
# ===================
# Use a custom MO file parser implementation.
# https://bitbucket.org/izi/polib/issue/36
# https://bitbucket.org/izi/polib/issue/44
# https://bitbucket.org/izi/polib/issue/45
# https://bitbucket.org/izi/polib/issue/47

@register_patch
def mo_parser_patch():
    polib._MOFileParser = moparser.Parser

# polib.detect_encoding()
# =======================
# Don't use polib's detect_encoding() for MO files, as i18nspector's own MO
# file parser has built-in encoding detection.

@register_patch
def detect_encoding_patch():
    def detect_encoding(path, binary_mode=False):
        if binary_mode:
            return
        return original(path)
    original = polib.detect_encoding
    polib.detect_encoding = detect_encoding

# vim:ts=4 sw=4 et

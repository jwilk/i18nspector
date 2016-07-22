# Copyright © 2012-2015 Jakub Wilk <jwilk@jwilk.net>
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

from lib import encodings
from lib import moparser

patches = []

def install_patches():
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
# - newline decoding: https://bugs.debian.org/692283
# - trailing comment parsing: https://bitbucket.org/izi/polib/issue/51
# - atypical comment parsing
# - parsing of empty files: https://bitbucket.org/izi/polib/issue/59

class Codecs(object):

    _iterlines = re.compile(r'[^\n]*(?:\n|\Z)').findall
    _atypical_comment = re.compile(r'#[^ .:,|~]').match

    def __getattr__(self, attr):
        return getattr(codecs, attr)

    def open(self, path, mode, encoding):
        if mode not in {'rU', 'rt'}:
            raise NotImplementedError
        if not encodings.is_ascii_compatible_encoding(encoding):
            encoding = 'ASCII'
        with open(path, 'rb') as file:
            contents = file.read()
        contents = contents.decode(encoding)
        pending_comments = []
        empty = True
        for line in self._iterlines(contents):
            if self._atypical_comment(line):
                line = '# ' + line[1:]
            if line[:2] in {'', '# '} or line.isspace():
                pending_comments += [line]
            else:
                for comment_line in pending_comments:
                    yield comment_line
                pending_comments = []
                yield line
                empty = False
        if empty:
            yield '# '

@register_patch
def codecs_patch():
    polib.codecs = polib.io = Codecs()

# polib.POFile.find()
# ===================
# Make POFile.find() always return None.
# That way the parser won't find the header entry, allowing us to parse it
# ourselves.

@register_patch
def pofile_find_patch():
    def pofile_find(self, *args, **kwargs):
        del self, args, kwargs
        return
    polib.POFile.find = pofile_find

# polib.unescape()
# ================
# Work around an escape sequence decoding bug.
# https://bitbucket.org/izi/polib/issue/31

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
        s = _short_x_escape_re.sub(r'\\x0\1', s)
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

# polib.POEntry.flags
# ===================
# Fix flag splitting.
# polib (<< 1.0.4) incorrectly requires that the flag-splitting comma is
# followed by a space.
# https://bitbucket.org/izi/polib/issue/46

@register_patch
def poentry_flags_patch():
    def get_flags(self):
        return self._i18nspector_flags
    def set_flags(self, flags):
        self._i18nspector_flags = [
            flag.strip(' \t\r\f\v')
            for subflags in flags
            for flag in subflags.split(',')
        ]
    polib.POEntry.flags = property(get_flags, set_flags)

# polib.POEntry.msgstr_plural
# ===========================
# Force msgstr_plural keys to be integers.
# polib (<< 1.0.4) uses strings there instead.
# https://bitbucket.org/izi/polib/issue/49

class IntDict(dict):

    def __setitem__(self, key, value):
        super().__setitem__(int(key), value)

    def __getitem__(self, key):
        return super().__getitem__(int(key))

@register_patch
def poentry_msgstr_plural_patch():
    def get_msgstr_plural(self):
        return self._i18nspector_msgstr_plural
    def set_msgstr_plural(self, d):
        self._i18nspector_msgstr_plural = IntDict(d)
    polib.POEntry.msgstr_plural = property(
        get_msgstr_plural,
        set_msgstr_plural,
    )

# polib._BaseEntry.__init__()
# ===========================
# Distinguish between empty and non-existent msgid_plural.
# Distinguish between empty and non-existent msgstr.

@register_patch
def base_entry_init_patch():
    def init(self, *args, **kwargs):
        original(self, *args, **kwargs)
        if 'msgid_plural' not in kwargs:
            self.msgid_plural = None
        if 'msgstr' not in kwargs:
            self.msgstr = None
    original = polib._BaseEntry.__init__
    polib._BaseEntry.__init__ = init

# polib.POEntry.translated()
# ==========================
# Consider the message translated if any msgstr[N] is non-empty.

@register_patch
def poentry_translated_patch():
    def translated(self):
        if self.obsolete:
            return False
        if 'fuzzy' in self.flags:
            return False
        return (
            self.msgstr or
            any(self.msgstr_plural.values())
        )
    polib.POEntry.translated = translated

# vim:ts=4 sts=4 sw=4 et

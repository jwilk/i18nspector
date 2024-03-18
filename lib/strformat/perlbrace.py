# Copyright © 2016-2024 Jakub Wilk <jwilk@jwilk.net>
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
Perl format checks: Locale::TextDomain
'''

import re

_field_re = re.compile(r'''
    (?P<literal> [^{]+ ) |
    (?:
        [{]
            (?P<name> [^\W\d]\w* )
        [}]
    )
''', re.VERBOSE)

def _printable_prefix(s, r=re.compile('[ -\x7E]+')):
    return r.match(s).group()

class Error(Exception):
    message = 'invalid placeholder specification'

class FormatString:

    def __init__(self, s):
        self._items = items = []
        arguments = set()
        last_pos = 0
        for match in _field_re.finditer(s):
            if match.start() != last_pos:
                raise Error(
                    _printable_prefix(s[last_pos:])
                )
            items += [match.group()]
            argname = match.group('name')
            if argname is not None:
                arguments.add(argname)
            last_pos = match.end()
        if last_pos != len(s):
            raise Error(
                _printable_prefix(s[last_pos:])
            )
        self.arguments = frozenset(arguments)

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

# vim:ts=4 sts=4 sw=4 et

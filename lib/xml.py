# Copyright © 2014 Jakub Wilk <jwilk@jwilk.net>
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
XML support
'''

import random
import string
import xml.parsers.expat

SyntaxError = xml.parsers.expat.ExpatError  # pylint: disable=redefined-builtin

_xe = (
    'i18nspector.' +
    ''.join(random.choice(string.ascii_lowercase) for x in range(12))
)

_source = '''\
<!DOCTYPE i18nspector SYSTEM "i18nspector.dtd" [
  <!ENTITY {xe} SYSTEM "{xe}">
]>
<i18nspector>&{xe};</i18nspector>
'''.format(xe=_xe).encode('ASCII')

def check_fragment(s):
    '''
    check if the string could be a well-formed XML fragment
    '''
    def ee_handler(context, base, systemid, publicid):
        assert base is None
        assert systemid == _xe
        assert publicid is None
        eparser = parser.ExternalEntityParserCreate(context)
        eparser.Parse(s.encode('UTF-8'), True)
        return 1
    parser = xml.parsers.expat.ParserCreate('UTF-8')
    parser.ExternalEntityRefHandler = ee_handler
    parser.Parse(_source, True)

# https://www.w3.org/TR/REC-xml/#NT-NameStartChar
# pylint: disable=line-too-long
_start_char = ':A-Z_a-z\xC0-\xD6\xD8-\xF6\xF8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\U00010000-\U000EFFFF'
_next_char = _start_char + '.0-9\xB7\u0300-\u036F\u203F\u2040-'
name_re = f'[{_start_char}][{_next_char}]*'

# vim:ts=4 sts=4 sw=4 et

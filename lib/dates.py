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

import datetime
import re

_re = re.compile('''
    ^ \s*
    ( [0-9]{4}-[0-9]{2}-[0-9]{2} ) # YYYY-MM-DD
    ( \s+ )
    ( [0-9]{2}:[0-9]{2} ) # hh:mm
    (?: : [0-9]{2} )? # ss
    \s*
    ( [+-] [0-9]{2} ) # ZZ
    :?
    ( [0-9]{2} ) # zz
    \s* $
''', re.VERBOSE)

def fix_date_format(s):
    match = _re.match(s)
    if match is None:
        return
    s = ''.join(match.groups())
    assert len(s) == 21
    try:
        parse_date(s)
    except ValueError:
        return
    return s

def parse_date(s):
    return datetime.datetime.strptime(s, '%Y-%m-%d %H:%M%z')

now = datetime.datetime.now()
now = now.replace(tzinfo=datetime.timezone.utc)
gettext_epoch = datetime.datetime(1995, 7, 2, tzinfo=datetime.timezone.utc)

# vim:ts=4 sw=4 et

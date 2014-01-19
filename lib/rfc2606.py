# Copyright © 2013, 2014 Jakub Wilk <jwilk@jwilk.net>
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
RFC 2606: Reserved Top Level DNS Names
'''

# http://tools.ietf.org/search/rfc2606

import re

_is_reserved = re.compile(r'''
( [.] test
| [.] example
| [.] invalid
| [.] localhost
| (^|[.])example[.](com|net|org)
) $
''', re.VERBOSE).search

def is_reserved_domain(domain):
    domain = domain.lower()
    return _is_reserved(domain)

def is_reserved_email(email):
    _, domain = email.rsplit('@', 1)
    return is_reserved_domain(domain)

# vim:ts=4 sw=4 et

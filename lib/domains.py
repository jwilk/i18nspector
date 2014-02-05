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
special-use domain names
'''

# http://www.iana.org/assignments/special-use-domain-names/special-use-domain-names.xhtml

import re

_regexps = [
    # RFC 1035, §3.5 <http://tools.ietf.org/html/rfc1035#section-3.5>:
    '.+[.]in-addr[.]arpa',
    # RFC 3596, §2.5 <http://tools.ietf.org/html/rfc3596#section-2.5>:
    '.+[.]ip6[.]arpa',
    # RFC 6761, §6 <http://tools.ietf.org/html/rfc6761#section-6>:
    '(.+[.])?test',
    '(.+[.])?localhost',
    '(.+[.])?invalid',
    '(.+[.])?example([.](com|net|org))?',
    # RFC 6762, §3 <http://tools.ietf.org/html/rfc6762#section-3>:
    '(.+[.])local',
]

_is_special = re.compile(
    '^({re})$'.format(re='|'.join(_regexps))
).match

def is_special_domain(domain):
    domain = domain.lower()
    return _is_special(domain)

def is_email_in_special_domain(email):
    _, domain = email.rsplit('@', 1)
    return is_special_domain(domain)

# vim:ts=4 sw=4 et

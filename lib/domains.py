# Copyright © 2013-2022 Jakub Wilk <jwilk@jwilk.net>
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

# https://www.iana.org/assignments/special-use-domain-names/special-use-domain-names.xhtml

import re

_regexps = [
    # RFC 1035, §3.5 <https://www.rfc-editor.org/rfc/rfc1035.html#section-3.5>:
    '.+[.]in-addr[.]arpa',
    # RFC 3596, §2.5 <https://www.rfc-editor.org/rfc/rfc3596.html#section-2.5>:
    '.+[.]ip6[.]arpa',
    # RFC 6761, §6 <https://www.rfc-editor.org/rfc/rfc6761.html#section-6>:
    '(.+[.])?test',
    '(.+[.])?localhost',
    '(.+[.])?invalid',
    '(.+[.])?example([.](com|net|org))?',
    # RFC 6762, §3 <https://www.rfc-editor.org/rfc/rfc6762.html#section-3>:
    '(.+[.])local',
]
_regexps = str.join('|', _regexps)
_is_special = re.compile(f'({_regexps})').fullmatch

def is_special_domain(domain):
    domain = domain.lower()
    return _is_special(domain)

def is_email_in_special_domain(email):
    _, domain = email.rsplit('@', 1)
    return is_special_domain(domain)

def is_dotless_domain(domain):
    return '.' not in domain

def is_email_in_dotless_domain(email):
    # Technically, e-mail addresses in dotless domains are not forbidden.
    # But in practice they are almost certainly mistakes.
    # See also: RFC 7085 <https://www.rfc-editor.org/rfc/rfc7085.html>
    _, domain = email.rsplit('@', 1)
    return is_dotless_domain(domain)

# vim:ts=4 sts=4 sw=4 et

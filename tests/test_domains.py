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

from nose.tools import (
    assert_false,
    assert_raises,
    assert_true,
)

import lib.domains as M

class test_domains:

    def t(self, domain, special=True):
        result = M.is_special_domain(domain)
        if special:
            assert_true(result)
        else:
            assert_false(result)

    def test_ok(self):
        self.t('test.jwilk.net', False)

    def test_in_addr_apra(self):
        self.t('119.216.184.93.in-addr.arpa')

    def test_ip6_arpa(self):
        self.t('7.a.a.0.7.9.0.1.7.4.4.1.f.b.6.2.d.6.0.0.0.2.2.0.0.0.8.2.6.0.6.2.ip6.arpa')

    def test_test(self):
        self.t('test')
        self.t('eggs.test')

    def test_localhost(self):
        self.t('localhost')
        self.t('eggs.localhost')

    def test_invalid(self):
        self.t('invalid')
        self.t('eggs.invalid')

    def test_example(self):
        self.t('example')
        for tld in 'com', 'net', 'org':
            self.t('example.{tld}'.format(tld=tld))
            self.t('eggs.example.{tld}'.format(tld=tld))

class test_emails:

    def t(self, email, special=True):
        result = M.is_email_in_special_domain(email)
        if special:
            assert_true(result)
        else:
            assert_false(result)

    def test_valid(self):
        self.t('jwilk@test.jwilk.net', False)

    def test_special(self):
        self.t('jwilk@example.net')

    def test_no_at(self):
        with assert_raises(ValueError):
            self.t('jwilk%jwilk.net')

# vim:ts=4 sts=4 sw=4 et

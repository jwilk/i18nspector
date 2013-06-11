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

PYTHON = python3
PREFIX = /usr/local
DESTDIR =

exe = i18nspector

bindir = $(PREFIX)/bin
basedir = $(PREFIX)/share/$(exe)
libdir = $(basedir)/lib
datadir = $(basedir)/data
mandir = $(PREFIX)/share/man

.PHONY: all
all: ;

.PHONY: install
install:
	# binary:
	install -d -m755 $(DESTDIR)$(bindir)
	sed -e "s#^basedir_fallback = .*#basedir_fallback = '$(basedir)/'#" $(exe) > $(DESTDIR)$(bindir)/$(exe)
	chmod 0755 $(DESTDIR)$(bindir)/$(exe)
	# library:
	( cd lib && find -type f ! -name '*.py[co]' ) \
	| sed -e 's#^[.]/##' \
	| xargs -t -I {} install -D -m644 lib/{} $(DESTDIR)$(libdir)/{}
	# data:
	install -d -m755 $(DESTDIR)$(datadir)
	install -m 644 data/* $(DESTDIR)$(datadir)
	# manual page:
	install -D -m644 doc/$(exe).1 $(DESTDIR)$(mandir)/man1/$(exe).1

.PHONY: test
test:
	$(PYTHON) -c 'import nose; nose.main()' -v

# vim:ts=4 sw=4 noet

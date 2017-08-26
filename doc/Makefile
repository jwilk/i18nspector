# Copyright © 2012-2017 Jakub Wilk <jwilk@jwilk.net>
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

export LC_ALL=C

rst2man = $(or $(shell which rst2man),rst2man.py)
exe = i18nspector

.PHONY: all
all: $(exe).1

tags.txt: ../data/tags
	../private/tags-as-rst > $(@).tmp
	mv $(@).tmp $(@)

$(exe).1: $(exe).txt tags.txt
	$(rst2man) --input-encoding=UTF-8:strict < $(<) > $(@).tmp
	sed -i -e '/^[.]BI/ { s/\\fP/\\fR/g; }' $(@).tmp  # work-around for https://bugs.debian.org/806601
	sed -i -e 's/^[.]de1/.de/' $(@).tmp  # work-around for https://bugs.debian.org/710678
	sed -i -e "s/\([a-z]\)\\\\(aq\([a-z]\)/\1'\2/g" $(@).tmp  # prefer ' to \(aq when used as an apostrophe
	sed -i -e '/^[.][\]" vim:/d' $(@).tmp
	mv $(@).tmp $(@)

.PHONY: clean
clean:
	rm -f tags.txt $(exe).1

# vim:ts=4 sts=4 sw=4 noet

exe = i18nspector
version = $(word 3,$(shell grep ^:version: ../$(exe).txt))
email = $(shell sed -n -e '/ -- .*<\(.*\)>.*/ { s//\1/; p; q }' ../changelog)

po_files = $(wildcard $(exe).*.po)
man_files = $(po_files:.po=.1)

.PHONY: all
all: $(exe).pot $(man_files)

xgettext_options = \
	--msgid-bugs-address='$(email)' \
	--package-name='$(exe)' \
	--package-version='$(version)' \

po4a_options = \
	-M UTF-8 \
	-f man \
	-o groff_code=verbatim \
	-o untranslated=INDENT,UNINDENT \

$(exe).pot: ../$(exe).1
	po4a-gettextize -m $(<) -p $(@).tmp $(po4a_options) $(xgettext_options)
	msggrep -v -X -E -e '^type: (SS|IP|TH)$$' $(@).tmp --no-location --no-wrap -o $(@).tmp  # skip boring parts
	sed -i -e '/^#\( \|$$\)/d' $(@).tmp
	mv $(@).tmp $(@)

%.1: %.po ../$(exe).1
	po4a-translate -k 0 $(po4a_options) -m ../$(exe).1 -p $(<) $(po4a_options) -l $(@).tmp
	mv $(@).tmp $(@)

.PHONY: clean
clean:
	rm -f $(exe).pot $(exe).*.1

# vim:ts=4 sw=4 noet

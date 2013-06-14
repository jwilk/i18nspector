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
	sed -i -e 's/^[.]de1/.de/' $(@).tmp  # work-around for http://bugs.debian.org/710678
	sed -i -e "s/\([a-z]\)\\\\(aq\([a-z]\)/\1'\2/g" $(@).tmp  # prefer ' to \(aq when used as an apostrophe
	mv $(@).tmp $(@)

.PHONY: clean
clean:
	rm -f tags.txt $(exe).1

# vim:ts=4 sw=4 noet

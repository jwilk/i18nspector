rst2man = $(or $(shell which rst2man),rst2man.py)
exe = i18nspector

.PHONY: all
all: $(exe).1

tags.txt: ../data/tags
	../private/tags-as-rst > $(@).tmp
	mv $(@).tmp $(@)

$(exe).1: $(exe).txt tags.txt
	$(rst2man) < $(<) > $(@).tmp
	mv $(@).tmp $(@)

.PHONY: clean
clean:
	rm -f tags.txt $(exe).1

# vim:ts=4 sw=4 noet

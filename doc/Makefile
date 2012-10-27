rst2man = $(or $(shell which rst2man) $(shell which rst2man.py))

.PHONY: all
all: gettext-inspector.1

tags.txt: ../data/tags
	../private/tags-as-rst > $(@).tmp
	mv $(@).tmp $(@)

gettext-inspector.1: gettext-inspector.txt tags.txt
	$(rst2man) < $(<) > $(@).tmp
	mv $(@).tmp $(@)

.PHONY: clean
clean:
	rm -f tags.txt gettext-inspector.1

# vim:ts=4 sw=4 noet

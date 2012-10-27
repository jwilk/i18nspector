rst2man = $(or $(shell which rst2man) $(shell which rst2man.py))

.PHONY: all
all: gettext-inspector.1

gettext-inspector.txt: gettext-inspector.txt.in
	../private/tags-as-rst --template $(<) > $(@).tmp
	mv $(@).tmp $(@)

gettext-inspector.1: gettext-inspector.txt
	$(rst2man) < $(<) > $(@).tmp
	mv $(@).tmp $(@)

.PHONY: clean
clean:
	rm -f gettext-inspector.txt gettext-inspector.1

# vim:ts=4 sw=4 noet

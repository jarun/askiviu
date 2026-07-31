INSTALL_PATH := /usr/local/bin/dotz

.PHONY: install uninstall

install:
	install -Dm755 dotz.py $(INSTALL_PATH)

uninstall:
	rm -f $(INSTALL_PATH)
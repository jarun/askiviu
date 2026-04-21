# Makefile for dot

.PHONY: install clean

install:
	pip install .

clean:
	rm -rf build dist *.egg-info

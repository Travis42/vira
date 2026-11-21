.PHONY: fetch gloss build test all

fetch:
	python3 -m vira fetch

gloss:
	python3 -m vira gloss

build:
	python3 -m vira build

test:
	python3 -m pytest -q

all: fetch gloss build test

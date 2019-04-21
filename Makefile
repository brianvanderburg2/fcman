override SHELL:=/bin/bash
override SHELLOPTS:=errexit:pipefail
export SHELLOPTS
override DATE:=$(shell date -u "+%Y%m%d-%H%M")


.PHONY: clean
clean:
	rm -rf test/output
	rm -rf output
	find -name "*.py[co]" -delete
	find -depth \( -path "*/__pycache__/*" -o -name __pycache__ \) -delete

.PHONY: tarball
tarball: NAME:=mrbavii-fcman-$(shell git symbolic-ref --short HEAD)-$(shell date +%Y%m%d)-$(shell git describe --always)
tarball: 
	mkdir -p output
	git archive --format=tar --prefix=$(NAME)/ HEAD | xz > output/$(NAME).tar.xz


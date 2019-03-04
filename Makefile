PACKAGE := openvpn_client_connect
.DEFAULT: test
.PHONY: all test coverage coveragereport pep8 pylint rpm clean
TEST_FLAGS_FOR_SUITE := -m unittest discover -f -v -s test
SUMMARY := OpenVPN script to allocate routes to connecting clients
DESCRIPTION := Dynamically allocates routes to connecting clients


all: test

test:
	python -B $(TEST_FLAGS_FOR_SUITE)

coverage:
	coverage run $(TEST_FLAGS_FOR_SUITE)
	@rm -f $(PACKAGE)/*.pyc test/*.pyc

coveragereport:
	coverage report -m $(PACKAGE)/*.py test/*.py

pep8:
	@find ./* `git submodule --quiet foreach 'echo -n "-path ./$$path -prune -o "'` -type f -name '*.py' -exec pep8 --show-source --max-line-length=100 {} \;

pylint:
	@find ./* `git submodule --quiet foreach 'echo -n "-path ./$$path -prune -o "'` -type f -name '*.py' -exec pylint -r no --disable=locally-disabled --rcfile=/dev/null {} \;

rpm:
	fpm -s python -t rpm --rpm-dist "$$(rpmbuild -E '%{?dist}' | sed -e 's#^\.##')" --iteration 1 setup.py
	@rm -rf build $(PACKAGE).egg-info

clean:
	rm -f $(PACKAGE)/*.pyc test/*.pyc
	rm -f *.rpm
	rm -rf build $(PACKAGE).egg-info

PACKAGE := openvpn_client_connect
.DEFAULT: test
.PHONY: all test coverage coveragereport pep8 pylint rpm clean
TEST_FLAGS_FOR_SUITE := -m unittest discover -f

PLAIN_PYTHON = $(shell which python 2>/dev/null)
PYTHON3 = $(shell which python3 2>/dev/null)
ifneq (, $(PYTHON3))
  PYTHON_BIN = $(PYTHON3)
  PY_PACKAGE_PREFIX = python3
endif
ifneq (, $(PLAIN_PYTHON))
  PYTHON_BIN = $(PLAIN_PYTHON)
  PY_PACKAGE_PREFIX = python
endif

COVERAGE2 = $(shell which coverage 2>/dev/null)
COVERAGE3 = $(shell which coverage-3 2>/dev/null)
ifneq (, $(COVERAGE2))
  COVERAGE = $(COVERAGE2)
endif
ifneq (, $(COVERAGE3))
  COVERAGE = $(COVERAGE3)
endif

all: test

test:
	$(PYTHON_BIN) -B $(TEST_FLAGS_FOR_SUITE) -s test

coverage:
	$(COVERAGE) run $(TEST_FLAGS_FOR_SUITE) -s test
	@rm -rf test/__pycache__
	@rm -f $(PACKAGE)/*.pyc test/*.pyc

coveragereport:
	$(COVERAGE) report -m $(PACKAGE)/* test/*.py

pep8:
	@find ./* `git submodule --quiet foreach 'echo -n "-path ./$$path -prune -o "'` -type f -name '*.py' -exec pep8 --show-source --max-line-length=100 {} \;

pylint:
	@find ./* `git submodule --quiet foreach 'echo -n "-path ./$$path -prune -o "'` -path ./test -prune -o -type f -name '*.py' -exec pylint -r no --rcfile=/dev/null {} \;
	@find ./test -type f -name '*.py' -exec pylint -r no --disable=protected-access,locally-disabled --rcfile=/dev/null {} \;

rpm:
	fpm -s python -t rpm --python-bin $(PYTHON_BIN) --no-python-fix-name --python-package-name-prefix $(PY_PACKAGE_PREFIX) --python-install-bin /usr/bin --rpm-dist "$$(rpmbuild -E '%{?dist}' | sed -e 's#^\.##')" --iteration 1 setup.py
	@rm -rf test/__pycache__
	@rm -rf build $(PACKAGE).egg-info

clean:
	rm -f $(PACKAGE)/*.pyc test/*.pyc
	rm -rf test/__pycache__
	rm -rf build $(PACKAGE).egg-info

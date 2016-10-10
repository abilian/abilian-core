.PHONY: develop test lint clean doc

# The source directory
SRC=abilian
# The package name
PKG=abilian

# On a 4 core laptop, 2 is optimal
NCPU=2

# pytest-sugar seems to be incompatible with pytest-xdist
PYTEST_MULTI=-n $(NCPU) -p no:sugar


all: test lint


#
# Setup
#
develop:
	@echo "--> Installing dependencies"
	pip install -U setuptools
	pip install -U -e '.[dev]'
	@echo ""

setup-git:
	@echo "--> Configuring git and installing hooks"
	git config branch.autosetuprebase always
	cd .git/hooks && ln -sf ../../tools/hooks/* ./
	@echo ""


#
# testing & checking
#
test-all: test test-readme

test:
	@echo "--> Running Python tests"
	py.test $(PYTEST_MULTI) .
	@echo ""

test-with-coverage:
	@echo "--> Running Python tests"
	py.test $(PYTEST_MULTI) --cov $(PKG) $(PKG) tests
	@echo ""

vagrant-tests:
	vagrant up
	vagrant ssh -c /vagrant/deploy/vagrant_test.sh


#
# Various Checkers
#
# TODO: add lint-js lint-rst
lint: lint-py lint-travis

lint-py:
	@echo "--> Linting Python files"
	flake8 $(SRC)
	@echo ""

lint-travis:
	@echo "--> Linting .travis.yml files"
	travis lint
	@echo ""
	
lint-js:
	@echo "--> Linting JS files"
	eslint ./abilian/web/resources/js/
	@echo ""

lint-rst:
	@echo "--> Linting .rst files"
	rst-lint *.rst docs/*.rst
	@echo ""


#
# Everything else
#
install:
	python setup.py install

doc: doc-html doc-pdf

doc-html:
	sphinx-build -W -b html docs/ docs/_build/html

doc-pdf:
	sphinx-build -W -b latex docs/ docs/_build/latex
	make -C docs/_build/latex all-pdf

clean:
	find . -name "*.pyc" -delete
	find . -name __pycache__ -delete
	find . -name .hypothesis -delete
	find . -name abilian.db -delete
	find . -type d -empty -delete
	rm -rf *.egg-info *.egg .coverage .eggs .cache
	rm -rf whoosh tests/whoosh tests/integration/whoosh
	rm -rf docs/_build docs/cache docs/tmp
	rm -rf $(SRC)/static/gen
	rm -rf dist build
	rm -rf htmlcov coverage.xml
	rm -rf docs/_build
	rm -f junit-*.xml

tidy: clean
	rm -rf .tox .dox .travis-solo

update-pot:
	# _n => ngettext, _l => lazy_gettext
	python setup.py extract_messages update_catalog compile_catalog

release:
	rm -rf /tmp/abilian-core
	git clone . /tmp/abilian-core
	cd /tmp/abilian-core ; python setup.py sdist
	cd /tmp/abilian-core ; python setup.py sdist upload

format:
	isort -a  "from __future__ import absolute_import, print_function, unicode_literals" \
		-rc $(SRC) tests *.py
	-yapf --style google -r -i $(SRC) tests *.py
	isort -rc $(SRC) tests *.py


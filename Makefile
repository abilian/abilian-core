.PHONY: develop test lint clean doc

# The source directory
SRC=abilian
# The package name
PKG=abilian

# On a 4 core laptop, 2 is optimal
NCPU=2

# pytest-sugar seems to be incompatible with pytest-xdist
# -s: no terminal capture.
PYTEST_MULTI=-n $(NCPU) -p no:sugar -s


all: test lint


#
# Setup
#
develop:
	@echo "--> Installing dependencies"
	pip install -U pip-tools setuptools
	pip install -U -e '.[dev]'
	pip install -r etc/dev-requirements.txt
	yarn
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
flake8:
	flake8 $(SRC)

lint: lint-ci lint-travis

lint-ci: lint-py lint-js lint-less lint-rst lint-doc lint-mypy

lint-py:
	@echo "--> Linting Python files"
	flake8 $(SRC)
	@echo ""

lint-mypy:
	@echo "--> Typechecking Python files w/ mypy"
	-mypy $(SRC)
	@echo ""

lint-py3k:
	@echo "--> Checking Python 3 compatibility"
	pylint --py3k abilian tests
	@echo ""

lint-travis:
	@echo "--> Linting .travis.yml files"
	travis lint
	@echo ""

lint-js:
	@echo "--> Linting JS files"
	-npm run eslint
	@echo ""

lint-less:
	@echo "--> Linting LESS files"
	-npm run stylelint
	@echo ""

lint-rst:
	@echo "--> Linting .rst files"
	rst-lint *.rst
	@echo ""

lint-doc:
	@echo "--> Linting doc"
	sphinx-build -W -b dummy docs/ docs/_build/
	@echo ""

#
# Everything else
#
install:
	pip install -U pip
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
	rm -f npm-debug.log

tidy: clean
	rm -rf .tox .dox .travis-solo
	rm -rf node_modules

update-pot:
	# _n => ngettext, _l => lazy_gettext
	python setup.py extract_messages update_catalog compile_catalog

release:
	git push --tags
	rm -rf /tmp/abilian-core
	git clone . /tmp/abilian-core
	cd /tmp/abilian-core ; python setup.py sdist
	cd /tmp/abilian-core ; python setup.py sdist upload

format:
	isort -a  "from __future__ import absolute_import, print_function, unicode_literals" \
		-rc $(SRC) tests *.py
	-yapf --style google -r -i $(SRC) tests *.py
	-add-trailing-comma `find abilian -name '*.py'`
	isort -rc $(SRC) tests *.py

update-deps:
	pip-compile -U > /dev/null
	pip-compile > /dev/null
	git --no-pager diff requirements.txt

sync-deps:
	pip install -r requirements.txt
	pip install -r etc/dev-requirements.txt
	pip install -e .

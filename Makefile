.PHONY: develop test lint clean doc

# The source directory
SRC=abilian
# The package name
PKG=abilian

# FIXME: We have a parallelism issue with soffice conversion
# NCPU ?= $(shell sysctl -n hw.ncpu || echo 1)
NCPU=1

# pytest-sugar seems to be incompatible with pytest-xdist
# -s: no terminal capture.
# PYTEST_MULTI=-n $(NCPU) -p no:sugar -s
PYTEST_MULTI=-n $(NCPU)


all: test lint


#
# Setup
#
develop:
	@echo "--> Installing dependencies"
	pip install -U pip setuptools wheel
	poetry install --develop .
	yarn
	@echo "--> Activating pre-commit hook"
	pre-commit install
	@echo "--> Configuring git"
	git config branch.autosetuprebase always
	@echo ""


#
# testing & checking
#
test-all: test test-readme

test:
	@echo "--> Running Python tests"
	pytest --ff -x -p no:randomly $(PYTEST_MULTI)
	@echo ""

test-randomly:
	@echo "--> Running Python tests in random order"
	pytest $(PYTEST_MULTI)
	@echo ""

test-with-coverage:
	@echo "--> Running Python tests"
	py.test $(PYTEST_MULTI) --cov $(PKG)
	@echo ""

vagrant-tests:
	vagrant up
	vagrant ssh -c /vagrant/deploy/vagrant_test.sh


#
# Various Checkers
#
lint: lint-py lint-js lint-less lint-rst lint-doc

lint-ci: lint

lint-all: lint lint-mypy lint-bandit

lint-py:
	@echo "--> Linting Python files /w flake8"
	flake8 $(SRC)
	@echo ""

flake8:
	flake8 $(SRC)

lint-mypy:
	@echo "--> Typechecking Python files w/ mypy"
	mypy $(SRC)
	@echo ""

lint-py3k:
	@echo "--> Checking Python 3 compatibility"
	pylint --py3k -j3 abilian
	@echo ""

lint-travis:
	@echo "--> Linting .travis.yml files"
	travis lint --no-interactive
	@echo ""

lint-js:
	@echo "--> Linting JS files"
	yarn run eslint abilian/web/resources/js/
	@echo ""

lint-less:
	@echo "--> Linting LESS files"
	yarn run stylelint ./abilian/web/resources/less/*.less
	@echo ""

lint-rst:
	@echo "--> Linting .rst files"
	rst-lint *.rst
	@echo ""

lint-doc:
	@echo "--> Linting doc"
	sphinx-build -W -b dummy docs/ docs/_build/
	@echo ""

lint-bandit:
	@echo "--> Linting python w/ Bandit"
	bandit -s B101 `find abilian -name '*.py' | grep -v test`
	@echo ""


#
# Formatting
#
format: format-py format-js

format-py:
	docformatter -i -r abilian
	black abilian demo tests *.py
	isort -rc -sg "**/__init__.py" abilian demo tests *.py

format-js:
	yarn run prettier --write --trailing-comma es5 \
		'abilian/web/resources/js/**/*.js' \
	yarn run prettier --write \
		--trailing-comma es5 --tab-width 2 \
		'abilian/web/resources/less/**/*.less'

futurize:
	isort -a  "from __future__ import absolute_import, print_function, unicode_literals" \
		-rc $(SRC) *.py

#
# Everything else
#
install:
	poetry install

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
	rm -rf *.egg-info *.egg .coverage .eggs .cache .mypy_cache .pyre
	rm -rf .pytest_cache .pytest .DS_Store
	rm -rf docs/_build docs/cache docs/tmp
	rm -rf $(SRC)/static/gen
	rm -rf dist build pip-wheel-metadata
	rm -rf htmlcov coverage.xml
	rm -rf docs/_build
	rm -f junit-*.xml
	rm -f npm-debug.log yarn-error.log

tidy: clean
	rm -rf .tox .dox .travis-solo
	rm -rf node_modules
	rm -rf instance

update-pot:
	# _n => ngettext, _l => lazy_gettext
	python setup.py extract_messages update_catalog compile_catalog

release:
	maketag
	git push --tags
	poetry publish --build

update-deps:
	pip install -U pip setuptools wheel
	poetry update

sync-deps:
	pip install -U pip setuptools wheel
	poetry install

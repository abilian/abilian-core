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
	pip install -U pip-tools setuptools
	pip install -U -e '.[dev]'
	pip install -r etc/dev-requirements.txt
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
flake8:
	flake8 $(SRC)

lint-ci: lint-py lint-py3k lint-less lint-rst lint-doc

lint: lint-py lint-js lint-rst lint-doc lint-travis

lint-all: lint lint-mypy lint-js lint-less lint-bandit

lint-py:
	@echo "--> Linting Python files /w flake8"
	flake8 $(SRC)
	@echo ""

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
	travis lint
	@echo ""

lint-js:
	@echo "--> Linting JS files"
	node_modules/.bin/eslint abilian/web/resources/js/
	@echo ""

lint-less:
	@echo "--> Linting LESS files"
	node_modules/.bin/stylelint ./abilian/web/resources/less/*.less
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

format: format-py format-js

format-py:
	-add-trailing-comma `find abilian -name '*.py'` demo/*.py *.py
	-yapf --style google -r -i abilian demo *.py
	# autopep8 -j3 -r --in-place -a --ignore E711 abilian demo *.py
	isort -rc abilian demo *.py

format-js:
	./node_modules/.bin/prettier --write \
		--trailing-comma es5 --tab-width 2 \
		'abilian/web/resources/js/**/*.js'

futurize-py-headers:
	isort -a  "from __future__ import absolute_import, print_function, unicode_literals" \
		-rc $(SRC) *.py

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
	rm -rf *.egg-info *.egg .coverage .eggs .cache .mypy_cache
	rm -rf .pytest_cache .pytest
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
	rm -rf instance

update-pot:
	# _n => ngettext, _l => lazy_gettext
	python setup.py extract_messages update_catalog compile_catalog

release:
	git push --tags
	rm -rf /tmp/abilian-core
	git clone . /tmp/abilian-core
	cd /tmp/abilian-core ; python setup.py sdist
	cd /tmp/abilian-core ; python setup.py sdist upload


update-deps:
	pip-compile -U > /dev/null
	pip-compile > /dev/null
	git --no-pager diff requirements.txt

sync-deps:
	pip install -r requirements.txt
	pip install -r etc/dev-requirements.txt
	pip install -e .

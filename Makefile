.PHONY: develop test pep8 pylama clean docs tox jslint

# The source directory
SRC=abilian
# The package name
PKG=abilian

# On a 4 core laptop, 2 is optimal
NCPU=2

# pytest-sugar seems to be incompatible with pytest-xdist
PYTEST_MULTI=-n $(NCPU) -p no:sugar

all: test


#
#
#
develop:
	@echo "--> Installing dependencies"
	pip install -U -e '.[dev]'
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


lint: lint-python

lint-python:
	@echo "--> Linting Python files"
	flake8 $(SRC)
	@echo ""

test-readme:
	rst-lint README.rst

#
# Various Checkers
#
pep8:
	pep8 -r $(SRC)

pep8-stats:
	pep8 -r --statistics -qq $(SRC) | sort -nr

pytest-pep8:
	py.test --pep8 -m pep8 $(SRC) tests

pytest-flake:
	py.test --flakes -m flakes $(SRC) tests

flake8:
	flake8 $(SRC)

pylama:
	pylama $(SRC)

pylint:
	pylint --rcfile=etc/pylintrc $(SRC)

js-lint:
	npm run lint --silent

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
	find . -name "*.pyc" | xargs rm -f
	find . -name __pycache__ | xargs rm -rf
	find . -name abilian.db | xargs rm -f
	rm -rf *.egg-info *.egg .coverage
	rm -rf whoosh tests/whoosh tests/integration/whoosh
	rm -rf docs/_build docs/cache docs/tmp
	rm -rf $(SRC)/static/gen
	rm -rf dist build
	rm -rf htmlcov coverage.xml
	rm -rf docs/_build
	rm -f junit-py27.xml

tidy: clean
	rm -rf .tox .dox .travis-solo

update-pot:
	# _n => ngettext, _l => lazy_gettext
	python setup.py extract_messages update_catalog compile_catalog

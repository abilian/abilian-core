.PHONY: test pep8 pylama clean docs tox

# The source director
SRC=abilian
# The package name
PKG=abilian
# Number of CPU (or less)
NCPU=2


all: test doc

#
# testing & checking
#
test:
	py.test -n $(NCPU) --tb=short $(PKG) tests

test-with-coverage:
	py.test -n $(NCPU) --cov $(PKG) --cov-config etc/coverage.rc \
	  --cov-report term-missing $(PKG) tests

tox:
	tox

#
# Various Checkers
#
pep8:
	pep8 -r $(SRC)

pep8-stats:
	pep8 -r --statistics -qq $(SRC) | sort -nr

pytest-pep8:
	py.test --pep8 -m pep8 $(SRC) tests

flake8:
	flake8 $(SRC)

pylama:
	pylama $(SRC)

pylint:
	pylint --rcfile=etc/pylint.rc $(SRC)

check-docs:
	sphinx-build -W -b html docs/ docs/_build/html

#
# Everything else
#
install:
	python setup.py install

doc: doc-html doc-pdf

doc-html:
	sphinx-build -b html docs/ docs/_build/html

doc-pdf:
	sphinx-build -b latex docs/ docs/_build/latex
	make -C docs/_build/latex all-pdf

clean:
	find . -name "*.pyc" | xargs rm -f
	find . -name abilian.db | xargs rm -f
	rm -f maxid.data
	rm -rf data tests/data tests/integration/data
	rm -rf tmp tests/tmp tests/integration/tmp
	rm -rf cache tests/cache tests/integration/cache
	rm -rf *.egg-info *.egg .coverage
	rm -rf whoosh tests/whoosh tests/integration/whoosh
	rm -rf docs/_build docs/cache docs/tmp
	rm -rf $(SRC)/static/gen
	rm -rf dist build
	rm -rf htmlcov
	rm -rf docs/_build
	rm -f junit-py27.xml

tidy: clean
	rm -rf .tox .travis-solo

update-pot:
	# _n => ngettext, _l => lazy_gettext
	python setup.py extract_messages update_catalog compile_catalog

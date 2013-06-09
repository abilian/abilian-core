.PHONY: test pep8 pylama clean docs tox

# The source director
SRC=abilian
# The package name
PKG=abilian

# Additional parameters
PEP8IGNORE=E111,E121,E201,E225,E501


all: test doc

#
# testing & checking
#
test:
	py.test -x $(PKG) tests

test-with-coverage:
	py.test --cov $(PKG) --cov-config etc/coverage.rc \
	  --cov-report term-missing $(PKG) tests

tox:
	tox

pep8:
	pep8 -r --ignore $(PEP8IGNORE) *.py $(SRC) tests

pylama:
	pylama -o etc/pylama.ini

check-docs:
	sphinx-build -W -b html docs/ docs/_build/html

#
# Everything else
#
install:
	python setup.py install

doc:
	python setup.py build_sphinx

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

tidy: clean
	rm -rf .tox

update-pot:
	# _n => ngettext, _l => lazy_gettext
	pybabel extract -F etc/babel.cfg -k "_n:1,2" -k "_l" -o messages.pot "${SRC}"
	pybabel update -i messages.pot -d $(SRC)/translations
	pybabel compile -d $(SRC)/translations

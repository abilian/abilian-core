.PHONY: test unit full-test pep8 clean docs

SRC=yaka
PEP8IGNORE=E111,E121,E201,E225,E501

all: test doc

#
# testing & checking
#
test:
	python -m nose.core -v tests/unit
	python -m nose.core -v tests/integration

unit:
	python -m nose.core -v tests/unit

test-with-coverage:
	python -m nose.core --with-coverage --cover-erase \
	   	--cover-package=$(SRC) tests

test-with-profile:
	python -m nose.core --with-profile tests

unit-with-coverage:
	python -m nose.core --with-coverage --cover-erase \
	   	--cover-package=$(SRC) tests/unit

unit-with-profile:
	python -m nose.core --with-profile tests/unit

full-test:
	tox -e py27

pep8:
	pep8 -r --ignore $(PEP8IGNORE) *.py $(SRC) tests

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
	find . -name yaka.db | xargs rm -f
	rm -f maxid.data
	rm -rf data tests/data tests/integration/data
	rm -rf tmp tests/tmp tests/integration/tmp
	rm -rf cache tests/cache tests/integration/cache
	rm -rf *.egg-info *.egg .coverage
	rm -rf whoosh tests/whoosh tests/integration/whoosh
	rm -rf docs/_build docs/cache docs/tmp
	rm -rf $(SRC)/static/gen
	rm -rf dist build

tidy: clean
	rm -rf .tox

update-pot:
	pybabel extract -F babel.cfg -o messages.pot .
	pybabel update -i messages.pot -d $(SRC)/translations
	pybabel compile -d $(SRC)/translations


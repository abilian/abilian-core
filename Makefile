.PHONY: test unit full-test pep8 clean

#
# testing
#
test:
	python -m nose.core -v tests/unit
	python -m nose.core -v tests/integration

unit:
	python -m nose.core -v tests/unit

test-with-coverage:
	python -m nose.core --with-coverage --cover-erase \
	   	--cover-package=yaka tests

test-with-profile:
	python -m nose.core --with-profile tests

unit-with-coverage:
	python -m nose.core --with-coverage --cover-erase \
	   	--cover-package=yaka tests/unit

unit-with-profile:
	python -m nose.core --with-profile tests/unit

#
# Everything else
#
install:
	python setup.py install

full-test:
	tox -e py27

pep8:
	pep8 -r --ignore E111,E225,E501 *.py yaka tests

clean:
	find . -name "*.pyc" | xargs rm -f
	find . -name yaka.db | xargs rm -f
	rm -f maxid.data
	rm -rf data tests/data tests/integration/data
	rm -rf tmp tests/tmp tests/integration/tmp
	rm -rf cache tests/cache tests/integration/cache
	rm -rf *.egg-info *.egg .coverage
	rm -rf whoosh tests/whoosh tests/integration/whoosh
	rm -rf doc/_build
	rm -rf yaka/static/gen
	rm -rf dist build

tidy: clean
	rm -rf .tox

update-pot:
	pybabel extract -F babel.cfg -o messages.pot .
	pybabel update -i messages.pot -d yaka/translations
	pybabel compile -d yaka/translations


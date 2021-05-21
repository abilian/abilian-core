.PHONY: all develop test lint clean doc format

# The package name
PKG=abilian

all: test lint

#
# Setup
#
develop: install-deps activate-pre-commit configure-git

install-deps:
	@echo "--> Installing dependencies"
	pip install -U pip setuptools wheel
	poetry install
	yarn

activate-pre-commit:
	@echo "--> Activating pre-commit hook"
	pre-commit install

configure-git:
	@echo "--> Configuring git"
	git config branch.autosetuprebase always


#
# testing & checking
#
test-all: test test-readme

test:
	@echo "--> Running Python tests"
	pytest --ff -x -p no:randomly
	@echo ""

test-randomly:
	@echo "--> Running Python tests in random order"
	pytest
	@echo ""

test-with-coverage:
	@echo "--> Running Python tests"
	pytest --cov $(PKG)
	@echo ""

test-with-typeguard:
	@echo "--> Running Python tests with typeguard"
	pytest --typeguard-packages=abilian
	@echo ""

vagrant-tests:
	vagrant up
	vagrant ssh -c /vagrant/deploy/vagrant_test.sh


#
# Various Checkers
#
lint: lint-py lint-js lint-rst lint-doc

lint-ci: lint

lint-all: lint lint-mypy lint-bandit

lint-py:
	@echo "--> Linting Python files /w flake8"
	flake8 src tests
	@echo ""

lint-mypy:
	@echo "--> Typechecking Python files w/ mypy"
	mypy src tests
	@echo ""

lint-py3k:
	@echo "--> Checking Python 3 compatibility"
	pylint --py3k -j3 src tests
	@echo ""

lint-travis:
	@echo "--> Linting .travis.yml files"
	travis lint --no-interactive
	@echo ""

lint-js:
	@echo "--> Linting JS files"
	yarn run eslint src/abilian/web/resources/js/
	@echo ""

lint-less:
	@echo "--> Linting LESS files"
	yarn run stylelint src/abilian/web/resources/less/
	@echo ""

lint-rst:
	@echo "--> Linting .rst files"
	rst-lint *.rst
	@echo ""

lint-doc:
	@echo "--> Linting doc"
	#sphinx-build -W -b dummy docs/ docs/_build/
	sphinx-build -b dummy docs/ docs/_build/
	@echo ""

lint-bandit:
	@echo "--> Linting python w/ Bandit"
	bandit -s B101 `find src -name '*.py' | grep -v test`
	@echo ""


#
# Formatting
#
format: format-py format-js format-less

format-py:
	docformatter -i -r src
	black src demo tests *.py
	isort src abilian demo tests *.py

format-js:
	yarn run prettier --write src/abilian/web/resources/js

format-less:
	yarn run prettier --write --tab-width 2 src/abilian/web/resources/less/*.less


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
	find . -type f -name *.pyc -delete
	find . -type d -name __pycache__ -delete
	rm -rf *.egg-info *.egg .coverage .eggs .cache .mypy_cache .pyre \
		.pytest_cache .pytest .DS_Store  docs/_build docs/cache docs/tmp \
		dist build pip-wheel-metadata junit-*.xml htmlcov coverage.xml \
		npm-debug.log yarn-error.log

tidy: clean
	rm -rf .tox .nox .dox .travis-solo
	rm -rf node_modules
	rm -rf instance

update-pot:
	# _n => ngettext, _l => lazy_gettext
	python setup.py extract_messages update_catalog compile_catalog

publish: clean
	git push --tags
	poetry build
	twine upload dist/*

update-deps:
	pip install -U pip setuptools wheel
	poetry update
	poetry export -o etc/requirements.txt
	@echo "Warning: dephell must be installed via pipx"
	dephell deps convert --from=pyproject.toml --to=setup.py
	black setup.py
	yarn upgrade -s --no-progress

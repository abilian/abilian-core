# -*- coding: utf-8 -*-

import sys
import setuptools
from setuptools.command.test import test as TestCommand
from setup_util import parse_requirements, parse_dependency_links


install_requires = parse_requirements([u'requirements.txt'])
dependency_links = parse_dependency_links([u'requirements.txt'])

tests_require = [
  "pytest",
  "pytest-xdist",
  "mock",
  "nose",
]

dev_requires = tests_require + [
  # To build docs
  "Sphinx",
  "sphinx-rtd-theme",
  # For coverage
  "coverage",
  "coveralls",
  "pytest-cov",
  "cov-core",
  # Static code analysis
  "pylama",
]


def get_long_description():
  description = open("README.rst").read()
  description += "\n\n" + open("CHANGES.rst").read()
  return description


class PyTest(TestCommand):
  def finalize_options(self):
    TestCommand.finalize_options(self)
    self.test_args = []
    self.test_suite = True

  def run_tests(self):
    # import here, cause outside the eggs aren't loaded
    import pytest

    errno = pytest.main(self.test_args)
    sys.exit(errno)


setuptools.setup(
  # Metadata
  name='abilian-core',
  version='0.2.1.dev0',
  url='http://docs.abilian.com/',
  license='LGPL',
  author='Abilian SAS',
  author_email='contact@abilian.com',
  description='A framework for social business (aka Enterprise 2.0) applications, based on Flask and SQLAlchemy',
  long_description=get_long_description(),
  platforms='any',
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Framework :: Flask',
  ],

  # Data
  packages=['abilian'],
  include_package_data=True,
  zip_safe=False,
  cmdclass={'test': PyTest},

  # Requirements & dependencies
  install_requires=install_requires,
  tests_require=tests_require,
  dependency_links=dependency_links,
  extras_require={
    'tests': tests_require,
    'dev': dev_requires,
  },
)

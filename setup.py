# -*- coding: utf-8 -*-

import os
import setuptools
from setup_util import parse_requirements, parse_dependency_links

# Should be deps-frozen.txt
requirements = parse_requirements([u'etc/deps.txt'])
dependency_links = parse_dependency_links([u'etc/deps.txt'])


def get_long_description():
  """
  Hack to provide a ``.rst`` description to PyPI even when the ``README`` is
  actually written using Markdown.
  """

  if os.path.exists("README.rst"):
    return open("README.rst").read()
  elif os.path.exists("README.md"):
    rst = os.popen("pandoc -r markdown -w rst -o - README.md").read()
    if rst:
      return rst
    else:
      return open("README.md").read()
  elif os.path.exists("README.txt"):
    return open("README.txt").read()
  else:
    return None


setuptools.setup(
  name='abilian-core',
  version='0.1.1.dev0',
  url='http://docs.abilian.com/',
  license='LGPL',
  author='Abilian SAS',
  author_email='contact@abilian.com',
  description='A framework for social business applications, based on Flask and SQLAlchemy',
  long_description=get_long_description(),
  packages=['abilian'],
  platforms='any',
  setup_requires=['setuptools-git'],
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    ],
  # These args are setuptools specifically
  install_requires=requirements,
  dependency_links=dependency_links,
  include_package_data=True,
  zip_safe=False,
)

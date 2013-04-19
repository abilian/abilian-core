# -*- coding: utf-8 -*-

import setuptools
import setup_util as deps

requires = deps.parse_requirements([u'deps.txt'])
depend_links = deps.parse_dependency_links([u'deps.txt'])

def get_long_description():
  import os

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
  name='Abilian Core',
  version='0.1dev',
  url='http://www.abilian.com/',
  license='LGPL',
  author='Stefane Fermigier',
  author_email='sf@fermigier.com',
  description='Base framework for E2.0 applications',
  long_description=get_long_description(),
  packages=['abilian'],
  platforms='any',
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    ],
  # These args are setuptools specifically
  install_requires=requires,
  dependency_links=depend_links,
  include_package_data=True,
  zip_safe=False,
)

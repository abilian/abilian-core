# -*- coding: utf-8 -*-

from setuptools import setup


def get_deps():
  import re

  deps_raw = [ line.strip() for line in open("deps.txt")]
  deps = []
  for dep in deps_raw:
    if not dep or dep.startswith("#"):
      continue
    m = re.search("#egg=(.*)", dep)
    if m:
      dep = m.group(1)
    deps.append(dep)
  return deps

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


metadata = dict(
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
  # These args are setuptools specific
  install_requires=get_deps(),
  include_package_data=True,
  zip_safe=False,
)

setup(**metadata)

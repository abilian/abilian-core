# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

deps = [ line.strip()
         for line in open("deps.txt")
         if line and not line.startswith("#") ]

metadata = dict(
  name='Yaka Core',
  version='0.1dev',
  url='http://www.yaka.biz/',
  license='LGPL',
  author='Stefane Fermigier',
  author_email='sf@fermigier.com',
  description='Enterprise social networking meets CRM',
  long_description=__doc__,
  packages=['yaka'],
  platforms='any',
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    ],
  # Unsupported by distutils.
  #install_requires=deps,
  #include_package_data=True,
  #zip_safe=False,
)

setup(**metadata)

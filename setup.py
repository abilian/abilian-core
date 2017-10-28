# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, unicode_literals

from distutils.command.build import build as _build

import setuptools
from pip.download import PipSession
from pip.req import parse_requirements
from setuptools.command.develop import develop as _develop
from setuptools.command.sdist import sdist as _sdist

session = PipSession()
_install_requires = parse_requirements(
    'requirements.in',
    session=session,
)
install_requires = [str(ir.req) for ir in _install_requires]

_dev_requires = parse_requirements(
    'etc/dev-requirements.txt',
    session=session,
)
dev_requires = [str(ir.req) for ir in _dev_requires]

LONG_DESCRIPTION = open('README.rst').read()


class Build(_build):
    sub_commands = [('compile_catalog', None)] + _build.sub_commands


class Sdist(_sdist):
    sub_commands = [('compile_catalog', None)] + _sdist.sub_commands


class Develop(_develop):

    def run(self):
        _develop.run(self)
        self.run_command('compile_catalog')


setuptools.setup(
    name='abilian-core',
    use_scm_version=True,
    url='https://github.com/abilian/abilian-core',
    license='LGPL',
    author='Abilian SAS',
    author_email='contact@abilian.com',
    description=(
        'A framework for enterprise applications '
        '(CRM, ERP, collaboration...), based on Flask and SQLAlchemy'
    ),
    long_description=LONG_DESCRIPTION,
    packages=['abilian'],
    zip_safe=False,
    platforms='any',
    setup_requires=['babel', 'setuptools-git', 'setuptools_scm>=1.5.5'],
    install_requires=install_requires,
    extras_require={
        'testing': dev_requires,
        'dev': dev_requires,
    },
    include_package_data=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Flask',
    ],
    cmdclass={
        'build': Build,
        'sdist': Sdist,
        'develop': Develop,
    },
)

Installing Abilian Core
=======================

Prerequisites (native dependencies)
-----------------------------------

Tu run Abilian, you will need to install the following native packages on
you operating system:

- The Python language itself. Currently only Python 2.7 is supported, we plan
  to support Python 3.3 as well in the future.

- The ``pip`` package manager for Python.

- Developpment tools, such as ``gcc``.

- Some librairies and tools for image manipulation and transformation:
  ``libpng``, ``libjpeg`` and ``ImageMagick``.

- More document transformation tools: ``poppler-utils``, ``unoconv``,
  ``LibreOffice``.


Install Python dependencies
---------------------------

Once you have installed your native packages, you can start installing your
Python dependencies using ``pip``.

First, you should create a virtualenv (ex: ``mkvirtualenv abilian``,
assuming you have installed ``mkvirtualenv``).

Then run ``pip install -r deps.txt``.


Testing
-------

Once you have installed the dependencies, you can run the test suite to check
that nothing is missing::

    make test

There's also a `tox <http://pypi.python.org/pypi/tox>`_ configuration that
runs the whole test suite in an isolated environment. You can run it simply
by calling::

    tox

from your shell.

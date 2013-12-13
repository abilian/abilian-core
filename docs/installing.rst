Installing Abilian Core
=======================

If you are a Python web developer (which is the primary target for this
project), you probably already know about:

-  Python 2.7
-  Virtualenv
-  Pip

So, after you have created and activated a virtualenv for the project,
just run::

    pip install -r etc/deps.txt

or::

    python setup.py develop

To use some features of the library, namely document and images
transformation, you will need to install the additional native packages,
using our operating system's package management tools (``dpkg``,
``yum``, ``brew``...):

-  A few image manipulation libraries (``libpng``, ``libjpeg``)
-  The ``poppler-utils``, ``unoconv``, ``LibreOffice``, ``ImageMagick``
   utilities


Testing
-------

Abilian Core come with a full unit and integration testing suite. You
can run it with ``make test`` (once your virtualenv has been activated).

Alternatively, you can use ``tox`` to run the full test suite in an
isolated environment.

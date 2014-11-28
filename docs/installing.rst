Installing Abilian Core
=======================

If you are a Python web developer (which is the primary target for this
project), you probably already know about:

-  Python 2.7
-  Virtualenv
-  Pip

So, after you have created and activated a virtualenv for the project,
just run::

    pip install -r requirements.txt

To use some features of the library, namely document and images
transformation, you will need to install the additional native packages,
using our operating system's package management tools (``dpkg``,
``yum``, ``brew``...):

-  A few image manipulation libraries (``libpng``, ``libjpeg``)

-  The ``poppler-utils``, ``unoconv``, ``LibreOffice``, ``ImageMagick``
   utilities

- `lesscss <http://lesscss.org/>`_:

  For Debian/Ubuntu the package is named `node-less`. If your distribution's
  package is too old, you may install `node-js <http://nodejs.org/>`_ >= 0.10 and
  `npm <https://www.npmjs.org/>`_. Lesscss can then be installed with:

  .. code-block:: sh

      $ sudo npm install -g less
      npm http GET https://registry.npmjs.org/less
      npm http 200 https://registry.npmjs.org/less
      ...
      $ which lessc
      /usr/bin/lessc


Testing
-------

Abilian Core come with a full unit and integration testing suite. You
can run it with ``make test`` (once your virtualenv has been activated).

Alternatively, you can use ``tox`` to run the full test suite in an
isolated environment.

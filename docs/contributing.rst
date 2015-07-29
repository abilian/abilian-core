Constributing to Abilian Core
=============================

Project on GitHub
-----------------

The project is hosted on GitHub at: `<https://github.com/abilian/abilian-core>`_.

Participation in the development of Abilian is welcome and encouraged, through
the various mechanisms provided by GitHub:

- `Bug reports and feature requests <https://github.com/abilian/abilian-core/issues>`_.

- `Forks and pull requests <https://github.com/abilian/abilian-core/pulls>`_.


License and copyright
---------------------

The Abilian code is copyrighted by Abilian SAS, a french company.

It is licenced under the LGPL (Lesser General Public License), which means
you can reuse the product as a library

If you contribute to Abilian, we ask you to transfer your rights to your
contribution to us.

In case you have questions, you're welcome to contact us.


Build Status
------------

We give a great deal of care to the quality of our software, and try to use
all the tools that are at our disposal to make it rock-solid.

This includes:

- Having an exhaustive test suite.

- Using continuous integration (CI) servers to run the test suite on every commit.

- Running tests.

- Using our products daily.

You can check the build status:

- `Our own Jenkins server <http://jenkins.abilian.com/job/Abilian-Core/>`_

- `On drone.io <https://drone.io/github.com/abilian/abilian-core/latest>`_

- `On Travis CI <https://travis-ci.org/abilian/abilian-core>`_

You can also check the coverage reports:

- `On coveralls.io <https://coveralls.io/r/abilian/abilian-core?branch=master>`_

Releasing
---------

We're now using `setuptools_scm` to manage version numbers.

It comes with some conventions on its own when it comes to releasing.

Here's what you should do to make a new release on PyPI:

1. Check that the CHANGES.rst file is correct.

2. Commit.

3. Tag (ex: `git tag 0.3.0`), using numbers that are consistent with semantic
   versionning.

4. Run `python setup.py sdist upload`.


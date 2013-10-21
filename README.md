About
=====

Abilian core framework and services. Based on Flask, SQLAlchemy and other
libraries.

Used at [Abilian](http://www.abilian.com/) to develop social business
applications such as Abilian CRM and Abilian SBE.


Current Build Status
--------------------

The official CI server for the project is our own Jenkins:
[![Build Status (Jenkins)](http://jenkins.abilian.com/job/Abilian-Core/badge/icon)](http://jenkins.abilian.com/job/Abilian-Core/)

Additional CI badges:
[![Build Status (drone.io)](https://drone.io/github.com/abilian/abilian-core/status.png)](https://drone.io/github.com/abilian/abilian-core/latest)
[![Build Status (travis)](https://api.travis-ci.org/abilian/abilian-core.png)](https://travis-ci.org/abilian/abilian-core)
[![Coverage Status](https://coveralls.io/repos/abilian/abilian-core/badge.png?branch=master)](https://coveralls.io/r/abilian/abilian-core?branch=master)


Install
=======

Prerequisites (native dependencies)
-----------------------------------

- Python 2.7
- A few image manipulation libraries (`libpng`, `libjpeg`...)
- `poppler-utils`, `unoconv`, `LibreOffice`, `ImageMagick`.
- `pip`

Look at the `fabfile.py` for the exact list.

Python modules
--------------

Create and activate a virtualenv (ex: `mkvirtualenv abilian`, assuming you have
mkvirtualenv installed).

Then run `pip install -r etc/deps.txt` or `python setup.py develop`.


Testing
=======

Short test
----------

Make sure all the dependencies are installed (cf. above), then
run `make test`.

With coverage
-------------

Run `make test-with-coverage`.

Full test suite
---------------

Install [tox](http://pypi.python.org/pypi/tox). Run `tox`.

On a VM
-------

1. Install [vagrant](http://vagrantup.com/) and Fabric (`pip install fabric`).

2. Download a box:

        vagrant box add precise64 http://files.vagrantup.com/precise64.box

3. TODO.
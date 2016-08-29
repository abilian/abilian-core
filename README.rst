About
=====

.. image:: http://jenkins.abilian.com/job/Abilian-Core/badge/icon
   :target: http://jenkins.abilian.com/job/Abilian-Core/

.. image:: https://api.travis-ci.org/abilian/abilian-core.png
   :target: https://travis-ci.org/abilian/abilian-core

.. image:: https://coveralls.io/repos/abilian/abilian-core/badge.png?branch=master
   :target: https://coveralls.io/r/abilian/abilian-core?branch=master

.. image:: https://pypip.in/download/abilian-core/badge.svg?period=month
    :target: https://pypi.python.org/pypi/abilian-core/
    :alt: Downloads


Abilian Core is an enterprise application development platform based on the `Flask micro-framework <http://flask.pocoo.org/>`_, the `SQLAlchemy ORM <http://www.sqlalchemy.org/>`_, good intentions and best practices (for some value of "best").

The full documentation is available on http://docs.abilian.com/.


Goals & principles
------------------

- Development must be easy and fun (some some definition of "easy" and "fun", of course)

- The less code (and configuration) we write, the better

- Leverage existing reputable open source libraries and frameworks, such as SQLAlchemy and Flask

- It must lower errors, bugs, project's time to deliver. It's intended to be a rapid application development tool

- It must promote best practices in software development, specially Test-Driven Development (as advocated by the `GOOS book <http://www.amazon.com/gp/product/0321503627/>`_)


Features
--------

Here's a short list of features that you may find appealing in Abilian:

Infrastructure
^^^^^^^^^^^^^^

-  Plugin framework

-  Asynchronous tasks (using `Celery <http://www.celeryproject.org/>`_)

-  Security model and service

Domain model and services
^^^^^^^^^^^^^^^^^^^^^^^^^

-  Persistent domain object model, based on SQLAlchemy

-  Audit

Content management and services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

-  Simple file-based content repository

-  Indexing service

-  Document preview and transformation

Social
^^^^^^

-  Users, groups and social graph (followers)

-  Activity streams

User Interface and API
^^^^^^^^^^^^^^^^^^^^^^

-  Forms (based on `WTForms <http://wtforms.simplecodes.com/>`_)

-  CRUD (Create, Retrieve, Edit/Update, Remove) interface from domain
   models

-  Labels and descriptions for each field

-  Various web utilities: view decorators, class-based views, Jinja2
   filters, etc.

-  A default UI based on `Bootstrap 3 <http://getbootstrap.com/>`_ and
   several carefully selected jQuery plugins such as
   `Select2 <http://ivaynberg.github.io/select2/>`_

-  REST and AJAX API helpers

-  i18n: support for multi-language via Babel, with multiple translation
   dictionaries

Management and admin
^^^^^^^^^^^^^^^^^^^^

-  Initial settings wizard

-  Admin and user settings framework

-  System monitoring (using `Sentry <https://getsentry.com/welcome/>`_)

Current status
--------------

Abilian Core is currently alpha (or even pre-alpha) software, in terms
of API stability.

It is currently used in several applications that have been developped
by `Abilian <http://www.abilian.com/>`_ over the last two years:

-  [Abilian SBE (Social Business
   Engine)](https://github.com/abilian/abilian-sbe) - an enterprise 2.0 (social
   collaboration) platform

-  Abilian EMS (Event Management System)

-  Abilian CRM (Customer / Contact / Community Relationship Management
   System)

-  Abilian Le MOOC - a MOOC prototype

-  Abilian CMS - a Web CMS

In other words, Abilian Core is the foundation for a small, but growing,
family of business-critical applications that our customers intend us to
support in the coming years.

So while Abilian Core APIs, object model and even architecture, may (and
most probably will) change due to various refactorings that are expected
as we can't be expected to ship perfect software on the firt release, we
also intend to treat it as a valuable business asset and keep
maintaining and improving it in the foreseeable future.

Roadmap & getting involved
--------------------------

If you need help or for general discussions about the Abilian Platform, we
recommend joing the `Abilian Users
<https://groups.google.com/forum/#!forum/abilian-users>`_ forum on Google
Groups.

We have a `roadmap on Pivotal
Tracker <https://www.pivotaltracker.com/s/projects/878951>`_ that we use
internally to manage our iterative delivery process.

For features and bug requests (or is it the other way around?), we
recommend that you use the `GitHub issue
tracker <https://github.com/abilian/abilian-core/issues>`_.


Install
=======

If you are a Python web developer (which is the primary target for this
project), you probably already know about:

-  Python 2.7
-  Virtualenv
-  Pip

So, after you have created and activated a virtualenv for the project,
just run::

    pip install -r requirements.txt

If you need to work on the project, first install the requirements as above,
then type:

    pip install -e '.[dev]'


To use some features of the library, namely document and images
transformation, you will need to install the additional native packages,
using our operating system's package management tools (``dpkg``,
``yum``, ``brew``...):

-  A few image manipulation libraries (``libpng``, ``libjpeg``)
-  The ``poppler-utils``, ``unoconv``, ``LibreOffice``, ``ImageMagick``
   utilities

Look at the ``fabfile.py`` for the exact list.


Testing
=======

Abilian Core come with a full unit and integration testing suite. You
can run it with ``make test`` (once your virtualenv has been activated and
all required dependencies have been installed, see above).

Alternatively, you can use ``tox`` to run the full test suite in an
isolated environment.


Licence
=======

Abilian Core is licensed under the LGPL.


Credits
=======

Abilian Core has been created by the development team at Abilian
(currently: Stefane and Bertrand), with financial support from our
wonderful customers, and R&D fundings from the French Government, the
Paris Region and the European Union.

We are also specially grateful to:

-  `Armin Ronacher <http://lucumr.pocoo.org/>`_ for his work on Flask.
-  `Michael Bayer <http://techspot.zzzeek.org/>`_ for his work on
   SQLAlchemy.
-  Everyone who has been involved with and produced open source software
   for the Flask ecosystem (Kiran Jonnalagadda and the
   `HasGeek <https://hasgeek.com/>`_ team, Max Countryman, Matt Wright,
   Matt Good, Thomas Johansson, James Crasta, and probably many others).
-  The creators of Django, Pylons, TurboGears, Pyramid and Zope, for
   even more inspiration.
-  The whole Python community.

Links
=====

- `Discussion list (Google Groups) <https://groups.google.com/forum/#!forum/abilian-users>`_
- `Documentation <http://docs.abilian.com/>`_
- `GitHub repository <https://github.com/abilian/abilian-core>`_
- `Corporate support <http://www.abilian.com>`_

About Abilian Core
==================

Abilian Core is an enterprise application development platform based on the `Flask micro-framework <http://flask.pocoo.org/>`_, the `SQLAlchemy ORM <http://www.sqlalchemy.org/>`_, good intentions and best practices (for some value of "best").

The full documentation is available on http://docs.abilian.com/.


Goals & principles
------------------

- Development must be easy and fun (some some definition of "easy" and "fun", of course)

- The less code (and configuration) we write, the better

- Leverage existing reputable open source libraries and frameworks, such as SQLAlchemy and Flask

- It must lower errors, bugs, project's time to deliver. It's intended to be a rapid application development tool

- It must promote best practices in software development, specially Test-Driven Development (as advocated by the `GOOS book <http://www.amazon.com/gp/product/0321503627/ref=as_li_qf_sp_asin_tl?ie=UTF8&camp=1789&creative=9325&creativeASIN=0321503627&linkCode=as2&tag=fermigiercom-20>`_)


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

-  Domain object model, based on SQLAlchemy

-  Audit

Content management and services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

-  i8n: support for multi-language via Babel, with multiple translation
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

-  Abilian SBE (Social Business Engine) - an enterprise 2.0 (social
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

We have a `roadmap on Pivotal
Tracker <https://www.pivotaltracker.com/s/projects/878951>`_ that we use
internally to manage our iterative delivery process.

For features and bug requests (or is it the other way around?), we
recommend that you use the `GitHub issue
tracker <https://github.com/abilian/abilian-core/issues>`_.

Licence
-------

Abilian Core is licensed under the LGPL.

Credits
-------

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


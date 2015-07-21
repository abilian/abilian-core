Changelog for Abilian Core
==========================

0.4.2 (unreleased)
~~~~~~~~~~~~~~~~~

TODO


0.4.1 (2015-07-21)
------------------

Bugfixes / cleanup
~~~~~~~~~~~~~~~~~~

- permission: no-op when service not running
- JS fixes
- CSS fixes
- https://github.com/mitsuhiko/flask/issues/1135


0.4.0 (2015-07-15)
------------------

Features
~~~~~~~~

- Object level permissions
- Add "meta" properties to entities
- Attached files to entities
- More flexible search filters
- Avatars
- Tag engine (alpha)

Fixes / cleanup
~~~~~~~~~~~~~~~

- JS: Upate ravenjs, requirejs, bootbox, jquery, scribe


0.3.6 (2015-05-27)
------------------

Fixes
~~~~~

- security service: fix exception on has_role()


0.3.5 (2015-05-27)
------------------

Features
~~~~~~~~

- default user avatar is now a circle with their last name initial (#12)
- add PRIVATE_SITE, app, blueprint and endpoint access controller registration
- Better handling of CSRF failures
- add dynamic row widget js
- js: add datatable advanced search

Fixes
~~~~~

- CSS (Bootstrap) fixes
- Permissions fixes

Updates
-------

- Updated Bootstrap to 3.3.4
- Updated flask-login to 0.2.11
- Updated Sentry JS code to 1.1.18


0.3.4 (2015-04-14)
------------------

- updated Select2 to 3.5.2
- enhanced fields and widgets
- set default SQLALCHEMY_POOL_RECYCLE to 30 minutes
- Users admin panel: fix roles not set; fix all assignable roles not listed; fix
  cannot set password during user creation.


0.3.3 (2015-03-31)
------------------

Features
~~~~~~~~

- Use ravenjs to monitor JS errors with Sentry
- Vocabularies


0.3.2 (2014-12-23)
------------------

- Minor bugfixes


0.3.1 (2014-12-23)
------------------

- Minor bugfixes


0.3.0 (2014-12-23)
------------------

Features
~~~~~~~~

- Added a virus scanner.
- Changed the WYSIWYG editor to Scribe.
- Vocabularies

API changes
~~~~~~~~~~~

- Deprecated the @templated decorator (will be removed in 0.4.0).

Building, tests
~~~~~~~~~~~~~~~

- Build: Use pbr to simplify setup.py.
- Dependencies: moved deps to ./requirements.txt + cleanup / update.
- Testing: Tox and Travis config updates.
- Testing: Run tests under Vagrant.
- QA: Fixed many pyflakes warnings.


0.2.0 (2014-08-07)
------------------

- Too long to list.


0.1.4 (2014-03-27)
------------------

- refactored abilian.core.entities, abilian.core.subjects. New module
  abilian.core.models containing modules: base, subjects, owned.
- Fixed or cleaned up dependencies.
- Fixed setupwizard.
- added config value: BABEL_ACCEPT_LANGUAGES, to limit supported languages and
  change order during negociation
- Switched CSS to LESS.
- Updated to Bootstrap 3.1.1


0.1.3 (2014-02-03)
------------------

- Update some dependencies
- Added login/logout via JSON api
- Added 'createuser' command


0.1.2 (2014-01-11)
------------------

- added jinja extension to collect JS snippets during page generation and put
  them at end of document ("deferred")
- added basic javascript to prevent double submission
- Added Flask-Migrate


0.1.1 (2013-12-26)
------------------

- Redesigned indexing:

  * single whoosh index for all objects
  * search results page do not need anymore to fetch actual object from database
  * index security information, used for filtering search results
  * Added "reindex" shell command


0.1 (2013-12-13)
----------------

- Initial release.


Changelog for Abilian Core
==========================

v0.11.21 (2021-08-02)
---------------------

- Fix licence in package metadata.

v0.11.19 (2021-04-07)
---------------------

- Cut a new release to fix the docs.

v0.11.18 (2021-03-16)
---------------------

- Prevent upgrading to SQLAlchemy 1.4

v0.11.10 (2020-08-04)
---------------------
- Fix tests.
- Cleanup API.
- Use sentry sdk instead of raven.
- Cleanup.


v0.11.7 (2020-07-30)
--------------------
- Format.
- Docstrings.
- Fix/silent lint errors.
- Cosmit py3k.
- Format.
- Marketing.
- Modernize code.
- Prettify front-end.
- Use proper booleans.
- Ci: add nox tests.
- Ci: fix noxfile.
- Ci: refact tox config.
- Ci: use bionic for travis.


v0.11.6 (2019-12-29)
--------------------

Fix
~~~
- New flake8 warnings.

Other
~~~~~
- Ci: Github actions.
- Ci: travis / py38.
- Refactor: f-strings.


v0.11.4 (2019-09-12)
--------------------
- Typing + format.
- Py3k.
- Travis for 3.8 (not working)


v0.11.3 (2019-08-07)
--------------------

Fix
~~~
- Search wasn't really configurable.
- Fix bug on debug toolbar for signals.

Other
~~~~~
- Remove "pyre-fixme" comments.
- Small refactor (f-strings).
- Typing issues fixed.
- Fix for readthedocs.
- Fix doc (sphinx) issues.
- Fix tests.
- Type hints.
- Typing fixes.
- Fix settings.
- Cleanup imports.
- Py3k-ize settings. May break things.
- Fix typing (pyre) issues.
- Format.
- Annotate w/ type warnings.
- Refactor: use f-strings.
- Py3k: using pyupgrade.


v0.11.6 (2019-12-29)
--------------------

Fix
~~~
- New flake8 warnings.

Other
~~~~~
- Ci: Github actions.
- Ci: travis / py38.
- Refactor: f-strings.


v0.11.5 (2019-10-07)
--------------------
- Deps


v0.11.4 (2019-09-12)
--------------------
- Typing + format.
- Py3k.
- Travis for 3.8 (not working)


v0.11.3 (2019-08-07)
--------------------

Fix
~~~
- Search wasn't really configurable.

Other
~~~~~
- Annotate w/ type warnings.
- Cleanup imports.
- Fix bug on debug toolbar for signals.
- Fix doc (sphinx) issues.
- Fix for readthedocs.
- Fix settings.
- Fix tests.
- Fix typing (pyre) issues.
- Format.
- Py3k-ize settings. May break things.
- Py3k: using pyupgrade.
- Remove "pyre-fixme" comments.
- Small refactor (f-strings).
- Type hints.
- Typing issues fixed.


v0.11.2 (2019-06-28)
--------------------

- Add flake8-mypy.
- Add type annotations.
- Better variable naming.
- Class BlobQuery is not needed.
- Cleanup imports.
- Couple of typing fixes.
- Fix incomplete refactoring.
- Format + typing.
- Make more robust.
- Py3k.
- Refactor caching.
- Refactor conversion service.
- Refactor: extract variable.
- Set up CI with Azure Pipelines.
- Skip test when soffice not available.
- Typing.


v0.11.1 (2019-05-02)
--------------------
- A couple of typing fixes.
- Dont run flake8-mypy for now.


0.11.0 (2019-04-15)
--------------------

- Drop Python 2 support.
- Rewrite code to be Python 3 only.
- Various fixes.


0.10.34 (2019-01-17)
--------------------

- Simplify indexing control DSL: __indexation_params__ -> __index_to__.


0.10.34 (2019-01-17)
--------------------

- Simplify indexing control DSL: __indexation_params__ -> __index_to__.


0.10.32 (2019-01-02)
--------------------

- Switched dependency management to poetry
- Py3k migration and fixes.


0.10.29 (2018-12-26)
--------------------

- Cleanup, small fixes related to updated dependencies.

0.10.29 (2018-12-26)
--------------------

- Cleanup, small fixes related to updated dependencies.

0.10.20 (2018-07-19)
--------------------

- Clean up audit objects by removing null values on init

0.10.15 (2018-07-05)
--------------------

- Unpin pillow, small cleanups.

0.10.14 (2018-06-11)
--------------------

- pin wtforms because 2.2 breaks our tests

0.10.12 (2018-04-27)
--------------------

- Fix for Flask 1.0

0.10.11 (2018-04-15)
--------------------

- Fix install under pip 10

0.10.8 (2018-04-04)
-------------------

- Refactor pytest fixtures. API has changed.

0.10.3 (2018-02-22)
-------------------

- Cleanup JS

0.10.2 (2018-02-21)
-------------------

- Refactor tests (use pytest fixtures)
- Refactor Application class


0.10.2 (2018-02-15)
-------------------

- Fix Py3k compatibility.


0.10.0 (2018-02-12)
-------------------

Breaking changes:

- Removed deprecated plugin loader
- Renamed `is_support_attachments` to `supports_attachments`

Other:

- Refactoring tests to use pytest's function-based tests instead
  of unittest's class-based tests.


0.9.30 (2018-01-11)
-------------------

- Don't depend on psycopg2, so you can use your favorite driver
  (ex: pg8000).

0.9.19-0.9.29
-------------

- Cleanup
- Bug fixes
- Python 3 compatibility
- Dependencies updates

0.9.18 (2017-10-06)
-------------------

- Relax dependency constraint on Bleach to allow upgrade
  of other deps.

0.9.17 (2017-10-02)
-------------------

- Cleanup
- Fix some warnings.

0.9.16 (2017-09-08)
-------------------

- JS cleanup and linting
- Deps updates

0.9.15 (2017-09-04)
-------------------

- Revert some buggy JS "clean up".
- Deps updates

0.9.12 (2017-08-28)
-------------------

- Code clean up.

0.9.11 (2017-08-03)
-------------------

- Workaround bug in Babel related to Python 3.

0.9.10 (2017-08-02)
-------------------

- Cleanup and prepare for Python 3.

0.9.9 (2017-08-01)
------------------

- Cleanup and prepare for Python 3.
- Use headless libreoffce for conversion instead of unoconv.

0.9.3 (2017-07-03)
------------------

- Add "impersonate" admin panel.

0.9.3 (2017-06-30)
------------------

- Fix bug on `form_valid`

0.7.24 (2017-01-10)
-------------------

- Downgrade Ravenjs :(

0.7.21 (2017-01-09)
-------------------

- Ravenjs update
- Update deps

0.7.10 (2016-08-30)
-------------------

- Fix issue with raven-js logging


0.7.9 (2016-08-29)
------------------

- More robust reindex command.
- Pytest > 3.0 compat


0.7.8 (2016-08-04)
------------------

- Use `bcrypt` library instead of `py-bcrypt`.
- Work on Py3k compatibility (not done yet)
- Update dependencies.


0.7.7 (2016-07-13)
------------------

- Work on Py3k compatibility (not done yet)
- Remove unneeded dependencies.
- Update dependencies.
- Harder linting.

0.7.0 (2016-05-31)
------------------

- Made compatible with Flask 0.11, SQLAlchemy 1.0 and a few other recent
  releases.
- General cleanup.

0.6.5 (2016-05-10)
------------------

Workaround some regression by not generating less source map.

0.6.2 (2016-05-09)
------------------

- Fix import error.

0.6.1 (2016-05-09)
------------------

- Allow SQLAlchemy 0.9.x for now
- Allow application/x-pdf mime type.

0.6.0 (2016-04-29)
------------------

- Upgrade SQLAlchemy to 1.0+.
- Dump config in sysinfo admin panel

Cleanup:

- Upgrade deps
- Reformat code using Google style rule


0.5.3-0.5.6 (2016-03-17)
------------------------

Features:

- dynamic row widget options to add controls at the bottom (23 hours ago)<yvon>

Fixes:

- fix datatable optionalcriterion filter (2 days ago)<yvon>
- fix jquery datable jqmigrate warning (2 days ago)<yvon>
- fix search criterion outerjoin (6 days ago)<yvon>
- textsearch criterion mysterious onclause fix (9 days ago)<yvon>

Cleanup:

- Upgrade deps
- Reformat code using Google style rule

0.5.2 (2016-02-16)
------------------

- Fix IPv6 / GeoIP issue
- Improve debug toolbar
- Improve dashboard
- Celery: expire task before next run scheduled


0.5.1 (2016-01-29)
------------------

- add security debug panel: shows permissions and roles assignments
- faster query_with_permission()
- Fix: user administration could remove non-assignable roles
- Subforms (Form used in FormFields / ListFormFields / etc) can filter their
  fields according to permission passed to top Form.


0.5.0 (2015-11-20)
------------------

- Editable comments
- Upgrade SQLAlchemy to 0.9
- Admin: add Tag panels


0.4.5 (2015-10-15)
------------------

Improvements and updates
~~~~~~~~~~~~~~~~~~~~~~~~

- Breaking: minor schemas changes. Migrations needed for existing applications
- tags in 'default' namespace are indexed in document's text for full text
  search on tag label
- age filter has a new option to show full date when date is not today
- run command: add `--ssl` option
- admin: manage groups membership from user page
- updated requirements to ensure sane minimum versions
- Role based access control makes more permissions checks againts roles and less
  simple role check

Fixes
~~~~~

- fixes for celery workers
- fix: check user has role on object with global role
- fix: check user has roles through group membership


0.4.4 (2015-08-07)
------------------

Design / UI
~~~~~~~~~~~

- Navbar is now non-fluid.

Updates
~~~~~~~

- Upgrade Jinja to 2.8 and Babel to 2.0

Fixes
~~~~~

- Fixed image cropping.


0.4.3 (2015-07-29)
------------------

Another release because there was a version number issue with the previous
one.

0.4.2 (2015-07-29)
------------------

Bugfixes / cleanup
~~~~~~~~~~~~~~~~~~

- Replace Scribe by CKEditor for better IE compatibility.
- Smaller bug fixes and code cleanups

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
~~~~~~~

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

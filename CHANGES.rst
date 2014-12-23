Changelog for Abilian Core
==========================

0.3.1 (unreleased)
------------------

- Nothing changed yet.


0.3.0 (2014-12-23)
------------------

Features
^^^^^^^^

- Added a virus scanner.
- Changed the WYSIWYG editor to Scribe.
- Vocabularies

API changes
^^^^^^^^^^^

- Deprecated the @templated decorator (will be removed in 0.4.0).

Building, tests
^^^^^^^^^^^^^^^

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


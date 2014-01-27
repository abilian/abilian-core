Changelog for Abilian Core
==========================

0.1.3 (unreleased)
------------------

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


# import os
#
#
# class TestConfig:
#     """Base class config settings for test cases.
#
#     The environment variable :envvar:`SQLALCHEMY_DATABASE_URI` can be
#     set to easily test against different databases.
#     """
#
#     SITE_NAME = "Abilian Test"
#     SQLALCHEMY_DATABASE_URI = "sqlite://"
#     SERVER_NAME = "localhost.localdomain"  # needed for url_for with '_external=True'
#     SQLALCHEMY_ECHO = False
#     TESTING = True
#     SECRET_KEY = "SECRET"
#     CSRF_ENABLED = False
#     WTF_CSRF_ENABLED = False
#
#     # during tests let httpexceptions be raised
#     TRAP_HTTP_EXCEPTIONS = False
#     TRAP_BAD_REQUEST_ERRORS = True
#
#     CELERY_ALWAYS_EAGER = True  # run tasks locally, no async
#     CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
#
#     MAIL_SENDER = "test@testcase.app.tld"
#
#     BABEL_ACCEPT_LANGUAGES = ["en", "fr"]
#     BABEL_DEFAULT_LOCALE = "en"
#
#     # It's a good idea to test with a timezone that's not your system timezone
#     # nor UTC. It can reveal problem with date handling within app
#     # (rule is: all dates are manipulated in UTC, and shown in user timezone).
#     #
#     # For example this one is GMT+8 and has no DST (tests should pass any time
#     # in year).
#     # BABEL_DEFAULT_TIMEZONE = 'Asia/Hong_Kong'
#     BABEL_DEFAULT_TIMEZONE = "UTC"  # this is flask-babel default
#
#     def __init__(self):
#         db_uri = os.environ.get("SQLALCHEMY_DATABASE_URI")
#         if db_uri:
#             self.SQLALCHEMY_DATABASE_URI = db_uri

class TestConfig(object):
  DEBUG = True
  TESTING = True

  SQLALCHEMY_DATABASE_URI = "sqlite://"
  SQLALCHEMY_ECHO = False

  CSRF_ENABLED = False
  SECRET_KEY = "tototiti"
  SALT = "retwis"
  WHOOSH_BASE = "whoosh"

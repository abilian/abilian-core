# -*- coding: utf-8 -*-
import os


class TestConfig(object):
  DEBUG = False
  TESTING = True

  SQLALCHEMY_DATABASE_URI = "sqlite://"
  SQLALCHEMY_ECHO = False

  CELERY_ALWAYS_EAGER = True # run tasks locally, no async
  CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

  CSRF_ENABLED = False
  SECRET_KEY = "tototiti"
  SALT = "retwis"
  WHOOSH_BASE = "whoosh"

  def __init__(self):
    db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
    if db_uri:
      self.SQLALCHEMY_DATABASE_URI = db_uri

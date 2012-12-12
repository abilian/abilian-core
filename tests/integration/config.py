# -*- coding: utf-8 -*-
import os

class TestConfig(object):
  DEBUG = True
  TESTING = True

  SQLALCHEMY_DATABASE_URI = "sqlite://"
  SQLALCHEMY_ECHO = False

  CSRF_ENABLED = False
  SECRET_KEY = "tototiti"
  SALT = "retwis"
  WHOOSH_BASE = "whoosh"

  def __init__(self):
    db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
    if db_uri:
      self.SQLALCHEMY_DATABASE_URI = db_uri

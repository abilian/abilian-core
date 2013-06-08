"""Base stuff for testing.
"""

import subprocess
assert not 'twill' in subprocess.__file__

from flask.ext.testing import TestCase

from abilian.application import Application
from abilian.core.entities import db

__all__ = ['TestConfig', 'BaseTestCase']


class TestConfig(object):
  SQLALCHEMY_DATABASE_URI = "sqlite://"
  SQLALCHEMY_ECHO = False
  TESTING = True
  SECRET = ""


class BaseTestCase(TestCase):

  config_class = TestConfig
  application_class = Application

  def create_app(self):
    config = self.config_class()
    self.app = self.application_class(config)
    return self.app

  def setUp(self):
    self.app.create_db()
    self.session = db.session

  def tearDown(self):
    db.session.remove()
    db.drop_all()
    db.engine.dispose()

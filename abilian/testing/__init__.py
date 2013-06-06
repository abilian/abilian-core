"""Base stuff for testing.
"""

from flask.ext.testing import TestCase

from abilian.application import Application
from abilian.core.entities import db


class TestConfig(object):
  SQLALCHEMY_DATABASE_URI = "sqlite://"
  SQLALCHEMY_ECHO = False


class BaseTestCase(TestCase):

  config_class = TestConfig

  def create_app(self):
    config = self.config_class()
    self.app = Application(config)
    return self.app

  def setUp(self):
    self.app.create_db()
    self.session = db.session

  def tearDown(self):
    db.session.remove()
    db.drop_all()
    db.engine.dispose()

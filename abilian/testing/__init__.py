"""Base stuff for testing.
"""

import subprocess
assert not 'twill' in subprocess.__file__

from flask.ext.testing import TestCase

from abilian.application import Application


__all__ = ['TestConfig', 'BaseTestCase']


class TestConfig(object):
  SQLALCHEMY_DATABASE_URI = "sqlite://"
  SQLALCHEMY_ECHO = False
  TESTING = True
  SECRET_KEY = "SECRET"


class BaseTestCase(TestCase):
  config_class = TestConfig
  application_class = Application

  def create_app(self):
    config = self.config_class()
    self.app = self.application_class(config)
    return self.app

  def setUp(self):
    self.app.create_db()
    self.session = self.db.session

  def tearDown(self):
    self.db.session.remove()
    self.db.drop_all()
    self.db.engine.dispose()

  @property
  def db(self):
    return self.app.extensions['sqlalchemy'].db

  # Useful for debugging
  def dump_routes(self):
    rules = list(self.app.url_map.iter_rules())
    rules.sort(key=lambda x: x.rule)
    for rule in rules:
      print rule, rule.methods, rule.endpoint

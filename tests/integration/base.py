"""
Base TestCase for integration tests.
"""

# Don't remove
import fix_path

import os
import uuid
from flask.ext.testing import TestCase

from yaka.core.extensions import db

from . import util
from .config import TestConfig
from .application import Application


BASEDIR = os.path.dirname(__file__)

class IntegrationTestCase(TestCase):

  init_data = False
  no_login = False

  def create_app(self):
    config = TestConfig()
    config.WHOOSH_BASE = os.path.join(BASEDIR, "whoosh", str(uuid.uuid4()))
    config.NO_LOGIN = self.no_login
    self.app = Application(config)

    return self.app

  def setUp(self):
    db.create_all()
    self.session = db.session
    if self.init_data:
      util.init_data()

  def tearDown(self):
    db.session.remove()
    db.drop_all()

  def assert_302(self, response):
    self.assert_status(response, 302)

  def assert_204(self, response):
    self.assert_status(response, 204)

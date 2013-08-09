"""
Base TestCase for integration tests.
"""

# Don't remove
import fix_path

import os
import uuid
import shutil
from flask.ext.testing import TestCase

from abilian.core.extensions import db
from abilian.application import Application

from .config import TestConfig


BASEDIR = os.path.dirname(__file__)


class IntegrationTestCase(TestCase):

  no_login = False

  def create_app(self):
    config = TestConfig()
    config.WHOOSH_BASE = os.path.join(BASEDIR, "whoosh", str(uuid.uuid4()))
    config.NO_LOGIN = self.no_login
    self.app = Application(config=config)

    return self.app

  def setUp(self):
    self.app.create_db()
    self.session = db.session

  def tearDown(self):
    db.session.remove()
    db.drop_all()
    # clear whoosh
    whoosh_base = self.app.config['WHOOSH_BASE']
    if os.path.isdir(whoosh_base):
      shutil.rmtree(whoosh_base)

  def assert_302(self, response):
    self.assert_status(response, 302)

  def assert_204(self, response):
    self.assert_status(response, 204)

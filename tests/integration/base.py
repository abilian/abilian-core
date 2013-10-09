"""
Base TestCase for integration tests.
"""

# Don't remove
import fix_path

import os

from abilian.testing import BaseTestCase

from .config import TestConfig

BASEDIR = os.path.dirname(__file__)

class IntegrationTestCase(BaseTestCase):
  config_class = TestConfig
  no_login = False

  def assert_302(self, response):
    self.assert_status(response, 302)

  def assert_204(self, response):
    self.assert_status(response, 204)

# coding=utf-8
"""
Base TestCase for integration tests.
"""
from __future__ import absolute_import, print_function, unicode_literals

from abilian.testing import BaseTestCase

from .config import TestConfig


class IntegrationTestCase(BaseTestCase):
    config_class = TestConfig
    no_login = False

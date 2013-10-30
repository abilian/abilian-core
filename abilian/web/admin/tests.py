# coding=utf-8
"""
"""
from __future__ import absolute_import

from flask import url_for
from abilian.testing import BaseTestCase


class TestViews(BaseTestCase):

  def get_setup_config(self):
    """ Called before creating application class
    """
    config = BaseTestCase.get_setup_config(self)
    config.NO_LOGIN = True
    return config

  def setUp(self):
    BaseTestCase.setUp(self)
    self.app.services['security'].start()

  def test_home(self):
    response = self.client.get(url_for("admin.dashboard"))
    self.assert_200(response)

  def test_sysinfo(self):
    response = self.client.get(url_for("admin.sysinfo"))
    self.assert_200(response)

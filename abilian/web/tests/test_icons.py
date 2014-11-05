# coding=utf-8
"""
"""
from __future__ import absolute_import

from abilian.web.action import Glyphicon, FAIcon, StaticIcon
from abilian.testing import BaseTestCase


class TestIcons(BaseTestCase):
  """
  test abilian.web.actions icons
  """
  def test_glyphicons(self):
    icon = Glyphicon('ok')
    self.assertEquals(
      icon.__html__(),
      u'<i class="glyphicon glyphicon-ok"></i>')

  def test_faicons(self):
    icon = FAIcon('check')
    self.assertEquals(
      icon.__html__(),
      u'<i class="fa fa-check"></i>')

  def test_staticicon(self):
    icon = StaticIcon('path/to/icon.png')
    self.assertEquals(
      icon.__html__(),
      u'<img src="/static/path/to/icon.png" width="12" height="12" />')

    icon = StaticIcon('path/to/icon.png', width=14)
    self.assertEquals(
      icon.__html__(),
      u'<img src="/static/path/to/icon.png" width="14" height="12" />')

    icon = StaticIcon('path/to/icon.png', height=14)
    self.assertEquals(
      icon.__html__(),
      u'<img src="/static/path/to/icon.png" width="12" height="14" />')

    icon = StaticIcon('path/to/icon.png', size=14)
    self.assertEquals(
      icon.__html__(),
      u'<img src="/static/path/to/icon.png" width="14" height="14" />')

    icon = StaticIcon('path/to/icon.png', size=14, css='avatar')
    self.assertEquals(
        icon.__html__(),
        u'<img class="avatar" src="/static/path/to/icon.png" width="14" '
        u'height="14" />')

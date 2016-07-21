# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from abilian.testing import BaseTestCase
from abilian.web.action import FAIcon, Glyphicon, StaticIcon


class TestIcons(BaseTestCase):
    """
    test abilian.web.actions icons
    """

    def test_glyphicons(self):
        icon = Glyphicon('ok')
        self.assertEqual(icon.__html__(),
                         u'<i class="glyphicon glyphicon-ok"></i>')

    def test_faicons(self):
        icon = FAIcon('check')
        self.assertEqual(icon.__html__(), u'<i class="fa fa-check"></i>')

    def test_staticicon(self):
        icon = StaticIcon('path/to/icon.png')
        self.assertEqual(
            icon.__html__(),
            u'<img src="/static/path/to/icon.png" width="12" height="12" />')

        icon = StaticIcon('path/to/icon.png', width=14)
        self.assertEqual(
            icon.__html__(),
            u'<img src="/static/path/to/icon.png" width="14" height="12" />')

        icon = StaticIcon('path/to/icon.png', height=14)
        self.assertEqual(
            icon.__html__(),
            u'<img src="/static/path/to/icon.png" width="12" height="14" />')

        icon = StaticIcon('path/to/icon.png', size=14)
        self.assertEqual(
            icon.__html__(),
            u'<img src="/static/path/to/icon.png" width="14" height="14" />')

        icon = StaticIcon('path/to/icon.png', size=14, css='avatar')
        self.assertEqual(
            icon.__html__(),
            u'<img class="avatar" src="/static/path/to/icon.png" width="14" '
            u'height="14" />')

# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask import url_for

from abilian.testing import BaseTestCase


class TestViews(BaseTestCase):

    def get_setup_config(self):
        """Called before creating application class."""
        config = BaseTestCase.get_setup_config(self)
        config.NO_LOGIN = True
        return config

    def setUp(self):
        BaseTestCase.setUp(self)
        self.app.services['security'].start()

    def test_home(self):
        response = self.client.get(url_for("admin.dashboard"))
        assert response.status_code == 200

    def test_sysinfo(self):
        response = self.client.get(url_for("admin.sysinfo"))
        assert response.status_code == 200

    def test_login_session(self):
        response = self.client.get(url_for("admin.login_sessions"))
        assert response.status_code == 200

    def test_audit(self):
        response = self.client.get(url_for("admin.audit"))
        assert response.status_code == 200

    def test_settings(self):
        response = self.client.get(url_for("admin.settings"))
        assert response.status_code == 200

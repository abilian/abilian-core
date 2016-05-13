# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import current_app
from flask_login import AnonymousUserMixin, LoginManager


class AnonymousUser(AnonymousUserMixin):

    def has_role(self, role):
        return current_app.services['security'].has_role(self, role)

    @property
    def groups(self):
        return set()


login_manager = LoginManager()
login_manager.anonymous_user = AnonymousUser

# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask_login import AnonymousUserMixin, LoginManager


class AnonymousUser(AnonymousUserMixin):

    def has_role(self, role):
        from abilian.services import get_service

        security = get_service("security")
        return security.has_role(self, role)

    @property
    def groups(self):
        return set()


login_manager = LoginManager()
login_manager.anonymous_user = AnonymousUser

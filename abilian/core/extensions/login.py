# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division

from flask import current_app
from flask_login import LoginManager, AnonymousUserMixin


class AnonymousUser(AnonymousUserMixin):

  def has_role(self, role):
    return current_app.services['security'].has_role(self, role)

  @property
  def groups(self):
    return set()


login_manager = LoginManager()
login_manager.anonymous_user = AnonymousUser

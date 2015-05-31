# coding=utf-8
"""
"""
from __future__ import absolute_import

from flask import Blueprint as BaseBlueprint
from abilian.services.security import Role, Anonymous


def allow_anonymous(user, roles, **kwargs):
  return True


def allow_access_for_roles(roles):
  """
  Access control helper to check user's roles against a list of valid roles
  """
  if isinstance(roles, Role):
    roles = (roles,)
  valid_roles = frozenset(roles)

  if Anonymous in valid_roles:
    return allow_anonymous

  def check_role(user, roles, **kwargs):
    # valid if roles intersection it not empty
    return bool(roles & valid_roles)

  return check_role


class Blueprint(BaseBlueprint):
  """
  An enhanced :class:`flask.blueprints.Blueprint` with access control helpers.
  """
  def __init__(self, name, import_name, allowed_roles=None, **kwargs):
    """
    :param roles: role or list of roles required to access any view in this
        blueprint.
    """
    BaseBlueprint.__init__(self, name, import_name, **kwargs)

    if allowed_roles is not None:
      if isinstance(allowed_roles, (str, unicode)):
        allowed_roles = Role(allowed_roles)

      if isinstance(allowed_roles, Role):
        allowed_roles = (allowed_roles,)
    else:
      allowed_roles = ()

    if allowed_roles:
      self.record_once(lambda s:
                       s.app.add_access_controller(
                         self.name,
                         allow_access_for_roles(allowed_roles))
      )

  def allow_any(self, func):
    pass

# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask import Blueprint as BaseBlueprint
from flask import current_app
from six import string_types

from abilian.services.security import Anonymous, Role


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
        security = current_app.services['security']
        return security.has_role(user, valid_roles)

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
            if isinstance(allowed_roles, string_types):
                allowed_roles = Role(allowed_roles)

            if isinstance(allowed_roles, Role):
                allowed_roles = (allowed_roles,)
        else:
            allowed_roles = ()

        if allowed_roles:
            self.record_once(
                lambda s: s.app.add_access_controller(self.name, allow_access_for_roles(allowed_roles)))

    def allow_any(self, func):
        pass

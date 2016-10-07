# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, unicode_literals

from flask import current_app
from flask_debugtoolbar.panels import DebugPanel

from abilian.core.entities import Entity
from abilian.core.models.subjects import Group
from abilian.i18n import _
from abilian.web.action import actions

from .models import Anonymous


class SecurityInfoDebugPanel(DebugPanel):
    """
    A panel to display current roles and permissions for "current" object.
    """
    name = 'SecurityInfo'

    @property
    def current_obj(self):
        return actions.context.get('object')

    @property
    def has_content(self):
        obj = self.current_obj
        return (obj is not None and isinstance(obj, Entity) and
                obj.id is not None)

    def nav_title(self):
        return _('Security Info')

    def nav_subtitle(self):
        """Subtitle showing until title in toolbar"""
        obj = self.current_obj
        if not obj:
            return _(u'No current object')

        try:
            return u'{}(id={})'.format(obj.__class__.__name__, obj.id)
        except:
            return u''

    def title(self):
        return self.nav_title()

    def url(self):
        return ''

    def content(self):
        obj = self.current_obj
        svc = current_app.services['security']
        context = self.context.copy()

        context['permissions'] = svc.get_permissions_assignments(obj=obj)
        context['roles'] = roles = dict()

        for principal, r in svc.get_role_assignements(obj=obj):
            if r not in roles:
                roles[r] = dict(anonymous=False, users=set(), groups=set())

            info = roles[r]
            if principal is Anonymous:
                info['anonymous'] = True
            elif isinstance(principal, Group):
                info['groups'].add(principal)
            else:
                info['users'].add(principal)

        for r in roles:
            info = roles[r]
            info['groups'] = [
                u'{g} (id={g.id})'.format(g=g)
                for g in sorted(
                    info['groups'], key=lambda g: g.name)
            ]
            users = sorted(
                info['users'],
                key=lambda u: (u.last_name.lower(), u.first_name.lower()))
            info['users'] = [
                u'{u} (id={u.id}, email="{u.email}")'.format(u=u) for u in users
            ]

        jinja_env = current_app.jinja_env
        jinja_env.filters.update(self.jinja_env.filters)
        template = jinja_env.get_or_select_template(
            'debug_panels/security_info_panel.html')

        return template.render(context)

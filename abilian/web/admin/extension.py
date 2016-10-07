# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import logging

from flask import Blueprint, g
from flask.helpers import _endpoint_from_view_func
from flask_login import current_user
from werkzeug.exceptions import Forbidden
from werkzeug.utils import import_string

from abilian.i18n import _l
from abilian.services.security import Admin as AdminRole
from abilian.services.security import security
from abilian.web.action import Endpoint, actions
from abilian.web.nav import BreadcrumbItem, NavGroup, NavItem

from .panel import AdminPanel

logger = logging.getLogger(__name__)

_BP_PREFIX = 'admin'


class Admin(object):
    """
    Flask extension for an admin interface with pluggable admin panels.

    Note: this is quite different that a Django-style admin interface.
    """

    def __init__(self, *panels, **kwargs):
        self.app = None
        self.panels = []
        self._panels_endpoints = {}
        self.nav_paths = {}
        self.breadcrumb_items = {}
        self.setup_blueprint()

        self.nav_root = NavGroup(
            'admin',
            'root',
            title=_l(u'Admin'),
            endpoint=None,
            condition=lambda context: (not current_user.is_anonymous and security.has_role(current_user, AdminRole))
        )

        for panel in panels:
            self.register_panel(panel)

        app = kwargs.pop('app', None)
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        panels = app.config.get('ADMIN_PANELS', ())

        # resolve fully qualified name into an AdminPanel object
        for fqn in panels:
            panel_class = import_string(fqn, silent=True)
            if panel_class is None:
                logger.warning('Could not import panel: "%s"', fqn)
                continue
            if not issubclass(panel_class, AdminPanel):
                logger.error('"%s" is not a %s.AdminPanel, skipping', fqn,
                             AdminPanel.__module__)
                continue

            self.register_panel(panel_class())
            logger.debug('Registered panel "%s"', fqn)

        if not self.panels:

            @self.blueprint.route('', endpoint='no_panel')
            def no_panels_view():
                return "No panels registered"

            self.nav_root.endpoint = 'admin.no_panel'
        else:
            self.nav_root.endpoint = self.nav_root.items[0].endpoint

        self.root_breadcrumb_item = BreadcrumbItem(
            label=self.nav_root.title,
            url=self.nav_root.endpoint,)

        app.register_blueprint(self.blueprint)

        with app.app_context():
            actions.register(self.nav_root, *self.nav_root.items)

        self.app = app
        app.extensions['admin'] = self

    def register_panel(self, panel):
        if self.app:
            raise ValueError(
                'Extension already initialized for app, cannot add more'
                ' panel')

        self.panels.append(panel)
        panel.admin = self
        rule = "/" + panel.id
        endpoint = nav_id = panel.id
        abs_endpoint = 'admin.{}'.format(endpoint)

        if hasattr(panel, 'get'):
            self.blueprint.add_url_rule(rule, endpoint, panel.get)
            self._panels_endpoints[abs_endpoint] = panel
        if hasattr(panel, 'post'):
            post_endpoint = endpoint + "_post"
            self.blueprint.add_url_rule(
                rule, post_endpoint, panel.post, methods=['POST'])
            self._panels_endpoints['admin.' + post_endpoint] = panel

        panel.install_additional_rules(
            self.get_panel_url_rule_adder(panel, rule, endpoint))

        nav = NavItem(
            'admin:panel',
            nav_id,
            title=panel.label,
            icon=panel.icon,
            divider=False,
            endpoint=abs_endpoint)
        self.nav_root.append(nav)
        self.nav_paths[abs_endpoint] = nav.path
        self.breadcrumb_items[panel] = BreadcrumbItem(
            label=panel.label, icon=panel.icon, url=Endpoint(abs_endpoint))

    def get_panel_url_rule_adder(self, panel, base_url, base_endpoint):
        extension = self

        def add_url_rule(rule, endpoint=None, view_func=None, *args, **kwargs):
            if not rule:
                # '' is already used for panel get/post
                raise ValueError('Invalid additional url rule: {}'.format(
                    repr(rule)))

            if endpoint is None:
                endpoint = _endpoint_from_view_func(view_func)

            if not endpoint.startswith(base_endpoint):
                endpoint = base_endpoint + '_' + endpoint

            extension._panels_endpoints['admin.' + endpoint] = panel
            return self.blueprint.add_url_rule(
                base_url + rule,
                endpoint=endpoint,
                view_func=view_func,
                *args,
                **kwargs)

        return add_url_rule

    def setup_blueprint(self):
        self.blueprint = Blueprint(
            "admin",
            __name__,
            template_folder='templates',
            url_prefix='/' + _BP_PREFIX)

        self.blueprint.url_value_preprocessor(self.build_breadcrumbs)
        self.blueprint.url_value_preprocessor(self.panel_preprocess_value)

        @self.blueprint.before_request
        def check_security():
            user = current_user._get_current_object()
            if not security.has_role(user, "admin"):
                raise Forbidden()

    def panel_preprocess_value(self, endpoint, view_args):
        panel = self._panels_endpoints.get(endpoint)
        if panel is not None:
            panel.url_value_preprocess(endpoint, view_args)

    def build_breadcrumbs(self, endpoint, view_args):
        g.breadcrumb.append(self.root_breadcrumb_item)
        g.nav['active'] = self.nav_paths.get(endpoint, self.nav_root.path)
        panel = self._panels_endpoints.get(endpoint)
        if panel:
            endpoint_bc = self.breadcrumb_items.get(panel)
        if endpoint_bc:
            g.breadcrumb.append(endpoint_bc)

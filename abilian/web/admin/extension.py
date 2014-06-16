# coding=utf-8
"""
"""
from __future__ import absolute_import
import logging

from werkzeug.utils import import_string
from flask import Blueprint, abort, url_for, request, g
from flask.ext.babel import lazy_gettext as _l
from flask.ext.login import current_user
from abilian.services.security import security
from abilian.web.action import actions
from abilian.web.nav import NavGroup, NavItem, BreadcrumbItem, Endpoint

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
    self.breadcrumb_items = {}
    self.setup_blueprint()

    self.nav_root = NavGroup(
      'admin', 'root', title=_l(u'Admin'),
      endpoint=None,
      condition=lambda context: (not current_user.is_anonymous()
                                 and security.has_role(current_user, "admin"))
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
        logger.error('"%s" is not a %s.AdminPanel, skipping', fqn, AdminPanel.__module__)
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
      url=Endpoint(self.nav_root.endpoint[0], **self.nav_root.endpoint[1])
    )

    app.register_blueprint(self.blueprint)

    with app.app_context():
      actions.register(self.nav_root, *self.nav_root.items)

    self.app = app
    app.extensions['admin'] = self

  def register_panel(self, panel):
    if self.app:
      raise ValueError("Extension already initialized for app, cannot add more panel")

    self.panels.append(panel)

    panel.admin = self
    rule = "/" + panel.id
    endpoint = nav_id = panel.id
    abs_endpoint = 'admin.{}'.format(endpoint)

    if hasattr(panel, 'get'):
      self.blueprint.add_url_rule(rule, endpoint, panel.get)
    if hasattr(panel, 'post'):
      endpoint += "_post"
      self.blueprint.add_url_rule(rule, endpoint, panel.post, methods=['POST'])

    nav = NavItem('admin:panel', nav_id,
                  title=panel.label, icon=panel.icon, divider=False,
                  endpoint=abs_endpoint)
    self.nav_root.append(nav)
    self.breadcrumb_items[abs_endpoint] = BreadcrumbItem(
      label=panel.label,
      icon=panel.icon,
      url=Endpoint(abs_endpoint)
    )

  def setup_blueprint(self):
    self.blueprint = Blueprint("admin", __name__,
                               template_folder='templates',
                               url_prefix='/' + _BP_PREFIX)

    self.blueprint.url_value_preprocessor(self.build_breadcrumbs)

    @self.blueprint.before_request
    def check_security():
      user = current_user._get_current_object()
      if not security.has_role(user, "admin"):
        abort(403)

    @self.blueprint.context_processor
    def inject_menu():
      menu = []
      for panel in self.panels:
        endpoint = 'admin.' + panel.id
        active = endpoint == request.endpoint
        entry = {'endpoint': endpoint,
                 'label': panel.label,
                 'url': url_for(endpoint),
                 'active': active}
        menu.append(entry)
      return dict(menu=menu)

  def build_breadcrumbs(self, endpoint, view_args):
    g.breadcrumb.append(self.root_breadcrumb_item)
    endpoint_bc = self.breadcrumb_items.get(endpoint)
    if endpoint_bc:
      g.breadcrumb.append(endpoint_bc)

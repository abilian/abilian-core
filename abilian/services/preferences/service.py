"""User preference service. (Currently brainstorming the API).

Notes:

- Preferences are user-specific
- For global setting, there should be a SettingService
"""

from flask import Blueprint, url_for, request, redirect, abort
from flask.ext.login import current_user
from flask.ext.babel import lazy_gettext as _l
from abilian.core.extensions import db
from abilian.web.nav import NavItem
from abilian.services.auth.service import user_menu

from .models import UserPreference

user_menu.items.insert(
  0,
  NavItem('user', 'preferences', title=_l(u'Preferences'), icon='cog',
          url=lambda context: request.url_root + 'preferences',
          condition=lambda context: not current_user.is_anonymous()
  ))

class PreferenceService(object):
  """
  Flask extension for a user-level preference service, with pluggable
  panels.
  """

  def __init__(self, *panels, **kwargs):
    self.app = None
    self.panels = []
    self.setup_blueprint()
    for panel in panels:
      self.register_panel(panel)

    app = kwargs.pop('app', None)
    if app:
      self.init_app(app)

  def init_app(self, app):
    self.app = app
    app.extensions['preferences'] = self
    app.register_blueprint(self.blueprint)

  def get_preferences(self, user=None):
    """Returns a string->value dictionnary representing the given user
    preferences.

    If no user is provided, the current user is used instead.
    """
    if user is None:
      user = current_user
    return { pref.key: pref.value for pref in user.preferences }

  def set_preferences(self, user=None, **kwargs):
    """Sets preferences from keyword arguments.
    """
    if user is None:
      user = current_user

    d = { pref.key: pref for pref in user.preferences }
    for k, v in kwargs.items():
      if k in d:
        d[k].value = v
      else:
        d[k] = UserPreference(user=user, key=k, value=v)
        db.session.add(d[k])

  def clear_preferences(self, user=None):
    """Clears the user preferences.
    """
    if user is None:
      user = current_user

    #  don't delete UserPreference 1 by 1 with session.delete, else
    #  user.preferences is not updated until commit() (not flush()). see
    #  http://docs.sqlalchemy.org/en/rel_0_7/orm/session.html#deleting-from-collections
    user.preferences = []

  def register_panel(self, panel):
    if self.app:
      raise ValueError("Extension already initialized for app, cannot add more panel")

    self.panels.append(panel)
    panel.preferences = self
    rule = "/" + getattr(panel, 'path', panel.id)
    endpoint = panel.id
    if hasattr(panel, 'get'):
      self.blueprint.add_url_rule(rule, endpoint, panel.get)
    if hasattr(panel, 'post'):
      endpoint += "_post"
      self.blueprint.add_url_rule(rule, endpoint, panel.post, methods=['POST'])

  def setup_blueprint(self):
    self.blueprint = Blueprint("preferences", __name__,
                               template_folder='templates',
                               url_prefix="/preferences")

    # @self.blueprint.before_request
    # def check_security():
    #   user = current_user._get_current_object()
    #   if security.has_role(user, "admin"):
    #     return
    #   else:
    #     abort(403)

    @self.blueprint.context_processor
    def inject_menu():
      menu = []
      for panel in self.panels:
        endpoint = 'preferences.' + panel.id
        active = endpoint == request.endpoint
        entry = {'endpoint': endpoint,
                 'label': panel.label,
                 'url': url_for(endpoint),
                 'active': active}
        menu.append(entry)
      return dict(menu=menu)

    @self.blueprint.route("/")
    def index():
      """Index redirects to the first accessible panel."""

      # Work around unit test failure. FIXME.
      if current_user.is_anonymous():
        return "OK"

      for panel in self.panels:
        if panel.is_accessible():
          return redirect(url_for("preferences." + panel.id))
      else:
        # Should not happen.
        abort(500)


preferences = PreferenceService()

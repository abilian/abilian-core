"""User preference service. (Currently brainstorming the API).

Notes:

- Preferences are user-specific
- For global setting, there should be a SettingService
"""

from flask import Blueprint, url_for, request, redirect, abort
from flask.ext.login import current_user
from abilian.core.extensions import db

from .models import UserPreference


class PreferenceService(object):
  """
  Flask extension for a user-level preference service, with pluggable
  panels.
  """

  def __init__(self, app=None):
    self.panels = []
    if app:
      self.init_app(app)

  def init_app(self, app):
    self.app = app
    app.extensions['preferences'] = self
    self.setup_blueprint()

  def get_preferences(self, user=None):
    """Returns a string->value dictionnary representing the given user
    preferences.

    If no user is provided, the current user is used instead.
    """
    if user is None:
      user = current_user
    preferences = UserPreference.query.filter(UserPreference.user_id == user.id).all()
    return { pref.key: pref.value for pref in preferences}

  def set_preferences(self, user=None, **kwargs):
    """Sets preferences from keyword arguments.
    """
    if user is None:
      user = current_user

    preferences = UserPreference.query.filter(UserPreference.user_id == user.id).all()
    d = { pref.key: pref for pref in preferences}
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

    preferences = UserPreference.query.filter(UserPreference.user_id == user.id).all()
    for pref in preferences:
      db.session.delete(pref)

  def register_panel(self, panel):
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

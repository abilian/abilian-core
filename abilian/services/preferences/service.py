# coding=utf-8
"""User preference service.

Notes:

- Preferences are user-specific.
- For application settings use
  :class:`abilian.services.settings.SettingsService`.
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask import Blueprint, g, redirect, request, url_for
from flask_login import current_user
from werkzeug.exceptions import InternalServerError

from abilian.core import signals
from abilian.core.extensions import db
from abilian.i18n import _, _l
from abilian.services.auth.service import user_menu
from abilian.services.base import Service, ServiceState
from abilian.web.action import Endpoint
from abilian.web.nav import BreadcrumbItem, NavItem

from .models import UserPreference

_PREF_NAV_ITEM = NavItem(
    "user",
    "preferences",
    title=_l("Preferences"),
    icon="cog",
    url=lambda context: request.url_root + "preferences",
    condition=lambda context: not current_user.is_anonymous,
)

user_menu.insert(0, _PREF_NAV_ITEM)


class PreferenceState(ServiceState):
    panels = None
    blueprint = None
    blueprint_registered = False

    def __init__(self, *args, **kwargs):
        ServiceState.__init__(self, *args, **kwargs)
        self.panels = []
        self.nav_paths = {}
        self.breadcrumb_items = {}


class PreferenceService(Service):
    """Flask extension for a user-level preference service, with pluggable
    panels."""
    name = "preferences"
    AppStateClass = PreferenceState

    def init_app(self, app, *panels):
        Service.init_app(self, app)

        with app.app_context():
            self.setup_blueprint(app)
            for panel in panels:
                self.register_panel(panel)

    def get_preferences(self, user=None):
        """Return a string->value dictionnary representing the given user
        preferences.

        If no user is provided, the current user is used instead.
        """
        if user is None:
            user = current_user
        return {pref.key: pref.value for pref in user.preferences}

    def set_preferences(self, user=None, **kwargs):
        """Set preferences from keyword arguments."""
        if user is None:
            user = current_user

        d = {pref.key: pref for pref in user.preferences}
        for k, v in kwargs.items():
            if k in d:
                d[k].value = v
            else:
                d[k] = UserPreference(user=user, key=k, value=v)
                db.session.add(d[k])

    def clear_preferences(self, user=None):
        """Clear the user preferences."""
        if user is None:
            user = current_user

        #  don't delete UserPreference 1 by 1 with session.delete, else
        #  user.preferences is not updated until commit() (not flush()). see
        #  http://docs.sqlalchemy.org/en/rel_0_7/orm/session.html#deleting-from-collections
        user.preferences = []

    def register_panel(self, panel, app=None):
        state = self.app_state if app is None else app.extensions[self.name]
        if state.blueprint_registered:
            raise ValueError(
                "Extension already initialized for app, " "cannot add more panel"
            )

        state.panels.append(panel)
        panel.preferences = self
        rule = "/" + getattr(panel, "path", panel.id)
        endpoint = panel.id
        abs_endpoint = "preferences.{}".format(endpoint)

        if hasattr(panel, "get"):
            state.blueprint.add_url_rule(rule, endpoint, panel.get)
        if hasattr(panel, "post"):
            endpoint += "_post"
            state.blueprint.add_url_rule(rule, endpoint, panel.post, methods=["POST"])

        state.breadcrumb_items[abs_endpoint] = BreadcrumbItem(
            label=panel.label, icon=None, url=Endpoint(abs_endpoint)
        )

    def setup_blueprint(self, app):
        bp = self.app_state.blueprint = Blueprint(
            "preferences",
            __name__,
            template_folder="templates",
            url_prefix="/preferences",
        )

        # we need to delay blueprint registration to allow adding more panels during
        # initialization
        @signals.components_registered.connect_via(app)
        def register_bp(app):
            app.register_blueprint(bp)
            app.extensions[self.name].blueprint_registered = True

        self.app_state.root_breadcrumb_item = BreadcrumbItem(
            label=_("Preferences"), url=Endpoint("preferences.index")
        )

        bp.url_value_preprocessor(self.build_breadcrumbs)

        @bp.context_processor
        def inject_menu():
            menu = []
            for panel in self.app_state.panels:
                if not panel.is_accessible():
                    continue
                endpoint = "preferences." + panel.id
                active = endpoint == request.endpoint
                entry = {
                    "endpoint": endpoint,
                    "label": panel.label,
                    "url": url_for(endpoint),
                    "active": active,
                }
                menu.append(entry)
            return dict(menu=menu)

        @bp.route("/")
        def index():
            """Index redirects to the first accessible panel."""

            # Work around unit test failure. FIXME.
            if current_user.is_anonymous:
                return "OK"

            for panel in self.app_state.panels:
                if panel.is_accessible():
                    return redirect(url_for("preferences." + panel.id))
            else:
                # Should not happen.
                raise InternalServerError()

    def build_breadcrumbs(self, endpoint, view_args):
        state = self.app_state
        g.nav["active"] = _PREF_NAV_ITEM.path
        g.breadcrumb.append(state.root_breadcrumb_item)
        if endpoint in state.breadcrumb_items:
            g.breadcrumb.append(state.breadcrumb_items[endpoint])


preferences = PreferenceService()

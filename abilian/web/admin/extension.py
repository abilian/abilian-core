""""""
import logging
from typing import Any, Callable, Dict, List, Optional

from flask import Blueprint, Flask, g
from flask.helpers import _endpoint_from_view_func
from flask_login import current_user
from werkzeug.exceptions import Forbidden
from werkzeug.utils import import_string

from abilian.core.util import unwrap
from abilian.i18n import _l
from abilian.services.security import Admin as AdminRole
from abilian.services.security import security
from abilian.web.action import Endpoint, actions
from abilian.web.nav import BreadcrumbItem, NavGroup, NavItem

from .panel import AdminPanel

logger = logging.getLogger(__name__)

_BP_PREFIX = "admin"


class Admin:
    """Flask extension for an admin interface with pluggable admin panels.

    Note: this is quite different that a Django-style admin interface.
    """

    def __init__(self, *panels: Any, **kwargs: Any) -> None:
        self.app = None
        self.panels: List[AdminPanel] = []
        self._panels_endpoints: Dict[str, AdminPanel] = {}
        self.nav_paths: Dict[str, str] = {}
        self.breadcrumb_items: Dict[AdminPanel, BreadcrumbItem] = {}
        self.setup_blueprint()

        def condition(context: Dict[str, bool]) -> bool:
            return not current_user.is_anonymous and security.has_role(
                current_user, AdminRole
            )

        self.nav_root = NavGroup(
            "admin", "root", title=_l("Admin"), endpoint=None, condition=condition
        )

        for panel in panels:
            self.register_panel(panel)

        app = kwargs.pop("app", None)
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        panels = app.config.get("ADMIN_PANELS", ())

        # resolve fully qualified name into an AdminPanel object
        for fqn in panels:
            panel_class = import_string(fqn, silent=True)
            if panel_class is None:
                logger.warning('Could not import panel: "%s"', fqn)
                continue
            if not issubclass(panel_class, AdminPanel):
                logger.error(
                    '"%s" is not a %s.AdminPanel, skipping', fqn, AdminPanel.__module__
                )
                continue

            self.register_panel(panel_class())
            logger.debug('Registered panel "%s"', fqn)

        if not self.panels:

            @self.blueprint.route("", endpoint="no_panel")
            def no_panels_view():
                return "No panels registered"

            self.nav_root.endpoint = "admin.no_panel"
        else:
            self.nav_root.endpoint = self.nav_root.items[0].endpoint

        self.root_breadcrumb_item = BreadcrumbItem(
            label=self.nav_root.title, url=self.nav_root.endpoint
        )

        app.register_blueprint(self.blueprint)

        with app.app_context():
            actions.register(self.nav_root, *self.nav_root.items)

        self.app = app
        app.extensions["admin"] = self

    def register_panel(self, panel: Any) -> None:
        if self.app:
            raise ValueError(
                "Extension already initialized for app, cannot add more" " panel"
            )

        self.panels.append(panel)
        panel.admin = self
        rule = "/" + panel.id
        endpoint = nav_id = panel.id
        abs_endpoint = f"admin.{endpoint}"

        if hasattr(panel, "get"):
            self.blueprint.add_url_rule(rule, endpoint, panel.get)
            self._panels_endpoints[abs_endpoint] = panel
        if hasattr(panel, "post"):
            post_endpoint = endpoint + "_post"
            self.blueprint.add_url_rule(
                rule, post_endpoint, panel.post, methods=["POST"]
            )
            self._panels_endpoints["admin." + post_endpoint] = panel

        panel.install_additional_rules(
            self.get_panel_url_rule_adder(panel, rule, endpoint)
        )

        nav = NavItem(
            "admin:panel",
            nav_id,
            title=panel.label,
            icon=panel.icon,
            endpoint=abs_endpoint,
        )
        self.nav_root.append(nav)
        self.nav_paths[abs_endpoint] = nav.path
        self.breadcrumb_items[panel] = BreadcrumbItem(
            label=panel.label, icon=panel.icon, url=Endpoint(abs_endpoint)
        )

    def get_panel_url_rule_adder(
        self, panel: Any, base_url: str, base_endpoint: str
    ) -> Callable:
        extension = self

        def add_url_rule(
            rule: str,
            endpoint: Optional[Any] = None,
            view_func: Optional[Callable] = None,
            **kwargs: Any,
        ) -> None:
            if not rule:
                # '' is already used for panel get/post
                raise ValueError(f"Invalid additional url rule: {repr(rule)}")

            if endpoint is None:
                endpoint = _endpoint_from_view_func(view_func)

            if not endpoint.startswith(base_endpoint):
                endpoint = base_endpoint + "_" + endpoint

            extension._panels_endpoints["admin." + endpoint] = panel
            self.blueprint.add_url_rule(
                base_url + rule, endpoint=endpoint, view_func=view_func, **kwargs
            )

        return add_url_rule

    def setup_blueprint(self) -> None:
        self.blueprint = Blueprint(
            "admin", __name__, template_folder="templates", url_prefix="/" + _BP_PREFIX
        )

        self.blueprint.url_value_preprocessor(self.build_breadcrumbs)
        self.blueprint.url_value_preprocessor(self.panel_preprocess_value)

        @self.blueprint.before_request
        def check_security() -> None:
            user = unwrap(current_user)
            if not security.has_role(user, "admin"):
                raise Forbidden()

    def panel_preprocess_value(self, endpoint: str, view_args: Dict[Any, Any]) -> None:
        panel = self._panels_endpoints.get(endpoint)
        if panel is not None:
            panel.url_value_preprocess(endpoint, view_args)

    def build_breadcrumbs(self, endpoint: str, view_args: Dict[Any, Any]) -> None:
        g.breadcrumb.append(self.root_breadcrumb_item)
        g.nav["active"] = self.nav_paths.get(endpoint, self.nav_root.path)
        panel = self._panels_endpoints.get(endpoint)
        if panel:
            endpoint_bc = self.breadcrumb_items.get(panel)
            if endpoint_bc:
                g.breadcrumb.append(endpoint_bc)

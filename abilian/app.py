"""Base Flask application class, used by tests or to be extended in real
applications."""
import errno
import importlib
import logging.config
import os
import sys
import warnings
from functools import partial
from itertools import chain, count
from pathlib import Path
from typing import Any, Callable, Collection, Dict, Optional, Union

import jinja2
import sqlalchemy as sa
import sqlalchemy.exc
from flask import Blueprint, Flask, abort, appcontext_pushed, g, request, \
    request_started
from flask.config import Config, ConfigAttribute
from flask.helpers import locked_cached_property
from flask_migrate import Migrate
from flask_talisman import DEFAULT_CSP_POLICY, Talisman
from sqlalchemy.orm.attributes import NEVER_SET

import abilian.core.util
import abilian.i18n
from abilian.config import default_config
from abilian.core import extensions, signals
from abilian.core.celery import FlaskCelery
from abilian.services import Service, activity_service, antivirus, \
    audit_service, auth_service, conversion_service, index_service, \
    preferences_service, repository_service, security_service, \
    session_repository_service, settings_service, vocabularies_service
from abilian.services.security import Anonymous
from abilian.services.security.models import Role
from abilian.web import csrf
from abilian.web.action import actions
from abilian.web.admin import Admin
from abilian.web.assets import AssetManagerMixin
from abilian.web.blueprints import allow_access_for_roles
from abilian.web.errors import ErrorManagerMixin
from abilian.web.hooks import init_hooks
from abilian.web.jinja import JinjaManagerMixin
from abilian.web.nav import BreadcrumbItem
from abilian.web.util import send_file_from_directory
from abilian.web.views import Registry as ViewRegistry

logger = logging.getLogger(__name__)
db = extensions.db
__all__ = ["create_app", "Application", "ServiceManager"]

# Silence those warnings for now.
warnings.simplefilter("ignore", category=sa.exc.SAWarning)


class ServiceManager:
    """Mixin that provides lifecycle (register/start/stop) support for
    services."""

    services: Dict[str, Service]

    def __init__(self) -> None:
        self.services = {}

    def start_services(self):
        for svc in self.services.values():
            svc.start()

    def stop_services(self):
        for svc in self.services.values():
            svc.stop()


class PluginManager:
    """Mixin that provides support for loading plugins."""

    config: Config

    #: Custom apps may want to always load some plugins: list them here.
    APP_PLUGINS = (
        "abilian.web.search",
        "abilian.web.tags",
        "abilian.web.comments",
        "abilian.web.uploads",
        "abilian.web.attachments",
    )

    def register_plugin(self, name: str) -> None:
        """Load and register a plugin given its package name."""
        logger.info("Registering plugin: " + name)
        module = importlib.import_module(name)
        module.register_plugin(self)  # type: ignore

    def register_plugins(self) -> None:
        """Load plugins listed in config variable 'PLUGINS'."""
        registered = set()
        for plugin_fqdn in chain(self.APP_PLUGINS, self.config["PLUGINS"]):
            if plugin_fqdn not in registered:
                self.register_plugin(plugin_fqdn)
                registered.add(plugin_fqdn)


class Application(
    ServiceManager,
    PluginManager,
    AssetManagerMixin,
    ErrorManagerMixin,
    JinjaManagerMixin,
    Flask,
):
    """Base application class.

    Extend it in your own app.
    """

    default_config = default_config

    #: If True all views will require by default an authenticated user, unless
    #: Anonymous role is authorized. Static assets are always public.
    private_site = ConfigAttribute("PRIVATE_SITE")

    #: instance of :class:`.web.views.registry.Registry`.
    default_view: ViewRegistry

    #: json serializable dict to land in Javascript under Abilian.api
    js_api: Dict[str, str]

    #: celery app class
    celery_app_cls = FlaskCelery

    def __init__(self, name: Optional[Any] = None, *args: Any, **kwargs: Any) -> None:
        name = name or __name__

        Flask.__init__(self, name, *args, **kwargs)

        ServiceManager.__init__(self)
        PluginManager.__init__(self)
        JinjaManagerMixin.__init__(self)

        self.default_view = ViewRegistry()
        self.js_api = {}

    def setup(self, config: Optional[type]) -> None:
        self.configure(config)

        # At this point we have loaded all external config files:
        # SQLALCHEMY_DATABASE_URI is definitively fixed (it cannot be defined in
        # database AFAICT), and LOGGING_FILE cannot be set in DB settings.
        self.setup_logging()

        appcontext_pushed.connect(self.install_id_generator)

        if not self.testing:
            self.init_sentry()

        # time to load config bits from database: 'settings'
        # First init required stuff: db to make queries, and settings service
        extensions.db.init_app(self)
        settings_service.init_app(self)

        self.register_jinja_loaders(jinja2.PackageLoader("abilian.web"))
        self.init_assets()
        self.install_default_handlers()

        with self.app_context():
            self.init_extensions()
            self.register_plugins()
            self.add_access_controller(
                "static", allow_access_for_roles(Anonymous), endpoint=True
            )
            # debugtoolbar: this is needed to have it when not authenticated
            # on a private site. We cannot do this in init_debug_toolbar,
            # since auth service is not yet installed.
            self.add_access_controller(
                "debugtoolbar", allow_access_for_roles(Anonymous)
            )
            self.add_access_controller(
                "_debug_toolbar.static",
                allow_access_for_roles(Anonymous),
                endpoint=True,
            )

        # TODO: maybe reenable later
        # self.maybe_register_setup_wizard()

        self._finalize_assets_setup()

        # At this point all models should have been imported: time to configure
        # mappers. Normally Sqlalchemy does it when needed but mappers may be
        # configured inside sa.orm.class_mapper() which hides a
        # misconfiguration: if a mapper is misconfigured its exception is
        # swallowed by class_mapper(model) results in this laconic
        # (and misleading) message: "model is not mapped"
        sa.orm.configure_mappers()

        signals.components_registered.send(self)

        request_started.connect(self.setup_nav_and_breadcrumbs)
        init_hooks(self)

        # Initialize Abilian core services.
        # Must come after all entity classes have been declared.
        # Inherited from ServiceManager. Will need some configuration love
        # later.
        if not self.testing:
            with self.app_context():
                self.start_services()

        setup(self)

    def setup_nav_and_breadcrumbs(self, app: Flask) -> None:
        """Listener for `request_started` event.

        If you want to customize first items of breadcrumbs, override
        :meth:`init_breadcrumbs`
        """
        g.nav = {"active": None}  # active section
        g.breadcrumb = []
        self.init_breadcrumbs()

    def init_breadcrumbs(self) -> None:
        """Insert the first element in breadcrumbs.

        This happens during `request_started` event, which is triggered
        before any url_value_preprocessor and `before_request` handlers.
        """
        g.breadcrumb.append(BreadcrumbItem(icon="home", url="/" + request.script_root))

    # TODO: remove
    def install_id_generator(self, sender: Flask, **kwargs: Any) -> None:
        g.id_generator = count(start=1)

    def configure(self, config: Optional[type]) -> None:
        if config:
            self.config.from_object(config)

        # Setup babel config
        languages = self.config["BABEL_ACCEPT_LANGUAGES"]
        languages = tuple(
            lang for lang in languages if lang in abilian.i18n.VALID_LANGUAGES_CODE
        )
        self.config["BABEL_ACCEPT_LANGUAGES"] = languages

        # This needs to be done dynamically
        if not self.config.get("SESSION_COOKIE_NAME"):
            self.config["SESSION_COOKIE_NAME"] = self.name + "-session"

        if not self.config.get("FAVICO_URL"):
            self.config["FAVICO_URL"] = self.config.get("LOGO_URL")

        if not self.debug and self.config["SECRET_KEY"] == "CHANGEME":
            logger.error("You must change the default secret config ('SECRET_KEY')")
            sys.exit()

    def check_instance_folder(self, create=False):
        """Verify instance folder exists, is a directory, and has necessary
        permissions.

        :param:create: if `True`, creates directory hierarchy

        :raises: OSError with relevant errno if something is wrong.
        """
        path = Path(self.instance_path)
        err = None
        eno = 0

        if not path.exists():
            if create:
                logger.info("Create instance folder: %s", path)
                path.mkdir(0o775, parents=True)
            else:
                err = "Instance folder does not exists"
                eno = errno.ENOENT
        elif not path.is_dir():
            err = "Instance folder is not a directory"
            eno = errno.ENOTDIR
        elif not os.access(str(path), os.R_OK | os.W_OK | os.X_OK):
            err = 'Require "rwx" access rights, please verify permissions'
            eno = errno.EPERM

        if err:
            raise OSError(eno, err, str(path))

    @locked_cached_property
    def data_dir(self) -> Path:
        path = Path(self.instance_path, "data")
        if not path.exists():
            path.mkdir(0o775, parents=True)

        return path

    def init_extensions(self) -> None:
        """Initialize flask extensions, helpers and services."""
        extensions.redis.init_app(self)
        extensions.mail.init_app(self)
        extensions.deferred_js.init_app(self)
        extensions.upstream_info.extension.init_app(self)
        actions.init_app(self)

        # auth_service installs a `before_request` handler (actually it's
        # flask-login). We want to authenticate user ASAP, so that sentry and
        # logs can report which user encountered any error happening later,
        # in particular in a before_request handler (like csrf validator)
        auth_service.init_app(self)

        # webassets
        self.setup_asset_extension()
        self.register_base_assets()

        # Babel (for i18n)
        babel = abilian.i18n.babel
        # Temporary (?) workaround
        babel.locale_selector_func = None
        babel.timezone_selector_func = None

        babel.init_app(self)
        babel.add_translations("wtforms", translations_dir="locale", domain="wtforms")
        babel.add_translations("abilian")
        babel.localeselector(abilian.i18n.localeselector)
        babel.timezoneselector(abilian.i18n.timezoneselector)

        # Flask-Migrate
        Migrate(self, db)

        # CSRF by default
        if self.config.get("WTF_CSRF_ENABLED"):
            extensions.csrf.init_app(self)
            self.extensions["csrf"] = extensions.csrf
            extensions.abilian_csrf.init_app(self)

        self.register_blueprint(csrf.blueprint)

        # images blueprint
        from .web.views.images import blueprint as images_bp

        self.register_blueprint(images_bp)

        # Abilian Core services
        security_service.init_app(self)
        repository_service.init_app(self)
        session_repository_service.init_app(self)
        audit_service.init_app(self)
        index_service.init_app(self)
        activity_service.init_app(self)
        preferences_service.init_app(self)
        conversion_service.init_app(self)
        vocabularies_service.init_app(self)
        antivirus.init_app(self)

        from .web.preferences.user import UserPreferencesPanel

        preferences_service.register_panel(UserPreferencesPanel(), self)

        from .web.coreviews import users

        self.register_blueprint(users.blueprint)

        # Admin interface
        Admin().init_app(self)

        # Celery async service
        # this allows all shared tasks to use this celery app
        if getattr(self, "celery_app_cls", None):
            celery_app = self.extensions["celery"] = self.celery_app_cls()
            # force reading celery conf now - default celery app will
            # also update our config with default settings
            celery_app.conf  # noqa
            celery_app.set_default()

        # dev helper
        if self.debug:
            # during dev, one can go to /http_error/403 to see rendering of 403
            http_error_pages = Blueprint("http_error_pages", __name__)

            @http_error_pages.route("/<int:code>")
            def error_page(code):
                """Helper for development to show 403, 404, 500..."""
                abort(code)

            self.register_blueprint(http_error_pages, url_prefix="/http_error")

    def add_url_rule_with_role(
        self,
        rule: str,
        endpoint: str,
        view_func: Callable,
        roles: Collection[Role] = (),
        **options: Any,
    ) -> None:
        """See :meth:`Flask.add_url_rule`.

        If `roles` parameter is present, it must be a
        :class:`abilian.service.security.models.Role` instance, or a list of
        Role instances.
        """
        self.add_url_rule(rule, endpoint, view_func, **options)

        if roles:
            self.add_access_controller(
                endpoint, allow_access_for_roles(roles), endpoint=True
            )

    def add_access_controller(
        self, name: str, func: Callable, endpoint: bool = False
    ) -> None:
        """Add an access controller.

        If `name` is None it is added at application level, else if is
        considered as a blueprint name. If `endpoint` is True then it is
        considered as an endpoint.
        """
        auth_state = self.extensions[auth_service.name]

        if endpoint:
            if not isinstance(name, str):
                msg = f"{repr(name)} is not a valid endpoint name"
                raise ValueError(msg)

            auth_state.add_endpoint_access_controller(name, func)
        else:
            auth_state.add_bp_access_controller(name, func)

    def add_static_url(
        self, url_path: str, directory: str, endpoint: str, roles: Collection[Role] = ()
    ) -> None:
        """Add a new url rule for static files.

        :param url_path: subpath from application static url path. No heading
            or trailing slash.
        :param directory: directory to serve content from.
        :param endpoint: flask endpoint name for this url rule.

        Example::

           app.add_static_url('myplugin',
                              '/path/to/myplugin/resources',
                              endpoint='myplugin_static')

        With default setup it will serve content from directory
        `/path/to/myplugin/resources` from url `http://.../static/myplugin`
        """
        url_path = self.static_url_path + "/" + url_path + "/<path:filename>"
        self.add_url_rule_with_role(
            url_path,
            endpoint=endpoint,
            view_func=partial(send_file_from_directory, directory=directory),
            roles=roles,
        )
        self.add_access_controller(
            endpoint, allow_access_for_roles(Anonymous), endpoint=True
        )


def setup(app: Flask) -> None:
    config = app.config

    # CSP
    if not app.debug:
        csp = config.get("CONTENT_SECURITY_POLICY", DEFAULT_CSP_POLICY)
        Talisman(app, content_security_policy=csp)

    # Debug Toolbar
    init_debug_toolbar(app)


def init_debug_toolbar(app: Union[Application, Application]) -> None:
    if not app.debug or app.testing:
        return

    try:
        from flask_debugtoolbar import DebugToolbarExtension
    except ImportError:
        logger.warning("Running in debug mode but flask_debugtoolbar is not installed.")
        return

    dbt = DebugToolbarExtension()
    default_config = dbt._default_config(app)
    init_dbt = dbt.init_app

    if "DEBUG_TB_PANELS" not in app.config:
        # add our panels to default ones
        app.config["DEBUG_TB_PANELS"] = list(default_config["DEBUG_TB_PANELS"])
    init_dbt(app)
    for view_name in app.view_functions:
        if view_name.startswith("debugtoolbar."):
            extensions.csrf.exempt(app.view_functions[view_name])


def create_app(
    config: Optional[type] = None, app_class: type = Application, **kw: Any
) -> Application:
    app = app_class(**kw)
    app.setup(config=config)

    # This is currently called from app.setup()
    # setup(app)

    return app

# coding=utf-8
"""
Base Flask application class, used by tests or to be extended
in real applications.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import errno
import importlib
import logging
import logging.config
import os
from functools import partial
from itertools import chain, count

import jinja2
import sqlalchemy as sa
import yaml
from babel.dates import LOCALTZ
from flask import (Blueprint, Flask, _request_ctx_stack, abort,
                   appcontext_pushed, current_app, g, render_template, request,
                   request_started)
from flask.config import ConfigAttribute
from flask.helpers import locked_cached_property
from flask_assets import Environment as AssetsEnv
from flask_assets import Bundle
from flask_babel import get_locale as babel_get_locale
from flask_migrate import Migrate
from flask_script import Manager as ScriptManager
from future.utils import string_types
from pathlib import Path
from pkg_resources import resource_filename
from sqlalchemy.orm.attributes import NEVER_SET, NO_VALUE
from werkzeug.datastructures import ImmutableDict
from werkzeug.utils import import_string

import abilian.core.util
import abilian.i18n
from abilian.core import extensions, redis, signals
from abilian.core.celery import FlaskCelery
from abilian.plugin.loader import AppLoader
from abilian.services import converter as conversion_service
from abilian.services import (
    activity_service, antivirus, audit_service, auth_service, index_service,
    preferences_service, repository_service, security_service,
    session_repository_service, settings_service, vocabularies_service)
from abilian.services.security import Anonymous
from abilian.web import csrf
from abilian.web.action import Endpoint, actions
from abilian.web.admin import Admin
from abilian.web.assets.filters import ClosureJS
from abilian.web.blueprints import allow_access_for_roles
from abilian.web.filters import init_filters
from abilian.web.nav import BreadcrumbItem
from abilian.web.util import send_file_from_directory, url_for
from abilian.web.views import Registry as ViewRegistry
from abilian.web.views.images import user_photo_url

logger = logging.getLogger(__name__)
db = extensions.db
__all__ = ['create_app', 'Application', 'ServiceManager']


class ServiceManager(object):
    """
    Mixin that provides lifecycle (register/start/stop) support for services.
    """

    def __init__(self):
        self.services = {}

    def start_services(self):
        for svc in self.services.values():
            svc.start()

    def stop_services(self):
        for svc in self.services.values():
            svc.stop()


class PluginManager(object):
    """
    Mixin that provides support for loading plugins.
    """

    def load_plugins(self):
        """Discover and load plugins.

        At this point, prefer explicit loading using the :method:~`register_plugin`
        method.
        """
        loader = AppLoader()
        loader.load(__name__.split('.')[0])
        loader.register(self)

    def register_plugin(self, name):
        """Load and register a plugin given its package name.
        """
        logger.info("Registering plugin: " + name)
        module = importlib.import_module(name)
        module.register_plugin(self)


default_config = dict(Flask.default_config)
default_config.update(
    PRIVATE_SITE=False,
    TEMPLATE_DEBUG=False,
    CSRF_ENABLED=True,
    BABEL_ACCEPT_LANGUAGES=None,
    DEFAULT_COUNTRY=None,
    PLUGINS=(),
    ADMIN_PANELS=(
        'abilian.web.admin.panels.dashboard.DashboardPanel',
        'abilian.web.admin.panels.audit.AuditPanel',
        'abilian.web.admin.panels.login_sessions.LoginSessionsPanel',
        'abilian.web.admin.panels.settings.SettingsPanel',
        'abilian.web.admin.panels.users.UsersPanel',
        'abilian.web.admin.panels.groups.GroupsPanel',
        'abilian.web.admin.panels.sysinfo.SysinfoPanel',
        'abilian.services.vocabularies.admin.VocabularyPanel',
        'abilian.web.tags.admin.TagPanel',
    ),
    CELERYD_MAX_TASKS_PER_CHILD=1000,
    CELERY_ACCEPT_CONTENT=['pickle', 'json', 'msgpack', 'yaml'],
    CELERY_TIMEZONE=LOCALTZ,
    SENTRY_USER_ATTRS=('email', 'first_name', 'last_name',),
    SENTRY_INSTALL_CLIENT_JS=True,  # also install client JS
    SENTRY_JS_VERSION='1.1.22',
    SENTRY_JS_PLUGINS=('console', 'jquery', 'native', 'require',),
    SESSION_COOKIE_NAME=None,
    SQLALCHEMY_POOL_RECYCLE=1800,  # 30min. default value in flask_sa is None
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    LOGO_URL=Endpoint('abilian_static', filename='img/logo-abilian-32x32.png'),
    ABILIAN_UPSTREAM_INFO_ENABLED=False,  # upstream info extension
    TRACKING_CODE_SNIPPET=u'',  # tracking code to insert before </body>
    MAIL_ADDRESS_TAG_CHAR=None,
)
default_config = ImmutableDict(default_config)


class Application(Flask, ServiceManager, PluginManager):
    """Base application class. Extend it in your own app.
    """
    default_config = default_config

    #: Custom apps may want to always load some plugins: list them here.
    APP_PLUGINS = ('abilian.web.search',
                   'abilian.web.tags',
                   'abilian.web.comments',
                   'abilian.web.uploads',
                   'abilian.web.attachments',)

    #: Environment variable used to locate a config file to load last (after
    #: instance config file). Use this if you want to override some settings on a
    #: configured instance.
    CONFIG_ENVVAR = 'ABILIAN_CONFIG'

    #: True if application has a config file and can be considered configured for
    #: site.
    configured = ConfigAttribute('CONFIGURED')

    #: If True all views will require by default an authenticated user, unless
    #: Anonymous role is authorized. Static assets are always public.
    private_site = ConfigAttribute('PRIVATE_SITE')

    #: instance of :class:`.web.views.registry.Registry`.
    default_view = None

    #: json serializable dict to land in Javascript under Abilian.api
    js_api = None

    #: :class:`flask.ext.script.Manager` instance for shell commands of this app.
    #: defaults to `.commands.manager`, relative to app name.
    script_manager = '.commands.manager'

    #: celery app class
    celery_app_cls = FlaskCelery

    def __init__(self, name=None, config=None, *args, **kwargs):
        kwargs.setdefault('instance_relative_config', True)
        name = name or __name__

        # used by make_config to determine if we try to load config from instance /
        # environment variable /...
        self._ABILIAN_INIT_TESTING_FLAG = (getattr(config, 'TESTING', False) if
                                           config else False)
        Flask.__init__(self, name, *args, **kwargs)
        del self._ABILIAN_INIT_TESTING_FLAG

        self._setup_script_manager()
        appcontext_pushed.connect(self._install_id_generator)
        ServiceManager.__init__(self)
        PluginManager.__init__(self)
        self.default_view = ViewRegistry()
        self.js_api = dict()

        if config:
            self.config.from_object(config)

        # at this point we have loaded all external config files:
        # SQLALCHEMY_DATABASE_URI is definitively fixed (it cannot be defined in
        # database AFAICT), and LOGGING_FILE cannot be set in DB settings.
        self.setup_logging()

        configured = bool(self.config.get('SQLALCHEMY_DATABASE_URI'))
        self.config['CONFIGURED'] = configured

        if not self.testing:
            self.init_sentry()

        if not configured:
            # set fixed secret_key so that any unconfigured worker will use, so that
            # session can be used during setup even if multiple processes are
            # processing requests.
            self.config['SECRET_KEY'] = 'abilian_setup_key'

        # time to load config bits from database: 'settings'
        # First init required stuff: db to make queries, and settings service
        extensions.db.init_app(self)
        settings_service.init_app(self)

        if configured:
            with self.app_context():
                try:
                    settings = self.services['settings'].namespace(
                        'config').as_dict()
                except sa.exc.DatabaseError as exc:
                    # we may get here if DB is not initialized and "settings" table is
                    # missing. Command "initdb" must be run to initialize db, but first we
                    # must pass app init
                    if not self.testing:
                        # durint tests this message will show up on every test, since db is
                        # always recreated
                        logging.error(exc.message)
                    self.db.session.rollback()
                else:
                    self.config.update(settings)

        if not self.config.get('FAVICO_URL'):
            self.config['FAVICO_URL'] = self.config.get('LOGO_URL')

        languages = self.config.get('BABEL_ACCEPT_LANGUAGES')
        if languages is None:
            languages = abilian.i18n.VALID_LANGUAGES_CODE
        else:
            languages = tuple(lang for lang in languages
                              if lang in abilian.i18n.VALID_LANGUAGES_CODE)
        self.config['BABEL_ACCEPT_LANGUAGES'] = languages

        self._jinja_loaders = list()
        self.register_jinja_loaders(jinja2.PackageLoader('abilian.web',
                                                         'templates'))

        js_filters = (('closure_js',) if self.config.get('PRODUCTION', False)
                      else None)

        self._assets_bundles = {
            'css': {'options': dict(filters=('less', 'cssmin'),
                                    output='style-%(version)s.min.css',)},
            'js-top': {'options': dict(output='top-%(version)s.min.js',
                                       filters=js_filters,)},
            'js': {'options': dict(output='app-%(version)s.min.js',
                                   filters=js_filters)},
        }

        # bundles for JS translations
        for lang in languages:
            code = 'js-i18n-' + lang
            filename = 'lang-' + lang + '-%(version)s.min.js'
            self._assets_bundles[code] = {
                'options': dict(output=filename,
                                filters=js_filters),
            }

        for http_error_code in (403, 404, 500):
            self.install_default_handler(http_error_code)

        with self.app_context():
            self.init_extensions()
            self.register_plugins()
            self.add_access_controller('static',
                                       allow_access_for_roles(Anonymous),
                                       endpoint=True)
            # debugtoolbar: this is needed to have it when not authenticated on a
            # private site. We cannot do this in init_debug_toolbar, since auth
            # service is not yet installed
            self.add_access_controller('debugtoolbar',
                                       allow_access_for_roles(Anonymous),)
            self.add_access_controller('_debug_toolbar.static',
                                       allow_access_for_roles(Anonymous),
                                       endpoint=True)

        self.maybe_register_setup_wizard()
        self._finalize_assets_setup()
        # At this point all models should have been imported: time to configure
        # mappers. Normally Sqlalchemy does it when needed but mappers may be
        # configured inside sa.orm.class_mapper() which hides a misconfiguration: if
        # a mapper is misconfigured its exception is swallowed by
        # class_mapper(model) results in this laconic (and misleading) message:
        # "model is not mapped"
        sa.orm.configure_mappers()

        signals.components_registered.send(self)
        self.before_first_request(self._set_current_celery_app)
        self.before_first_request(lambda: signals.register_js_api.send(self))

        request_started.connect(self._setup_nav_and_breadcrumbs)

        # Initialize Abilian core services.
        # Must come after all entity classes have been declared.
        # Inherited from ServiceManager. Will need some configuration love later.
        if not self.config.get('TESTING', False):
            with self.app_context():
                self.start_services()

    def _setup_script_manager(self):
        manager = self.script_manager

        if manager is None or isinstance(manager, ScriptManager):
            return

        if isinstance(manager, (bytes, unicode)):
            manager = str(manager)
            if manager.startswith('.'):
                manager = self.import_name + manager

            manager_import_path = manager
            manager = import_string(manager, silent=True)
            if manager is None:
                # fallback on abilian-core's
                logger.warning(
                    '\n' + ('*' * 79) + '\n'
                    'Could not find command manager at %r, using a default one\n'
                    'Some commands might not be available\n' +
                    ('*' * 79) + '\n', manager_import_path)
                from abilian.core.commands import setup_abilian_commands
                manager = ScriptManager()
                setup_abilian_commands(manager)

            self.script_manager = manager

    def _install_id_generator(self, sender, **kwargs):
        g.id_generator = count(start=1)

    def _set_current_celery_app(self):
        """Listener for `before_first_request`.

        Set our celery app as current, so that task use the correct config.
        Without that tasks may use their default set app.
        """
        self.extensions['celery'].set_current()

    def _setup_nav_and_breadcrumbs(self, app=None):
        """Listener for `request_started` event.

        If you want to customize first items of breadcrumbs, override
        :meth:`init_breadcrumbs`
        """
        g.nav = {'active': None}  # active section
        g.breadcrumb = []
        self.init_breadcrumbs()

    def init_breadcrumbs(self):
        """Insert the first element in breadcrumbs.

        This happens during `request_started` event, which is triggered before any
        url_value_preprocessor and `before_request` handlers.
        """
        g.breadcrumb.append(BreadcrumbItem(icon=u'home',
                                           url=u'/' + request.script_root))

    def check_instance_folder(self, create=False):
        """Verify instance folder exists, is a directory, and has necessary permissions.

        :param:create: if `True`, creates directory hierarchy

        :raises: OSError with relevant errno
        """
        path = Path(self.instance_path)
        err = None
        eno = 0

        if not path.exists():
            if create:
                logger.info('Create instance folder: %s',
                            unicode(path).encode('utf-8'))
                path.mkdir(0o775, parents=True)
            else:
                err = 'Instance folder does not exists'
                eno = errno.ENOENT
        elif not path.is_dir():
            err = 'Instance folder is not a directory'
            eno = errno.ENOTDIR
        elif not os.access(str(path), os.R_OK | os.W_OK | os.X_OK):
            err = 'Require "rwx" access rights, please verify permissions'
            eno = errno.EPERM

        if err:
            raise OSError(eno, err, str(path))

        if not self.DATA_DIR.exists():
            self.DATA_DIR.mkdir(0o775, parents=True)

    def make_config(self, instance_relative=False):
        config = Flask.make_config(self, instance_relative)
        if not config.get('SESSION_COOKIE_NAME'):
            config['SESSION_COOKIE_NAME'] = self.name + '-session'

        # during testing DATA_DIR is not created by instance app, but we still need
        # this attribute to be set
        self.DATA_DIR = Path(self.instance_path, 'data')

        if self._ABILIAN_INIT_TESTING_FLAG:
            # testing: don't load any config file!
            return config

        if instance_relative:
            self.check_instance_folder(create=True)

        cfg_path = os.path.join(config.root_path, 'config.py')
        logger.info('Try to load config: "%s"', cfg_path)
        try:
            config.from_pyfile(cfg_path, silent=False)
        except IOError:
            return config

        config.from_envvar(self.CONFIG_ENVVAR, silent=True)

        if 'WTF_CSRF_ENABLED' not in config:
            config['WTF_CSRF_ENABLED'] = config.get('CSRF_ENABLED', True)

        return config

    def setup_logging(self):
        self.logger  # force flask to create application logger before logging
        # configuration; else, flask will overwrite our settings

        log_level = self.config.get("LOG_LEVEL")
        if log_level:
            self.logger.setLevel(log_level)

        logging_file = self.config.get('LOGGING_CONFIG_FILE')
        if logging_file:
            logging_file = os.path.abspath(os.path.join(self.instance_path,
                                                        logging_file))
        else:
            logging_file = resource_filename(__name__, 'default_logging.yml')

        if logging_file.endswith('.conf'):
            # old standard 'ini' file config
            logging.config.fileConfig(logging_file,
                                      disable_existing_loggers=False)
        elif logging_file.endswith('.yml'):
            # yml config file
            logging_cfg = yaml.load(open(logging_file, 'r'))
            logging_cfg.setdefault('version', 1)
            logging_cfg.setdefault('disable_existing_loggers', False)
            logging.config.dictConfig(logging_cfg)

    def init_debug_toolbar(self):
        if (not self.testing and self.config.get('DEBUG_TB_ENABLED') and
                'debugtoolbar' not in self.blueprints):
            try:
                from flask_debugtoolbar import DebugToolbarExtension, DebugToolbar
            except ImportError:
                logger.warning('DEBUG_TB_ENABLED is on but flask_debugtoolbar '
                               'is not installed.')
            else:
                try:
                    default_config = DebugToolbar.config
                    init_dbt = DebugToolbarExtension
                except AttributeError:
                    # debugtoolbar > 0.8.0
                    dbt = DebugToolbarExtension()
                    default_config = dbt._default_config(self)
                    init_dbt = dbt.init_app

                if 'DEBUG_TB_PANELS' not in self.config:
                    # add our panels to default ones
                    self.config['DEBUG_TB_PANELS'] = list(default_config[
                        'DEBUG_TB_PANELS'])
                    self.config['DEBUG_TB_PANELS'].append(
                        'abilian.services.indexing.debug_toolbar.IndexedTermsDebugPanel')
                init_dbt(self)
                for view_name in self.view_functions:
                    if view_name.startswith('debugtoolbar.'):
                        extensions.csrf.exempt(self.view_functions[view_name])

    def init_extensions(self):
        """Initialize flask extensions, helpers and services.
        """
        self.init_debug_toolbar()
        redis.Extension(self)
        extensions.mail.init_app(self)
        extensions.upstream_info.extension.init_app(self)
        actions.init_app(self)

        from abilian.core.jinjaext import DeferredJS
        DeferredJS(self)

        # auth_service installs a `before_request` handler (actually it's
        # flask-login). We want to authenticate user ASAP, so that sentry and logs
        # can report which user encountered any error happening later, in particular
        # in a before_request handler (like csrf validator)
        auth_service.init_app(self)

        # webassets
        self._setup_asset_extension()
        self._register_base_assets()

        # Babel (for i18n)
        abilian.i18n.babel.init_app(self)
        abilian.i18n.babel.add_translations('wtforms',
                                            translations_dir='locale',
                                            domain='wtforms')
        abilian.i18n.babel.add_translations('abilian')
        abilian.i18n.babel.localeselector(abilian.i18n.localeselector)
        abilian.i18n.babel.timezoneselector(abilian.i18n.timezoneselector)

        # Flask-Migrate
        Migrate(self, self.db)

        # CSRF by default
        if self.config.get('CSRF_ENABLED'):
            extensions.csrf.init_app(self)
            self.extensions['csrf'] = extensions.csrf
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
        self.register_blueprint(users.bp)

        # Admin interface
        Admin().init_app(self)

        # Celery async service
        # this allows all shared tasks to use this celery app
        celery_app = self.extensions['celery'] = self.celery_app_cls()
        # force reading celery conf now - default celery app will
        # also update our config with default settings
        celery_app.conf  # noqa
        celery_app.set_default()

        # dev helper
        if self.debug:
            # during dev, one can go to /http_error/403 to see rendering of 403
            http_error_pages = Blueprint('http_error_pages', __name__)

            @http_error_pages.route('/<int:code>')
            def error_page(code):
                """ Helper for development to show 403, 404, 500..."""
                abort(code)

            self.register_blueprint(http_error_pages, url_prefix='/http_error')

    def register_plugins(self):
        """Load plugins listed in config variable 'PLUGINS'.
        """
        registered = set()
        for plugin_fqdn in chain(self.APP_PLUGINS, self.config['PLUGINS']):
            if plugin_fqdn not in registered:
                self.register_plugin(plugin_fqdn)
                registered.add(plugin_fqdn)

    def maybe_register_setup_wizard(self):
        if self.configured:
            return

        logger.info('Application is not configured, installing setup wizard')
        from abilian.web import setupwizard

        self.register_blueprint(setupwizard.setup, url_prefix='/setup')

    def add_url_rule(self, rule, endpoint=None, view_func=None, **options):
        """See :meth:`Flask.add_url_rule`.

        If `roles` parameter is present, it must be a
        :class:`abilian.service.security.models.Role` instance, or a list of
        Role instances.
        """
        roles = options.pop('roles', None)
        super(Application, self).add_url_rule(rule, endpoint, view_func,
                                              **options)

        if roles:
            self.add_access_controller(endpoint,
                                       allow_access_for_roles(roles),
                                       endpoint=True)

    def add_access_controller(self, name, func, endpoint=False):
        """Add an access controller.

        If `name` is None it is added at application level, else if is
        considered as a blueprint name. If `endpoint` is True then it is
        considered as an endpoint.
        """
        auth_state = self.extensions[auth_service.name]
        adder = auth_state.add_bp_access_controller

        if endpoint:
            adder = auth_state.add_endpoint_access_controller
            if not isinstance(name, string_types):
                raise ValueError('{} is not a valid endpoint name', repr(name))

        adder(name, func)

    def add_static_url(self, url_path, directory, endpoint=None, roles=None):
        """Add a new url rule for static files.

        :param endpoint: flask endpoint name for this url rule.
        :param url: subpath from application static url path. No heading or trailing
                    slash.
        :param directory: directory to serve content from.

        Example::

           app.add_static_url('myplugin',
                              '/path/to/myplugin/resources',
                              endpoint='myplugin_static')

        With default setup it will serve content from directory
        `/path/to/myplugin/resources` from url `http://.../static/myplugin`
        """
        url_path = self.static_url_path + '/' + url_path + '/<path:filename>'
        self.add_url_rule(url_path,
                          endpoint=endpoint,
                          view_func=partial(send_file_from_directory,
                                            directory=directory),
                          roles=roles)
        self.add_access_controller(endpoint,
                                   allow_access_for_roles(Anonymous),
                                   endpoint=True)

    #
    # Templating and context injection setup
    #
    def create_jinja_environment(self):
        env = Flask.create_jinja_environment(self)
        env.globals.update(app=current_app,
                           csrf=csrf,
                           get_locale=babel_get_locale,
                           local_dt=abilian.core.util.local_dt,
                           _n=abilian.i18n._n,
                           url_for=url_for,
                           user_photo_url=user_photo_url,
                           NO_VALUE=NO_VALUE,
                           NEVER_SET=NEVER_SET,)
        init_filters(env)
        return env

    @property
    def jinja_options(self):
        options = dict(Flask.jinja_options)

        extensions = options.setdefault('extensions', [])
        ext = 'abilian.core.jinjaext.DeferredJSExtension'
        if ext not in extensions:
            extensions.append(ext)

        if 'bytecode_cache' not in options:
            cache_dir = Path(self.instance_path, 'cache', 'jinja')
            if not cache_dir.exists():
                cache_dir.mkdir(0o775, parents=True)

            options['bytecode_cache'] = jinja2.FileSystemBytecodeCache(
                str(cache_dir), '%s.cache')

        if (self.config.get('DEBUG', False) and
                self.config.get('TEMPLATE_DEBUG', False)):
            options['undefined'] = jinja2.StrictUndefined
        return options

    def register_jinja_loaders(self, *loaders):
        """Register one or many `jinja2.Loader` instances for templates lookup.

        During application initialization plugins can register a loader so that
        their templates are available to jinja2 renderer.

        Order of registration matters: last registered is first looked up (after
        standard Flask lookup in app template folder). This allows a plugin to
        override templates provided by others, or by base application. The
        application can override any template from any plugins from its template
        folder (See `Flask.Application.template_folder`).

        :raise: `ValueError` if a template has already been rendered
        """
        if not hasattr(self, '_jinja_loaders'):
            raise ValueError(
                'Cannot register new jinja loaders after first template rendered')

        self._jinja_loaders.extend(loaders)

    @locked_cached_property
    def jinja_loader(self):
        """Search templates in custom app templates dir (default flask behaviour),
        fallback on abilian templates.
        """
        loaders = self._jinja_loaders
        del self._jinja_loaders
        loaders.append(Flask.jinja_loader.func(self))
        loaders.reverse()
        return jinja2.ChoiceLoader(loaders)

    # Error handling
    def handle_user_exception(self, e):
        # If session.transaction._parent is None, then exception has occured in
        # after_commit(): doing a rollback() raises an error and would hide actual
        # error
        session = db.session()
        if session.is_active and session.transaction._parent is not None:
            # inconditionally forget all DB changes, and ensure clean session during
            # exception handling
            session.rollback()
        else:
            self._remove_session_save_objects()

        return Flask.handle_user_exception(self, e)

    def handle_exception(self, e):
        session = db.session()
        if not session.is_active:
            # something happened in error handlers and session is not usable anymore.
            #
            self._remove_session_save_objects()

        return Flask.handle_exception(self, e)

    def _remove_session_save_objects(self):
        """
        Used during exception handling in case we need to remove() session: keep
        instances and merge them in the new session.
        """
        if self.testing:
            return
        # Before destroying the session, get all instances to be attached to the
        # new session. Without this, we get DetachedInstance errors, like when
        # tryin to get user's attribute in the error page...
        old_session = db.session()
        g_objs = []
        for key in iter(g):
            obj = getattr(g, key)
            if (isinstance(obj, db.Model) and
                    sa.orm.object_session(obj) in (None, old_session)):
                g_objs.append((key, obj, obj in old_session.dirty))

        db.session.remove()
        session = db.session()

        for key, obj, load in g_objs:
            # replace obj instance in bad session by new instance in fresh session
            setattr(g, key, session.merge(obj, load=load))

        # refresh `current_user`
        user = getattr(_request_ctx_stack.top, 'user', None)
        if user is not None and isinstance(user, db.Model):
            _request_ctx_stack.top.user = session.merge(user, load=load)

    def log_exception(self, exc_info):
        """Log exception only if sentry is not installed (this avoids getting error
        twice in sentry).
        """
        if 'sentry' not in self.extensions:
            super(Application, self).log_exception(exc_info)

    def init_sentry(self):
        """Install Sentry handler if config defines 'SENTRY_DSN'.
        """
        if self.config.get('SENTRY_DSN'):
            try:
                from abilian.core.sentry import Sentry
            except ImportError:
                logger.error(
                    'SENTRY_DSN is defined in config but package "raven" is not '
                    'installed.')
                return

            ext = Sentry(self, logging=True, level=logging.ERROR)
            ext.client.tags['app_name'] = self.name
            ext.client.tags['process_type'] = 'web'
            server_name = str(self.config.get('SERVER_NAME'))
            ext.client.tags['configured_server_name'] = server_name

    @property
    def db(self):
        return self.extensions['sqlalchemy'].db

    @property
    def redis(self):
        return self.extensions['redis'].client

    def create_db(self):
        from abilian.core.models.subjects import User

        db.create_all()
        if User.query.get(0) is None:
            root = User(id=0,
                        last_name=u'SYSTEM',
                        email=u'system@example.com',
                        can_login=False)
            db.session.add(root)
            db.session.commit()

    def _setup_asset_extension(self):
        assets = self.extensions['webassets'] = AssetsEnv(self)
        assets.debug = not self.config.get('PRODUCTION', False)
        assets.requirejs_config = {'waitSeconds': 90, 'shim': {}, 'paths': {},}

        assets_base_dir = Path(self.instance_path, 'webassets')
        assets_dir = assets_base_dir / 'compiled'
        assets_cache_dir = assets_base_dir / 'cache'
        for path in (assets_base_dir, assets_dir, assets_cache_dir):
            if not path.exists():
                path.mkdir()

        assets.directory = str(assets_dir)
        assets.cache = str(assets_cache_dir)
        manifest_file = assets_base_dir / 'manifest.json'
        assets.manifest = 'json:{}'.format(str(manifest_file))

        # set up load_path for application static dir. This is required since we are
        # setting Environment.load_path for other assets (like core_bundle below),
        # in this case Flask-Assets uses webasssets resolvers instead of Flask's one
        assets.append_path(self.static_folder, self.static_url_path)

        # filters options
        less_args = ['-ru']
        assets.config['less_extra_args'] = less_args
        assets.config['less_as_output'] = True
        if assets.debug:
            assets.config['less_source_map_file'] = 'style.map'

        # setup static url for our assets
        from abilian.web import assets as core_bundles
        core_bundles.init_app(self)

        # static minified are here
        assets.url = self.static_url_path + '/min'
        assets.append_path(str(assets_dir), assets.url)
        self.add_static_url('min',
                            str(assets_dir),
                            endpoint='webassets_static',
                            roles=Anonymous,)

    def _finalize_assets_setup(self):
        assets = self.extensions['webassets']
        assets_dir = Path(assets.directory)
        closure_base_args = [
            '--jscomp_warning',
            'internetExplorerChecks',
            '--source_map_format',
            'V3',
            '--create_source_map',
        ]

        for name, data in self._assets_bundles.items():
            bundles = data.get('bundles', [])
            options = data.get('options', {})
            filters = options.get('filters') or []
            options['filters'] = []
            for f in filters:
                if f == 'closure_js':
                    js_map_file = str(assets_dir / '{}.map'.format(name))
                    f = ClosureJS(extra_args=closure_base_args + [js_map_file])
                options['filters'].append(f)

            if not options['filters']:
                options['filters'] = None

            if bundles:
                assets.register(name, Bundle(*bundles, **options))

    def register_asset(self, type_, *assets):
        """Register webassets bundle to be served on all pages.

        :param type_: `"css"`, `"js-top"` or `"js""`.

        :param \*asset:
            a path to file, a :ref:`webassets.Bundle <webassets:bundles>` instance
            or a callable that returns a :ref:`webassets.Bundle <webassets:bundles>`
            instance.

        :raises KeyError: if `type_` is not supported.
        """
        supported = self._assets_bundles.keys()
        if type_ not in supported:
            raise KeyError("Invalid type: %s. Valid types: ", repr(type_),
                           ', '.join(sorted(supported)))

        for asset in assets:
            if not isinstance(asset, Bundle) and callable(asset):
                asset = asset()

            self._assets_bundles[type_].setdefault('bundles', []).append(asset)

    def register_i18n_js(self, *paths):
        """Register templates path translations files, like `select2/select2_locale_{lang}.js`.

        Only existing files are registered.
        """
        languages = self.config['BABEL_ACCEPT_LANGUAGES']
        assets = self.extensions['webassets']

        for path in paths:
            for lang in languages:
                filename = path.format(lang=lang)
                try:
                    assets.resolver.search_for_source(assets, filename)
                except IOError:
                    logger.debug('i18n JS not found, skipped: "%s"', filename)
                else:
                    self.register_asset('js-i18n-' + lang, filename)

    def _register_base_assets(self):
        """Register assets needed by Abilian.

        This is done in a separate method in order to allow applications to redefine it at will.
        """
        from abilian.web import assets as bundles

        self.register_asset('css', bundles.LESS)
        self.register_asset('js-top', bundles.TOP_JS)
        self.register_asset('js', bundles.JS)
        self.register_i18n_js(*bundles.JS_I18N)

    def install_default_handler(self, http_error_code):
        """Install a default error handler for `http_error_code`.

        The default error handler renders a template named error404.html for
        http_error_code 404.
        """
        logger.debug('Set Default HTTP error handler for status code %d',
                     http_error_code)
        handler = partial(self.handle_http_error, http_error_code)
        self.errorhandler(http_error_code)(handler)

    def handle_http_error(self, code, error):
        """Helper that renders `error{code}.html`.

        Convenient way to use it::

           from functools import partial
           handler = partial(app.handle_http_error, code)
           app.errorhandler(code)(handler)
        """
        # 5xx code: error on server side
        if (code / 100) == 5:
            # ensure rollback if needed, else error page may
            # have an error, too, resulting in raw 500 page :-(
            db.session.rollback()

        template = 'error{:d}.html'.format(code)
        return render_template(template, error=error), code


def create_app(config=None):
    return Application(config)

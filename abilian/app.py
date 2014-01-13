"""
Base Flask application class, used by tests or to be extended
in real applications.
"""
import os
import errno
import yaml
import logging
import logging.config
from itertools import chain
from functools import partial
from pkg_resources import resource_filename

import sqlalchemy as sa
from sqlalchemy.orm.attributes import NO_VALUE

from werkzeug.datastructures import ImmutableDict
from babel.dates import LOCALTZ
import jinja2
from flask import (
  Flask, g, request, current_app, has_app_context, render_template,
  request_started, Blueprint, abort
  )
from flask.config import ConfigAttribute
from flask.helpers import locked_cached_property
from flask.ext.assets import Bundle, Environment as AssetsEnv
from flask.ext.babel import get_locale as babel_get_locale
from flask.ext.migrate import Migrate

import abilian.i18n
from abilian.core import extensions, signals
import abilian.core.util
from abilian.web.action import actions
from abilian.web.views import Registry as ViewRegistry
from abilian.web.nav import BreadcrumbItem
from abilian.web.filters import init_filters
from abilian.web.util import send_file_from_directory, url_for
from abilian.web.admin import Admin
from abilian.web import csrf
from abilian.plugin.loader import AppLoader
from abilian.services import (
    audit_service, index_service, activity_service, auth_service,
    settings_service, security_service, preferences_service)


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
    """
    Discovers and loads plugins.

    At this point, prefer explicit loading using the :method:~`register_plugin`
    method.
    """
    loader = AppLoader()
    loader.load(__name__.split('.')[0])
    loader.register(self)

  def register_plugin(self, name):
    """
    Loads and registers a plugin given its package name.
    """
    logger.info("Registering plugin: " + name)
    import importlib

    module = importlib.import_module(name)
    module.register_plugin(self)


default_config = dict(Flask.default_config)
default_config.update(
  TEMPLATE_DEBUG=False,
  CSRF_ENABLED=True,
  PLUGINS=(),
  ADMIN_PANELS=(
    'abilian.web.admin.panels.dashboard.DashboardPanel',
    'abilian.web.admin.panels.audit.AuditPanel',
    'abilian.web.admin.panels.login_sessions.LoginSessionsPanel',
    'abilian.web.admin.panels.settings.SettingsPanel',
    'abilian.web.admin.panels.sysinfo.SysinfoPanel',
  ),
  SENTRY_USER_ATTRS=('email', 'first_name', 'last_name',),
)
default_config = ImmutableDict(default_config)


class Application(Flask, ServiceManager, PluginManager):
  """
  Base application class. Extend it in your own app.
  """
  default_config = default_config

  #: Custom apps may want to always load some plugins: list them here.
  APP_PLUGINS = ('abilian.web.search',)

  #: Environment variable used to locate a config file to load last (after
  #: instance config file). Use this if you want to override some settings on a
  #: configured instance.
  CONFIG_ENVVAR = 'ABILIAN_CONFIG'

  #: True if application as a config file and can be considered configured for
  #: site.
  configured = ConfigAttribute('CONFIGURED')

  #: instance of :class:`.web.views.registry.Registry`.
  default_view = None

  def __init__(self, name=None, config=None, *args, **kwargs):
    kwargs.setdefault('instance_relative_config', True)
    name = name or __name__

    # used by make_config to determine if we try to load config from instance /
    # environment variable /...
    self._ABILIAN_INIT_TESTING_FLAG = (getattr(config, 'TESTING', False)
                                       if config else False)
    Flask.__init__(self, name, *args, **kwargs)
    del self._ABILIAN_INIT_TESTING_FLAG

    ServiceManager.__init__(self)
    PluginManager.__init__(self)
    self.default_view = ViewRegistry()

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
          settings = self.services['settings'].namespace('config').as_dict()
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

    self._jinja_loaders = list()
    self.register_jinja_loaders(
      jinja2.PackageLoader('abilian.web', 'templates'))

    self._assets_bundles = {
      'css': {'options': dict(filters='cssimporter, cssrewrite',
                              output='style-%(version)s.min.css')},
      'js-top': {'options': dict(output='top-%(version)s.min.js')},
      'js': {'options': dict(output='app-%(version)s.min.js')},
    }

    for http_error_code in (403, 404, 500):
      self.install_default_handler(http_error_code)

    self.init_extensions()
    self.register_plugins()
    self.maybe_register_setup_wizard()
    self._finalize_assets_setup()
    # at this point all models should have been imported: time to configure
    # mappers. Normally Sqlalchemy does it when needed but mappers may be
    # configured inside sa.orm.class_mapper() which hides a misconfiguration: if
    # a mapper is misconfigured its exception is swallowed by
    # class_mapper(model) results in this laconic (and misleading) message:
    # "model is not mapped"
    sa.orm.configure_mappers()

    signals.components_registered.send(self)

    request_started.connect(self._setup_breadcrumbs)

    # Initialize Abilian core services.
    # Must come after all entity classes have been declared.
    # Inherited from ServiceManager. Will need some configuration love later.
    if not self.config.get('TESTING', False):
      if has_app_context():
        self.start_services()
      else:
        with self.app_context():
          self.start_services()

  def _setup_breadcrumbs(self, app=None):
    """
    Listener for `request_started` event.

    If you want to customize first items of breadcrumbs, override
    :meth:`init_breadcrumbs`
    """
    g.breadcrumb = []
    self.init_breadcrumbs()

  def init_breadcrumbs(self):
    """
    Inserts the first element in breadcrumbs.

    This happens during `request_started` event, which is triggered before any
    url_value_preprocessor and `before_request` handlers.
    """
    g.breadcrumb.append(BreadcrumbItem(icon=u'home',
                                       url=u'/' + request.script_root))

  def check_instance_folder(self, create=False):
    """
    Verifies instance folder exists, is a directory, and has necessary permissions.

    :param:create: if `True`, creates directory hierarchy

    :raises: OSError with relevant errno
    """
    path = self.instance_path
    err = None

    if not os.path.exists(path):
      if create:
        logger.info('Create instance folder: {}'.format(path.encode('utf-8')))
        os.makedirs(path, 0775)
      else:
        err = 'Instance folder does not exists'
        eno = errno.ENOENT
    elif not os.path.isdir(path):
      err = 'Instance folder not a directory'
      eno = errno.ENOTDIR
    elif not os.access(path, os.R_OK | os.W_OK | os.X_OK):
      err = 'Require "rwx" access rights, please verify permissions'
      eno = errno.EPERM

    if err:
      raise OSError(eno, err, path)

  def make_config(self, instance_relative=False):
    config = Flask.make_config(self, instance_relative)

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

    logging_file = self.config.get('LOGGING_CONFIG_FILE')
    if logging_file:
      logging_file = os.path.abspath(os.path.join(self.instance_path,
                                                  logging_file))
    else:
      logging_file = resource_filename(__name__, 'default_logging.yml')

    if logging_file.endswith('.conf'):
      # old standard 'ini' file config
      logging.config.fileConfig(logging_file, disable_existing_loggers=False)
    elif logging_file.endswith('.yml'):
      # yml config file
      logging_cfg = yaml.load(open(logging_file, 'r'))
      logging_cfg.setdefault('version', 1)
      logging.config.dictConfig(logging_cfg)

  def init_debug_toolbar(self):
    if (not self.testing
        and self.config.get('DEBUG_TB_ENABLED')
        and 'debugtoolbar' not in self.blueprints):
      try:
        from flask.ext.debugtoolbar import DebugToolbarExtension, DebugToolbar
      except ImportError:
        logger.warning('DEBUG_TOOLBAR is on but flask.ext.debugtoolbar is not '
                       'installed.')
      else:
        try:
          default_config = DebugToolbar.config
          init_dbt = DebugToolbarExtension
        except AttributeError:
          # debugtoolbar > 0.8.0
          dbt = DebugToolbarExtension()
          default_config = dbt._default_config(self)
          init_dbt = dbt.init_app

        if not 'DEBUG_TB_PANELS' in self.config:
          # add our panels to default ones
          self.config['DEBUG_TB_PANELS'] = list(default_config['DEBUG_TB_PANELS'])
          self.config['DEBUG_TB_PANELS'].append(
            'abilian.services.indexing.debug_toolbar.IndexedTermsDebugPanel'
          )
        init_dbt(self)


  def init_extensions(self):
    """
    Initializes flask extensions, helpers and services.
    """
    self.init_debug_toolbar()
    extensions.mail.init_app(self)
    actions.init_app(self)

    from abilian.core.jinjaext import DeferredJS
    DeferredJS(self)

    # webassets
    self._setup_asset_extension()
    self._register_base_assets()

    # Babel (for i18n)
    abilian.i18n.babel.init_app(self)
    abilian.i18n.babel.add_translations('abilian')
    abilian.i18n.babel.localeselector(get_locale)
    abilian.i18n.babel.timezoneselector(get_timezone)

    # Flask-Migrate
    Migrate(self, self.db)

    # Abilian Core services
    auth_service.init_app(self)
    security_service.init_app(self)
    audit_service.init_app(self)
    index_service.init_app(self)
    activity_service.init_app(self)
    preferences_service.init_app(self)

    from .web.preferences.user import UserPreferencesPanel
    preferences_service.register_panel(UserPreferencesPanel(), self)

    from .web.coreviews import users
    self.register_blueprint(users.bp)

    # Admin interface
    Admin().init_app(self)

    # Celery async service
    extensions.celery.config_from_object(self.config)

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
    """
    Loads plugins listed in config variable 'PLUGINS'.
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

  def add_static_url(self, url_path, directory, endpoint=None):
    """
    Adds a new url rule for static files.

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
                                        directory=directory))

  #
  # Templating and context injection setup
  #
  def create_jinja_environment(self):
    env = Flask.create_jinja_environment(self)
    env.globals.update(
      app=current_app,
      csrf=csrf,
      get_locale=babel_get_locale,
      local_dt=abilian.core.util.local_dt,
      url_for=url_for,
      NO_VALUE=NO_VALUE,
    )
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
      cache_dir = os.path.join(self.instance_path, 'cache', 'jinja')
      if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, 0775)

      options['bytecode_cache'] = jinja2.FileSystemBytecodeCache(cache_dir,
                                                                 '%s.cache')

    if (self.config.get('DEBUG', False)
        and self.config.get('TEMPLATE_DEBUG', False)):
      options['undefined'] = jinja2.StrictUndefined
    return options

  def register_jinja_loaders(self, *loaders):
    """
    Registers one or many `jinja2.Loader` instances for templates lookup.

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
        'Cannot register new jinja loaders after first template rendered'
      )

    self._jinja_loaders.extend(loaders)

  @locked_cached_property
  def jinja_loader(self):
    """
    Searches templates in custom app templates dir (default flask behaviour),
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
    if db.session().transaction._parent is not None:
      # inconditionally forget all DB changes, and ensure clean session during
      # exception handling
      db.session.rollback()

    return Flask.handle_user_exception(self, e)

  def handle_exception(self, e):
    session = db.session()
    if not session.is_active and session.transaction._parent is not None:
      # something happened in error handlers and session is not usable, rollback
      # will restore a usable session.
      #
      # "session.transaction._parent is not None": see comment in
      # handle_user_exception()
      session.rollback()
    return Flask.handle_exception(self, e)

  def log_exception(self, exc_info):
    """
    Log exception only if sentry is not installed (this avoids getting error
    twice in sentry).
    """
    if 'sentry' not in self.extensions:
      super(Application, self).log_exception(exc_info)

  def init_sentry(self):
    """
    Installs Sentry handler if config defines 'SENTRY_DSN'.
    """
    if self.config.get('SENTRY_DSN', None):
      try:
        from abilian.core.sentry import Sentry
      except ImportError:
        logger.error(
          'SENTRY_DSN is defined in config but package "raven" is not '
          'installed.')
        return

      Sentry(self, logging=True, level=logging.ERROR)

  @property
  def db(self):
    return self.extensions['sqlalchemy'].db

  def create_db(self):
    from abilian.core.subjects import User

    db.create_all()
    if User.query.get(0) is None:
      root = User(id=0, last_name=u'SYSTEM', email=u'system@example.com',
                  can_login=False)
      db.session.add(root)
      db.session.commit()

  def _setup_asset_extension(self):
    assets = self.extensions['webassets'] = AssetsEnv(self)
    assets.debug = not self.config.get('PRODUCTION', False)

    assets_base_dir = os.path.join(self.instance_path, 'webassets')
    assets_dir = os.path.join(assets_base_dir, 'compiled')
    assets_cache_dir = os.path.join(assets_base_dir, 'cache')
    for path in (assets_base_dir, assets_dir, assets_cache_dir):
      if not os.path.exists(path):
        os.mkdir(path)

    assets.directory = assets_dir
    assets.cache = assets_cache_dir
    manifest_file = os.path.join(assets_base_dir, 'manifest.json')
    assets.manifest = 'json:{}'.format(manifest_file)

    # setup static url for our assets
    from abilian.web import assets as core_bundles

    assets.append_path(core_bundles.RESOURCES_DIR, '/static/abilian')
    self.add_static_url('abilian', core_bundles.RESOURCES_DIR,
                        endpoint='abilian_static', )

    # static minified are here
    assets.url = self.static_url_path + '/min'
    self.add_static_url('min', assets_dir, endpoint='webassets_static', )

  def _finalize_assets_setup(self):
    assets = self.extensions['webassets']

    for name, data in self._assets_bundles.items():
      bundles = data.get('bundles', [])
      options = data.get('options', {})
      if bundles:
        assets.register(name, Bundle(*bundles, **options))

  def register_asset(self, type_, asset):
    """
    Registers webassets bundle to be served on all pages.

    :param type_: `"css"`, `"js-top"` or `"js""`.
    :param asset: a `webassets.Bundle
                  <http://elsdoerfer.name/docs/webassets/bundles.html>`_
                  instance or a callable that returns a Bundle instance.
    :raises KeyError: if `type_` is not supported.
    """
    supported = self._assets_bundles.keys()
    if type_ not in supported:
      raise KeyError("Invalid type: %s. Valid types: ",
                     repr(type_), ', '.join(sorted(supported)))

    if not isinstance(asset, Bundle) and callable(asset):
      asset = asset()
    assert isinstance(asset, Bundle)

    self._assets_bundles[type_].setdefault('bundles', []).append(asset)

  def _register_base_assets(self):
    """
    Registers assets needed by Abilian. This is done in a separate method in
    order to allow applications to redefins it at will.
    """
    from abilian.web import assets as bundles

    debug = self.config.get('DEBUG')
    self.register_asset('css', bundles.CSS if not debug else bundles.CSS_DEBUG)
    self.register_asset('js-top',
                        bundles.TOP_JS if not debug else bundles.TOP_JS_DEBUG)
    self.register_asset('js', bundles.JS if not debug else bundles.JS_DEBUG)

  def install_default_handler(self, http_error_code):
    """
    Installs a default error handler for `http_error_code`.

    The default error handler renders a template named error404.html for
    http_error_code 404.
    """
    logger.debug('Set Default HTTP error handler for status code %d',
                 http_error_code)
    handler = partial(self.handle_http_error, http_error_code)
    self.errorhandler(http_error_code)(handler)

  def handle_http_error(self, code, error):
    """
    Helper that renders `error{code}.html`.

    Convenient way to use it::

       from functools import partial
       handler = partial(app.handle_http_error, code)
       app.errorhandler(code)(handler)
    """
    if (code / 100) == 5:
      # 5xx code: error on server side
      db.session.rollback()  # ensure rollback if needed, else error page may
                             # have an error, too, resulting in raw 500 page :-()

    template = 'error{:d}.html'.format(code)
    return render_template(template, error=error), code


def create_app(config=None):
  return Application(config)


# Additional config for Babel
def get_locale():
  # if a user is logged in, use the locale from the user settings
  user = getattr(g, 'user', None)
  if user is not None:
    locale = getattr(user, 'locale', None)
    if locale:
      return locale

  # Otherwise, try to guess the language from the user accept
  # header the browser transmits.  We support de/fr/en in this
  # example.  The best match wins.
  return request.accept_languages.best_match(['en', 'fr'])


def get_timezone():
  return LOCALTZ

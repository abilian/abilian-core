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

import sqlalchemy as sa
from sqlalchemy.orm.attributes import NO_VALUE

from werkzeug.datastructures import ImmutableDict
import jinja2
from flask import (
  Flask, g, request, current_app, has_app_context, render_template,
  )
from flask.helpers import locked_cached_property
from flask.ext.assets import Bundle, Environment as AssetsEnv
from flask.ext.babel import gettext as _, get_locale as babel_get_locale

from abilian.core import extensions, signals
import abilian.core.util
from abilian.web.action import actions
from abilian.web.nav import BreadcrumbItem
from abilian.web.views import http_error_pages
from abilian.web.filters import init_filters
from abilian.web.util import send_file_from_directory
from abilian.plugin.loader import AppLoader
from abilian.services import (audit_service, index_service, activity_service,
                              auth_service)

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
  def load_plugins(self):
    """Discovers and load plugins.

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
    import importlib
    module = importlib.import_module(name)
    module.register_plugin(self)


default_config = dict(Flask.default_config)
default_config.update(
  TEMPLATE_DEBUG=False,
  PLUGINS=(),
  )
default_config = ImmutableDict(default_config)


class Application(Flask, ServiceManager, PluginManager):
  """
  Base application class. Extend it in your own app.
  """
  default_config = default_config

  #: Custom apps may want to always load some plugins: list them here.
  APP_PLUGINS = ()

  #: Environment variable used to locate a config file to load last (after
  #: instance config file). Use this if you want to override some settings on a
  #: configured instance.
  CONFIG_ENVVAR = 'ABILIAN_CONFIG'

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

    if config:
      self.config.from_object(config)

    self.setup_logging()
    self._jinja_loaders = list()
    self.register_jinja_loaders(jinja2.PackageLoader('abilian.web', 'templates'))

    for http_error_code in (403, 404, 500):
      self.install_default_handler(http_error_code)

    self.init_extensions()
    self.register_plugins()
    # at this point all models should have been imported: time to configure
    # mappers. Normally Sqlalchemy does it when needed but mappers may be
    # configured inside sa.orm.class_mapper() which hides a misconfiguration: if
    # a mapper is misconfigured its exception is swallowed by
    # class_mapper(model) results in this laconic (and misleading) message:
    # "model is not mapped"
    sa.orm.configure_mappers()

    signals.components_registered.send(self)

    self.before_request(self._setup_breadcrumbs)

    # Initialize Abilian core services.
    # Must come after all entity classes have been declared.
    # Inherited from ServiceManager. Will need some configuration love later.
    if not self.config.get('TESTING', False):
      if has_app_context():
        self.start_services()
      else:
        with self.app_context():
          self.start_services()

  def _setup_breadcrumbs(self):
    """ Before request handler. If you want to customize first items of
    breadcrumbs override :meth:`init_breadcrumbs`
    """
    g.breadcrumb = []
    self.init_breadcrumbs()

  def init_breadcrumbs(self):
    g.breadcrumb.append(BreadcrumbItem(_(u'Home'),
                                       url=u'/' + request.script_root))

  def check_instance_folder(self):
    """ Verify instance path exists, is a directory, and has necessary
    permissions

    :raises: OSError with relevant errno
    """
    path = self.instance_path
    err = None

    if not os.path.exists(path):
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
    self.check_instance_folder()
    config = Flask.make_config(self, instance_relative)

    if self._ABILIAN_INIT_TESTING_FLAG:
      # testing: don't load any config file!
      return config

    if instance_relative:
      cfg_path = os.path.join(self.instance_path, 'config.py')
      logger.info('Try to load config: "%s"', cfg_path)
      config.from_pyfile(cfg_path, silent=True)

    config.from_envvar(self.CONFIG_ENVVAR, silent=True)
    return config

  def setup_logging(self):
    self.logger # force flask to create application logger before logging
                # configuration; else, flask will overwrite our settings

    logging_file = self.config.get('LOGGING_CONFIG_FILE')
    if logging_file:
      logging_file = os.path.abspath(os.path.join(self.instance_path,
                                                  logging_file))
      if logging_file.endswith('.conf'):
        # old standard 'ini' file config
        logging.config.fileConfig(logging_file, disable_existing_loggers=False)
      elif logging_file.endswith('.yml'):
        # yml config file
        logging_cfg = yaml.load(open(logging_file, 'r'))
        logging_cfg.setdefault('version', 1)
        logging.config.dictConfig(logging_cfg)

  def init_extensions(self):
    """ Initialize flask extensions, helpers and services
    """
    extensions.db.init_app(self)
    extensions.mail.init_app(self)
    actions.init_app(self)

    # webassets
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

    base_bundles = (
      ('css', Bundle(self.css_bundle,
                     filters='cssimporter, cssrewrite',
                     output='style-%(version)s.min.css')),
      ('js-top', Bundle(self.top_js_bundle, output='top-%(version)s.min.js')),
      ('js', Bundle(self.js_bundle, output='app-%(version)s.min.js')),
    )
    for name, bundle in base_bundles:
      assets.register(name, bundle)

    # webassets: setup static url for our assets
    from abilian.web import assets as core_bundles
    assets.append_path(core_bundles.RESOURCES_DIR, '/static/abilian')

    self.add_url_rule(
      self.static_url_path + '/abilian/<path:filename>',
      endpoint='abilian_static',
      view_func=partial(send_file_from_directory,
                        directory=core_bundles.RESOURCES_DIR))

    assets.url = self.static_url_path + '/min'
    self.add_url_rule(
      self.static_url_path + '/min/<path:filename>',
      endpoint='webassets_static',
      view_func=partial(send_file_from_directory, directory=assets_dir))

    # Babel (for i18n)
    extensions.babel.init_app(self)
    extensions.babel.add_translations('abilian')
    extensions.babel.localeselector(get_locale)
    extensions.babel.timezoneselector(get_timezone)

    auth_service.init_app(self)
    audit_service.init_app(self)
    index_service.init_app(self)
    activity_service.init_app(self)

    # celery async service
    extensions.celery.config_from_object(self.config)

    # dev helper
    if self.config['DEBUG']:
      self.register_blueprint(http_error_pages, url_prefix='/http_error')


  def register_plugins(self):
    """ Load plugins listed in config variable 'PLUGINS'
    """
    registered = set()
    for plugin_fqdn in chain(self.APP_PLUGINS, self.config['PLUGINS']):
      if plugin_fqdn not in registered:
        self.register_plugin(plugin_fqdn)
        registered.add(plugin_fqdn)

  # Jinja setup
  def create_jinja_environment(self):
    env = Flask.create_jinja_environment(self)
    env.globals.update(
      app=current_app,
      get_locale=babel_get_locale,
      NO_VALUE=NO_VALUE,
    )
    init_filters(env)
    return env

  @property
  def jinja_options(self):
    options = dict(Flask.jinja_options)
    if (self.config.get('DEBUG', False)
        and self.config.get('TEMPLATE_DEBUG', False)):
      options['undefined'] = jinja2.StrictUndefined
    return options

  def register_jinja_loaders(self, *loaders):
    """ Register one or many `jinja2.Loader` instances for templates lookup.

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
    """ Search templates in custom app templates dir (default flask behaviour),
    fallback on abilian templates
    """
    loaders = self._jinja_loaders
    del self._jinja_loaders
    loaders.append(Flask.jinja_loader.func(self))
    loaders.reverse()
    return jinja2.ChoiceLoader(loaders)

  # Error handling
  def handle_user_exception(self, e):
    # inconditionally forget all DB changes, and ensure clean session during
    # exception handling
    db.session.rollback()
    return Flask.handle_user_exception(self, e)

  def handle_exception(self, e):
    if not db.session().is_active:
      # something happened in error handlers and session is not usable, rollback
      # will restore a usable session
      db.session().rollback()
    return Flask.handle_exception(self, e)


  @property
  def db(self):
    return self.extensions['sqlalchemy'].db

  def create_db(self):
    from abilian.core.subjects import User
    with self.app_context():
      db.create_all()
      if User.query.get(0) is None:
        root = User(id=0, last_name=u'SYSTEM', email=u'system@example.com', can_login=False)
        db.session.add(root)
        db.session.commit()

  @property
  def css_bundle(self):
    """ :return: CSS resources
        :rtype: `webassets.Bundle <http://elsdoerfer.name/docs/webassets/bundles.html>`_
    """
    from abilian.web import assets as bundles
    debug = self.config.get('DEBUG')
    return bundles.CSS if not debug else bundles.CSS_DEBUG

  @property
  def top_js_bundle(self):
    """ Javascript resources to put before beginning of document, in <head>

        :return: JS resources
        :rtype: `webassets.Bundle <http://elsdoerfer.name/docs/webassets/bundles.html>`_
    """
    from abilian.web import assets as bundles
    debug = self.config.get('DEBUG')
    return bundles.TOP_JS if not debug else bundles.TOP_JS_DEBUG

  @property
  def js_bundle(self):
    """ Javascript resources to put at end of document, just before </body>

        :return: JS resources
        :rtype: `webassets.Bundle <http://elsdoerfer.name/docs/webassets/bundles.html>`_
    """
    from abilian.web import assets as bundles
    debug = self.config.get('DEBUG')
    return bundles.JS if not debug else bundles.JS_DEBUG

  def install_default_handler(self, http_error_code):
    """ Installs a default error handler for `http_error_code`.

    The default error handler renders a template named error404.html for
    http_error_code 404.
    """
    logger.debug('Set Default HTTP error handler for status code %d',
                 http_error_code)
    handler = partial(self.handle_http_error, http_error_code)
    self.errorhandler(http_error_code)(handler)

  def handle_http_error(self, code, error):
    """ Helper that renders error{code}.html

    Convenient way to use it::

       from functools import partial
       handler = partial(app.handle_http_error, code)
       app.errorhandler(code)(handler)
    """
    if (code / 100) == 5:
      # 5xx code: error on server side
      db.session.rollback() # ensure rollback if needed, else error page may
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
  # otherwise try to guess the language from the user accept
  # header the browser transmits.  We support de/fr/en in this
  # example.  The best match wins.
  return request.accept_languages.best_match(['en', 'fr'])

def get_timezone():
  return abilian.core.util.system_tz

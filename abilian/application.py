"""
Base Flask application class, used by tests or to be extended
in real applications.
"""
import os
import yaml
import logging
from itertools import chain

from werkzeug.datastructures import ImmutableDict
from flask import Flask, g, request, current_app, has_app_context
from flask.helpers import locked_cached_property
import jinja2

from abilian.core.extensions import mail, db, celery, babel
import abilian.core.util
from abilian.web.filters import init_filters
from abilian.plugin.loader import AppLoader
from abilian.services import audit_service, index_service, activity_service

logger = logging.getLogger(__name__)

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

    At this point, prefer explicit loading using the `register_plugin`
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

  #: custom apps may want to always load some plugins: list them here
  APP_PLUGINS = ()

  #: environment variable used to locate a config file to load last (after
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
    self.init_extensions()
    self.register_plugins()

    # Initialise Abilian core services.
    # Must come after all entity classes have been declared.
    # Inherited from ServiceManager. Will need some configuration love later.
    if not self.config.get('TESTING', False):
      if has_app_context():
        self.start_services()
      else:
        with self.app_context():
          self.start_services()

  def make_config(self, instance_relative=False):
    config = Flask.make_config(self, instance_relative)

    if self._ABILIAN_INIT_TESTING_FLAG:
      # testing: don't load any config file!
      return config

    if instance_relative:
      cfg_path = os.path.join(self.instance_path, 'config.py')
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
    db.init_app(self)
    mail.init_app(self)

    # Babel (for i18n)
    babel.init_app(self)
    babel.add_translations('abilian')
    babel.localeselector(get_locale)
    babel.timezoneselector(get_timezone)

    audit_service.init_app(self)
    index_service.init_app(self)
    activity_service.init_app(self)

    # celery async service
    celery.config_from_object(self.config)

  def register_plugins(self):
    """ Load plugins listing in config variable 'PLUGINS'
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

  @locked_cached_property
  def jinja_loader(self):
    """ Search templates in custom app templates dir (default flask behaviour),
    fallback on abilian templates
    """
    return jinja2.ChoiceLoader([
      Flask.jinja_loader.func(self),
      jinja2.PackageLoader('abilian', 'templates'),
    ])

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

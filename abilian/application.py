"""
Base Flask application class, used by tests or to be extended
in real applications.
"""
import yaml
from flask import Flask, g, request, logging
from flask.helpers import locked_cached_property
import jinja2

from abilian.core.extensions import mail, db, celery, babel
from abilian.web.filters import init_filters
from abilian.plugin.loader import AppLoader
from abilian.services import audit_service, index_service, activity_service

logger = logging.getLogger(__name__)

__all__ = ['create_app', 'Application', 'ServiceManager']


class ServiceManager(object):
  """
  Mixin that provides lifecycle (register/start/stop) support for services.

  XXX: too much hardcoding here.
  """

  def register_services(self):
    audit_service.init_app(self)
    index_service.init_app(self)
    activity_service.init_app(self)

  def start_services(self):
    audit_service.start()
    index_service.start()
    activity_service.start()

  def stop_services(self):
    audit_service.stop()
    index_service.stop()
    activity_service.stop()


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


class Application(Flask, ServiceManager, PluginManager):
  """
  Base application class. Extend it in your own app.
  """
  def __init__(self, config):
    Flask.__init__(self, __name__)

    # TODO: deal with envvar and pyfile
    self.config.from_object(config)
    self.setup_logging()

    # Initialise helpers and services
    db.init_app(self)
    mail.init_app(self)

    # Babel (for i18n)
    babel.init_app(self)
    babel.add_translations('abilian')
    babel.localeselector(get_locale)
    babel.timezoneselector(get_timezone)

    # celery async service
    celery.config_from_object(config)

    # Initialise filters
    init_filters(self)
    #init_auth(self)

    self.register_services()
    # Note

  def setup_logging(self):
    self.logger # force flask to create application logger before logging
                # configuration; else, flask will overwrite our settings

    logging_file = self.config.get('LOGGING_CONFIG_FILE')
    if logging_file:
      if logging_file.endswith('.conf'):
        # old standard 'ini' file config
        logging.config.fileConfig(logging_file, disable_existing_loggers=False)
      elif logging_file.endswith('.yml'):
        # yml config file
        logging_cfg = yaml.load(open(logging_file, 'r'))
        logging_cfg.setdefault('version', 1)
        logging.config.dictConfig(logging_cfg)

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


  def create_db(self):
    from abilian.core.subjects import User
    with self.app_context():
      db.create_all()
      if User.query.get(0) is None:
        root = User(id=0, last_name=u'SYSTEM', email=u'system@example.com', can_login=False)
        db.session.add(root)
        db.session.commit()


def create_app(config):
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

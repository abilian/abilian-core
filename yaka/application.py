"""
Base Flask application class, used by tests or to be extended
in real applications.
"""

from flask import Flask

from yaka.core.extensions import mail, db
from yaka.web.filters import init_filters

from yaka.services import audit_service, index_service, activity_service


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


class Application(Flask, ServiceManager):
  """
  Base application class. Extend it in your own app.
  """
  def __init__(self, config):
    Flask.__init__(self, __name__)

    # TODO: deal with envvar and pyfile
    self.config.from_object(config)

    # Initialise helpers and services
    db.init_app(self)
    mail.init_app(self)

    # Initialise filters
    init_filters(self)
    #init_auth(self)

    self.register_services()
    # Note

  def create_db(self):
    from yaka.core.subjects import User
    with self.app_context():
      db.create_all()
      if User.query.get(0) is None:
        root = User(id=0, last_name=u'SYSTEM', email='system@example.com', can_login=False)
        db.session.add(root)
        db.session.commit()


def create_app(config):
  return Application(config)

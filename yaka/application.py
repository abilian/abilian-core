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
  XXX: probably too much hardcoding here.
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


def create_app(config):
  return Application(config)

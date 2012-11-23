"""Application factory specific for the tests.

TODO: make it so it can be used as a base class for client application.
"""

from flask import Flask

from yaka.core.extensions import mail, db
from yaka.web.filters import init_filters

from yaka.services import audit_service, index_service


__all__ = ['create_app', 'Application']


class Application(Flask):
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

  def register_services(self):
    audit_service.init_app(self)
    index_service.init_app(self)

    # TODO:
    #self.extensions['activity'] = activity.get_service(self)

  def start_services(self):
    audit_service.start()
    index_service.start()

  def stop_services(self):
    audit_service.stop()
    index_service.stop()


def create_app(config):
  return Application(config)

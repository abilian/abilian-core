"""Application factory specific for the tests.
"""

from flask import Flask

from yaka.core.extensions import mail, db
from yaka.web.filters import init_filters

#from .auth import init_auth

from yaka.services import audit_service

# Import entity classes. Don't remove
# TODO move this to a plugin / app system
#from .apps.crm.entities import *
#from .apps.dm import File, Folder
#from .apps.crm.entities import *


__all__ = ['create_app']


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

  def register_services(self):
    audit_service.init_app(self)

    # Initiate services
    #self.extensions['indexing'] = indexing.get_service(self)
    #self.extensions['activity'] = activity.get_service(self)

  def start_services(self):
    audit_service.start()

  def stop_services(self):
    audit_service.stop()


def create_app(config):
  return Application(config)

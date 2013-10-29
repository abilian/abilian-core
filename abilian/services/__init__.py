"""
Modules that provide services. They are implemented as
Flask extensions (see: http://flask.pocoo.org/docs/extensiondev/ )

"""

from flask import current_app

from .base import Service, ServiceState

# Homegrown extensions.
from .audit import audit_service
from .indexing import service as index_service
from .conversion import converter
from .activity import ActivityService
from .auth import AuthService
from .settings import SettingsService

__all__ = ['Service', 'ServiceState', 'get_service',
           'audit_service', 'index_service', 'activity_service', 'auth_service',
           'settings_service']

auth_service = AuthService()
activity_service = ActivityService()
settings_service = SettingsService()

def get_service(service):
  return current_app.services.get(service)

"""
Modules that provide services. They are implemented as
Flask extensions (see: http://flask.pocoo.org/docs/extensiondev/ )

"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from flask import current_app

from .base import Service, ServiceState

# Homegrown extensions.
from .audit import audit_service
from .indexing import service as index_service
from .security import security as security_service
from .repository import (
    repository as repository_service,
    session_repository as session_repository_service,)
from .preferences import preferences as preferences_service
from .conversion import converter
from .activity import ActivityService
from .auth import AuthService
from .settings import SettingsService
from .vocabularies import vocabularies as vocabularies_service
from .antivirus import service as antivirus

__all__ = [
    'Service', 'ServiceState', 'get_service', 'audit_service', 'index_service',
    'activity_service', 'auth_service', 'settings_service', 'security_service',
    'preferences_service', 'repository_service', 'session_repository_service',
    'vocabularies_service', 'converter', 'antivirus'
]

auth_service = AuthService()
activity_service = ActivityService()
settings_service = SettingsService()


def get_service(service):
    return current_app.services.get(service)

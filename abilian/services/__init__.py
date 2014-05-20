"""
Modules that provide services. They are implemented as
Flask extensions (see: http://flask.pocoo.org/docs/extensiondev/ )

"""

__all__ = ['Service', 'ServiceState',
           'audit_service', 'index_service', 'activity_service']

from .base import Service, ServiceState

# Homegrown extensions.
from .audit import AuditService, audit_service
from .indexing import service as index_service
from .security import security as security_service
from .repository import (
  repository as repository_service,
  session_repository as session_repository_service,
)
from .preferences import preferences as preferences_service
from .conversion import converter
from .activity import ActivityService

__all__ = ['Service', 'ServiceState', 'get_service',
           'audit_service', 'index_service', 'activity_service', 'auth_service',
           'settings_service', 'security_service', 'preferences_service',
           'repository_service', 'session_repository_service']

from .activity import ActivityService
activity_service = ActivityService()

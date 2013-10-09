"""
Modules that provide services. They are implemented as
Flask extensions (see: http://flask.pocoo.org/docs/extensiondev/ )

"""

__all__ = ['Service', 'ServiceState',
           'audit_service', 'index_service', 'activity_service', 'auth_service']

from .base import Service, ServiceState

# Homegrown extensions.
from .audit import audit_service
from .indexing import service as index_service
from .conversion import converter

from .activity import ActivityService
activity_service = ActivityService()

from .auth import AuthService
auth_service = AuthService()

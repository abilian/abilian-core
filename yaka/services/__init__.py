"""Modules that provide services (no UI).

"""

__all__ = ['audit_service', 'index_service', 'activity_service']

# Homegrown extensions.
from .audit import AuditService
audit_service = AuditService()

from .indexing import WhooshIndexService
index_service = WhooshIndexService()

from .activity import ActivityService
activity_service = ActivityService()

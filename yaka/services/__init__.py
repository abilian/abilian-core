"""Modules that provide services (no UI).

"""

# Homegrown extensions.
from .audit import AuditService
audit_service = AuditService()

from .indexing import WhooshIndexService
index_service = WhooshIndexService()

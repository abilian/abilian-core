"""Application settings service."""
from .models import register
from .service import SettingsService

__all__ = ["SettingsService", "register"]

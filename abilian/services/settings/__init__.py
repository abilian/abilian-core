# coding=utf-8
"""Application settings service."""
from __future__ import absolute_import, division, print_function

from .models import register
from .service import SettingsService

__all__ = ["SettingsService", "register"]

# coding=utf-8
"""Modules that provide services.

They are implemented as Flask extensions (see:
http://flask.pocoo.org/docs/extensiondev/ )
"""
from __future__ import absolute_import, division, print_function

from flask import current_app

# This one first
from .base import Service, ServiceState

from .activity import ActivityService
from .antivirus import service as antivirus
from .audit import audit_service
from .auth import AuthService
from .conversion import conversion_service, converter
from .indexing import service as index_service
from .preferences import preferences as preferences_service
from .repository import repository as repository_service
from .repository import session_repository as session_repository_service
from .security import security as security_service
from .settings import SettingsService
from .vocabularies import vocabularies as vocabularies_service

auth_service = AuthService()
activity_service = ActivityService()
settings_service = SettingsService()


def get_service(service):
    return current_app.services[service]

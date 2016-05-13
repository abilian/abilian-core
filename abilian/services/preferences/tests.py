# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import current_app
from flask_login import current_user

from abilian.core.models.subjects import User
from abilian.testing import BaseTestCase

from .models import UserPreference
from .panel import PreferencePanel
from .service import PreferenceService


class VisiblePanel(PreferencePanel):
    id = label = 'visible'

    def is_accessible(self):
        return True

    def get(self):
        return u'Visible'


class AdminPanel(PreferencePanel):
    id = label = 'admin'

    def is_accessible(self):
        return current_app.services['security'].has_role(current_user, "admin")

    def get(self):
        return u'Admin'


class App(BaseTestCase.application_class):

    def init_extensions(self):
        super(App, self).init_extensions()
        prefs = self.services['preferences']
        prefs.app_state.panels = []
        prefs.register_panel(VisiblePanel(), self)
        prefs.register_panel(AdminPanel(), self)


class PreferencesTestCase(BaseTestCase):

    application_class = App

    def test_preferences(self):
        user = User(email=u"test@example.com")
        assert UserPreference.query.all() == []

        preference_service = PreferenceService()

        preferences = preference_service.get_preferences(user)
        self.assertEquals(preferences, {})

        preference_service.set_preferences(user, digest='daily')
        self.session.flush()

        preferences = preference_service.get_preferences(user)
        self.assertEquals(preferences, {'digest': 'daily'})

        preference_service.clear_preferences(user)
        self.session.flush()

        preferences = preference_service.get_preferences(user)
        self.assertEquals(preferences, {})
        assert UserPreference.query.all() == []

    def test_preferences_with_various_types(self):
        user = User(email=u"test@example.com")
        preference_service = PreferenceService()

        preference_service.set_preferences(user, some_int=1)
        self.session.flush()
        preferences = preference_service.get_preferences(user)
        self.assertEquals(preferences, {'some_int': 1})

        preference_service.set_preferences(user, some_bool=True)
        self.session.flush()
        preferences = preference_service.get_preferences(user)
        self.assertEquals(preferences, {'some_int': 1, 'some_bool': True})

    def test_visible_panels(self):
        user = User(email=u"test@example.com")
        app = self.app
        security = app.services['security']
        security.start()

        for cp in app.template_context_processors['preferences']:
            ctx = cp()
            if 'menu' in ctx:
                break

        with self.login(user):
            assert [p['endpoint']
                    for p in ctx['menu']] == ['preferences.visible']
            security.grant_role(user, 'admin')
            ctx = cp()
            assert [p['endpoint'] for p in ctx['menu']
                   ] == ['preferences.visible', 'preferences.admin']

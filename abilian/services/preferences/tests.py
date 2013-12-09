from abilian.core.subjects import User
from abilian.testing import BaseTestCase

from .service import PreferenceService
from .models import UserPreference


class PreferencesTestCase(BaseTestCase):

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

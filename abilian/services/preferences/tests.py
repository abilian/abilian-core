from abilian.core.subjects import User
from abilian.testing import BaseTestCase

from .service import PreferenceService


class PreferencesTestCase(BaseTestCase):

  def test_preferences(self):
    user = User(email="test@example.com")

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

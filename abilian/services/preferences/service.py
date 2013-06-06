"""User preference service. (Currently brainstorming the API).

Notes:

- Preferences are user-specific
- For global setting, there should be a SettingService
"""
from abilian.core.extensions import db

from .models import UserPreference


class PreferenceService(object):

  def __init__(self):
    self.preferences = {}

  def get_preferences(self, user=None):
    """Returns a string->value dictionnary representing the given user
    preferences.

    If no user is provided, the current user is used instead.
    """
    preferences = UserPreference.query.filter(UserPreference.user_id == user.id).all()
    return { pref.key: pref.value for pref in preferences}

  def set_preferences(self, user=None, **kwargs):
    """Sets preferences from keyword arguments.
    """
    preferences = UserPreference.query.filter(UserPreference.user_id == user.id).all()
    d = { pref.key: pref for pref in preferences}
    for k, v in kwargs.items():
      if k in d:
        d[k].value = v
      else:
        d[k] = UserPreference(key=k, value=v)
        db.session.add(d[k])

  def clear_preferences(self, user=None):
    """Clears the user preferences.
    """
    preferences = UserPreference.query.filter(UserPreference.user_id == user.id).all()
    for pref in preferences:
      db.session.delete(pref)

"""User preference service. (Currently brainstorming the API).

Notes:

- Preferences are user-specific
- For global setting, there should be a SettingService
"""


class PreferenceService(object):

  def get_preferences(self, user=None):
    """Returns a string->value dictionnary representing the given user
    preferences. If no user is provided, the current user is used instead.
    """

  def set_preferences(self, user=None, **kwargs):
    """Sets preferences from keyword arguments.
    """

  def clear_preferences(self, user=None):
    """Clears the user preferences."""
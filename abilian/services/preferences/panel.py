
class PreferencePanel(object):
  """
  Base classe for preference panels.

  Currently this class does nothing. I may be useful in the future either
  as just a marker interface (for automatic plugin discovery / registration),
  or to add some common functionnalities. Otherwise, it will be removed.
  """
  def is_accessible(self):
    return True

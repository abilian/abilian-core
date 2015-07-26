from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

class PreferencePanel(object):
  """
  Base class for preference panels.

  Currently, this class does nothing. I may be useful in the future either
  as just a marker interface (for automatic plugin discovery / registration),
  or to add some common functionnalities. Otherwise, it will be removed.
  """
  def is_accessible(self):
    return True

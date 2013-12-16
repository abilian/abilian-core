# coding=utf-8
"""
"""
from __future__ import absolute_import


class AdminPanel(object):
  """
  Base classe for admin panels.

  Currently this class does nothing. It may be useful in the future
  either as just a marker interface (for automatic plugin discovery /
  registration), or to add some common functionnalities. Otherwise, it
  will be removed.
  """
  id = None
  label = None
  icon = None

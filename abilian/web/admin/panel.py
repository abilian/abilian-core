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

  def install_additional_rules(self, add_url_rule):
    """
    This method can be redefined in subclasses to install custom url rules

    All rules are relative to panel 'base' rule, don't prefix rules with panel
    id, it will be done by `add_url_rule`.

    :param add_url_rule: function to use to add url rules, same interface as
        :meth:`flask.blueprint.Blueprint.add_url_rule`.
    """
    pass

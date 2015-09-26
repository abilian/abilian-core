# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division

from flask import current_app, g
from flask_debugtoolbar.panels import DebugPanel

from abilian.i18n import _
from abilian.web.action import actions


class ActionDebugPanel(DebugPanel):
  """

  """
  name = 'Actions'
  has_content = True
  routes = []

  def nav_title(self):
    return _('Actions')

  def title(self):
    return _('Actions')

  def url(self):
    return ''

  def content(self):
    actions_for_template = []
    for category, actions2 in actions.actions().items():
      for action in actions2:
        d = {
          'category': action.category,
          'title': action.title,
          'class': action.__class__.__name__,
        }
        try:
          d['endpoint'] = unicode(action.endpoint)
        except:
          d['endpoint'] = '<Exception>'
        try:
          d['url'] = action.url(g.action_context)
        except:
          d['url'] = '<Exception>'
        actions_for_template.append(d)

    actions_for_template.sort(key=lambda x: (x['category'], x['title']))

    ctx = {'actions': actions_for_template}

    jinja_env = current_app.jinja_env
    jinja_env.filters.update(self.jinja_env.filters)
    template = jinja_env.get_or_select_template(
      'debug_panels/actions_panel.html')
    return template.render(ctx)

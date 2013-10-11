# coding=utf-8
""" Navigation elements.

Abilian define theses categories:
  `section`:
    Used for navigation elements relevant to site section
  `user`:
    User for element that should appear in user menu
"""
from __future__ import absolute_import

from .action import Action

class NavItem(Action):
  """ A single navigation item
  """
  divider = False

  def __init__(self, category, name, divider=False, *args, **kwargs):
    category = 'navigation:' + category
    Action.__init__(self, category, name, *args, **kwargs)
    self.divider = divider

class NavGroup(NavItem):
  """ A navigation group renders a list of items
  """
  template_string = '''
    <ul class="nav navbar-nav">
      <li class="dropdown">
        <a href="#" class="dropdown-toggle" data-toggle="dropdown">
          {%- if action.icon %}<i class="glyphicon glyphicon-{{ action.icon }}"></i>{% endif %}
          {{ action.title }} <b class="caret"></b>
        </a>
        <ul class="dropdown-menu">
          {%- for item in action.items %}
          <li>{{ item.render() }}</li>
          {%- endfor %}
        </ul>
      </li>
    </ul>
    '''

  def __init__(self, category, name, items=(), *args, **kwargs):
    NavItem.__init__(self, category, name, *args, **kwargs)
    self.items = list(items)

  def append(self, item):
    self.items.append(item)



# coding=utf-8
"""
Navigation elements.

Abilian define theses categories:
  `section`:
    Used for navigation elements relevant to site section
  `user`:
    User for element that should appear in user menu
"""
from __future__ import absolute_import

from jinja2 import Template, Markup
from flask import url_for
from .action import Action, Endpoint, Glyphicon


class NavItem(Action):
  """
  A single navigation item.
  """
  divider = False

  def __init__(self, category, name, divider=False, *args, **kwargs):
    category = 'navigation:' + category
    Action.__init__(self, category, name, *args, **kwargs)
    self.divider = divider


class NavGroup(NavItem):
  """
  A navigation group renders a list of items.
  """
  template_string = '''
    <ul class="nav navbar-nav">
      <li class="dropdown">
        <a class="dropdown-toggle" data-toggle="dropdown">
          {%- if action.icon %}{{ action.icon }}{% endif %}
          {{ action.title }} <b class="caret"></b>
        </a>
        <ul class="dropdown-menu">
          {%- for item in action.items %}
          {%- if item.divider %}<li class="divider"></li>{%- endif %}
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


class BreadcrumbItem(object):
  """
  A breadcrumb element has at least a label or an icon.
  """
  #: Label shown to user. May be an i18n string instance
  label = None

  #: Icon to use.
  icon = None

  #: Additional text, can be used as tooltip for example
  description = None

  #: either an unicode string or an :class:`Endpoint` instance.
  _url = None

  template_string = (
    u'<a href="{{ item.url }}">'
    u'{%- if item.icon %}{{ item.icon }} {%- endif %}'
    u'{{ item.label }}'
    u'</a>'
    )

  def __init__(self, label=u'', url=u'#', icon=None, description=None):
    assert label or icon
    self.label = label
    if isinstance(icon, basestring):
      icon = Glyphicon(icon)

    self.icon = icon
    self.description = description
    self._url = url
    self.__template = Template(self.template_string)

  @property
  def url(self):
    return unicode(self._url)

  def render(self):
    return Markup(self.__template.render(item=self))

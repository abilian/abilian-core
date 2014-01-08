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
from .action import Action


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
          {%- if action.icon %}<i class="glyphicon glyphicon-{{ action.icon }}"></i>{% endif %}
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


class Endpoint(object):

  # FIXME: *args doesn't seem to be relevant.
  def __init__(self, name, *args, **kwargs):
    self.name = name
    self.args = args
    self.kwargs = kwargs

  def __unicode__(self):
    return unicode(url_for(self.name, *self.args, **self.kwargs))

  def __repr__(self):
    return 'Endpoint({name}, *{args}, **{kwargs})'.format(
      name=repr(self.name),
      args=repr(self.args),
      kwargs=repr(self.kwargs),
      )


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
    u'{%- if item.icon %}<i class="glyphicon glyphicon-{{ item.icon }}">'
    u'</i> {%- endif %}'
    u'{{ item.label }}'
    u'</a>'
    )

  def __init__(self, label=u'', url=u'#', icon=None, description=None):
    assert label or icon
    self.label = label
    self.icon = icon
    self.description = description
    self._url = url
    self.__template = Template(self.template_string)

  @property
  def url(self):
    return unicode(self._url)

  def render(self):
    return Markup(self.__template.render(item=self))

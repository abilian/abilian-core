# coding=utf-8
"""
Navigation elements.

Abilian define theses categories:
  `section`:
    Used for navigation elements relevant to site section
  `user`:
    User for element that should appear in user menu
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import g
from future.utils import string_types
from jinja2 import Markup, Template

from .action import ACTIVE, ENABLED, Action, Glyphicon, getset


class NavItem(Action):
    """
    A single navigation item.
    """
    divider = False

    def __init__(self, category, name, divider=False, *args, **kwargs):
        category = 'navigation:' + category
        Action.__init__(self, category, name, *args, **kwargs)
        self.divider = divider

    @getset
    def status(self, value=None):
        current = g.nav.get('active')
        if current is None:
            return ENABLED

        if not current.startswith('navigation:'):
            current = 'navigation:' + current

        status = ACTIVE if current == self.path else ENABLED
        return status

    @property
    def path(self):
        return self.category + ':' + self.name


class NavGroup(NavItem):
    """
    A navigation group renders a list of items.
    """
    template_string = '''
    <ul class="nav navbar-nav {{ action.css_class }}">
      <li class="dropdown">
        <a class="dropdown-toggle" data-toggle="dropdown">
          {%- if action.icon %}{{ action.icon }}{% endif %}
          {{ action.title }} <b class="caret"></b>
        </a>
        <ul class="dropdown-menu">
          {%- for item in action_items %}
          {%- if item.divider %}<li class="divider"></li>{%- endif %}
          <li class="{{ item.status|safe }}">{{ item.render() }}</li>
          {%- endfor %}
        </ul>
      </li>
    </ul>
    '''

    def __init__(self, category, name, items=(), *args, **kwargs):
        NavItem.__init__(self, category, name, *args, **kwargs)
        self.items = list(items)
        self._paths = {self.path}
        for i in self.items:
            self._paths.add(i.path)

    def append(self, item):
        self.items.append(item)
        self._paths.add(item.path)

    def insert(self, pos, item):
        self.items.insert(pos, item)
        self._paths.add(item.path)

    def get_render_args(self, **kwargs):
        params = super(NavGroup, self).get_render_args(**kwargs)
        params['action_items'] = [a for a in self.items if a.available(params)]
        return params

    @getset
    def status(self, value=None):
        current = g.nav.get('active')
        if current is None:
            return ENABLED

        if not current.startswith('navigation:'):
            current = 'navigation:' + current
        status = ACTIVE if current in self._paths else ENABLED
        return status


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

    template_string = (u'{%- if url %}<a href="{{ url }}">{%- endif %}'
                       u'{%- if item.icon %}{{ item.icon }} {%- endif %}'
                       u'{{ item.label }}'
                       u'{%- if url %}</a>{%- endif %}')

    def __init__(self, label=u'', url=u'#', icon=None, description=None):
        # don't test 'label or...': if label is a lazy_gettext, it will be
        # resolved. If this item is created in a url_value_preprocessor, it will
        # setup i18n before auth has loaded user, so i18n will fallback on browser
        # negociation instead of user's site preference, and load wrong catalogs for
        # the whole request.
        assert (label is not None or icon is None)
        self.label = label
        if isinstance(icon, string_types):
            icon = Glyphicon(icon)

        self.icon = icon
        self.description = description
        self._url = url
        self.__template = Template(self.template_string)

    @property
    def url(self):
        return unicode(self._url)

    def render(self):
        return Markup(self.__template.render(item=self, url=self.url))

# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import re

from flask import current_app, g
from flask.signals import appcontext_pushed
from future.utils import string_types
from jinja2 import Markup, Template

from abilian.core.singleton import UniqueName
from abilian.web import csrf
from abilian.web.util import url_for

log = logging.getLogger(__name__)

__all__ = ('Action', 'ModalActionMixin', 'actions')


class Status(UniqueName):
    """
    Action UI status names
    """

#: default action status: show in UID, usable, not marked "current"
ENABLED = Status(u'enabled')
#: action is "active" or "current". For example the current navigation item.
ACTIVE = Status(u'active')
#: action should be shown in a disabled state
DISABLED = Status(u'disabled')


def getset(f):
    """
    Shortcut for a custom getter/ standard setter.

    Usage::

      @getset
      def my_property(self, value=None):
          if value is None:
              return getter_value
          set_value(value)

    Default value for `value` should be any marker that helps distinguish
    between getter or setter mode. If None is not appropriate a good approach is
    to use a unique object instance::

      MARK = object()
      # test like this
      if value is MARK:
        # getter mode
    """
    return property(f, f)


class Icon(object):
    """Base abstract class for icons.
    """

    def __html__(self):
        raise NotImplementedError

    def __unicode__(self):
        return self.__html__()


class NamedIconBase(Icon):
    """Renders markup for named icons set.
    """
    template = None

    def __init__(self, name=u''):
        self.name = name

    def __html__(self):
        return self.template.render(name=self.name)


class Glyphicon(NamedIconBase):
    """Renders markup for bootstrap's glyphicons.
    """
    template = Template(u'<i class="glyphicon glyphicon-{{ name }}"></i>')


class FAIcon(NamedIconBase):
    """Renders markup for FontAwesome icons.
    """
    template = Template(u'<i class="fa fa-{{ name }}"></i>')


class FAIconStacked(NamedIconBase):
    """Stacked FA icons.
    """
    template = Template(
        u'<span class="fa-stack {%- if stack_class %} {{ stack_class }}'
        u'{%- endif %}">\n'
        u'  <i class="fa fa-{{ name }}"></i>\n'
        u'  <i class="fa fa-{{ second }}"></i>\n'
        u'</span>')

    def __init__(self, name, second, stack=u''):
        """
        @param name: first icon name, support additional css classes.

        @param second: second icon. Can be 'ban fa-stack-2x text-danger' for
        example.

        @param stack: additional class on top-level element, i.e 'fa-lg'.
        """
        if u'fa-stack-' not in name:
            name += u' fa-stack-1x'
        if u'fa-stack-' not in second:
            second += u' fa-stack-1x'

        super(FAIconStacked, self).__init__(name)
        self.second = second
        self.stack = stack

    def __html__(self):
        return self.template.render(name=self.name,
                                    second=self.second,
                                    stack_class=self.stack)


class DynamicIcon(Icon):
    template = Template(u'<img {%- if css %} class="{{ css }}"{% endif %} '
                        u'src="{{ url }}" '
                        u'width="{{ width }}" height="{{ height }}" />')

    def __init__(self,
                 endpoint=None,
                 width=12,
                 height=12,
                 css=u'',
                 size=None,
                 url_args=None,
                 **fixed_url_args):
        self.endpoint = endpoint
        self.css = css
        self.fixed_url_args = dict()
        self.fixed_url_args.update(fixed_url_args)
        self.url_args_callback = url_args

        if size is not None:
            width = height = size

        self.width = width
        self.height = height

    def get_url_args(self):
        kw = dict()
        kw.update(self.fixed_url_args)
        return kw

    def __html__(self):
        endpoint = self.endpoint
        if callable(endpoint):
            endpoint = endpoint()

        url_args = self.get_url_args()
        if self.url_args_callback is not None:
            url_args = self.url_args_callback(self, url_args)

        return self.template.render(url=url_for(endpoint, **url_args),
                                    width=self.width,
                                    height=self.height,
                                    css=self.css)


class StaticIcon(DynamicIcon):
    """
    Renders markup for icon located in static folder served by `endpoint`.

    Default endpoint is application static folder.
    """

    def __init__(self,
                 filename,
                 endpoint='static',
                 width=12,
                 height=12,
                 css=u'',
                 size=None):
        DynamicIcon.__init__(
            self, endpoint,
            width, height,
            css, size,
            filename=filename)


class Endpoint(object):

    # FIXME: *args doesn't seem to be relevant.
    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs

    def get_kwargs(self):
        """Hook for subclasses.

        The key and values in the returned dictionnary can be safely changed
        without side effects on self.kwargs (provided you don't alter
        mutable values, like calling list.pop()).
        """
        return self.kwargs.copy()

    def __unicode__(self):
        return unicode(url_for(self.name, *self.args, **self.get_kwargs()))

    def __repr__(self):
        return '{cls}({name!r}, *{args!r}, **{kwargs!r})'.format(
            cls=self.__class__.__name__,
            name=self.name,
            args=self.args,
            kwargs=self.kwargs,)


class Action(object):
    """Action interface.
    """
    Endpoint = Endpoint
    category = None
    name = None
    title = None
    description = None
    icon = None
    _url = None
    CSS_CLASS = u'action action-{category} action-{category}-{name}'

    #: A :class:`Endpoint` instance, a string for a simple endpoint, a tuple
    #: ``(endpoint_name, kwargs)``  or a callable which accept a : context dict
    #: and returns one of those a valid values.
    endpoint = None

    #: A boolean (or something that can be converted to boolean), or a callable
    #: which accepts a context dict as parameter. See :meth:`available`.
    condition = None

    template_string = (u'<a class="{{ action.css_class }}" href="{{ url }}">'
                       u'{%- if action.icon %}{{ action.icon }} {% endif %}'
                       u'{{ action.title }}'
                       u'</a>')

    def __init__(self,
                 category,
                 name,
                 title=None,
                 description=None,
                 icon=None,
                 url=None,
                 endpoint=None,
                 condition=None,
                 status=None,
                 template=None,
                 template_string=None,
                 button=None,
                 css=None):
        """
        :param button: if not `None`, a valid `btn` class (i.e `default`,
        `primary`...)

        :param css: additional css class string

        :param template: optional: a template file name or a list of filenames.

        :param template_string: template_string to use. Defaults to
        `Action.template_string`
        """
        self.category = category
        self.name = name

        if button is not None:
            self.CSS_CLASS = self.CSS_CLASS + u' btn btn-{}'.format(button)
        if css is not None:
            self.CSS_CLASS = self.CSS_CLASS + u' ' + css
        self._build_css_class()

        self.title = title
        self.description = description
        if isinstance(icon, string_types):
            icon = Glyphicon(icon)
        self.icon = icon
        self._url = url
        self._status = Status(status) if status is not None else ENABLED
        self.endpoint = endpoint
        if not callable(endpoint) and not isinstance(endpoint, Endpoint):
            # property getter will make it and Endpoint instance
            self.endpoint = self.endpoint
        self.condition = condition

        self._enabled = True
        self.template = template
        if template_string:
            self.template_string = template_string

    #: ui status. A :class:`Status` instance
    @getset
    def status(self, value=None):
        status = self._status
        if value is not None:
            self._status = status = Status(value)
        return status

    #: Boolean. Disabled actions are unconditionnaly skipped.
    @getset
    def enabled(self, value=None):
        enabled = self._enabled
        if value is not None:
            assert isinstance(value, bool)
            self._enabled = enabled = value
        return enabled

    def _get_and_call(self, attr):
        attr = '_' + attr
        value = getattr(self, attr)
        if callable(value):
            value = value(actions.context)
        return value

    @property
    def title(self):
        return self._get_and_call('title')

    @title.setter
    def title(self, title):
        self._title = title

    def _build_css_class(self):
        css_cat = self.CSS_CLASS.format(action=self,
                                        category=self.category,
                                        name=self.name)
        css_cat = re.sub(r'[^ _a-zA-Z0-9-]', '-', css_cat)
        self.css_class = css_cat

    @property
    def description(self):
        return self._get_and_call('description')

    @description.setter
    def description(self, description):
        self._description = description

    @property
    def icon(self):
        return self._get_and_call('icon')

    @icon.setter
    def icon(self, icon):
        self._icon = icon

    @property
    def endpoint(self):
        endpoint = self._get_and_call('endpoint')
        if endpoint is None:
            return

        if not isinstance(endpoint, Endpoint):
            if isinstance(endpoint, string_types):
                endpoint = self.Endpoint(endpoint)
            elif isinstance(endpoint, (tuple, list)):
                assert len(endpoint) == 2
                endpoint, kwargs = endpoint
                assert isinstance(endpoint, string_types)
                assert isinstance(kwargs, dict)
                endpoint = self.Endpoint(endpoint, **kwargs)
            else:
                raise ValueError('Invalid endpoint specifier: "%s"' %
                                 repr(endpoint))

        return endpoint

    @endpoint.setter
    def endpoint(self, endpoint):
        self._endpoint = endpoint

    def available(self, context):
        """
        Determine if this actions is available in this `context`.

        :param context: a dict whose content is left to application needs; if
                        :attr:`.condition` is a callable it receives `context`
                        in parameter.
        """
        if not self._enabled:
            return False
        try:
            return self.pre_condition(context) and self._check_condition(
                context)
        except:
            return False

    def pre_condition(self, context):
        """
        Called by :meth:`.available` before checking condition.

        Subclasses may override it to ease creating actions with repetitive
        check (for example: actions that apply on a given content type
        only).
        """
        return True

    def _check_condition(self, context):
        if self.condition is None:
            return True

        if callable(self.condition):
            return self.condition(context)
        else:
            return bool(self.condition)

    def render(self, **kwargs):
        if not self.template:
            self.template = Template(self.template_string)

        template = self.template

        if not isinstance(template, Template):
            template = current_app.jinja_env.get_or_select_template(template)

        params = self.get_render_args(**kwargs)
        return Markup(template.render(params))

    def get_render_args(self, **kwargs):
        params = dict(action=self)
        params.update(actions.context)
        params.update(kwargs)
        params['csrf'] = csrf
        params['url'] = self.url(params)
        return params

    def url(self, context=None):
        if callable(self._url):
            return self._url(context)

        endpoint = self.endpoint
        if endpoint:
            return unicode(endpoint)
        return self._url


class ModalActionMixin(object):
    template_string = (
        u'<a class="{{ action.css_class }}" href="{{ url }}" data-toggle="modal">'
        u'{%- if action.icon %}{{ action.icon}} {% endif %}'
        u'{{ action.title }}'
        u'</a>')


class ButtonAction(Action):
    template_string = (
        u'<button type="submit" '
        u'class="btn btn-{{ action.btn_class }} {{ action.css_class}}" '
        u'name="{{ action.submit_name }}" '
        u'value="{{ action.name }}">'
        u'{%- if action.icon %}{{ action.icon }} {% endif %}'
        u'{{ action.title }}</button>')

    btn_class = 'default'

    def __init__(self,
                 category,
                 name,
                 submit_name="__action",
                 btn_class='default',
                 *args,
                 **kwargs):
        Action.__init__(self, category, name, *args, **kwargs)
        self.submit_name = submit_name
        self.btn_class = btn_class


class ActionGroup(Action):
    """A group of single actions
    """
    template_string = (
        u'<div class="btn-group" role="group" aria-label="{{ action.name}}">'
        u'{%- for entry in action_items %}'
        u'{{ entry.render() }}'
        u'{%- endfor %}'
        u'</div>')

    def __init__(self, category, name, items=(), *args, **kwargs):
        super(ActionGroup, self).__init__(category, name, *args, **kwargs)
        self.items = list(items)

    def get_render_args(self, **kwargs):
        params = super(ActionGroup, self).get_render_args(**kwargs)
        params['action_items'] = [a for a in self.items if a.available(params)]
        return params


class ActionDropDown(ActionGroup):
    """Renders as a button dropdown
    """
    template_string = u'''
  <div class="btn-group">
    <button type="button" class="{{ action.css_class }} dropdown-toggle"
            data-toggle="dropdown" aria-expanded="false">
    {%- if action.icon %}{{ action.icon }} {% endif %}
    {{ action.title }}
    <span class="caret"></span>
    </button>
    <ul class="dropdown-menu" role="menu">
    {%- for entry in action_items %}
      {%- if entry.divider %}<li class="divider"></li>{%- endif %}
      <li>{{ entry.render() }}</a>
      </li>
    {%- endfor %}
    </ul>
  </div>
  '''


class ActionGroupItem(Action):
    #: if True, add a divider in dropdowns
    divider = False

    def __init__(self, category, name, divider=False, *args, **kwargs):
        super(ActionGroupItem, self).__init__(category, name, *args, **kwargs)
        self.divider = divider


class ActionRegistry(object):
    """The Action registry.

    This is a Flask extension which registers :class:`.Action` sets. Actions are
    grouped by category and are ordered by registering order.

    From your application use the instanciated registry :data:`.actions`.

    The registry is available in jinja2 templates as `actions`.
    """
    __EXTENSION_NAME = 'abilian:actions'

    def init_app(self, app):
        if self.__EXTENSION_NAME in app.extensions:
            log.warning(
                'ActionRegistry.init_app: actions already enabled on this application')
            return

        app.extensions[self.__EXTENSION_NAME] = dict(categories=dict())
        appcontext_pushed.connect(self._init_context, app)

        @app.context_processor
        def add_registry_to_jinja_context():
            return dict(actions=self)

    def installed(self, app=None):
        """Return `True` if the registry has been installed in current applications
        """
        if app is None:
            app = current_app
        return self.__EXTENSION_NAME in app.extensions

    def register(self, *actions):
        """ Register `actions` in the current application. All `actions` must be an
        instance of :class:`.Action` or one of its subclasses.

        If `overwrite` is `True`, then it is allowed to overwrite an existing
        action with same name and category; else `ValueError` is raised.
        """
        assert self.installed(), "Actions not enabled on this application"
        assert all(map(lambda a: isinstance(a, Action), actions))

        for action in actions:
            cat = action.category
            reg = self._state['categories'].setdefault(cat, [])
            reg.append(action)

    def actions(self, context=None):
        """ Return a mapping of category => actions list.

        Actions are filtered according to :meth:`.Action.available`.

        if `context` is None, then current action context is used
        (:attr:`context`).
        """
        assert self.installed(), "Actions not enabled on this application"
        result = {}
        if context is None:
            context = self.context

        for cat, actions in self._state['categories'].items():
            result[cat] = [a for a in actions if a.available(context)]
        return result

    def for_category(self, category, context=None):
        """ Returns actions list for this category in current application.

        Actions are filtered according to :meth:`.Action.available`.

        if `context` is None, then current action context is used
        (:attr:`context`)
        """
        assert self.installed(), "Actions not enabled on this application"
        actions = self._state['categories'].get(category, [])

        if context is None:
            context = self.context

        return filter(lambda a: a.available(context), actions)

    @property
    def _state(self):
        return current_app.extensions[self.__EXTENSION_NAME]

    def _init_context(self, sender):
        g.action_context = {}

    @property
    def context(self):
        """ Return action context (dict type). Applications can modify it to suit
        their needs.
        """
        return g.action_context


actions = ActionRegistry()

# coding=utf-8
import logging
from jinja2 import Template, Markup
from flask import current_app, g, url_for

log = logging.getLogger(__name__)

__all__ = ('Action', 'ModalActionMixin', 'actions')


def getset(f):
  """ Shortcut for a custom getter/ standard setter
  """
  return property(f, f)


class Action(object):
  """ Action interface.
  """
  category = None
  name = None
  title = None
  description = None
  icon = None
  _url = None

  #: A string for a simple endpoint, a tuple ``(endpoint_name, kwargs)`` to be
  #: passed to ``url_for(endpoint_name, **kwargs)`` or a callable which accept a
  #: context dict and returns a valid value.
  endpoint = None

  #: A boolean (or something that can be converted to boolean), or a callable
  #: which accepts a context dict as parameter.
  condition = None

  template_string = (
    u'<a href="{{ url }}">'
    u'{%- if action.icon %}<i class="glyphicon glyphicon-{{ action.icon }}"></i> {% endif %}'
    u'{{ action.title }}'
    u'</a>'
  )

  def __init__(self, category, name, title=None, description=None, icon=None,
               url=None, endpoint=None, condition=None):
    self.category = category
    self.name = name

    self.title = title
    self.description = description
    self.icon = icon
    self._url = url
    self.endpoint = endpoint
    self.condition = condition

    self._active = True

  #: Boolean. Inactive actions are unconditionnaly skipped.
  @getset
  def active(self, value=None):
    active = self._active
    if value is not None:
      assert isinstance(value, bool)
      self._active = active = value
    return active

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

    if isinstance(endpoint, basestring):
      endpoint = (endpoint, {})
    elif isinstance(endpoint, (tuple, list)):
      assert len(endpoint) == 2
      assert isinstance(endpoint[0], basestring)
      assert isinstance(endpoint[1], dict)
    else:
      raise ValueError('Invalid endpoint specifier: "%s"' % repr(endpoint))

    return endpoint

  @endpoint.setter
  def endpoint(self, endpoint):
    self._endpoint = endpoint

  def available(self, context):
    """ Determine if this actions is available in this `context`. `context`
    is a dict whose content is left to application needs; if :attr:`.condition`
    is a callable it receives `context` in parameter.
    """
    if not self._active:
      return False
    return self.pre_condition(context) and self._check_condition(context)

  def pre_condition(self, context):
    """ Called by :meth:`.available` before checking condition. Subclasses may
    override it to ease creating actions with repetitive check (for example:
    actions that apply on a given content type only).
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
    params = dict(action=self)
    params.update(actions.context)
    params.update(kwargs)
    params['url'] = self.url(params)
    tmpl = Template(self.template_string)
    return Markup(tmpl.render(params))

  def url(self, context=None):
    if callable(self._url):
      return self._url(context)

    endpoint = self.endpoint
    if endpoint:
      return url_for(endpoint[0], **endpoint[1])
    return self._url


class ModalActionMixin(object):
  template_string = (
    u'<a href="{{ url }}" data-toggle="modal">'
    u'{%- if action.icon %}<i class="glyphicon glyphicon-{{ action.icon }}"></i> {% endif %}'
    u'{{ action.title }}'
    u'</a>'
  )

class ButtonAction(Action):
  template_string = (
    u'<button type="submit" class="btn btn-{{ action.btn_class }}" '
    u'name="{{ action.submit_name }}" '
    u'value="{{ action.name }}">'
    u'{%- if action.icon %}<i class="glyphicon glyphicon-{{ action.icon }}"></i> {% endif %}'
    u'{{ action.title }}</button>'
  )

  btn_class = 'default'

  def __init__(self, category, name, submit_name="__action", btn_class= 'default',
               *args, **kwargs):
        Action.__init__(self, category, name, *args, **kwargs)
        self.submit_name = submit_name
        self.btn_class = btn_class


class ActionRegistry(object):
  """ The Action registry.

  This is a Flask extension which registers :class:`.Action` sets. Actions are
  grouped by category and are ordered by registering order.

  From your application use the instanciated registry :data:`.actions`.

  The registry is available in jinja2 templates as `actions`.
  """
  __EXTENSION_NAME = 'abilian:actions'

  def init_app(self, app):
    if self.__EXTENSION_NAME in app.extensions:
      log.warning('ActionRegistry.init_app: actions already enabled on this application')
      return

    app.extensions[self.__EXTENSION_NAME] = dict(categories=dict())
    app.before_request(self._before_request)

    @app.context_processor
    def add_registry_to_jinja_context():
      return dict(actions=self)

  def installed(self, app=None):
    """ Return `True` if the registry has been installed in current applications
    """
    if app == None:
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

  def _before_request(self):
    g.action_context = {}

  @property
  def context(self):
    """ Return action context (dict type). Applications can modify it to suit
    their needs.
    """
    return g.action_context

actions = ActionRegistry()

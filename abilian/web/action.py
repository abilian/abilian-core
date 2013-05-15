# coding=utf-8
from jinja2 import Template, Markup
from flask import current_app, g

__all__ = ('Action', 'ModalActionMixin', 'actions')

class Action(object):
  """ Action interface
  """
  category = None
  name = None
  title = None
  description = None
  icon = None
  _url = None
  #: a bool (or something that can be converted to bool), or a callable which
  #: accept a context dict as parameter.
  condition = None

  template_string = (
    u'<a href="{{ url }}">'
    u'{%- if action.icon %}<i class="icon-{{ action.icon }}"></i>{%- endif %}'
    u'{{ action.title }}'
    u'</a>'
    )

  def __init__(self, category, name, title=None, description=None, icon=None,
               url=None, condition=None):
    self.category = category
    self.name = name

    if title is not None:
      self.title = title
    if description is not None:
      self.description = description
    if icon is not None:
      self.icon = icon
    if url is not None:
      self._url = url
    if condition is not None:
      self.condition = condition

    self._active = True

  def _active_getset(self, value=None):
    active = self._active
    if value is not None:
      assert isinstance(value, bool)
      self._active = active = value
    return active

  #: boolean. Inactive actions are unconditionnaly skipped
  active = property(_active_getset, _active_getset)

  def available(self, context):
    """ Determine if this actions is available in this ``context``. ``context``
    is a dict whose content is left to application needs; if :attr:`.condition`
    is a callable it receives ``context`` in parameter.
    """
    if not self._active:
      return False
    return self.pre_condition(context) and self._check_condition(context)

  def pre_condition(self, context):
    """ Called by :meth:``.available`` before checking condition. Subclasses may
    override it to ease creating actions with repetitive check (for example:
    actions that apply on a given content type only)
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
    return self._url


class ModalActionMixin(object):
  template_string = (
    u'<a href="{{ url }}" data-toggle="modal">'
    u'{%- if action.icon %}<i class="icon-{{ action.icon }}"></i>{%- endif %}'
    u'{{ action.title }}'
    u'</a>'
    )


class ActionRegistry(object):
  """ The Action registry.

  This is a Flask extension which registers :class:`.Action` sets. Actions are
  grouped by category and are ordered by registering order.

  From your application use the instanciated registry :data:`.actions`.

  The registry is available in jinja2 templates as ``actions``
  """
  __EXTENSION_NAME = 'abilian:actions'

  def init_app(self, app):
    app.extensions[self.__EXTENSION_NAME] = dict(categories=dict())
    app.before_request(self._before_request)

    @app.context_processor
    def add_registry_to_jinja_context():
      return dict(actions=self)

  def installed(self, app=None):
    """ Return True if the registry has been installed in current applications
    """
    if app == None:
      app = current_app
    return self.__EXTENSION_NAME in app.extensions

  def register(self, *actions):
    """ Register ``actions`` in current application. All ``actions`` must be an
    instance of :class:`.Action` or one of its subclasses.

    If ``overwrite`` is True then it is allowed to overwrite an existing
    action with same name and category; else ValueError is raised.
    """
    assert(self.installed(), "Actions not enabled on this application")
    assert(all(map(lambda a: isinstance(a, Action), actions)))

    for action in actions:
      cat = action.category
      reg = self._state['categories'].setdefault(cat, [])
      reg.append(action)

  def actions(self, context=None):
    """ Return a mapping of category => actions list.

    Actions are filtered according to :meth:`.Action.available`.

    if ``context`` is None, then current action context is used
    (:attr:``context``)
    """
    assert(self.installed(), "Actions not enabled on this application")
    result = {}
    if context is None:
      context = self.context

    for cat, actions in self._state['categories'].items():
      result[cat] = [a for a in actions if a.available(context)]
    return result

  def for_category(self, category, context=None):
    """ Returns actions list for this category in current application.

    Actions are filtered according to :meth:`.Action.available`.

    if ``context`` is None, then current action context is used
    (:attr:``context``)
    """
    assert(self.installed(), "Actions not enabled on this application")
    try:
      actions = self._state['categories'][category]
    except KeyError:
      raise KeyError('Category "{category} does not exist"')

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

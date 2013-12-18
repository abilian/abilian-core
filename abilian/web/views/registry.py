# coding=utf-8
from __future__ import absolute_import

import inspect
from flask import url_for, Blueprint
from abilian.core.entities import Entity


class Registry(object):
  """
  Registry for default (canonical) views for entities.

  There is one registry per application instance.
  """
  def __init__(self, *args, **kwargs):
    self._map = dict()

  def register(self, entity, url_func):
    """
    Associates a `url_func` with entity's type.

    :param:entity: an :class:`abilian.core.entities.Entity` class or
    instance.

    :param:url_func: any callable that accepts an entity instance and
    return an url for it.
    """
    if not inspect.isclass(entity):
      entity = entity.__class__
    assert issubclass(entity, Entity)
    self._map[entity.entity_type] = url_func

  def url_for(self, entity, object_id=None):
    """
    Returns canonical view for given entity instance.


    If no view has been registered the registry will try to find an
    endpoint named with entity's class lowercased followed by '.view'
    and that accepts `object_id=entity.id` to generates an url.

    :param entity: a instance of a subclass of
        :class:`abilian.core.entities.Entity`, or an object type string.

    :param object_id: if `entity` is not an instance, this parameter
        must be set to target id. This is usefull when you know the type and
        id of an object but don't want to retrieve it from DB.

    :raise KeyError: if no view can be found for the given entity.
    """
    object_type = entity

    if not isinstance(object_type, basestring):
      assert isinstance(entity, Entity)
      object_id = entity.id
      object_type = entity.object_type

    url_func = self._map.get(object_type)
    if url_func is not None:
      return url_func(entity, object_type, object_id)

    try:
      return url_for('{}.view'.format(object_type.rsplit('.')[-1].lower()),
                     object_id=object_id)
    except:
      raise KeyError(object_type)


class default_view(object):
  """
  Decorator to register a view as default view for given entity class.
  """

  def __init__(self, app_or_blueprint, entity, id_attr='object_id', endpoint=None):
    self.app_or_blueprint = app_or_blueprint
    self.is_bp = isinstance(app_or_blueprint, Blueprint)
    self.entity = entity
    self.id_attr = id_attr
    self.endpoint = endpoint

  def __call__(self, view):
    endpoint = self.endpoint

    if endpoint is None:
      endpoint = view.__name__
      if self.is_bp:
        endpoint = '.' + endpoint

    if endpoint[0] == '.':
      endpoint = self.app_or_blueprint.name + endpoint

    def default_url(obj, obj_type, obj_id):
      kwargs = { self.id_attr: obj_id }
      return url_for(endpoint, **kwargs)

    if self.is_bp:
      @self.app_or_blueprint.record_once
      def set_default_view(state):
        state.app.default_view.register(self.entity, default_url)
    else:
      self.app_or_blueprint.default_view.register(self.entity, default_url)

    return view

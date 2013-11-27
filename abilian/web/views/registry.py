# coding=utf-8
from __future__ import absolute_import

import inspect
from functools import partial
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

  def url_for(self, entity):
    """
    Returns canonical view for given entity instance.


    If no view has been registered the registry will try to find an endpoint
    named with entity's class lowercased followed by '.view' and that
    accepts `object_id=entity.id` to generates an url.

    :raise:KeyError if no view can be found for the given entity.
    """
    assert isinstance(entity, Entity)
    url_func = self._map.get(entity.entity_type)
    if url_func is not None:
      return url_func(entity)

    try:
      return url_for('{}.view'.format(entity.__class__.__name__.lower()),
                     object_id=entity.id)
    except:
      raise KeyError(entity.entity_type)


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

    def default_url(obj):
      kwargs = { self.id_attr: obj.id }
      return url_for(endpoint, **kwargs)

    if self.is_bp:
      @self.app_or_blueprint.record_once
      def set_default_view(state):
        state.app.default_view.register(self.entity, default_url)
    else:
      self.app_or_blueprint.default_view.register(self.entity, default_url)

    return view

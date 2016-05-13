# coding=utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import inspect
from operator import attrgetter, itemgetter

from flask import Blueprint, url_for
from whoosh.searching import Hit

from abilian.core.extensions import db


class Registry(object):
    """
    Registry for default (canonical) views for entities.

    There is one registry per application instance.
    """

    def __init__(self, *args, **kwargs):
        self._map = dict()

    def register(self, entity, url_func):
        """
        Associate a `url_func` with entity's type.

        :param:entity: an :class:`abilian.core.extensions.db.Model` class or
        instance.

        :param:url_func: any callable that accepts an entity instance and
        return an url for it.
        """
        if not inspect.isclass(entity):
            entity = entity.__class__
        assert issubclass(entity, db.Model)
        self._map[entity.entity_type] = url_func

    def url_for(self, entity=None, object_type=None, object_id=None, **kwargs):
        """
        Return canonical view URL for given entity instance.

        If no view has been registered the registry will try to find an
        endpoint named with entity's class lowercased followed by '.view'
        and that accepts `object_id=entity.id` to generates an url.

        :param entity: a instance of a subclass of
            :class:`abilian.core.extensions.db.Model`,
            :class:`whoosh.searching.Hit` or :class:`python:dict`

        :param object_id: if `entity` is not an instance, this parameter
            must be set to target id. This is usefull when you know the type and
            id of an object but don't want to retrieve it from DB.

        :raise KeyError: if no view can be found for the given entity.
        """
        if object_type is None:
            assert isinstance(entity, (db.Model, Hit, dict))
            getter = attrgetter if isinstance(entity, db.Model) else itemgetter
            object_id = getter('id')(entity)
            object_type = getter('object_type')(entity)

        url_func = self._map.get(object_type)
        if url_func is not None:
            return url_func(entity, object_type, object_id, **kwargs)

        try:
            return url_for(
                '{}.view'.format(object_type.rsplit('.')[-1].lower()),
                object_id=object_id,
                **kwargs)
        except:
            raise KeyError(object_type)


class default_view(object):
    """
    Decorator to register a view as default view for given entity class.

    :param id_attr: url parameter name for object id.
    :param endpoint: endpoint to use, defaults to view function's name.
    :param kw_func: function to process keywords to be passed to url_for. Useful
       for additional keywords. This function receives: kw, obj, obj_type,
       obj_id, \*\*kwargs. It must return kw.
    """

    def __init__(self,
                 app_or_blueprint,
                 entity,
                 id_attr='object_id',
                 endpoint=None,
                 kw_func=None):
        self.app_or_blueprint = app_or_blueprint
        self.is_bp = isinstance(app_or_blueprint, Blueprint)
        self.entity = entity
        self.id_attr = id_attr
        self.endpoint = endpoint
        self.kw_func = kw_func

    def __call__(self, view):
        endpoint = self.endpoint

        if endpoint is None:
            endpoint = view.__name__
            if self.is_bp:
                endpoint = '.' + endpoint

        if endpoint[0] == '.':
            endpoint = self.app_or_blueprint.name + endpoint

        def default_url(obj, obj_type, obj_id, **kwargs):
            kw = {}
            kw.update(kwargs)
            if self.id_attr is not None:
                # some objects have url with GET parameters only
                kw[self.id_attr] = obj_id

            if self.kw_func:
                kw = self.kw_func(kw, obj, obj_type, obj_id, **kwargs)
            return url_for(endpoint, **kw)

        if self.is_bp:

            @self.app_or_blueprint.record_once
            def set_default_view(state):
                state.app.default_view.register(self.entity, default_url)
        else:
            self.app_or_blueprint.default_view.register(self.entity,
                                                        default_url)

        return view

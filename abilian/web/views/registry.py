import inspect
from operator import attrgetter, itemgetter
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Type, Union

from flask import Blueprint, url_for
from flask.blueprints import BlueprintSetupState
from whoosh.searching import Hit

from abilian.core.entities import Entity
from abilian.core.extensions import db

if TYPE_CHECKING:
    from abilian.app import Application


class Registry:
    """Registry for default (canonical) views for entities.

    There is one registry per application instance.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._map: Dict[str, Callable] = {}

    def register(self, entity: Union[Entity, Type[Entity]], url_func: Callable) -> None:
        """Associate a `url_func` with entity's type.

        :param:entity: an :class:`abilian.core.extensions.db.Model` class or
            instance.
        :param:url_func: any callable that accepts an entity instance and
            return an url for it.
        """
        if not inspect.isclass(entity):
            entity = entity.__class__
        assert issubclass(entity, db.Model)
        self._map[entity.entity_type] = url_func

    def url_for(
        self,
        entity: Union[db.Model, Hit, Dict, None] = None,
        object_type: Optional[str] = None,
        object_id: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Return canonical view URL for given entity instance.

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
        assert isinstance(entity, (db.Model, Hit, dict))
        if object_type is None:
            getter = attrgetter if isinstance(entity, db.Model) else itemgetter
            object_id = getter("id")(entity)
            object_type = getter("object_type")(entity)

        url_func: Optional[Callable] = self._map.get(object_type)
        if url_func is not None:
            return url_func(entity, object_type, object_id, **kwargs)

        try:
            blueprint_name = object_type.rsplit(".")[-1].lower()
            endpoint = f"{blueprint_name}.view"
            return url_for(endpoint, object_id=object_id, **kwargs)
        except Exception:
            raise KeyError(object_type)


class default_view:
    r"""Decorator to register a view as default view for given entity class.

    :param id_attr: url parameter name for object id.
    :param endpoint: endpoint to use, defaults to view function's name.
    :param kw_func: function to process keywords to be passed to url_for. Useful
       for additional keywords. This function receives: kw, obj, obj_type,
       obj_id, \*\*kwargs. It must return kw.
    """

    def __init__(
        self,
        app_or_blueprint: Union["Application", Blueprint],
        entity: Entity,
        id_attr: str = "object_id",
        endpoint: Optional[Any] = None,
        kw_func: Optional[Any] = None,
    ) -> None:
        self.app_or_blueprint = app_or_blueprint
        self.is_bp = isinstance(app_or_blueprint, Blueprint)
        self.entity = entity
        self.id_attr = id_attr
        self.endpoint = endpoint
        self.kw_func = kw_func

    def __call__(self, view: Callable) -> Callable:
        endpoint = self.endpoint

        if endpoint is None:
            endpoint = view.__name__
            if self.is_bp:
                endpoint = "." + endpoint

        if endpoint[0] == ".":
            endpoint = self.app_or_blueprint.name + endpoint

        def default_url(obj: Entity, obj_type: str, obj_id: int, **kwargs: Any) -> str:
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
            def set_default_view(state: BlueprintSetupState) -> None:
                state.app.default_view.register(self.entity, default_url)

        else:
            self.app_or_blueprint.default_view.register(self.entity, default_url)

        return view

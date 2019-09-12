import logging
from typing import TYPE_CHECKING, Any, Optional, Tuple, Type

from flask import Request
from sqlalchemy import func, orm
from sqlalchemy.sql.expression import or_

from abilian.core.entities import EntityQuery
from abilian.core.models import Model

if TYPE_CHECKING:
    from abilian.web.frontend import Module

logger = logging.getLogger(__name__)


class UNDEFINED:
    pass


_UNDEFINED = UNDEFINED()


class BaseCriterion:
    form_default_value: Any = _UNDEFINED
    """
    Values to set by default when adding a filter. The provided value(s) must be
    the ones used in html, not in python.

    Subclasses can also define property.
    """

    def __init__(
        self, name: str, label: str = "", form_default_value: Any = _UNDEFINED
    ) -> None:
        self.name = name
        self.label = label

        if form_default_value is not _UNDEFINED:
            self.form_default_value = form_default_value  # optionnal default value

    # model must be set before calling any method or property
    _model = None

    def _get_model(self):
        if self._model is None:
            raise ValueError("Model not set")
        return self._model

    def _set_model(self, model: Type[Model]) -> None:
        if self._model is not None:
            raise ValueError("Model already set")

        self._model = model

    model = property(_get_model, _set_model)

    def filter(self, query, module, request, searched_text, *args, **kwargs):
        raise NotImplementedError

    @property
    def has_form_filter(self):
        return True

    @property
    def form_filter_type(self):
        raise NotImplementedError

    @property
    def form_filter_args(self):
        raise NotImplementedError

    @property
    def form_unset_value(self):
        raise NotImplementedError

    @property
    def has_form_default_value(self):
        return self.form_default_value is not _UNDEFINED

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name}>"


class TextSearchCriterion(BaseCriterion):
    """Fulltext search on given attributes."""

    def __init__(
        self,
        name: str,
        label: str = "",
        attributes: Optional[Tuple[str, str]] = None,
        search_fmt: str = "%{q}%",
    ) -> None:
        super().__init__(name, label)
        self.attributes = dict.fromkeys(
            attributes if attributes is not None else (name,)
        )
        self._attributes_prepared = False

        if isinstance(search_fmt, str):
            search_fmt = [search_fmt]

        self.search_fmt = search_fmt

    def _prepare_attributes(self):
        to_del = []

        for attr_name in self.attributes:
            name = attr_name
            val = self.attributes[name] = {}

            if "." in attr_name:
                # related model
                rel_attr_name, name = attr_name.split(".", 1)
                model, attr = self.get_rel_attr(attr_name, self.model)
            else:
                rel_attr_name = None
                model = None
                attr = getattr(self.model, attr_name, None)

            if attr is None:
                logger.debug(
                    'Model: "%s", could not find "%s"',
                    self.model.__class__.__name__,
                    attr_name,
                )
                to_del.append(attr_name)
            else:
                val.update(
                    {
                        "attr": attr,
                        "name": name,
                        "model": model,
                        "rel_attr_name": rel_attr_name,
                    }
                )

        for k in to_del:
            del self.attributes[k]

        self._attributes_prepared = True

    def filter(
        self,
        query: EntityQuery,
        module: "Module",
        request: Request,
        searched_text: str,
        *args,
        **kwargs,
    ) -> EntityQuery:

        if not searched_text:
            return query

        if not self._attributes_prepared:
            self._prepare_attributes()

        clauses = []
        has_joins = False

        for attr_name, val in self.attributes.items():
            if self.is_excluded(attr_name, request):
                continue

            attr = val["attr"]

            if val["model"] is not None:
                # related model - generate an alias, required when searched model has
                # more than one relationship with another model
                model = orm.aliased(val["model"])
                attr = getattr(model, attr.key)

                join_attr = getattr(module.managed_class, val["rel_attr_name"])
                query = query.outerjoin(model, join_attr)

                has_joins = True

            # TODO: gérer les accents
            for fmt in self.search_fmt:
                like_txt = fmt.format(q=searched_text)
                clauses.append(func.lower(attr).like(like_txt))

        if clauses:
            query = query.filter(or_(*clauses)).distinct()

        if has_joins:
            query = query.reset_joinpoint()

        return query

    def get_rel_attr(self, attr_name, model):
        """For a related attribute specification, returns (related model,
        attribute).

        Returns (None, None) if model is not found, or (model, None) if
        attribute is not found.
        """
        rel_attr_name, attr_name = attr_name.split(".", 1)
        rel_attr = getattr(self.model, rel_attr_name, None)
        rel_model = None
        attr = None

        if rel_attr is not None:
            rel_model = rel_attr.property.mapper.class_
            attr = getattr(rel_model, attr_name, None)

        return rel_model, attr

    def is_excluded(self, attr_name: str, request: Request):
        """To be overriden by subclasses that want to filter searched
        attributes."""
        return False

    @property
    def has_form_filter(self) -> bool:
        return False


class TextCriterion(TextSearchCriterion):
    def __init__(self, name, label="", attributes=None, search_fmt="%{q}%"):
        super().__init__(name, label, attributes, search_fmt)

    def filter(self, query, module, request, searched_text, *args, **kwargs):
        my_searched_text = request.values.get(self.name, "").strip()
        if my_searched_text:
            return super().filter(
                query, module, request, my_searched_text.lower(), *args, **kwargs
            )
        else:
            return query

    @property
    def has_form_filter(self):
        return True

    @property
    def form_filter_type(self):
        return "text"

    @property
    def form_filter_args(self):
        return []

    @property
    def form_unset_value(self):
        return ""

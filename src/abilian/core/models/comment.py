""""""
from __future__ import annotations

import abc
from typing import Any, Type

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, UnicodeText
from sqlalchemy.orm import backref, relationship

from abilian.core.entities import Entity, EntityQuery
from abilian.services.security import CREATE, DELETE, WRITE, Anonymous, Owner

#: name of backref on target :class:`Entity` object
ATTRIBUTE = "__comments__"


class Commentable(metaclass=abc.ABCMeta):
    id: int


def register(cls: type[Entity]) -> type:
    """Register an :class:`Entity` as a commentable class.

    Can be used as a class decorator:

    .. code-block:: python

      @comment.register
      class MyContent(Entity):
          ...
    """
    if not issubclass(cls, Entity):
        raise ValueError("Class must be a subclass of abilian.core.entities.Entity")

    Commentable.register(cls)
    return cls


def is_commentable(obj_or_class: Any) -> bool:
    """
    :param obj_or_class: a class or instance
    """
    if isinstance(obj_or_class, type):
        return issubclass(obj_or_class, Commentable)

    if not isinstance(obj_or_class, Commentable):
        return False

    if obj_or_class.id is None:
        return False

    return True


def for_entity(obj, check_commentable=False):
    """Return comments on an entity."""
    if check_commentable and not is_commentable(obj):
        return []

    return getattr(obj, ATTRIBUTE)


class CommentQuery(EntityQuery):
    def all(self):
        return EntityQuery.all(self.order_by(Comment.created_at))


class Comment(Entity):
    """A Comment related to an :class:`Entity`."""

    __default_permissions__ = {WRITE: {Owner}, DELETE: {Owner}, CREATE: {Anonymous}}

    entity_id = Column(Integer, ForeignKey(Entity.id), nullable=False)

    #: Commented entity
    entity = relationship(
        Entity,
        lazy="immediate",
        foreign_keys=[entity_id],
        backref=backref(
            ATTRIBUTE,
            lazy="select",
            order_by="Comment.created_at",
            cascade="all, delete-orphan",
        ),
    )

    #: comment's main content
    body = Column(UnicodeText(), CheckConstraint("trim(body) != ''"), nullable=False)

    query_class = CommentQuery

    @property
    def history(self):
        return self.meta.get("abilian.core.models.comment", {}).get("history", [])

    def __repr__(self):
        class_ = self.__class__
        mod_ = class_.__module__
        classname = class_.__name__
        return "<{}.{} instance at 0x{:x} entity id={!r} date={}".format(
            mod_, classname, id(self), self.entity_id, self.created_at
        )

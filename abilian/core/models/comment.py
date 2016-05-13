# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import abc

import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, Integer, UnicodeText
from sqlalchemy.orm import backref, relationship

from abilian.core.entities import Entity
from abilian.services.security import CREATE, DELETE, WRITE, Anonymous, Owner

#: name of backref on target :class:`Entity` object
ATTRIBUTE = '__comments__'


class Commentable(object):
    __metaclass__ = abc.ABCMeta


def register(cls):
    """Register an :class:`Entity` as a commentable class.

    Can be used as a class decorator:

    .. code-block:: python

      @comment.register
      class MyContent(Entity):
          ...
    """
    if not issubclass(cls, Entity):
        raise ValueError(
            'Class must be a subclass of abilian.core.entities.Entity')

    Commentable.register(cls)
    return cls


def is_commentable(obj):
    """
    :param obj: a class or instance
    """
    if isinstance(obj, type):
        return issubclass(obj, Commentable)

    if not isinstance(obj, Commentable):
        return False

    if obj.id is None:
        return False

    return True


def for_entity(obj, check_commentable=False):
    """Return comments on an entity.
    """
    if check_commentable and not is_commentable(obj):
        return []

    return getattr(obj, ATTRIBUTE)


class Comment(Entity):
    """A Comment related to an :class:`Entity`.
    """
    __default_permissions__ = {
        WRITE: {Owner},
        DELETE: {Owner},
        CREATE: {Anonymous},
    }

    @sa.ext.declarative.declared_attr
    def __mapper_args__(cls):
        # we cannot use super(Comment, cls): declared_attr happens during class
        # construction. super(cls, cls) could work; as long as `cls` is not a
        # subclass of `Comment`: it would enter into an infinite loop.
        #
        # Entity.__mapper_args__ calls the descriptor with 'Entity', not `cls`.
        args = Entity.__dict__['__mapper_args__'].fget(cls)
        args['order_by'] = cls.created_at
        return args

    entity_id = Column(Integer, ForeignKey(Entity.id), nullable=False)

    #: Commented entity
    entity = relationship(Entity,
                          lazy='immediate',
                          foreign_keys=[entity_id],
                          backref=backref(ATTRIBUTE,
                                          lazy='select',
                                          order_by='Comment.created_at',
                                          cascade="all, delete-orphan",))

    #: comment's main content
    body = Column(UnicodeText(),
                  sa.CheckConstraint("trim(body) != ''"),
                  nullable=False)

    @property
    def history(self):
        return self.meta.get('abilian.core.models.comment', {}).get('history',
                                                                    [])

    def __repr__(self):
        class_ = self.__class__
        mod_ = class_.__module__
        classname = class_.__name__
        return '<{}.{} instance at 0x{:x} entity id={!r}'\
            .format(mod_, classname, id(self), self.entity_id)

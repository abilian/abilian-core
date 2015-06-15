# coding=utf-8
"""
"""
from __future__ import absolute_import

import sqlalchemy as sa
from sqlalchemy import Column, UnicodeText, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref

from abilian.core.entities import Entity


class Comment(Entity):
  """
  A Comment related to an :class:`Entity`.
  """
  @sa.ext.declarative.declared_attr
  def __mapper_args__(cls):
    args = super(cls, cls).__mapper_args__
    args['order_by'] = cls.created_at
    return args

  #: name of backref on target :class:`Entity` object
  ATTRIBUTE = '__comments__'

  entity_id = Column(Integer, ForeignKey(Entity.id), nullable=False)

  #: Commented entity
  entity = relationship(
    Entity,
    lazy='immediate',
    foreign_keys=[entity_id],
    backref=backref(ATTRIBUTE,
                    lazy='select',
                    order_by='Comment.created_at',
                    cascade="all, delete-orphan",
                  )
  )

  #: comment's main content
  body = Column(
    UnicodeText(),
    sa.CheckConstraint("trim(body) != ''"),
    nullable=False)

  def __repr__(self):
    class_ = self.__class__
    mod_ = class_.__module__
    classname = class_.__name__
    return '<{}.{} instance at 0x{:x} entity id={!r}'\
        .format(mod_, classname, id(self), self.entity_id)

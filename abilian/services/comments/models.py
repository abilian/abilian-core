# coding=utf-8
"""
"""
from __future__ import absolute_import

import sqlalchemy as sa
from sqlalchemy import Column, Unicode, Integer, ForeignKey

from abilian.core.entities import Entity


# Local constants
MAX_COMMENT_LENGTH = 8000


class Comment(Entity):
  """A Comment on a Commentable object.
  """

  entity_id = Column(Integer, ForeignKey(Entity.id), nullable=False)
  #: Commented entity
  entity = sa.orm.relation(Entity, foreign_keys=[entity_id])

  #: the comment's body, as HTML (?).
  content = Column(Unicode(MAX_COMMENT_LENGTH))

  @property
  def target(self):
    cls = None  # get the class somehow
    return cls.query.get(self.target_id)

  def __repr__(self):
    class_ = self.__class__
    mod_ = class_.__module__
    classname = class_.__name__
    return '<{}.{} instance at 0x{:x} entity id={}'\
        .format(mod_, classname, id(self), self.entity_id)

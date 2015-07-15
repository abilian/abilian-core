# coding=utf-8
"""
"""
from __future__ import absolute_import

from functools import total_ordering
import sqlalchemy as sa

from .base import Model, IdMixin
from abilian.core.entities import Entity


#: backref attribute on tagged elements
TAGS_ATTR = '__tags__'

entity_tag_tbl = sa.Table(
  'entity_tags', Model.metadata,
  sa.Column('tag_id', sa.Integer, sa.ForeignKey('tag.id', ondelete='CASCADE')),
  sa.Column('entity_id', sa.Integer, sa.ForeignKey(Entity.id, ondelete='CASCADE')),
  sa.UniqueConstraint('tag_id', 'entity_id'),
)


@total_ordering
class Tag(IdMixin, Model):
  """
  Tags are text labels that can be attached to :class:`entities <.Entity>`.

  They are namespaced, so that independent group of tags can be defined in the
  application. The default namespace is `"default"`.
  """
  __tablename__ = 'tag'
  
  #: namespace
  ns = sa.Column(sa.UnicodeText(), nullable=False,
                 default=u'default', server_default=u'default')

  #: Label visible to the user
  label = sa.Column(sa.UnicodeText(), nullable=False)

  #: :class:`entities <.Entity>` attached to this tag
  entities = sa.orm.relationship(
    Entity, collection_class=set,
    secondary=entity_tag_tbl,
    backref=sa.orm.backref(TAGS_ATTR, collection_class=set),
  )
  
  __mapper_args__ = {
    'order_by': label,
  }
  
  __table_args__ = (
    sa.UniqueConstraint('ns', 'label'),
    # namespace is not empty and is not surrounded by space characters
    sa.CheckConstraint(
      sa.sql.and_(
        sa.sql.func.trim(sa.sql.column('ns')) == sa.sql.column('ns'),
        sa.sql.column('ns') != u''),
    ),
    # label is not empty and is not surrounded by space characters
    sa.CheckConstraint(
      sa.sql.and_(
        sa.sql.func.trim(sa.sql.column('label')) == sa.sql.column('label'),
        sa.sql.column('label') != u''),
    ),
  )

  def __unicode__(self):
    return self.label

  def __lt__(self, other):
    return unicode(self).lower().__lt__(unicode(other).lower())

  def __repr__(self):
    cls = self.__class__
    return '<{mod}.{cls} id={t.id!r} ns={t.ns!r} label={t.label!r} at 0x{addr:x}>'.format(
      mod=cls.__module__, cls=cls.__name__, t=self, addr=id(self),
    )
  

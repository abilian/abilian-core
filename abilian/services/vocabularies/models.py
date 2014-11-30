# coding=utf-8
"""
"""
from __future__ import absolute_import

import sqlalchemy as sa
from sqlalchemy import Column
from flask.ext.sqlalchemy import BaseQuery

from abilian.core.extensions import db
from abilian.core.util import slugify


_BaseMeta = db.Model.__class__


class VocabularyQuery(BaseQuery):
  """
  """
  def active(self):
    """
    Returns only valid vocabulary items
    """
    return self.filter_by(active=True)

  def by_position(self, position):
    """
    Like `.get()`, but by position number
    """
    # don't use .first(), so that MultipleResultsFound can be raised
    try:
      return self.filter_by(position=position).one()
    except sa.orm.exc.NoResultFound:
      return None


class _VocabularyMeta(_BaseMeta):
  """
  Metaclass for vocabularies. Enforces `__tablename__`.
  """
  def __new__(cls, name, bases, d):
    meta = d.get('Meta')
    tblprefix = 'vocabulary_'

    group = slugify(meta.group or u'', u'_').encode('ascii')
    if group:
      tblprefix += group + '_'

    vocname = name.lower().replace('vocabulary', '')
    meta.name = vocname
    d['__tablename__'] = tblprefix + vocname
    return _BaseMeta.__new__(cls, name, bases, d)


class BaseVocabulary(db.Model):
  """
  Base abstract class for vocabularies
  """
  __metaclass__ = _VocabularyMeta
  __abstract__ = True
  query_class = VocabularyQuery

  id = Column(sa.Integer(), primary_key=True, autoincrement=True)
  label = Column(sa.UnicodeText(), nullable=False)
  active = Column(sa.Boolean(), nullable=False, server_default=sa.sql.true(),
                  default=True)
  default = Column(sa.Boolean(), nullable=False, server_default=sa.sql.false(),
                   default=False)
  position = Column(sa.Integer, nullable=False, unique=True)

  __table_args__ = (
      sa.CheckConstraint(sa.sql.func.trim(sa.sql.text('label')) != u''),
  )

  @sa.ext.declarative.declared_attr
  def __mapper_args__(cls):
    return {'order_by': [cls.__table__.c.position.asc()]}

  class Meta:
    label = None
    group = None

  def __repr__(self):
    fmt = ('<{module}.{cls} id={id} label={label} position={position} '
           'active={active} default={default} at 0x{addr:x}')
    cls = self.__class__
    return fmt.format(module=cls.__module__,
                      cls=cls.__name__,
                      id=self.id,
                      label=repr(self.label),
                      position=repr(self.position),
                      active=repr(self.active),
                      default=repr(self.default),
                      addr=id(self),)


@sa.event.listens_for(BaseVocabulary, "before_insert", propagate=True)
def _before_insert(mapper, connection, target):
  """
  Set item to last position if position not defined
  """
  if target.position is None:
    func = sa.sql.func
    stmt = sa.select([func.coalesce(func.max(mapper.mapped_table.c.position),
                                    -1)])
    target.position = connection.execute(stmt).scalar() + 1


def Vocabulary(name, label=None, group=None):
  name = 'Vocabulary' + name.capitalize()
  Meta = type('Meta', (object,), dict(label=label, group=group))
  return type(name, (BaseVocabulary,), dict(Meta=Meta))

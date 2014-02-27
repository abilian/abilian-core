"""
Base class for entities, objects that are managed by the Abilian framwework
(unlike SQLAlchemy models which are considered lower-level).
"""
from __future__ import absolute_import

from inspect import isclass
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import mapper, Session
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Integer, String, UnicodeText
from sqlalchemy import event

from .extensions import db
from .util import memoized, friendly_fqcn
from .models import BaseMixin
from .models.base import (
  Indexable, SYSTEM, SEARCHABLE, EDITABLE
)

__all__ = ['Entity', 'all_entity_classes', 'db', 'ValidationError']

#
# Manual validation
#
class ValidationError(Exception):
  pass


def validation_listener(mapper, connection, target):
  if hasattr(target, "_validate"):
    target._validate()

event.listen(mapper, 'before_insert', validation_listener)
event.listen(mapper, 'before_update', validation_listener)

#
# CRUD events. TODO: connect to signals instead?
#
def before_insert_listener(mapper, connection, target):
  if hasattr(target, "_before_insert"):
    target._before_insert()


def before_update_listener(mapper, connection, target):
  if hasattr(target, "_before_update"):
    target._before_update()


def before_delete_listener(mapper, connection, target):
  if hasattr(target, "_before_delete"):
    target._before_delete()

event.listen(mapper, 'before_insert', before_insert_listener)
event.listen(mapper, 'before_update', before_update_listener)
event.listen(mapper, 'before_delete', before_delete_listener)


class _EntityInherit(object):
  __indexable__ = True

  @declared_attr
  def id(cls):
    return Column(
      Integer,
      ForeignKey('entity.id', use_alter=True, name='fk_inherited_entity_id'),
      primary_key=True,
      info=SYSTEM|SEARCHABLE)

  @declared_attr
  def __mapper_args__(cls):
    return {'polymorphic_identity': cls.entity_type,
            'inherit_condition': cls.id == Entity.id}


BaseMeta = db.Model.__class__


class EntityMeta(BaseMeta):
  """
  Metaclass for Entities. It properly sets-up subclasses by adding
  _EntityInherit to `__bases__`.

  `_EntityInherit` provides `id` attibute and `__mapper_args__`
  """

  def __new__(mcs, classname, bases, d):
    if (d['__module__'] != EntityMeta.__module__ or classname != 'Entity'):
      if not any(issubclass(b, _EntityInherit) for b in bases):
        bases = (_EntityInherit,) + bases
        d['id'] = _EntityInherit.id

      if d.get('entity_type') is None:
        d['entity_type'] = d['__module__'] + '.' + classname

    return BaseMeta.__new__(mcs, classname, bases, d)

  def __init__(cls, classname, bases, d):
    bases = cls.__bases__
    BaseMeta.__init__(cls, classname, bases, d)


class Entity(Indexable, BaseMixin, db.Model):
  """
  Base class for Abilian entities.

  From Sqlalchemy POV Entities use `Joined-Table inheritance
  <http://docs.sqlalchemy.org/en/rel_0_8/orm/inheritance.html#joined-table-inheritance>`_,
  thus entities subclasses cannot use inheritance themselves (as of 2013
  Sqlalchemy does not support multi-level inheritance)
  """
  __metaclass__ = EntityMeta
  __mapper_args__ = {'polymorphic_on': '_entity_type'}
  __indexable__ = False
  __indexation_args__ = {}
  __indexation_args__.update(Indexable.__indexation_args__)
  index_to = __indexation_args__.setdefault('index_to', ())
  index_to += BaseMixin.__indexation_args__.setdefault('index_to', ())
  __indexation_args__['index_to'] = index_to
  del index_to

  name = Column('name', UnicodeText(),
                info=EDITABLE|SEARCHABLE|dict(index_to=('name', 'name_prefix',
                                                        'text')))

  _entity_type = Column('entity_type', String(1000), nullable=False)
  entity_type = None

  @property
  def object_type(self):
    return unicode(self.entity_type)

  @property
  def entity_class(self):
    return self.entity_type and friendly_fqcn(self.entity_type)

  # Default magic metadata, should not be necessary
  # TODO: remove
  __editable__ = frozenset()
  __searchable__ = frozenset()
  __auditable__ = frozenset()

  base_url = None

  def __init__(self, *args, **kwargs):
    db.Model.__init__(self, *args, **kwargs)
    BaseMixin.__init__(self)


# TODO: make this unecessary
@event.listens_for(Entity, 'class_instrument', propagate=True)
def register_metadata(cls):
  #print "register_metadata called for class", cls
  cls.__editable__ = set()

  # TODO: use SQLAlchemy 0.8 introspection
  if hasattr(cls, '__table__'):
    columns = cls.__table__.columns
  else:
    columns = [ v for k, v in vars(cls).items() if isinstance(v, Column) ]

  for column in columns:
    name = column.name
    info = column.info

    if info.get("editable", True):
      cls.__editable__.add(name)


@event.listens_for(Session, 'before_flush')
def polymorphic_update_timestamp(session, flush_context, instances):
  """
  This listeners ensure an update statement is emited for "entity" table
  to update 'updated_at'.

  With joined-table inheritance if the only modified attributes are
  subclass's ones, then no update statement will be emitted.
  """
  for obj in session.dirty:
    if not isinstance(obj, Entity):
      continue
    state = sa.inspect(obj)
    history = state.get_history('updated_at', state.dict)
    if not any((history.added, history.deleted)):
      obj.updated_at = datetime.utcnow()


@memoized
def all_entity_classes():
  """
  Returns the list of all concrete persistent classes that are subclasses of
  Entity.
  """
  persistent_classes = Entity._decl_class_registry.values()
  # with sqlalchemy 0.8 _decl_class_registry holds object that are not classes
  return [ cls for cls in persistent_classes
           if isclass(cls) and issubclass(cls, Entity) ]


def register_all_entity_classes():
  for cls in all_entity_classes():
    register_metadata(cls)

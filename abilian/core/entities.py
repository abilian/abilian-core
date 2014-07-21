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
from .util import memoized, friendly_fqcn, slugify
from .models import BaseMixin
from .models.base import (
  Indexable, SYSTEM, SEARCHABLE, EDITABLE, NOT_SEARCHABLE
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


def auto_slug_on_insert(mapper, connection, target):
  """
  Generates a slug from :prop:`Entity.auto_slug` for new entities, unless slug
  is already set.
  """
  if target.slug is None and target.name:
    target.slug = target.auto_slug

def auto_slug_after_insert(mapper, connection, target):
  """
  Generates a slug from entity_type and id, unless slug is already set.
  """
  if target.slug is None:
    target.slug = u'{name}{sep}{id}'.format(name=target.entity_class.lower(),
                                            sep=target.SLUG_SEPARATOR,
                                            id=target.id)

class _EntityInherit(object):
  """
  Mixin for Entity subclasses. Entity meta-class takes care of inserting it in
  base classes.
  """
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

      d['SLUG_SEPARATOR'] = unicode(d.get('SLUG_SEPARATOR',
                                          Entity.SLUG_SEPARATOR))

    cls = BaseMeta.__new__(mcs, classname, bases, d)
    event.listen(cls, 'before_insert', auto_slug_on_insert)
    event.listen(cls, 'after_insert', auto_slug_after_insert)
    return cls

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

  The name is a string that is shown to the user; it could be a title
  for document, a folder name, etc.

  The slug attribute may be used in URLs to reference the entity, but
  uniqueness is not enforced, even within same entity type. For example
  if an entity class represent folders, one could want uniqueness only
  within same parent folder.

  If slug is empty at first creation, its is derived from the name. When name
  changes the slug is not updated. If name is also empty, the slug will be the
  friendly entity_type with concatenated with entity's id.
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

  SLUG_SEPARATOR = u'-' # \x2d \u002d HYPHEN-MINUS

  name = Column('name', UnicodeText(),
                info=EDITABLE|SEARCHABLE|dict(index_to=('name', 'name_prefix',
                                                        'text')))

  slug = Column('slug', UnicodeText(), info=SEARCHABLE)

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

  def __init__(self, *args, **kwargs):
    db.Model.__init__(self, *args, **kwargs)
    BaseMixin.__init__(self)

  @property
  def auto_slug(self):
    """
    This property is used to auto-generate a slug from the name attribute.
    It can be customized by subclasses.
    """
    slug = self.name
    if slug is not None:
      slug = slugify(slug, separator=self.SLUG_SEPARATOR)
    return slug


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

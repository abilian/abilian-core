"""
Base class for entities, objects that are managed by the Abilian framwework
(unlike SQLAlchemy models which are considered lower-level).
"""
from __future__ import absolute_import

from inspect import isclass
from datetime import datetime
import json

from flask import g

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship, mapper, Session
from sqlalchemy.orm.util import class_mapper
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Integer, DateTime, String, UnicodeText
from sqlalchemy import event

from whoosh.fields import ID, STORED

from .extensions import db
from .util import memoized, fqcn, friendly_fqcn


__all__ = ['Entity', 'all_entity_classes', 'db', 'ValidationError']


class Info(dict):

  def __init__(self, **kw):
    for k, v in kw.items():
      self[k] = v

  def copy(self):
    # dict.copy would return an instance of dict
    return self.__class__(**self)

  def __add__(self, other):
    d = self.copy()
    d.update(other)
    return d

  __or__ = __add__


EDITABLE = Info(editable=True)
NOT_EDITABLE = Info(editable=False)
AUDITABLE = Info(auditable=True)
AUDITABLE_HIDDEN = Info(auditable=True, audit_hide_content=True)
NOT_AUDITABLE = Info(auditable=False)
SEARCHABLE = Info(searchable=True)
NOT_SEARCHABLE = Info(searchable=False)
EXPORTABLE = Info(exportable=True)
NOT_EXPORTABLE = Info(exportable=False)

#: SYSTEM properties are properties defined by the system
#: and not supposed to be changed manually.
SYSTEM = Info(editable=False, auditable=False)


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


class IdMixin(object):
  id = Column(Integer, primary_key=True, info=SYSTEM|SEARCHABLE)


class Indexable(object):
  """
  Mixin with sensible defaults for indexable objects.
  """
  __indexable__ = True
  __indexation_args__ = {
    'index_to': (('object_key', (('object_key',
                                  ID(stored=True, unique=True)),)),
                 ('object_type', (('object_type',
                                   ID(stored=True, unique=False)),)),
                 ),
    }

  @classmethod
  def _object_type(cls):
    return fqcn(cls)

  @property
  def object_type(self):
    return self._object_type()

  @property
  def object_key(self):
    return u'{}:{}'.format(self.object_type, self.id)


class TimestampedMixin(object):
  created_at = Column(DateTime, default=datetime.utcnow, info=SYSTEM|SEARCHABLE)
  updated_at = Column(DateTime, default=datetime.utcnow,
                      onupdate=datetime.utcnow,
                      info=SYSTEM|SEARCHABLE)
  deleted_at = Column(DateTime, default=None, info=SYSTEM)


class OwnedMixin(object):

  __indexation_args__ = {
    'index_to': (('creator', ('creator',)),
                 ('creator_name', (('creator_name', STORED),)),
                 ('owner', ('owner',)),
                 ('owner_name', (('owner_name', STORED),)),
      ),
    }

  def __init__(self, *args, **kwargs):
    if hasattr(g, 'user'):
      if not self.creator and not g.user.is_anonymous():
        self.creator = g.user
      if not self.owner and not g.user.is_anonymous():
        self.owner = g.user

  @declared_attr
  def creator_id(cls):
    return Column(ForeignKey("user.id"), info=SYSTEM)

  @declared_attr
  def creator(cls):
    pj = "User.id == %s.creator_id" % cls.__name__
    return relationship("User", primaryjoin=pj, lazy='joined', uselist=False,
                        info=SYSTEM|SEARCHABLE)

  @property
  def creator_name(self):
    return unicode(self.creator) if self.creator else u''

  @declared_attr
  def owner_id(cls):
    return Column(ForeignKey("user.id"), info=SYSTEM)

  @declared_attr
  def owner(cls):
    pj = "User.id == %s.owner_id" % cls.__name__
    return relationship("User", primaryjoin=pj, lazy='joined', uselist=False,
                        info=SYSTEM|SEARCHABLE)

  @property
  def owner_name(self):
    return unicode(self.owner) if self.owner else u''


class BaseMixin(IdMixin, TimestampedMixin, OwnedMixin):

  @declared_attr
  def __tablename__(cls):
    return cls.__name__.lower()

  def __init__(self):
    OwnedMixin.__init__(self)

  def __repr__(self):
    name = self._name

    # Just in case....
    if isinstance(name, unicode):
      name = name.encode("ascii", errors="ignore")

    return "<%s %s id=%s>" % (self.__class__.__name__, name, str(self.id))

  @property
  def column_names(self):
    return [ col.name for col in class_mapper(self.__class__).mapped_table.c ]

  def to_dict(self):
    if hasattr(self, "__exportable__"):
      exported = self.__exportable__ + ['id']
    else:
      exported = self.column_names
    d = {}
    for k in exported:
      v = getattr(self, k)
      if type(v) == datetime:
        v = v.isoformat()
      d[k] = v
    return d

  def to_json(self):
    return json.dumps(self.to_dict())

  #FIXME: remove when all entities will have a default view registered
  @property
  def _url(self):
    return self.base_url + "/%d" % self.id

  def _icon(self, size=12):
    return "/static/icons/%s-%d.png" % (self.__class__.__name__.lower(), size)

  #FIXME: we can do better than that
  @property
  def _name(self):
    if hasattr(self, 'title'):
      return self.title
    elif hasattr(self, 'name'):
      return self.name
    else:
      raise NotImplementedError()

  def __unicode__(self):
    return self._name


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

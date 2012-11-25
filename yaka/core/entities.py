"""
Base class for entities, objects that are managed by the Abilian framwework
(unlike SQLAlchemy models which are considered lower-level).
"""

from datetime import datetime
import json
from threading import Lock
import sys

from flask import g

from sqlalchemy.ext.declarative import AbstractConcreteBase, declared_attr
from sqlalchemy.orm.util import class_mapper
from sqlalchemy.schema import Column
from sqlalchemy.types import Integer, DateTime
from sqlalchemy import event

from .extensions import db

from .util import memoized


__all__ = ['Entity', 'all_entity_classes']


class Info(dict):

  def __init__(self, **kw):
    for k, v in kw.items():
      self[k] = v

  def __add__(self, other):
    d = self.copy()
    for k, v in other.items():
      d[k] = v
    return d


EDITABLE = Info(editable=True)
NOT_EDITABLE = Info(editable=False)
AUDITABLE = Info(auditable=True)
NOT_AUDITABLE = Info(auditable=False)
SEARCHABLE = Info(searchable=True)
NOT_SEARCHABLE = Info(searchable=False)
EXPORTABLE = Info(exportable=True)
NOT_EXPORTABLE = Info(exportable=False)

#: SYSTEM properties are properties defined by the system
#: and not supposed to be changed manually.
SYSTEM = Info(editable=False, auditable=False)


# TODO: get rid of flask-sqlalchemy, replace db.Model by Base?
#Base = declarative_base()


# TODO: very hackish. Use Redis instead?
# We will need a simpler implementation for unit tests, also, so
# we have to get rid of the singleton.
class IdGenerator(object):
  """Dummy integer id generator."""

  # TODO: one counter and one lock per class ?

  def __init__(self):
    self.lock = Lock()
    try:
      self.current = int(open("maxid.data").read())
    except:
      self.current = 0

  def new(self):
    with self.lock:
      self.current += 1
      with open("maxid.data", "wc") as fd:
        fd.write(str(self.current))
    return self.current


# Singleton. Yuck :( !
id_gen = IdGenerator()


# Special case for "unowned" object? Maybe not. XXX.
class DummyUser(object):
  name = "Nobody"
  _url = ""
  photo = ""

nobody = DummyUser()


# Cache to speed up demos. TODO: remove later.
user_cache = {}


class Entity(AbstractConcreteBase, db.Model):
  """Base class for Yaka entities."""

  base_url = None

  id = Column(Integer, primary_key=True, info=SYSTEM)

  created_at = Column(DateTime, default=datetime.utcnow, info=SYSTEM)
  updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,
                      info=SYSTEM)
  deleted_at = Column(DateTime, default=None, info=SYSTEM)

  @declared_attr
  def creator_id(self):
    return Column(Integer, info=SYSTEM)
    #return Column(Integer, ForeignKey("UserBase.id"), info=SYSTEM)

  @declared_attr
  def owner_id(self):
    return Column(Integer)
    #return Column(Integer, ForeignKey("UserBase.id"))

  # TODO: doesn't work.
  #@declared_attr
  #def creator(self):
  #  return relationship("User")
  #@declared_attr
  #def owner(self):
  #  return relationship("User")

  # FIXME: extremely suboptimal
  @property
  def creator(self):
    from .subjects import User
    if self.creator_id:
      if self.creator_id in user_cache:
        return user_cache[self.creator_id]
      else:
        user = User.query.get(self.creator_id)
        user_cache[self.creator_id] = user
        return user
    else:
      return nobody

  @property
  def owner(self):
    from .subjects import User
    if self.owner_id:
      if self.owner_id in user_cache:
        return user_cache[self.owner_id]
      else:
        user = User.query.get(self.owner_id)
        user_cache[self.owner_id] = user
        return user
    else:
      return nobody

  # Should not be necessary
  __editable__ = set()
  __searchable__ = set()
  __auditable__ = set()

  def __init__(self, **kw):
    self.id = id_gen.new()
    if hasattr(g, 'user'):
      if not self.creator_id:
        self.creator_id = g.user.id
      if not self.owner_id:
        self.owner_id = g.user.id
    self.update(kw)

  def __repr__(self):
    if hasattr(self, 'name'):
      if isinstance(self.name, unicode):
        name = self.name.encode("ascii", errors="ignore")
      else:
        name = self.name
    else:
      name = "with id=%s" % self.id
    return "<%s %s>" % (self.__class__.__name__, name)

  @property
  def column_names(self):
    return [ col.name for col in class_mapper(self.__class__).mapped_table.c ]

  def update(self, d):
    for k, v in d.items():
      assert k in self.column_names, "%s not allowed" % k
      if type(v) == type(""):
        v = unicode(v)
      setattr(self, k, v)

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

  @property
  def _url(self):
    return self.base_url + "/%d" % self.id

  def _icon(self, size=12):
    return "/static/icons/%s-%d.png" % (self.__class__.__name__.lower(), size)

  @property
  def _name(self):
    if hasattr(self, 'name'):
      return self.name
    else:
      raise NotImplementedError()

  def __unicode__(self):
    return self._name


# TODO: make this unecessary
def register_metadata(cls):
  #print "register_metadata called for class", cls
  cls.__editable__ = set()
  cls.__searchable__ = set()
  cls.__auditable__ = set()

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
    if info.get('searchable', False):
      cls.__searchable__.add(name)
    if info.get('auditable', True):
      cls.__auditable__.add(name)


event.listen(Entity, 'class_instrument', register_metadata)


@memoized
def all_entity_classes():
  """
  Returns the list of all concrete persistent classes that are subclasses of
  Entity.
  """
  classes = set()
  for module_name, module in sys.modules.items():
    for name in dir(module):
      v = getattr(module, name)
      if isinstance(v, type) and issubclass(v, Entity) and hasattr(v, '__table__'):
        classes.add(v)
  return classes


def register_all_entity_classes():
  for cls in all_entity_classes():
    register_metadata(cls)

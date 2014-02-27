# coding=utf-8
"""
"""
from __future__ import absolute_import

import json

from sqlalchemy.orm.util import class_mapper
from sqlalchemy.ext.declarative import declared_attr

from .base import IdMixin, TimestampedMixin
from .owned import OwnedMixin

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

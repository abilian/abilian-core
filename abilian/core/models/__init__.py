# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division
from datetime import datetime
import json

from six import python_2_unicode_compatible
from sqlalchemy.orm.util import class_mapper
from sqlalchemy.ext.declarative import declared_attr

from .base import (Model, IdMixin, TimestampedMixin, EDITABLE, NOT_EDITABLE,
                   AUDITABLE, AUDITABLE_HIDDEN, NOT_AUDITABLE, SEARCHABLE,
                   NOT_SEARCHABLE, EXPORTABLE, NOT_EXPORTABLE, SYSTEM)  # noqa

from .owned import OwnedMixin


@python_2_unicode_compatible
class BaseMixin(IdMixin, TimestampedMixin, OwnedMixin):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    def __init__(self):
        OwnedMixin.__init__(self)

    def __repr__(self):
        return '<{} instance at 0x{:x} name={!r} id={}>'.format(
            self.__class__.__name__, id(self), self.name, str(self.id))

    @property
    def column_names(self):
        return [col.name for col in class_mapper(self.__class__).mapped_table.c]

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

    def _icon(self, size=12):
        return "/static/icons/%s-%d.png" % (self.__class__.__name__.lower(),
                                            size)

    #FIXME: we can do better than that
    @property
    def _name(self):
        if hasattr(self, 'title'):
            return self.title
        elif hasattr(self, 'name'):
            return self.name
        else:
            raise NotImplementedError()

    def __str__(self):
        return self.name

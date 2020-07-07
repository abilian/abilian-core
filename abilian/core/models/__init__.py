""""""
import json
from datetime import datetime

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm.util import class_mapper

from .base import AUDITABLE, AUDITABLE_HIDDEN, EDITABLE, EXPORTABLE, \
    NOT_AUDITABLE, NOT_EDITABLE, NOT_EXPORTABLE, NOT_SEARCHABLE, SEARCHABLE, \
    SYSTEM, IdMixin, Model, TimestampedMixin
from .owned import OwnedMixin


class BaseMixin(IdMixin, TimestampedMixin, OwnedMixin):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    def __init__(self) -> None:
        OwnedMixin.__init__(self)

    def __repr__(self):
        return "<{} instance at 0x{:x} name={!r} id={}>".format(
            self.__class__.__name__, id(self), self.name, str(self.id)
        )

    @property
    def column_names(self):
        return [col.name for col in class_mapper(self.__class__).mapped_table.c]

    def to_dict(self):
        if hasattr(self, "__exportable__"):
            exported = self.__exportable__ + ["id"]
        else:
            exported = self.column_names
        d = {}
        for k in exported:
            v = getattr(self, k)
            if isinstance(v, datetime):
                v = v.isoformat()
            d[k] = v
        return d

    def to_json(self):
        return json.dumps(self.to_dict())

    def _icon(self, size=12):
        class_name = self.__class__.__name__.lower()
        return f"/static/icons/{class_name}-{size}.png"

    # FIXME: we can do better than that
    @property
    def _name(self):
        if hasattr(self, "title"):
            return self.title
        elif hasattr(self, "name"):
            return self.name
        else:
            raise NotImplementedError()

    def __str__(self):
        return self.name or ""

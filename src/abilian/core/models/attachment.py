""""""
from __future__ import annotations

import abc

import sqlalchemy as sa
import sqlalchemy.event
from sqlalchemy import Column, ForeignKey, Integer, UnicodeText
from sqlalchemy.orm import backref, relationship

from abilian.core.entities import Entity, EntityQuery

from .blob import Blob

#: name of backref on target :class:`Entity` object
ATTRIBUTE = "__attachments__"


class SupportAttachment(metaclass=abc.ABCMeta):
    pass


def register(cls):
    """Register an :class:`~.Entity` as an attachable class.

    Can be used as a class decorator:

    .. code-block:: python

      @attachment.register
      class MyContent(Entity):
          ....
    """
    if not issubclass(cls, Entity):
        raise ValueError("Class must be a subclass of abilian.core.entities.Entity")

    SupportAttachment.register(cls)
    return cls


def supports_attachments(obj):
    """
    :param obj: a class or instance

    :returns: True is obj supports attachments.
    """
    if isinstance(obj, type):
        return issubclass(obj, SupportAttachment)

    if not isinstance(obj, SupportAttachment):
        return False

    if obj.id is None:
        return False

    return True


def for_entity(obj, check_support_attachments=False):
    """Return attachments on an entity."""
    if check_support_attachments and not supports_attachments(obj):
        return []

    return getattr(obj, ATTRIBUTE)


class AttachmentQuery(EntityQuery):
    def all(self):
        return EntityQuery.all(self.order_by(Attachment.created_at))


class Attachment(Entity):
    """An Attachment owned by an :class:`Entity`."""

    __auditable_entity__ = ("entity", "attachment", ("id", "name"))

    entity_id = Column(Integer, ForeignKey(Entity.id), nullable=False)

    #: owning entity
    entity = relationship(
        Entity,
        lazy="immediate",
        foreign_keys=[entity_id],
        backref=backref(
            ATTRIBUTE,
            lazy="select",
            order_by="Attachment.created_at",
            cascade="all, delete-orphan",
        ),
    )

    blob_id = Column(Integer, sa.ForeignKey(Blob.id), nullable=False)
    #: file. Stored in a :class:`Blob`
    blob = relationship(Blob, cascade="all, delete", foreign_keys=[blob_id])

    description = Column(UnicodeText(), nullable=False, default="", server_default="")

    query_class = AttachmentQuery

    def __repr__(self):
        class_ = self.__class__
        mod_ = class_.__module__
        classname = class_.__name__
        return "<{}.{} instance at 0x{:x} entity id={!r}>".format(
            mod_, classname, id(self), self.entity_id
        )


@sa.event.listens_for(Attachment, "before_insert", propagate=True)
@sa.event.listens_for(Attachment, "before_update", propagate=True)
def set_attachment_name(mapper, connection, target):
    if target.name:
        return

    blob = target.blob
    if not blob:
        return

    filename = blob.meta.get("filename")
    if filename is not None:
        target.name = filename

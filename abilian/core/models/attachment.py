# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import abc

import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, Integer, UnicodeText
from sqlalchemy.orm import backref, relationship

from abilian.core.entities import Entity

from .blob import Blob

#: name of backref on target :class:`Entity` object
ATTRIBUTE = '__attachments__'


class SupportAttachment(object):
    __metaclass__ = abc.ABCMeta


def register(cls):
    """Register an :class:`~.Entity` as a attachmentable class.

    Can be used as a class decorator:

    .. code-block:: python

      @attachment.register
      class MyContent(Entity):
          ....
    """
    if not issubclass(cls, Entity):
        raise ValueError(
            'Class must be a subclass of abilian.core.entities.Entity')

    SupportAttachment.register(cls)
    return cls


def is_support_attachments(obj):
    """
    :param obj: a class or instance
    """
    if isinstance(obj, type):
        return issubclass(obj, SupportAttachment)

    if not isinstance(obj, SupportAttachment):
        return False

    if obj.id is None:
        return False

    return True


def for_entity(obj, check_support_attachments=False):
    """Return attachments on an entity.
    """
    if check_support_attachments and not is_support_attachments(obj):
        return []

    return getattr(obj, ATTRIBUTE)


class Attachment(Entity):
    """An Attachment owned by an :class:`Entity`.
    """
    __auditable_entity__ = ('entity', 'attachment', ('id', 'name'))

    @sa.ext.declarative.declared_attr
    def __mapper_args__(cls):
        # we cannot use super(Attachment, cls): declared_attr happens during class
        # construction. super(cls, cls) could work; as long as `cls` is not a
        # subclass of `Attachment`: it would enter into an infinite loop.
        #
        # Entity.__mapper_args__ calls the descriptor with 'Entity', not `cls`.
        args = Entity.__dict__['__mapper_args__'].fget(cls)
        args['order_by'] = cls.created_at
        return args

    entity_id = Column(Integer, ForeignKey(Entity.id), nullable=False)

    #: owning entity
    entity = relationship(
        Entity,
        lazy='immediate',
        foreign_keys=[entity_id],
        backref=backref(
            ATTRIBUTE,
            lazy='select',
            order_by='Attachment.created_at',
            cascade="all, delete-orphan",))

    blob_id = Column(Integer, sa.ForeignKey(Blob.id), nullable=False)
    #: file. Stored in a :class:`Blob`
    blob = relationship(Blob, cascade='all, delete', foreign_keys=[blob_id])

    description = Column(
        UnicodeText(),
        nullable=False,
        default='',
        server_default='',)

    def __repr__(self):
        class_ = self.__class__
        mod_ = class_.__module__
        classname = class_.__name__
        return '<{}.{} instance at 0x{:x} entity id={!r}'\
            .format(mod_, classname, id(self), self.entity_id)


@sa.event.listens_for(Attachment, 'before_insert', propagate=True)
@sa.event.listens_for(Attachment, 'before_update', propagate=True)
def set_attachment_name(mapper, connection, target):
    if target.name:
        return

    blob = target.blob
    if not blob:
        return

    filename = blob.meta.get('filename')
    if filename is not None:
        target.name = filename

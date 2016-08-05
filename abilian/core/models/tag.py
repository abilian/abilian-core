# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import abc
from functools import total_ordering

import sqlalchemy as sa
from six import python_2_unicode_compatible, text_type

from abilian.core.entities import Entity

from .base import IdMixin, Model

#: backref attribute on tagged elements
TAGS_ATTR = '__tags__'


class SupportTagging(object):
    __metaclass__ = abc.ABCMeta


def register(cls):
    """Register an :class:`~.Entity` as a taggable class.

    Can be used as a class decorator:

    .. code-block:: python

      @tag.register
      class MyContent(Entity):
          ....
    """
    if not issubclass(cls, Entity):
        raise ValueError(
            'Class must be a subclass of abilian.core.entities.Entity')

    SupportTagging.register(cls)
    return cls


def is_support_tagging(obj):
    """
    :param obj: a class or instance
    """
    if isinstance(obj, type):
        return issubclass(obj, SupportTagging)

    if not isinstance(obj, SupportTagging):
        return False

    if obj.id is None:
        return False

    return True


entity_tag_tbl = sa.Table(
    'entity_tags',
    Model.metadata,
    sa.Column(
        'tag_id', sa.Integer, sa.ForeignKey(
            'tag.id', ondelete='CASCADE')),
    sa.Column(
        'entity_id', sa.Integer, sa.ForeignKey(
            Entity.id, ondelete='CASCADE')),
    sa.UniqueConstraint('tag_id', 'entity_id'),)


@total_ordering
@python_2_unicode_compatible
class Tag(IdMixin, Model):
    """Tags are text labels that can be attached to :class:`entities <.Entity>`.

    They are namespaced, so that independent group of tags can be defined in the
    application. The default namespace is `"default"`.
    """
    __tablename__ = 'tag'

    #: namespace
    ns = sa.Column(
        sa.UnicodeText(),
        nullable=False,
        default='default',
        server_default='default')

    #: Label visible to the user
    label = sa.Column(sa.UnicodeText(), nullable=False)

    #: :class:`entities <.Entity>` attached to this tag
    entities = sa.orm.relationship(
        Entity,
        collection_class=set,
        secondary=entity_tag_tbl,
        backref=sa.orm.backref(
            TAGS_ATTR, collection_class=set),)

    __mapper_args__ = {'order_by': label,}

    __table_args__ = (
        sa.UniqueConstraint(ns, label),
        # namespace is not empty and is not surrounded by space characters
        sa.CheckConstraint(sa.sql.and_(sa.sql.func.trim(ns) == ns, ns != u''),),
        # label is not empty and is not surrounded by space characters
        sa.CheckConstraint(
            sa.sql.and_(sa.sql.func.trim(label) == label, label != u''),),)

    def __str__(self):
        return self.label

    def __lt__(self, other):
        return text_type(self).lower().__lt__(text_type(other).lower())

    def __repr__(self):
        cls = self.__class__
        return '<{mod}.{cls} id={t.id!r} ns={t.ns!r} label={t.label!r} at 0x{addr:x}>'.format(
            mod=cls.__module__,
            cls=cls.__name__,
            t=self,
            addr=id(self),)

# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask import g
from six import text_type
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, ForeignKey
from whoosh.fields import STORED

from .base import AUDITABLE, EDITABLE, SEARCHABLE, SYSTEM
from .subjects import User


class OwnedMixin(object):
    __indexation_args__ = {
        "index_to": (
            ("creator", ("creator",)),
            ("creator_name", (("creator_name", STORED),)),
            ("owner", ("owner",)),
            ("owner_name", (("owner_name", STORED),)),
        )
    }

    def __init__(self, *args, **kwargs):
        try:
            user = g.user
            if not self.creator and not g.user.is_anonymous:
                self.creator = user
            if not self.owner and not g.user.is_anonymous:
                self.owner = user
        except (RuntimeError, AttributeError):
            pass

    @declared_attr
    def creator_id(cls):
        return Column(ForeignKey(User.id), info=SYSTEM)

    @declared_attr
    def creator(cls):
        primary_join = "User.id == {}.creator_id".format(cls.__name__)
        return relationship(
            User,
            primaryjoin=primary_join,
            lazy="joined",
            uselist=False,
            info=SYSTEM | SEARCHABLE,
        )

    @property
    def creator_name(self):
        return text_type(self.creator) if self.creator else ""

    @declared_attr
    def owner_id(cls):
        return Column(ForeignKey(User.id), info=EDITABLE | AUDITABLE)

    @declared_attr
    def owner(cls):
        primary_join = "User.id == {}.owner_id".format(cls.__name__)
        return relationship(
            User,
            primaryjoin=primary_join,
            lazy="joined",
            uselist=False,
            info=EDITABLE | AUDITABLE | SEARCHABLE,
        )

    @property
    def owner_name(self):
        return text_type(self.owner) if self.owner else ""

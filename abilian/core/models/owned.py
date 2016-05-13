# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import g
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, ForeignKey
from whoosh.fields import STORED

from .base import AUDITABLE, EDITABLE, SEARCHABLE, SYSTEM
from .subjects import User


class OwnedMixin(object):
    __indexation_args__ = {
        'index_to': (('creator', ('creator',)),
                     ('creator_name', (('creator_name', STORED),)),
                     ('owner', ('owner',)),
                     ('owner_name', (('owner_name', STORED),)),)
    }

    def __init__(self, *args, **kwargs):
        if hasattr(g, 'user'):
            if not self.creator and not g.user.is_anonymous():
                self.creator = g.user
            if not self.owner and not g.user.is_anonymous():
                self.owner = g.user

    @declared_attr
    def creator_id(cls):
        return Column(ForeignKey(User.id), info=SYSTEM)

    @declared_attr
    def creator(cls):
        pj = "User.id == %s.creator_id" % cls.__name__
        return relationship(User,
                            primaryjoin=pj,
                            lazy='joined',
                            uselist=False,
                            info=SYSTEM | SEARCHABLE)

    @property
    def creator_name(self):
        return unicode(self.creator) if self.creator else u''

    @declared_attr
    def owner_id(cls):
        return Column(ForeignKey(User.id), info=EDITABLE | AUDITABLE)

    @declared_attr
    def owner(cls):
        pj = "User.id == %s.owner_id" % cls.__name__
        return relationship(User,
                            primaryjoin=pj,
                            lazy='joined',
                            uselist=False,
                            info=EDITABLE | AUDITABLE | SEARCHABLE)

    @property
    def owner_name(self):
        return unicode(self.owner) if self.owner else u''

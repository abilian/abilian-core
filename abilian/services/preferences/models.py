"""
Models for user preferences.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import backref, relation

from abilian.core.extensions import db
from abilian.core.models.subjects import User
from abilian.core.sqlalchemy import JSON


class UserPreference(db.Model):
    """An atom of user preference."""
    __tablename__ = 'user_preference'
    __table_args__ = (UniqueConstraint('user_id', 'key'),)

    #: Unique id for this preference.
    id = Column(Integer, primary_key=True, autoincrement=True)

    #: The user who set this preference.
    user = relation(User,
                    backref=backref('preferences',
                                    cascade="all, delete, delete-orphan"))
    user_id = Column(ForeignKey(User.id))

    #: The key
    key = Column(String, nullable=False)

    #: The value
    value = Column(JSON, nullable=False)

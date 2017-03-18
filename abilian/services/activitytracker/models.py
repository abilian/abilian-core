
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from sqlalchemy import Column, DateTime, Integer, String

from abilian.core.extensions import db
from datetime import datetime


class Viewed(db.Model):
    __tablename__ = "views_track"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)

    #: viewed object id
    object_id = Column(Integer, nullable=False)

    #: user id
    user_id = Column(Integer, nullable=False)

    #: time of view
    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=True)


class SignalLog(db.Model):
    __tablename__ = "signal_log"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)

    sender = Column(String(120), nullable=False)

    object_id = Column(Integer, nullable=False)

    user_id = Column(Integer, nullable=False)

    signal_time = Column(DateTime, default=datetime.utcnow, nullable=True)

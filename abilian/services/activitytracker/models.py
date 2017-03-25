from __future__ import absolute_import, division, print_function, \
    unicode_literals

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer

from abilian.core.extensions import db


class Viewed(db.Model):
    __tablename__ = "views_track"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)

    #: viewed object id
    object_id = Column(Integer, nullable=False)

    #: user id
    user_id = Column(Integer, nullable=False)

    #: time of view
    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=True)

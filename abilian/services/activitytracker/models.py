from __future__ import absolute_import, division, print_function, \
    unicode_literals

from datetime import datetime

from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import DateTime, Integer

from abilian.core.entities import Entity, db
from abilian.core.models.subjects import User


def _default_from(column):
    """
    Helper for default and onupdates parameters in a Column definitions.

    Returns a `context-sensitive default function <http://docs.sqlalchemy.org/en/rel_0_8/core/defaults.html#context-sensitive-default-functions>`_
    to set value from another column.
    """

    def _default_value(context):
        return context.current_parameters[column]

    return _default_value


class Track(db.Model):
    __tablename__ = "track"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)

    #: viewed object id
    object_id = Column(
        Integer, default=_default_from('_fk_object_id'), nullable=False)
    _fk_object_id = Column(Integer, ForeignKey(Entity.id, ondelete="SET NULL"))
    object = relationship(Entity, foreign_keys=_fk_object_id)

    #: user id
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    user = relationship(User, foreign_keys=user_id)

    track_logs = db.relationship(
        'TrackLog',
        backref='track',
        order_by='TrackLog.viewed_at',
        lazy='dynamic',)


class TrackLog(db.Model):
    __tablename__ = "track_log"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)

    track_id = db.Column(db.Integer, db.ForeignKey('track.id'))

    #: time of view
    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=True)

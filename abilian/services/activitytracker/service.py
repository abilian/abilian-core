"""

"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from abilian.services import Service
from abilian.core.extensions import db
from datetime import datetime
from .models import Viewed

__all__ = ['activitytracker', 'ActivityTracker']


class ActivityTracker(Service):
    name = 'activitytracker'

    def track_object(self, object_id, user_id):
        if not Viewed.query.filter(Viewed.object_id == object_id, Viewed.user_id == user_id).count():
            db.session.add(Viewed(object_id=object_id, user_id=user_id))
            db.session.commit()
        else:
            Viewed.query.filter(Viewed.object_id == object_id, Viewed.user_id == user_id).update({Viewed.viewed_at: datetime.utcnow()})

    # get a specific tracked object
    def get_tracked_object(self, object_id, user_id):
        track = Viewed.query.filter(Viewed.object_id == object_id, Viewed.user_id == user_id).first()
        return track

    # get all viewers of a specific object
    def get_viewers(self, object_id):
        viewers = Viewed.query.filter(Viewed.object_id == object_id).all()
        return viewers

    # get all viewed objects from a specific user
    def get_viewed_objects(self, user_id):
        viewed_objects = Viewed.query.filter(Viewed.user_id == user_id).all()
        return viewed_objects


# Instanciate the service
activitytracker = ActivityTracker()

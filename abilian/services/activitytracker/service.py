"""

"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from abilian.services import Service
from abilian.core.extensions import db
from .models import Viewed

__all__ = ['activitytracker', 'ActivityTracker']


class ActivityTracker(Service):
    name = 'activitytracker'

    def track_object(self, object_id, user_id):
        db.session.add(Viewed(object_id=object_id, user_id=user_id))
        db.session.commit()

    #: get tracks of a specific object and user
    def get_tracked_object(self, object_id, user_id):
        track = Viewed.query \
            .filter(Viewed.object_id == object_id, Viewed.user_id == user_id) \
            .order_by(Viewed.viewed_at.asc()) \
            .all()
        return track

    #: get all tracks that are related to a specific object
    def get_object_tracks(self, object_id):
        object_tracks = Viewed.query \
            .filter(Viewed.object_id == object_id) \
            .all()
        return object_tracks

    # get all viewers of a specific object
    def get_viewers(self, object_id):
        viewers = Viewed.query \
            .filter(Viewed.object_id == object_id) \
            .group_by(Viewed.user_id) \
            .all()
        return viewers

    # get all viewed objects from a specific user
    def get_viewed_objects(self, user_id):
        viewed_objects = Viewed.query \
            .filter(Viewed.user_id == user_id) \
            .group_by(Viewed.object_id) \
            .all()
        return viewed_objects


# Instanciate the service
activitytracker = ActivityTracker()

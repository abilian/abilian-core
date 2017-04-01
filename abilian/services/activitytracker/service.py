"""

"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from abilian.services import Service
from abilian.core.extensions import db
from .models import ViewsTrack

__all__ = ['activitytracker', 'ActivityTracker']


class ActivityTracker(Service):
    name = 'activitytracker'

    def track_object(self, object_id, user_id):
        if object_id and user_id:
            db.session.add(ViewsTrack(object_id=object_id, user_id=user_id))
            db.session.commit()

    #: get tracks of a specific object and user
    def get_tracked_object(self, object_id, user_id):
        if object_id and user_id:
            view_objects = ViewsTrack.query \
                .filter(ViewsTrack.object_id == object_id, ViewsTrack.user_id == user_id) \
                .order_by(ViewsTrack.viewed_at.asc()) \
                .all()
        return view_objects

    #: get all tracks that are related to a specific object
    def get_object_tracks(self, object_id):
        if object_id:
            view_objects = ViewsTrack.query \
                .filter(ViewsTrack.object_id == object_id) \
                .all()
        return view_objects

    # get all viewers of a specific object
    def get_viewers(self, object_id):
        if object_id:
            view_objects = ViewsTrack.query \
                .filter(ViewsTrack.object_id == object_id) \
                .group_by(ViewsTrack.user_id) \
                .all()
        return view_objects

    # get all ViewTrack objects from a specific user
    def get_viewed_objects(self, user_id):
        if user_id:
            view_objects = ViewsTrack.query \
                .filter(ViewsTrack.user_id == user_id) \
                .group_by(ViewsTrack.object_id) \
                .all()
        return view_objects


# Instanciate the service
activitytracker = ActivityTracker()

from __future__ import absolute_import, division, print_function, \
    unicode_literals

from abilian.core.extensions import db
from abilian.services import Service

from .models import Track, TrackLog

__all__ = ['activitytracker', 'ActivityTracker']


class ActivityTracker(Service):
    name = 'activitytracker'

    def track_object(self, object_id, user_id):
        track = Track.query.filter(Track.object_id == object_id,
                                   Track.user_id == user_id)
        if track.count():
            db.session.add(TrackLog(track=track.first()))
        else:
            new_track = Track(object_id=object_id, user_id=user_id)
            current_track_log = TrackLog(track=new_track)
            db.session.add(new_track)
            db.session.add(current_track_log)

        db.session.commit()

    #: get tracks of a specific object and user
    def get_tracked_object(self, object_id, user_id):
        view_objects = Track.query. \
            filter(Track.object_id == object_id, Track.user_id == user_id) \
            .first()
        return view_objects

    # get all viewers of a specific object
    def get_viewers(self, object_id):
        view_objects = Track.query \
            .filter(Track.object_id == object_id) \
            .all()
        return view_objects

    # get all ViewTrack objects from a specific user
    def get_viewed_objects(self, user_id):
        view_objects = Track.query \
            .filter(Track.user_id == user_id) \
            .all()
        return view_objects


# Instanciate the service
activitytracker = ActivityTracker()

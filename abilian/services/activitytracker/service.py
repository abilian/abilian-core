"""

"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from abilian.services import Service
from abilian.core.extensions import db
from datetime import datetime
from .models import Viewed, SignalLog


class ActivityTracker(Service):
    name = 'activitytracker'

    def object_tracked(self, sender, object_id, user_id):
        db.session.add(SignalLog(sender=sender, object_id=object_id, user_id=user_id))
        db.session.commit()

    def track_object(self, object_id, user_id):
        if not Viewed.query.filter(Viewed.object_id == object_id, Viewed.user_id == user_id).count():
            db.session.add(Viewed(object_id=object_id, user_id=user_id))
            db.session.commit()
        else:
            Viewed.query.filter(Viewed.object_id == object_id, Viewed.user_id == user_id).update({Viewed.viewed_at: datetime.utcnow()})

    def get_tracked_object(self, object_id, user_id):
        track = Viewed.query.filter(Viewed.object_id == object_id, Viewed.user_id == user_id).first()
        return track

    def get_viewers(self, object_id):
        viewers = Viewed.query.filter(Viewed.object_id == object_id).all()
        return viewers

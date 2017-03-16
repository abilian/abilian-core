"""

"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from abilian.services import Service
from abilian.core.extensions import db
from datetime import datetime

from .models import Viewed


class ActivityTracker(Service):
    name = 'activitytracker'

    def init_app(self, app):
        Service.init_app(self, app)

    def start(self):
        Service.start(self)

    def stop(self):
        Service.stop(self)

    def track_object(self, object_id, user_id):
        if not Viewed.query.filter(Viewed.object_id == object_id, Viewed.user_id == user_id).count():
            db.session.add(Viewed(object_id=object_id, user_id=user_id))
            db.session.commit()
        else:
            Viewed.query.filter(Viewed.object_id == object_id, Viewed.user_id == user_id)\
            .update({Viewed.viewed_at: datetime.utcnow()})

    def get_tracked_object(self, object_id, user_id):
        track = Viewed.query.filter(Viewed.object_id == object_id, Viewed.user_id == user_id).first()
        return track

    def get_viewers(self, object_id):
        viewers = Viewed.query.filter(Viewed.object_id == object_id).all()
        return viewers

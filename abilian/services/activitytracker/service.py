"""

"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from abilian.services import Service
from abilian.core.extensions import db
from datetime import datetime
from blinker import signal
from .models import Viewed
import logging


class ActivityTracker(Service):
    name = 'activitytracker'

    def __init__(self, signals=False):
        self.signals = signals
        if self.signals:
            self.init_signals()

    def init_app(self, app):
        Service.init_app(self, app)

    def init_signals(self):
        self.traked_object_signal = signal('object-tracked')
        self.get_traks_signal = signal('get-traks')
        self.get_viewers_signal = signal('get-viewers')
        self.traked_object_signal.connect(self.traker_signal_callback)
        self.get_traks_signal.connect(self.traker_signal_callback)
        self.get_viewers_signal.connect(self.traker_signal_callback)

    def start(self):
        Service.start(self)

    def stop(self):
        Service.stop(self)

    def traker_signal_callback(self, sender, action):
        logging.warn("{} : {} : {}".format(sender.name, action, datetime.utcnow()))

    def track_object(self, object_id, user_id):
        if self.signals:
            self.traked_object_signal.send(self, action="object-tracked")
        if not Viewed.query.filter(Viewed.object_id == object_id, Viewed.user_id == user_id).count():
            db.session.add(Viewed(object_id=object_id, user_id=user_id))
            db.session.commit()
        else:
            Viewed.query.filter(Viewed.object_id == object_id, Viewed.user_id == user_id)\
            .update({Viewed.viewed_at: datetime.utcnow()})

    def get_tracked_object(self, object_id, user_id):
        if self.signals:
            self.get_traks_signal.send(self, action="get-tracks")
        track = Viewed.query.filter(Viewed.object_id == object_id, Viewed.user_id == user_id).first()
        return track

    def get_viewers(self, object_id):
        if self.signals:
            self.get_viewers_signal.send(self, action="get-viewers")
        viewers = Viewed.query.filter(Viewed.object_id == object_id).all()
        return viewers

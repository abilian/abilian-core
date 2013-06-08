from abilian.core.extensions import db
from abilian.core.signals import activity

from .models import ActivityEntry


__all__ = ['ActivityService']


class ActivityService(object):

  def __init__(self, app=None):
    self.running = False
    if app:
      self.init_app(app)

  def init_app(self, app):
    self.app = app

  def start(self):
    assert not self.running
    activity.connect(self.log_activity)
    self.running = True

  def stop(self):
    assert self.running
    activity.disconnect(self.log_activity)
    self.running = False

  def log_activity(self, sender, actor, verb, object, subject=None):
    assert self.running
    entry = ActivityEntry()
    entry.actor = actor
    entry.verb = verb
    entry.object_id = object.id
    entry.object_class = object.__class__.__name__
    if subject:
      entry.subject_id = subject.id
      entry.subject_class = subject.__class__.__name__

    db.session.add(entry)

  @staticmethod
  def entries_for_actor(actor, limit=50):
    return ActivityEntry.query.filter(ActivityEntry.actor_id == actor.id).limit(limit).all()

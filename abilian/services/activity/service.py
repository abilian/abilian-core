from sqlalchemy import event
from sqlalchemy.orm.session import Session

from flask import g

from abilian.services import Service
from abilian.core.signals import activity

from .models import ActivityEntry

__all__ = ['ActivityService']


class ActivityService(Service):
  name = 'activity'

  _listening = False

  def init_app(self, app):
    Service.init_app(self, app)

    if not self._listening:
      event.listen(Session, "after_flush", self.flush)
      self._listening = True

  def start(self):
    Service.start(self)
    activity.connect(self.log_activity)

  def stop(self):
    Service.stop(self)
    activity.disconnect(self.log_activity)

  def log_activity(self, sender, actor, verb, object, target=None):
    assert self.running
    entry = ActivityEntry()
    entry.actor = actor
    entry.verb = verb
    entry._object = object
    entry._target = target
    if not hasattr(g, 'activities_to_flush'):
      g.activities_to_flush = []
    g.activities_to_flush.append(entry)

  def flush(self, session, flush_context):
    if not hasattr(g, 'activities_to_flush'):
      return

    while g.activities_to_flush:
      entry = g.activities_to_flush.pop()
      entry.object_id = entry._object.id
      entry.object_class = entry._object.__class__.__name__

      if entry._target:
        entry.target_id = entry._target.id
        entry.target_class = entry._target.__class__.__name__
      session.add(entry)

  @staticmethod
  def entries_for_actor(actor, limit=50):
    return ActivityEntry.query.filter(ActivityEntry.actor_id == actor.id).limit(limit).all()

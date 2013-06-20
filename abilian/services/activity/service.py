from flask import g
from sqlalchemy import event
from sqlalchemy.orm.session import Session
from abilian.core.extensions import db
from abilian.core.signals import activity

from .models import ActivityEntry


__all__ = ['ActivityService']


class ActivityService(object):

  def __init__(self, app=None):
    self.running = False
    self.listening = False
    if app:
      self.init_app(app)

  def init_app(self, app):
    self.app = app

  def start(self):
    assert not self.running
    activity.connect(self.log_activity)
    self.running = True

    if not self.listening:
      event.listen(Session, "after_flush", self.flush)
      self.listening = True

  def stop(self):
    assert self.running
    activity.disconnect(self.log_activity)
    self.running = False
    self.listening = False

  def log_activity(self, sender, actor, verb, object, subject=None):
    assert self.running
    entry = ActivityEntry()
    entry.actor = actor
    entry.verb = verb
    entry._object = object
    entry._subject = subject
    if not hasattr(g, 'activities_to_flush'):
      g.activities_to_flush = []
    g.activities_to_flush.append(entry)

  def flush(self, session, flush_context):
    if not hasattr(g, 'activities_to_flush'):
      return

    transaction = session.begin(subtransactions=True)

    for entry in g.activities_to_flush:
      entry.object_id = entry._object.id
      entry.object_class = entry._object.__class__.__name__

      if entry._subject:
        entry.subject_id = entry._subject.id
        entry.subject_class = entry._subject.__class__.__name__
      db.session.add(entry)

    transaction.commit()

  @staticmethod
  def entries_for_actor(actor, limit=50):
    return ActivityEntry.query.filter(ActivityEntry.actor_id == actor.id).limit(limit).all()

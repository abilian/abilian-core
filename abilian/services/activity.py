"""
Activity Service.

See: http://activitystrea.ms/specs/json/1.0/
See: http://activitystrea.ms/specs/atom/1.0/#activity
See: http://stackoverflow.com/questions/1443960/how-to-implement-the-activity-stream-in-a-social-network

TODO: replace `subject` by `target`. Also look wether other attributes from
the spec need to be implemented.
"""

from datetime import datetime

from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Integer, DateTime, Text

from abilian.core.entities import db, all_entity_classes
from abilian.core.signals import activity
from abilian.core.subjects import User


# TODO: review the design as it hits the DB with too many requests.
class ActivityEntry(db.Model):
  """Main table for all activities."""

  id = Column(Integer, primary_key=True)
  happened_at = Column(DateTime, default=datetime.utcnow)

  verb = Column(Text)

  actor_id = Column(Integer, ForeignKey(User.id))
  actor = relationship(User)

  object_class = Column(Text)
  object_id = Column(Integer)

  subject_class = Column(Text)
  subject_id = Column(Integer)

  def __repr__(self):
    return "<ActivityEntry id=%s actor=%s verb=%s object=%s subject=%s>" % (
      self.id, self.actor, self.verb, "TODO", "TODO")

  @property
  def object(self):
    for cls in all_entity_classes():
      if cls.__name__ == self.object_class:
        return cls.query.get(self.object_id)
    raise Exception("Unknown class: %s" % self.object_class)


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

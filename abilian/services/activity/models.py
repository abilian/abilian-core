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
from abilian.core.subjects import User

__all__ = ['ActivityEntry']


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

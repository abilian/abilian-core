"""
Activity Service.

See: http://activitystrea.ms/specs/json/1.0/
See: http://activitystrea.ms/specs/atom/1.0/#activity
See: http://stackoverflow.com/questions/1443960/how-to-implement-the-activity-stream-in-a-social-network

TODO: replace `subject` by `target`. Also look wether other attributes from
the spec need to be implemented.
"""

from datetime import datetime
from flask import logging

from sqlalchemy.orm import relationship, synonym
from sqlalchemy.schema import Column, ForeignKey, Index
from sqlalchemy.types import Integer, DateTime, Text

from abilian.core.entities import db, all_entity_classes
from abilian.core.subjects import User

__all__ = ['ActivityEntry']

logger = logging.getLogger(__name__)


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
  target_class = synonym('subject_class')
  target_id = synonym('subject_id')

  # TODO: replace the above (and the index below) by:
  # target_class = Column(Text)
  # target_id = Column(Integer)

  __table_args__ = (
    Index('object_index', 'object_class', 'object_id'),
    #Index('target_index', 'target_class', 'target_id'),
    Index('target_index', 'subject_class', 'subject_id'),
  )

  def __repr__(self):
    return "<ActivityEntry id=%s actor=%s verb=%s object=%s target=%s>" % (
      self.id, self.actor, self.verb, self.object, self.target)

  @property
  def object(self):
    if self.object_class is None:
      # TODO: object is probably never None, check the specs.
      return None
    if self.object_id is None:
      logger.warning("object_id is null on ActivityEntry with id=%d" % self.id)
      # TODO: should not happen
      return None
    for cls in all_entity_classes():
      if cls.__name__ == self.object_class:
        return cls.query.get(self.object_id)
    raise Exception("Unknown class: %s" % self.object_class)

  @property
  def target(self):
    if self.target_class is None:
      return None
    if self.target_id is None:
      # TODO: should not happen
      logger.warning("target_id is null on ActivityEntry with id=%d" % self.id)
      return None
    for cls in all_entity_classes():
      if cls.__name__ == self.target_class:
        return cls.query.get(self.target_id)
    raise Exception("Unknown class: %s" % self.target_class)

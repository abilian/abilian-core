from sqlalchemy.orm import object_session

from abilian.services import Service
from abilian.core.signals import activity

from .models import ActivityEntry

__all__ = ['ActivityService']


class ActivityService(Service):
  name = 'activity'

  def init_app(self, app):
    Service.init_app(self, app)

  def start(self):
    Service.start(self)
    activity.connect(self.log_activity)

  def stop(self):
    Service.stop(self)
    activity.disconnect(self.log_activity)

  def log_activity(self, sender, actor, verb, object, target=None):
    assert self.running
    entry = ActivityEntry(actor=actor, verb=verb, object=object, target=target)
    entry.object_type = object.entity_type

    if target is not None:
        entry.target_type = target.entity_type

    object_session(object).add(entry)

  @staticmethod
  def entries_for_actor(actor, limit=50):
    return ActivityEntry.query.filter(ActivityEntry.actor == actor).limit(limit).all()

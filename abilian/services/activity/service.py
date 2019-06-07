# coding=utf-8
""""""
import sqlalchemy as sa
from sqlalchemy.orm import object_session

from abilian.core.entities import Entity
from abilian.core.signals import activity
from abilian.services import Service

from .models import ActivityEntry

__all__ = ["ActivityService"]


class ActivityService(Service):
    name = "activity"

    def init_app(self, app):
        Service.init_app(self, app)

    def start(self, ignore_state: bool = False) -> None:
        super().start(ignore_state)
        activity.connect(self.log_activity)

    def stop(self, ignore_state: bool = False) -> None:
        super().stop(ignore_state)
        activity.disconnect(self.log_activity)

    def log_activity(self, sender, actor, verb, object, target=None):
        assert self.running
        if not isinstance(object, Entity):
            # generic forms may send signals inconditionnaly. For now we have activity
            # only for Entities
            return

        session = object_session(object)
        kwargs = {"actor": actor, "verb": verb, "object_type": object.entity_type}

        if sa.inspect(object).deleted:
            # object is in deleted state: flush has occurred, don't reference it or
            # we'll have an error when adding entry to session
            kwargs["object_id"] = object.id
        else:
            kwargs["object"] = object

        if target is not None:
            kwargs["target_type"] = target.entity_type
            if sa.inspect(target).deleted:
                kwargs["target_id"] = target.id
            else:
                kwargs["target"] = target

        entry = ActivityEntry(**kwargs)
        entry.object_type = object.entity_type
        session.add(entry)

    @staticmethod
    def entries_for_actor(actor, limit=50):
        return (
            ActivityEntry.query.filter(ActivityEntry.actor == actor).limit(limit).all()
        )

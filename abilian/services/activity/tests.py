from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.core.subjects import User
from abilian.testing import BaseTestCase

from .service import ActivityService


class Message1(Entity):
  pass

class ActivityTestCase(BaseTestCase):

  def setUp(self):
    BaseTestCase.setUp(self)
    self.activity_service = ActivityService()
    self.activity_service.start()

  def test(self):
    service = self.activity_service
    user = User(email=u'test@example.com')
    message = Message1()

    db.session.add(user)
    db.session.add(message)
    db.session.flush()

    service.log_activity(None, user, "post", message)
    db.session.flush()

    entries = service.entries_for_actor(user, 10)
    self.assertEquals(len(entries), 1)
    entry = entries[0]
    self.assertEquals(entry.actor, user)
    self.assertEquals(entry.object, message)



# coding=utf-8
"""
"""
from __future__ import absolute_import

import sqlalchemy as sa

from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.core.models.subjects import User
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
    message = Message1(creator=user, owner=user,
                       name=u'test message')

    with self.session.begin_nested():
      self.session.add(user)
      self.session.add(message)
    service.log_activity(None, user, "post", message)
    self.session.commit()

    m_id, m_type = message.id, message.entity_type

    entries = service.entries_for_actor(user, 10)
    self.assertEquals(len(entries), 1)

    entry = entries[0]
    self.assertEquals(entry.actor, user)
    self.assertEquals(entry.actor_id, user.id)
    self.assertEquals(entry.object, message)
    self.assertEquals(entry.object_type, m_type)
    self.assertEquals(entry._fk_object_id, m_id)
    self.assertEquals(entry.object_id, m_id)
    self.assertIs(entry.target, None)

    # test entry doesn't reference target if its in deleted state
    self.session.delete(message)
    self.session.flush()
    # send activity after flush: activity should not reference an instance in
    # "deleted state"
    service.log_activity(None, user, "delete", message)
    self.session.flush()

    entries = service.entries_for_actor(user, 10)
    self.assertEquals(len(entries), 2)
    entry = entries[1]
    self.assertIs(entry.object, None)
    self.assertEquals(entry.object_type, m_type)
    self.assertIs(entry._fk_object_id, None)
    self.assertEquals(entry.object_id, m_id)
    self.assertIs(entry.target, None)

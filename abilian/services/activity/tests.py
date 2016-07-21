# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from abilian.core.entities import Entity
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
        user = User(email='test@example.com')
        message = Message1(creator=user, owner=user, name='test message')

        with self.session.begin_nested():
            self.session.add(user)
            self.session.add(message)
        service.log_activity(None, user, "post", message)
        self.session.commit()

        m_id, m_type = message.id, message.entity_type

        entries = service.entries_for_actor(user, 10)
        assert len(entries) == 1

        entry = entries[0]
        assert entry.actor == user
        assert entry.actor_id == user.id
        assert entry.object == message
        assert entry.object_type == m_type
        assert entry._fk_object_id == m_id
        assert entry.object_id == m_id
        assert entry.target is None

        # test entry doesn't reference target if its in deleted state
        self.session.delete(message)
        self.session.flush()
        # send activity after flush: activity should not reference an instance in
        # "deleted state"
        service.log_activity(None, user, "delete", message)
        self.session.flush()

        entries = service.entries_for_actor(user, 10)
        assert len(entries) == 2
        entry = entries[1]
        assert entry.object is None
        assert entry.object_type == m_type
        assert entry._fk_object_id is None
        assert entry.object_id == m_id
        assert entry.target is None

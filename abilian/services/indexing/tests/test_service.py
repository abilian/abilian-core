# coding=utf-8
"""
"""
from __future__ import absolute_import
import sqlalchemy as sa
from abilian.core.entities import Entity
from abilian.testing import BaseTestCase

class IndexedContact(Entity):

  name = sa.Column(sa.UnicodeText)


class IndexingServiceTestCase(BaseTestCase):

  def setUp(self):
    BaseTestCase.setUp(self)
    self.svc = self.app.services['indexing']
    self.svc.start()

  def get_setup_config(self):
    cfg = BaseTestCase.get_setup_config(self)
    # cfg.SQLALCHEMY_ECHO = True
    return cfg

  def test_index_only_after_final_commit(self):
    contact = IndexedContact(name=u'John Doe')
    state = self.svc.app_state
    self.session.begin(nested=True)

    self.assertEquals(state.to_update, [])
    self.session.add(contact)

    # no commit: model is in wait queue
    self.session.flush()
    self.assertEquals(state.to_update, [('new', contact)])

    # commit but in a sub transaction: model still in wait queue
    self.session.commit()
    self.assertEquals(state.to_update, [('new', contact)])

    # 'final' commit: models sent for indexing update
    self.session.commit()
    self.assertEquals(state.to_update, [])

  def test_clear(self):
    # just check no exception happens
    self.svc.clear()

    # check no double stop (would raise AssertionError from service base)
    self.svc.start()
    self.svc.stop()
    self.svc.clear()

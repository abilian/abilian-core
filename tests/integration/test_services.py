from nose.tools import eq_
from sqlalchemy import Column, UnicodeText, Text, LargeBinary
from base import IntegrationTestCase

from yaka.services.audit import AuditEntry, AuditService
from yaka.core.entities import Entity, SEARCHABLE


class Account(Entity):
  __tablename__ = 'account'

  name = Column(UnicodeText, default=u"", info=SEARCHABLE)
  website = Column(Text, default=u"")
  office_phone = Column(UnicodeText, default=u"")


class TestAudit(IntegrationTestCase):

  def setUp(self):
    AuditService.instance().start()
    IntegrationTestCase.setUp(self)

  def tearDown(self):
    IntegrationTestCase.tearDown(self)
    AuditService.instance().stop()

  def test_audit(self):
    eq_(0, len(AuditEntry.query.all()))

    account = Account(name="John SARL")
    self.session.add(account)
    self.session.commit()

    eq_(1, len(AuditEntry.query.all()))

    account.website = "http://www.john.com/"
    self.session.commit()

    eq_(2, len(AuditEntry.query.all()))

    self.session.delete(account)
    self.session.commit()

    eq_(3, len(AuditEntry.query.all()))

from nose.tools import eq_
from sqlalchemy import Column, UnicodeText, Text

from yaka.services import audit
from yaka.services.audit import AuditEntry
from yaka.core.entities import Entity, SEARCHABLE

from .base import IntegrationTestCase


class Account(Entity):
  __tablename__ = 'account'

  name = Column(UnicodeText, default=u"", info=SEARCHABLE)
  website = Column(Text, default=u"")
  office_phone = Column(UnicodeText, default=u"")


class TestAudit(IntegrationTestCase):

  def setUp(self):
    audit.init_app(self.app)
    audit.start()
    IntegrationTestCase.setUp(self)

  def tearDown(self):
    IntegrationTestCase.tearDown(self)
    audit.stop()

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

import datetime
from itertools import count

import sqlalchemy as sa
from sqlalchemy.orm.attributes import NEVER_SET
from sqlalchemy import (Column, Unicode, UnicodeText, Text, Date, ForeignKey,
                        Integer)

from abilian.core.models.base import SEARCHABLE, AUDITABLE_HIDDEN
from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.testing import BaseTestCase

from . import audit_service
from . import AuditEntry, CREATION, UPDATE, DELETION


class DummyAccount(Entity):
  name = Column(UnicodeText, default=u"", info=SEARCHABLE)
  password = Column(Unicode, default=u'*', info=AUDITABLE_HIDDEN)
  website = Column(Text, default=u"")
  office_phone = Column(UnicodeText, default=u"")
  birthday = Column(Date)


class AccountRelated(db.Model):
  __tablename__ = 'account_related'
  __auditable_entity__ = ('account', 'data', ('id',))
  id = Column(Integer, primary_key=True)

  account_id = Column(Integer, ForeignKey(DummyAccount.id), nullable=False)
  account = sa.orm.relationship(
    DummyAccount,
    backref=sa.orm.backref('data',
                           order_by='AccountRelated.id',
                           cascade='all, delete-orphan'))

  text = Column(UnicodeText, default=u"")


class CommentRelated(db.Model):
  __tablename__ = 'account_related_comment'
  __auditable_entity__ = ('related.account',
                          'data.comments',
                          ('related.id', 'id'))
  id = Column(Integer, primary_key=True)

  related_id = Column(Integer, ForeignKey(AccountRelated.id), nullable=False)
  related = sa.orm.relationship(
    AccountRelated,
    backref=sa.orm.backref('comments', order_by='CommentRelated.id',
                           cascade='all, delete-orphan'))
  text = Column(UnicodeText, default=u"")


class TestAudit(BaseTestCase):

  def setUp(self):
    audit_service.start()
    BaseTestCase.setUp(self)

  def tearDown(self):
    BaseTestCase.tearDown(self)
    if audit_service.running:
      audit_service.stop()

  def test_audit(self):
    # Creation of system user(0) should have created one entry.
    # We clear it for this test.
    AuditEntry.query.delete()
    db.session.flush()
    assert len(AuditEntry.query.all()) == 0

    account = DummyAccount(name=u"John SARL")
    db.session.add(account)
    db.session.commit()
    assert len(AuditEntry.query.all()) == 1

    entry = AuditEntry.query.one()
    assert entry.type == CREATION
    assert entry.entity_id == account.id
    assert entry.entity == account

    account.website = "http://www.john.com/"
    db.session.commit()
    assert len(AuditEntry.query.all()) == 2

    entry = AuditEntry.query.order_by(AuditEntry.happened_at).all()[1]
    assert entry.type == UPDATE
    assert entry.entity_id == account.id
    assert entry.entity == account
    assert entry.changes == {u'website': (u'', u'http://www.john.com/')}

    account.birthday = datetime.date(2012, 12, 25)
    db.session.commit()
    assert len(AuditEntry.query.all()) == 3

    entry = AuditEntry.query.order_by(AuditEntry.happened_at).all()[2]
    assert entry.type == UPDATE
    assert entry.entity_id == account.id
    assert entry.entity == account
    assert entry.changes == {u'birthday': (None, datetime.date(2012, 12, 25))}

    # content hiding
    account.password = u'new super secret password'
    assert account.__changes__ == {u'password': (u'******', u'******')}
    db.session.commit()

    entry = AuditEntry.query.order_by(AuditEntry.happened_at).all()[3]
    assert entry.type == UPDATE
    assert entry.entity_id == account.id
    assert entry.entity == account
    assert entry.changes == {u'password': (u'******', u'******')}

    # deletion
    db.session.delete(account)
    db.session.commit()
    assert len(AuditEntry.query.all()) == 5

    entry = AuditEntry.query.order_by(AuditEntry.happened_at).all()[4]
    assert entry.type == DELETION
    assert entry.entity_id == account.id
    assert entry.entity is None

    # check all entries are still present (but have lost reference to entity)
    entries = AuditEntry.query.all()
    assert len(entries) == 5
    assert all(e.entity_id == account.id for e in entries)
    assert all(e.entity is None for e in entries)

  def test_audit_related(self):
    AuditEntry.query.delete()
    db.session.flush()
    assert len(AuditEntry.query.all()) == 0

    #  helper
    audit_idx = count()
    audit_query = AuditEntry.query.order_by(AuditEntry.happened_at)

    def next_entry():
      return audit_query.all()[audit_idx.next()]

    account = DummyAccount(name=u"John SARL")
    db.session.add(account)
    db.session.commit()
    assert len(AuditEntry.query.all()) == 1
    audit_idx.next()

    data = AccountRelated(account=account, text=u'text 1')
    db.session.add(data)
    db.session.commit()

    entry = next_entry()
    assert entry.op == CREATION
    assert entry.related
    assert entry.entity_type == account.entity_type
    assert entry.entity_id == account.id
    assert entry.entity == account

    changes = entry.changes
    assert len(changes) == 1
    assert 'data 1' in changes
    changes = changes['data 1']
    assert changes == {'text': (NEVER_SET, u'text 1'),
                       'account_id': (NEVER_SET, 1),
                       'id': (None, 1), }

    comment = CommentRelated(related=data, text=u'comment')
    db.session.add(comment)
    db.session.commit()
    entry = next_entry()
    assert entry.op == CREATION
    assert entry.related
    assert entry.entity_type == account.entity_type
    assert entry.entity_id == account.id

    changes = entry.changes
    assert len(changes) == 1
    assert 'data.comments 1 1' in changes
    changes = changes['data.comments 1 1']
    assert changes == {'text': (NEVER_SET, u'comment'),
                       'related_id': (NEVER_SET, 1),
                       'id': (None, 1), }

    comment = CommentRelated(related=data, text=u'comment 2')
    db.session.add(comment)
    db.session.commit()
    entry = next_entry()
    assert entry.op == CREATION
    assert entry.related
    assert entry.entity_type == account.entity_type
    assert entry.entity_id == account.id

    changes = entry.changes
    assert len(changes) == 1
    assert 'data.comments 1 2' in changes
    changes = changes['data.comments 1 2']
    assert changes == {'text': (NEVER_SET, u'comment 2'),
                       'related_id': (NEVER_SET, 1),
                       'id': (None, 2), }

    # deletion
    db.session.delete(comment)
    db.session.commit()

    entry = next_entry()
    assert entry.op == DELETION
    assert entry.related
    assert entry.entity_id == account.id
    # entity not deleted: audit should still have reference to it
    assert entry.entity == account

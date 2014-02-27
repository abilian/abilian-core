from unittest import TestCase
from datetime import datetime
import sqlalchemy as sa

from abilian.core.models.base import SEARCHABLE, NOT_SEARCHABLE, AUDITABLE, Info
from abilian.core.models.subjects import User

from .dummy import DummyContact


class EntityTestCase(TestCase):
  def test(self):
    contact = DummyContact(first_name=u"John")
    self.assertEquals(None, contact.creator)
    self.assertEquals(None, contact.owner)

    user = User()
    contact.owner = user
    contact.creator = user

  def test_updated_at(self):
    engine = sa.create_engine('sqlite:///:memory:', echo=False)
    Session = sa.orm.sessionmaker(bind=engine)
    session = Session()

    setattr(session, '_model_changes', {})  # flask-sqlalchemy as listeners
                                            # looking for this

    DummyContact.metadata.create_all(engine)
    contact = DummyContact()
    session.add(contact)
    session.commit()

    assert isinstance(contact.updated_at, datetime)
    updated = contact.updated_at

    contact.first_name = u'John'
    session.commit()

    assert isinstance(contact.updated_at, datetime)
    assert contact.updated_at > updated


class InfoTestCase(TestCase):

  def test(self):
    info = SEARCHABLE
    assert info['searchable']

    info = NOT_SEARCHABLE
    assert not info['searchable']

    info = SEARCHABLE + AUDITABLE
    assert info['searchable']
    assert info['auditable']
    assert isinstance(info, Info)

    info = SEARCHABLE | AUDITABLE
    assert info['searchable']
    assert info['auditable']
    assert isinstance(info, Info)


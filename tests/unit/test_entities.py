from unittest import TestCase
from tests.unit.dummy import DummyContact

from yaka.core.entities import SEARCHABLE, NOT_SEARCHABLE, AUDITABLE
from yaka.core.subjects import User


class EntityTestCase(TestCase):
  def test(self):
    contact = DummyContact(first_name=u"John")
    self.assertEquals(None, contact.creator)
    self.assertEquals(None, contact.owner)

    user = User()
    contact.owner = user
    contact.creator = user


class InfoTestCase(TestCase):

  def test(self):
    info = SEARCHABLE
    assert info['searchable']

    info = NOT_SEARCHABLE
    assert not info['searchable']

    info = SEARCHABLE + AUDITABLE
    assert info['searchable']
    assert info['auditable']

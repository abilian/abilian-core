from unittest import TestCase

from abilian.core.entities import SEARCHABLE, NOT_SEARCHABLE, AUDITABLE
from abilian.core.subjects import User

from .dummy import DummyContact


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

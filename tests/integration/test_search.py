"""
Test the index service.
"""
from sqlalchemy import UnicodeText, Text, Column
from abilian.core.entities import Entity, SEARCHABLE
from abilian.services import index_service

from .base import IntegrationTestCase


class DummyContact1(Entity):
  salutation = Column(UnicodeText, default=u"")
  first_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
  last_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
  email = Column(Text, default=u"")


class IndexingTestCase(IntegrationTestCase):

  def setUp(self):
    index_service.start()
    IntegrationTestCase.setUp(self)

  def tearDown(self):
    IntegrationTestCase.tearDown(self)
    if index_service.running:
      index_service.stop()

  def test_contacts_are_indexed(self):
    contact = DummyContact1(first_name=u"John", last_name=u"Test User", email=u"test@example.com")
    self.session.add(contact)
    self.session.commit()

    # Check 3 different APIs
    search_result = list(DummyContact1.search_query(u"john").all())
    assert len(search_result) == 1
    assert contact == search_result[0]

    search_result = list(DummyContact1.search_query.search(u"john", get_models=True))
    assert len(search_result) == 1
    assert contact.id == int(search_result[0]['id'])
    assert contact == search_result[0].model

    search_result = list(index_service.search(u"john"))
    assert len(search_result) == 1
    assert contact.id == int(search_result[0]['id'])

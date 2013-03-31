"""
Test the index service.
"""

from .base import IntegrationTestCase
from ..unit.dummy import DummyContact

from abilian.services import index_service


class IndexingTestCase(IntegrationTestCase):

  def setUp(self):
    index_service.start()
    IntegrationTestCase.setUp(self)

  def tearDown(self):
    IntegrationTestCase.tearDown(self)
    if index_service.running:
      index_service.stop()

  def test_contacts_are_indexed(self):
    contact = DummyContact(first_name=u"John", last_name=u"Test User", email=u"test@example.com")
    self.session.add(contact)
    self.session.commit()

    # Check 3 different APIs
    search_result = list(DummyContact.search_query(u"john").all())
    assert len(search_result) == 1
    assert contact == search_result[0]

    search_result = list(DummyContact.search_query.search(u"john", get_models=True))
    assert len(search_result) == 1
    assert contact.id == int(search_result[0]['id'])
    assert contact == search_result[0].model

    search_result = list(index_service.search(u"john"))
    assert len(search_result) == 1
    assert contact.id == int(search_result[0]['id'])

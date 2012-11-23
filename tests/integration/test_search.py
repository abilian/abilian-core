from unittest import skip
from nose.tools import eq_, ok_

from sqlalchemy import Column, UnicodeText, Text
from base import IntegrationTestCase

from yaka.services import indexing
from yaka.core.entities import SEARCHABLE, Entity

from .util import DataLoader


class Contact(Entity):
  """Mixin class for persons."""

  salutation = Column(UnicodeText, default=u"")
  first_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
  last_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
  email = Column(Text, default=u"")

@skip
class SearchTestCase(IntegrationTestCase):
  # Hack to work around test framework bug
  __name__ = "Search test case"

  init_data = True
  no_login = True

  def setUp(self):
    # TODO
    self.index = indexing.get_service()
    self.index.start()
    IntegrationTestCase.setUp(self)

  def tearDown(self):
    IntegrationTestCase.tearDown(self)
    self.index.stop()

  def test_contacts_are_indexed(self):
    contact = Contact(first_name="John", last_name="Test User", email="test@example.com")
    self.session.add(contact)
    self.session.commit()

    # Check 3 different APIs
    search_result = list(Contact.search_query(u"john").all())
    eq_(1, len(search_result))
    eq_(contact, search_result[0])

    search_result = list(Contact.search_query.search(u"john"))
    eq_(1, len(search_result))
    eq_(contact, search_result[0][1])
    eq_(contact.id, int(search_result[0][0]['id']))

    search_result = list(self.index.search(u"john"))
    eq_(1, len(search_result))
    eq_(contact, search_result[0][1])
    eq_(contact.id, int(search_result[0][0]['id']))

  @skip
  def test_basic_search(self):
    # Note: there a guy named "Paul Dupont" in the test data
    response = self.client.get("/search/?q=dupont")
    self.assert_200(response)
    ok_("Paul" in response.data)

  @skip
  def test_live_search(self):
    response = self.client.get("/search/live?q=dupont")
    self.assert_200(response)
    ok_("Paul" in response.data)

  @skip
  def test_document_search(self):
    loader = DataLoader()
    loader.load_users()
    loader.load_files()

    response = self.client.get("/search/docs?q=rammstein")
    self.assert_200(response)
    print response.data
    ok_("Wikipedia" in response.data)

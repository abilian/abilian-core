from sqlalchemy import Column, UnicodeText, Text
from base import IntegrationTestCase

from yaka.services import index_service
from yaka.core.entities import SEARCHABLE, Entity


class Contact(Entity):
  """Mixin class for persons."""

  salutation = Column(UnicodeText, default=u"")
  first_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
  last_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
  email = Column(Text, default=u"")


class SearchTestCase(IntegrationTestCase):
  # Hack to work around test framework bug
  __name__ = "Search test case"

  init_data = True
  no_login = True

  def setUp(self):
    index_service.init_app(self.app)
    index_service.start()
    IntegrationTestCase.setUp(self)

  def tearDown(self):
    IntegrationTestCase.tearDown(self)
    if index_service.running:
      index_service.stop()

  def test_contacts_are_indexed(self):
    contact = Contact(first_name="John", last_name="Test User", email="test@example.com")
    self.session.add(contact)
    self.session.commit()

    # Check 3 different APIs
    search_result = list(Contact.search_query(u"john").all())
    assert len(search_result) == 1
    assert contact == search_result[0]

    search_result = list(Contact.search_query.search(u"john"))
    assert len(search_result) == 1
    assert contact == search_result[0][1]
    assert contact.id == int(search_result[0][0]['id'])

    search_result = list(index_service.search(u"john"))
    assert len(search_result) == 1
    assert contact == search_result[0][1]
    assert contact.id == int(search_result[0][0]['id'])


# TODO: move this tests to a package that actually provides web UI.
#  def test_basic_search(self):
#    # Note: there a guy named "Paul Dupont" in the test data
#    response = self.client.get("/search/?q=dupont")
#    self.assert_200(response)
#    assert "Paul" in response.data
#
#  def test_live_search(self):
#    response = self.client.get("/search/live?q=dupont")
#    self.assert_200(response)
#    assert "Paul" in response.data
#
#  def test_document_search(self):
#    loader = DataLoader()
#    loader.load_users()
#    loader.load_files()
#
#    response = self.client.get("/search/docs?q=rammstein")
#    self.assert_200(response)
#    print response.data
#    assert "Wikipedia" in response.data

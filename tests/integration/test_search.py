"""
Test the index service.
"""
import mimetypes
from random import choice, randint, sample
from os import listdir
from genericpath import isdir
from os.path import dirname

from sqlalchemy import Column, UnicodeText, Text, join
from base import IntegrationTestCase
from yaka.core.extensions import db
from yaka.core.subjects import User

from yaka.services import index_service
from yaka.core.entities import SEARCHABLE, Entity


class Contact(Entity):
  """Mixin class for persons."""

  salutation = Column(UnicodeText, default=u"")
  first_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
  last_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
  email = Column(Text, default=u"")


class IndexingTestCase(IntegrationTestCase):

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

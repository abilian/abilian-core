"""
Test the index service.
"""
from sqlalchemy import Column, Text, UnicodeText
from sqlalchemy.orm import column_property

from abilian.core.entities import SEARCHABLE, Entity
from abilian.services import index_service

from .base import IntegrationTestCase


def gen_name(ctx):
    params = ctx.current_parameters
    return u'{} {}'.format(
        params.get('first_name') or u'', params.get('last_name') or u'').strip()


class DummyContact1(Entity):
    name = column_property(
        Column('name',
               UnicodeText(),
               info=SEARCHABLE,
               default=gen_name,
               onupdate=gen_name),
        Entity.name)

    salutation = Column(UnicodeText, default=u"")
    first_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
    last_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
    email = Column(Text, default=u"")


class IndexingTestCase(IntegrationTestCase):
    SERVICES = ('security', 'indexing',)

    def tearDown(self):
        if index_service.running:
            index_service.stop()
        IntegrationTestCase.tearDown(self)

    def test_contacts_are_indexed(self):
        self.login_system()
        contact = DummyContact1(first_name=u"John",
                                last_name=u"Test User",
                                email=u"test@example.com")
        self.session.add(contact)
        self.session.commit()

        search_result = index_service.search(u'john')
        assert len(search_result) == 1
        found = search_result[0]
        assert contact.id == found['id']
        assert contact.name == found['name']

        search_result = index_service.search(u"john")
        assert len(search_result) == 1
        assert contact.id == int(search_result[0]['id'])

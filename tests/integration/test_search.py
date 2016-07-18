"""
Test the index service.
"""
from __future__ import absolute_import, print_function, unicode_literals

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
        Column(
            'name',
            UnicodeText(),
            info=SEARCHABLE,
            default=gen_name,
            onupdate=gen_name),
        Entity.name)

    salutation = Column(UnicodeText, default="")
    first_name = Column(UnicodeText, default="", info=SEARCHABLE)
    last_name = Column(UnicodeText, default="", info=SEARCHABLE)
    email = Column(Text, default="")


class IndexingTestCase(IntegrationTestCase):
    SERVICES = ('security', 'indexing')

    def tearDown(self):
        if index_service.running:
            index_service.stop()
        IntegrationTestCase.tearDown(self)

    def test_contacts_are_indexed(self):
        self.login_system()
        contact = DummyContact1(
            first_name="John", last_name="Test User", email="test@example.com")
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

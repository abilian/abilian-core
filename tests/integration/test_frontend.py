"""
Test the frontend.
"""
from flask.ext.wtf import Form
from sqlalchemy import Column, String, UnicodeText

from abilian.core.entities import Entity
from abilian.testing import BaseTestCase
from abilian.web.frontend import CRUDApp, Module


class EmailAddress(object):
    pass


class Contact(Entity):
    __tablename__ = 'contact'

    email = Column(String, nullable=False)
    first_name = Column(UnicodeText)
    last_name = Column(UnicodeText)


class ContactEditForm(Form):
    _groups = [[u'Main', ['email', 'first_name', 'last_name']]]


class Contacts(Module):
    managed_class = Contact

    list_view_columns = [
        dict(name='_name', width=35),
        dict(name='first_name', width=25),
        dict(name='last_name', width=14),
        dict(name='email', width=20),
    ]

    edit_form_class = ContactEditForm

    related_views = [
        # TODO
        #('Visites', 'visites', ('partenaire', 'visiteur', 'date')),
    ]


class SimpleCRM(CRUDApp):
    modules = [Contacts()]
    url = "/crm"


class FrontendTestCase(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)
        self.crm = SimpleCRM(self.app)

    def test(self):
        response = self.client.get("/crm/contacts/json")
        self.assert_200(response)

        # TODO: test more endpoints (but these needs the templates).
        # /crm/contacts/export_xls
        # /crm/contacts/export
        # /crm/contacts/json2
        # /crm/contacts/json
        # /crm/contacts/new
        # /crm/contacts/new
        # /crm/contacts/
        # /crm/contacts/<int:entity_id>/delete
        # /crm/contacts/<int:entity_id>/edit
        # /crm/contacts/<int:entity_id>/edit
        # /crm/contacts/<int:entity_id>

        # response = self.client.get("/crm/contacts/")
        # self.assert_200(response)
        #
        # response = self.client.get("/crm/contacts/new")
        # self.assert_200(response)

        # response = self.client.get("/crm/contacts/json2")
        # self.assert_200(response)

        # response = self.client.get("/crm/contacts/export")
        # self.assert_200(response)

        # response = self.client.get("/crm/contacts/export_xls")
        # self.assert_200(response)

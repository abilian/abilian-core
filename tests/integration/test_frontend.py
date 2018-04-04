# coding=utf-8
"""Test the frontend."""
from __future__ import absolute_import, print_function, unicode_literals

from flask_wtf import Form
from sqlalchemy import Column, String, UnicodeText

from abilian.core.entities import Entity
from abilian.web.frontend import CRUDApp, Module


class EmailAddress(object):
    pass


class Contact(Entity):
    __tablename__ = 'contact'

    email = Column(String, nullable=False)
    first_name = Column(UnicodeText)
    last_name = Column(UnicodeText)


class ContactEditForm(Form):
    _groups = [['Main', ['email', 'first_name', 'last_name']]]


class Contacts(Module):
    managed_class = Contact
    list_view_columns = [
        {
            'name': '_name',
            'width': 35,
        },
        {
            'name': 'first_name',
            'width': 25,
        },
        {
            'name': 'last_name',
            'width': 14,
        },
        {
            'name': 'email',
            'width': 20,
        },
    ]
    edit_form_class = ContactEditForm
    related_views = ()


class SimpleCRM(CRUDApp):
    modules = [Contacts()]
    url = "/crm"


def test_json(app, client, db_session):
    SimpleCRM(app)
    response = client.get("/crm/contacts/json")
    assert response.status_code == 200


def test_contact_list(app, client, db_session):
    SimpleCRM(app)
    response = client.get("/crm/contacts/")
    assert response.status_code == 200

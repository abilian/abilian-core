"""
Test the frontend.
"""
from flask.ext.wtf import Form
from sqlalchemy import Column, UnicodeText, String

from abilian.core.entities import Entity
from abilian.web.frontend import CRUDApp, Module

from .base import IntegrationTestCase


class EmailAddress(object):
  pass


class Contact(Entity):
  __tablename__ = 'contact'

  email = Column(String, nullable=False)
  first_name = Column(UnicodeText)
  last_name = Column(UnicodeText)


class ContactEditForm(Form):
  _groups = [
    [u'Main', ['email', 'first_name', 'last_name']]
  ]


class Contacts(Module):
  managed_class = Contact

  list_view_columns = [
    dict(name='_name', width=35),
    dict(name='partenaire', width=25),
    dict(name='titre', width=14),
    dict(name='email', width=20)]

  edit_form_class = ContactEditForm

  related_views = [
    # TODO
    #('Visites', 'visites', ('partenaire', 'visiteur', 'date')),
  ]


class SimpleCRM(CRUDApp):
  modules = [Contacts()]
  url = "/crm"


class FrontendTestCase(IntegrationTestCase):

  def setUp(self):
    crm = SimpleCRM(self.app)

  def test(self):
    pass

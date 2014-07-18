# coding=utf-8
"""
"""
from __future__ import absolute_import

from unittest import TestCase
from datetime import datetime
import sqlalchemy as sa

from abilian.core.models.base import SEARCHABLE, NOT_SEARCHABLE, AUDITABLE, Info
from abilian.core.models.subjects import User

from .dummy import DummyContact


class EntityTestCase(TestCase):

  def get_session(self):
    engine = sa.create_engine('sqlite:///:memory:', echo=False)
    Session = sa.orm.sessionmaker(bind=engine)
    session = Session()

    setattr(session, '_model_changes', {})  # flask-sqlalchemy as listeners
                                            # looking for this

    DummyContact.metadata.create_all(engine)
    return session

  def test(self):
    contact = DummyContact(first_name=u"John")
    self.assertEquals(None, contact.creator)
    self.assertEquals(None, contact.owner)

    user = User()
    contact.owner = user
    contact.creator = user

  def test_auto_slug_property(self):
    obj = DummyContact(name=u'a b c')
    self.assertEquals(obj.auto_slug, u'a-b-c')
    obj.name = u"C'est l'été !"
    self.assertEquals(obj.auto_slug, u'c-est-l-ete')

    # with a special space character
    obj.name = u"a_b\u205fc" # U+205F: MEDIUM MATHEMATICAL SPACE
    self.assertEquals(obj.auto_slug, u'a-b-c')

    # with non-ascii translatable chars, like EN DASH U+2013 (–) and EM DASH
    # U+2014 (—). Standard separator is \u002d (\x2d) "-" HYPHEN-MINUS.
    # this test may fails depending on how  unicode normalization + char
    # substitution is done (order matters).
    obj.name = u'a\u2013b\u2014c' # u'a–b—c'
    slug = obj.auto_slug
    self.assertEquals(slug, u'a-b-c')
    self.assertTrue(u'\u2013' not in slug)
    self.assertTrue(u'\u002d' in slug)

  def test_updated_at(self):
    session = self.get_session()
    contact = DummyContact()
    session.add(contact)
    session.commit()

    assert isinstance(contact.updated_at, datetime)
    updated = contact.updated_at

    contact.first_name = u'John'
    session.commit()

    assert isinstance(contact.updated_at, datetime)
    assert contact.updated_at > updated

  def test_auto_slug(self):
    session = self.get_session()
    contact = DummyContact(name=u'Pacôme Hégésippe Adélard Ladislas')

    session.add(contact)
    session.flush()
    self.assertEquals(contact.slug, u'pacome-hegesippe-adelard-ladislas')

    # test when name is None
    contact = DummyContact()
    session.add(contact)
    session.flush()
    expected = u'dummycontact-{}'.format(contact.id)
    self.assertEquals(contact.slug, expected)


class InfoTestCase(TestCase):

  def test(self):
    info = SEARCHABLE
    assert info['searchable']

    info = NOT_SEARCHABLE
    assert not info['searchable']

    info = SEARCHABLE + AUDITABLE
    assert info['searchable']
    assert info['auditable']
    assert isinstance(info, Info)

    info = SEARCHABLE | AUDITABLE
    assert info['searchable']
    assert info['auditable']
    assert isinstance(info, Info)

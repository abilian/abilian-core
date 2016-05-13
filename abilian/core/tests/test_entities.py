# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from datetime import datetime
from unittest import TestCase

import sqlalchemy as sa

from abilian.core.entities import Entity
from abilian.core.models.base import (AUDITABLE, NOT_SEARCHABLE, SEARCHABLE,
                                      Info)
from abilian.core.models.subjects import User
from abilian.services import security
from abilian.testing import BaseTestCase as AbilianTestCase

from .dummy import DummyContact


class EntityTestCase(TestCase):

    def get_session(self):
        engine = sa.create_engine('sqlite:///:memory:', echo=False)
        Session = sa.orm.sessionmaker(bind=engine)
        session = Session()

        # flask-sqlalchemy as listeners looking for this
        session._model_changes = {}

        DummyContact.metadata.create_all(engine)
        return session

    def test(self):
        contact = DummyContact(first_name=u"John")
        assert contact.creator is None
        assert contact.owner is None

        user = User()
        contact.owner = user
        contact.creator = user

    def test_auto_slug_property(self):
        session = self.get_session()
        obj = DummyContact(name=u'a b c')
        session.add(obj)
        session.flush()
        assert obj.auto_slug == u'a-b-c'

        obj.name = u"C'est l'été !"
        assert obj.auto_slug == u'c-est-l-ete'

        # with a special space character
        obj.name = u"a_b\u205fc"  # U+205F: MEDIUM MATHEMATICAL SPACE
        assert obj.auto_slug == u'a-b-c'

        # with non-ascii translatable chars, like EN DASH U+2013 (–) and EM DASH
        # U+2014 (—). Standard separator is \u002d (\x2d) "-" HYPHEN-MINUS.
        # this test may fails depending on how  unicode normalization + char
        # substitution is done (order matters).
        obj.name = u'a\u2013b\u2014c'  # u'a–b—c'
        slug = obj.auto_slug
        assert slug == u'a-b-c'
        assert u'\u2013' not in slug
        assert u'\u002d' in slug

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
        contact1 = DummyContact(name=u'Pacôme Hégésippe Adélard Ladislas')
        session.add(contact1)
        session.flush()
        assert contact1.slug == u'pacome-hegesippe-adelard-ladislas'

        # test when name is None
        contact2 = DummyContact()
        session.add(contact2)
        session.flush()
        expected = u'dummycontact-{}'.format(contact2.id)
        assert contact2.slug == expected

        # test numbering if slug already exists:
        contact3 = DummyContact(name=u'Pacôme Hégésippe Adélard Ladislas')
        session.add(contact3)
        session.flush()
        assert contact3.slug == u'pacome-hegesippe-adelard-ladislas-1'

    def test_polymorphic_update_timestamp(self):
        session = self.get_session()
        contact = DummyContact(name=u'Pacôme Hégésippe Adélard Ladislas')
        session.add(contact)
        session.flush()

        updated_at = contact.updated_at
        assert updated_at
        contact.email = u'p@example.com'
        session.flush()
        assert contact.updated_at > updated_at

    def test_meta(self):
        session = self.get_session()
        e = DummyContact(name=u'test')
        e.meta['key'] = u'value'
        e.meta['number'] = 42
        session.add(e)
        session.flush()
        e_id = e.id
        session.expunge(e)
        del e
        e = session.query(DummyContact).get(e_id)
        assert e.meta['key'] == u'value'
        assert e.meta['number'] == 42

    def test_entity_type(self):

        class MyType(Entity):
            pass

        expected = __name__ + '.MyType'
        self.assertEquals(MyType.entity_type, expected)
        self.assertEquals(MyType._object_type(), expected)

        class Fixed(Entity):
            entity_type = 'some.fixed.module.fixed_type'

        assert Fixed.entity_type == 'some.fixed.module.fixed_type'
        assert Fixed._object_type() == 'some.fixed.module.fixed_type'

        class OtherBase(Entity):
            ENTITY_TYPE_BASE = 'some.module'

        assert OtherBase.entity_type == 'some.module.OtherBase'
        assert OtherBase._object_type() == 'some.module.OtherBase'

        # test when ENTITY_TYPE_BASE is in ancestors
        class Base(object):
            ENTITY_TYPE_BASE = 'from.ancestor'

        class InheritedBase(Base, Entity):
            pass

        assert InheritedBase.entity_type == 'from.ancestor.InheritedBase'
        assert InheritedBase._object_type() == 'from.ancestor.InheritedBase'


class PermissionsTestCase(AbilianTestCase):

    def test_default_permissions(self):

        class MyRestrictedType(Entity):
            __default_permissions__ = {
                security.READ: {security.Anonymous},
                security.WRITE: {security.Owner},
                security.CREATE: {security.Writer},
                security.DELETE: {security.Owner},
            }

        assert isinstance(MyRestrictedType.__default_permissions__, frozenset)
        expected = frozenset(((security.READ, frozenset((security.Anonymous,))),
                              (security.WRITE, frozenset((security.Owner,))),
                              (security.CREATE, frozenset((security.Writer,))),
                              (security.DELETE, frozenset((security.Owner,))),))
        assert MyRestrictedType.__default_permissions__ == expected

        self.app.db.create_all()  # create missing 'mytype' table

        obj = MyRestrictedType(name=u'test object')
        self.session.add(obj)
        PA = security.PermissionAssignment
        query = self.session.query(PA.role) \
            .filter(PA.object == obj)

        assert query.filter(PA.permission == security.READ).all() \
               == [(security.Anonymous,)]

        assert query.filter(PA.permission == security.WRITE).all() \
               == [(security.Owner,)]

        assert query.filter(PA.permission == security.DELETE).all() \
               == [(security.Owner,)]

        # special case:
        assert query.filter(PA.permission == security.CREATE).all() \
               == []

        svc = self.app.services['security']
        permissions = svc.get_permissions_assignments(obj)
        assert permissions == {
            security.READ: {security.Anonymous},
            security.WRITE: {security.Owner},
            security.DELETE: {security.Owner},
        }


def test_info():
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

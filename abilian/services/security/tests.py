# -*- coding: utf-8 -*-
from __future__ import absolute_import

import unittest

from flask.ext.login import AnonymousUserMixin

from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.core.models.subjects import User, Group
from abilian.testing import BaseTestCase

from . import (security, RoleAssignment, InheritSecurity, Role,
               Admin)


TEST_EMAIL = u"joe@example.com"
TEST_PASSWORD = "tototiti"


def init_user():
  user = User(first_name=u"Joe", last_name=u"User", email=TEST_EMAIL,
              password=TEST_PASSWORD)
  db.session.add(user)
  db.session.flush()


class RoleTestCase(unittest.TestCase):

  def test_singleton(self):
    admin = Role('admin')
    other_admin = Role('admin')
    self.assertIs(admin, other_admin)
    self.assertEquals(id(admin), id(other_admin))

  def test_equality(self):
    admin = Role('admin')
    self.assertEquals(admin, 'admin')
    self.assertEquals(admin, u'admin')


class IntegrationTestCase(BaseTestCase):

  def setUp(self):
    BaseTestCase.setUp(self)
    # init_user()
    security.init_app(self.app)
    security.start()

  def tearDown(self):
    security.stop()
    security.clear()
    BaseTestCase.tearDown(self)


class DummyModel(Entity):
  pass


class FolderishModel(Entity, InheritSecurity):
  pass


class SecurityTestCase(IntegrationTestCase):
  def test_anonymous_user(self):
    # anonymous user is not an SQLAlchemy instance and must be handled
    # specifically to avoid tracebacks
    anon = AnonymousUserMixin()
    assert not security.has_role(anon, 'read')

  def test_root_user(self):
    """ Root user always has any role, any permission
    """
    root = User.query.get(0)
    assert security.has_role(root, Admin)
    assert security.has_permission(root, 'manage')

    obj = DummyModel()
    self.session.add(obj)
    self.session.flush()
    assert security.has_role(root, Admin, obj)
    assert security.has_permission(root, 'manage', obj)

  def test_grant_basic_roles(self):
    user = User(email=u"john@example.com", password="x")
    self.session.add(user)
    self.session.flush()

    security.grant_role(user, Admin)
    assert security.has_role(user, Admin)
    assert security.get_roles(user) == [Admin]
    assert security.get_roles(user) == ['admin']

    # clear roles cache for better coverage: has_permission uses
    # _fill_role_cache_batch(), get_roles uses _fill_role_cache()
    delattr(user, '__roles_cache__')
    assert security.has_permission(user, "read")
    assert security.has_permission(user, "write")
    assert security.has_permission(user, "manage")

    security.ungrant_role(user, "admin")
    assert not security.has_role(user, "admin")
    assert security.get_roles(user) == []

    assert not security.has_permission(user, "read")
    assert not security.has_permission(user, "write")
    assert not security.has_permission(user, "manage")

  def test_grant_basic_roles_on_groups(self):
    user = User(email=u"john@example.com", password="x")
    group = Group(name=u"Test Group")
    user.groups.append(group)
    self.session.add(user)
    self.session.flush()

    security.grant_role(group, "admin")
    assert security.has_role(group, "admin")

    # FIXME
    #assert security.get_roles(group) == ['admin']

    assert security.has_permission(user, "read")
    assert security.has_permission(user, "write")
    assert security.has_permission(user, "manage")

    security.ungrant_role(group, "admin")
    assert not security.has_role(group, "admin")
    #assert security.get_roles(group) == []

    assert not security.has_permission(user, "read")
    assert not security.has_permission(user, "write")
    assert not security.has_permission(user, "manage")

  def test_grant_roles_on_objects(self):
    user = User(email=u"john@example.com", password=u"x")
    obj = DummyModel()
    self.session.add_all([user, obj])
    self.session.flush()

    security.grant_role(user, "manager", obj)
    assert security.has_role(user, "manager", obj)
    assert security.get_roles(user, obj) == ['manager']

    assert security.has_permission(user, "read", obj)
    assert security.has_permission(user, "write", obj)
    assert security.has_permission(user, "manage", obj)

    security.ungrant_role(user, "manager", obj)
    assert not security.has_role(user, "manager", obj)
    assert security.get_roles(user, obj) == []

    assert not security.has_permission(user, "read", obj)
    assert not security.has_permission(user, "write", obj)
    assert not security.has_permission(user, "manage", obj)

  def test_grant_roles_unique(self):
    user = User(email=u"john@example.com", password="x")
    obj = DummyModel()
    self.session.add_all([user, obj])
    self.session.flush()

    assert RoleAssignment.query.count() == 0

    security.grant_role(user, "manager", obj)
    self.session.flush()
    assert RoleAssignment.query.count() == 1

    security.grant_role(user, "manager", obj)
    self.session.flush()
    assert RoleAssignment.query.count() == 1

    security.grant_role(user, "reader", obj)
    self.session.flush()
    assert RoleAssignment.query.count() == 2

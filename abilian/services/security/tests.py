# -*- coding: utf-8 -*-
from __future__ import absolute_import

import unittest

from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.core.models.subjects import User, Group
from abilian.testing import BaseTestCase

from . import (
  security, RoleAssignment, PermissionAssignment,
  InheritSecurity, SecurityAudit,
  Role, Permission, READ, WRITE, Reader, Writer, Owner, Creator,
  Admin, Anonymous, Authenticated)


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

  def test_ordering(self):
    roles = [Authenticated, Admin, Anonymous]
    roles.sort()
    assert roles == [Admin, Anonymous, Authenticated]

  def test_enumerate_assignables(self):
    assert Role.assignable_roles() == [Admin]


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
    anon = self.app.login_manager.anonymous_user()
    assert not security.has_role(anon, 'read')
    assert security.get_roles(anon) == [Anonymous]
    assert not security.has_permission(anon, 'read')

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
    assert security.get_principals(Admin) == [user]

    # clear roles cache for better coverage: has_permission uses
    # _fill_role_cache_batch(), get_roles uses _fill_role_cache()
    delattr(user, '__roles_cache__')
    assert security.has_permission(user, "read")
    assert security.has_permission(user, "write")
    assert security.has_permission(user, "manage")

    security.ungrant_role(user, "admin")
    assert not security.has_role(user, "admin")
    assert security.get_roles(user) == []
    assert security.get_principals(Admin) == []

    assert not security.has_permission(user, "read")
    assert not security.has_permission(user, "write")
    assert not security.has_permission(user, "manage")

  def test_grant_basic_roles_on_groups(self):
    user = User(email=u"john@example.com", password="x")
    group = Group(name=u"Test Group")
    user.groups.add(group)
    self.session.add(user)
    self.session.flush()

    security.grant_role(group, "admin")
    assert security.has_role(group, "admin")
    assert security.get_roles(group) == ['admin']
    assert security.get_principals(Admin) == [group]

    assert security.has_permission(user, "read")
    assert security.has_permission(user, "write")
    assert security.has_permission(user, "manage")

    security.ungrant_role(group, "admin")
    assert not security.has_role(group, "admin")
    assert security.get_roles(group) == []
    assert security.get_principals(Admin) == []

    assert not security.has_permission(user, "read")
    assert not security.has_permission(user, "write")
    assert not security.has_permission(user, "manage")

  def test_grant_roles_on_objects(self):
    user = User(email=u"john@example.com", password=u"x")
    group = Group(name=u"Test Group")
    user.groups.add(group)
    obj = DummyModel()
    self.session.add_all([user, obj])
    self.session.flush()

    security.grant_role(user, 'global_role')
    security.grant_role(user, "reader", obj)
    assert security.has_role(user, "reader", obj)
    assert security.get_roles(user, obj) == ['reader']
    assert security.get_principals(Reader) == []
    assert security.get_principals(Reader, object=obj) == [user]

    assert security.has_permission(user, "read", obj)
    assert not security.has_permission(user, "write", obj)
    assert not security.has_permission(user, "manage", obj)

    # test get_roles "global": object roles should not appear
    assert security.get_roles(user) == ['global_role']

    security.ungrant_role(user, "reader", obj)
    assert not security.has_role(user, "reader", obj)
    assert security.get_roles(user, obj) == []

    assert not security.has_permission(user, "read", obj)
    assert not security.has_permission(user, "write", obj)
    assert not security.has_permission(user, "manage", obj)

    # owner / creator roles
    assert security.get_principals(Owner, object=obj) == []
    assert security.get_principals(Creator, object=obj) == []
    old_owner = obj.owner
    old_creator = obj.creator
    obj.owner = user
    assert security.get_roles(user, obj) == [Owner]
    assert security.get_principals(Owner, object=obj) == [user]
    assert security.get_principals(Creator, object=obj) == []
    obj.owner = old_owner
    obj.creator = user
    assert security.get_roles(user, obj) == [Creator]
    assert security.get_principals(Owner, object=obj) == []
    assert security.get_principals(Creator, object=obj) == [user]
    obj.creator = old_creator

    # permissions through group membership
    security.grant_role(group, "manager", obj)
    assert security.has_role(group, "manager", obj)
    assert security.get_roles(group, obj) == ['manager']

    # group membership: user hasn't role set, but has permissions
    assert security.get_roles(user, obj) == []
    assert security.has_permission(user, "read", obj)
    assert security.has_permission(user, "write", obj)
    assert security.has_permission(user, "manage", obj)

    group.members.remove(user)
    self.session.flush()
    assert not security.has_role(user, "manager", obj)
    assert security.get_roles(user, obj) == []
    assert not security.has_permission(user, "read", obj)
    assert not security.has_permission(user, "write", obj)
    assert not security.has_permission(user, "manage", obj)

    security.ungrant_role(group, "manager", obj)
    assert not security.has_role(group, "manager", obj)
    assert security.get_roles(group, obj) == []

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

  def test_inherit(self):
    folder = FolderishModel()
    self.session.add(folder)
    self.session.flush()

    self.assertEquals(SecurityAudit.query.count(), 0)

    security.set_inherit_security(folder, False)
    self.session.flush()
    self.assertFalse(folder.inherit_security)
    self.assertEquals(SecurityAudit.query.count(), 1)

    security.set_inherit_security(folder, True)
    self.session.flush()
    self.assertTrue(folder.inherit_security)
    self.assertEquals(SecurityAudit.query.count(), 2)

  def test_has_permission_on_objects(self):
    user = User(email=u"john@example.com", password=u"x")
    group = Group(name=u"Test Group")
    user.groups.add(group)
    obj = DummyModel()
    self.session.add_all([user, obj])
    self.session.flush()

    # global role provides permissions on any object
    security.grant_role(user, Reader)
    assert security.has_permission(user, READ, obj=obj)
    assert not security.has_permission(user, WRITE, obj=obj)

    security.grant_role(user, Writer, obj=obj)
    assert security.has_permission(user, WRITE, obj=obj)

    # permission assignment
    security.ungrant_role(user, Reader)
    security.ungrant_role(user, Writer, object=obj)
    security.grant_role(user, Authenticated)
    assert not security.has_permission(user, READ, obj=obj)
    assert not security.has_permission(user, WRITE, obj=obj)

    pa = PermissionAssignment(role=Authenticated, permission=READ, object=obj)
    self.session.add(pa)
    self.session.flush()
    assert security.has_permission(user, READ, obj=obj)

    self.session.delete(pa)
    self.session.flush()
    assert not security.has_permission(user, READ, obj=obj)

    # test when object is *not* in session (newly created objects have id=None
    # for instance)
    obj = DummyModel()
    assert security.has_role(user, Reader, object=obj) is False

  def test_has_permission_custom_roles(self):
    user = User(email=u"john@example.com", password="x")
    self.session.add(user)
    self.session.flush()

    role = Role('custom_role')
    permission = Permission('custom permission')
    assert not security.has_permission(user, permission, roles=role)
    security.grant_role(user, role)
    assert not security.has_permission(user, permission)
    assert security.has_permission(user, permission, roles=role)

    # Permission always granted if Anonymous role
    assert security.has_permission(user, permission, roles=Anonymous)

    # test convert legacy permission & implicit mapping
    security.grant_role(user, 'reader')
    assert security.has_permission(user, 'read')
    assert not security.has_permission(user, 'write')
    assert not security.has_permission(user, 'manage')

    security.grant_role(user, 'writer')
    assert security.has_permission(user, 'read')
    assert security.has_permission(user, 'write')
    assert not security.has_permission(user, 'manage')

    security.grant_role(user, 'manager')
    assert security.has_permission(user, 'read')
    assert security.has_permission(user, 'write')
    assert security.has_permission(user, 'manage')

# -*- coding: utf-8 -*-
from __future__ import absolute_import

import unittest

from flask.ext.login import AnonymousUserMixin

from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.core.models.subjects import User, Group
from abilian.testing import BaseTestCase

from . import (security, RoleAssignment, InheritSecurity, Role,
               Anonymous, Authenticated, Admin)


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


# class FolderSecurityTestCase(IntegrationTestCase):
#   @skip
#   def test_security_inheritance(self):
#     """
#     user rights:
#
#     . (r,w)
#     └── l1_folder (r)
#         └── l2_folder ()
#     """
#     user = User(email=u"john@example.com", password="x")
#     repository = self.app.extensions['content_repository']
#     root = FolderishModel(name=u"")
#     l1_folder = root.create_subfolder(u'level1')
#     l2_folder = l1_folder.create_subfolder(u'level2')
#     self.session.add_all([user, root, l1_folder, l2_folder])
#     self.session.flush()
#     security.grant_role(user, "reader", root)
#     security.grant_role(user, "writer", root)
#     security.grant_role(user, "reader", l1_folder)
#     self.session.commit()
#
#     # inherit_security is True by default
#     assert root.inherit_security is True
#     assert l1_folder.inherit_security is True
#     assert l2_folder.inherit_security is True
#
#     # root rights are propagated: (r,w) on all
#     assert repository.has_permission(user, "read", root)
#     assert repository.has_permission(user, "write", root)
#     assert repository.has_permission(user, "read", l1_folder)
#     assert repository.has_permission(user, "write", l1_folder)
#     assert repository.has_permission(user, "read", l2_folder)
#     assert repository.has_permission(user, "write", l2_folder)
#
#     # remove inheritance on l1
#     l1_folder.inherit_security = False
#     self.session.add(l1_folder)
#     self.session.commit()
#
#     # /: (r,w), l1_folder: (r), l2_folder: (r)
#     assert repository.has_permission(user, "read", root)
#     assert repository.has_permission(user, "write", root)
#     assert repository.has_permission(user, "read", l1_folder)
#     assert not repository.has_permission(user, "write", l1_folder)
#     assert repository.has_permission(user, "read", l2_folder)
#     assert not repository.has_permission(user, "write", l2_folder)
#
#   def test_web_permisions(self):
#     d = dict(email=TEST_EMAIL, password=TEST_PASSWORD)
#     response = self.client.post("/login/", data=d)
#     self.assertEquals(response.status_code, 302)
#
#     response = self.get("/crm/")
#     self.assertEquals(response.status_code, 403)
#
#     response = self.get("/admin/")
#     self.assertEquals(response.status_code, 403)
#
#     # Try again after granting role "admin"
#     user = User.query.filter(User.email == TEST_EMAIL).one()
#     security.grant_role(user, "admin")
#
#     response = self.get("/admin/")
#     self.assertEquals(response.status_code, 200)
#

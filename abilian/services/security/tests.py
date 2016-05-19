# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import unittest

from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.core.models.subjects import Group, User
from abilian.testing import BaseTestCase

from . import (READ, WRITE, Admin, Anonymous, Authenticated, Creator,
               InheritSecurity, Owner, Permission, PermissionAssignment, Reader,
               Role, RoleAssignment, SecurityAudit, Writer, security)

TEST_EMAIL = u"joe@example.com"
TEST_PASSWORD = "tototiti"


def init_user():
    user = User(first_name=u"Joe",
                last_name=u"User",
                email=TEST_EMAIL,
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
        assert not security.has_role(anon, 'reader')
        assert security.has_role(anon, Anonymous)
        assert security.get_roles(anon) == [Anonymous]
        assert not security.has_permission(anon, 'read')

    def test_has_role_authenticated(self):
        anon = self.app.login_manager.anonymous_user()
        user = User(email=u"john@example.com", password="x")
        self.session.add(user)
        self.session.flush()
        assert not security.has_role(anon, Authenticated)
        assert security.has_role(user, Authenticated)

    def test_root_user(self):
        """ Root user always has any role, any permission
    """
        root = User.query.get(0)
        assert security.has_role(root, Admin)
        assert security.has_role(root, Anonymous)
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

        # everybody always has role Anonymous
        assert security.has_role(user, Anonymous)

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

        assert security.has_role(user, Admin)

        assert security.has_permission(user, "read")
        assert security.has_permission(user, "write")
        assert security.has_permission(user, "manage")

        security.ungrant_role(group, "admin")
        assert not security.has_role(group, "admin")
        assert security.get_roles(group) == []
        assert security.get_principals(Admin) == []

        assert not security.has_role(user, "admin")
        assert not security.has_permission(user, "read")
        assert not security.has_permission(user, "write")
        assert not security.has_permission(user, "manage")

    def test_grant_roles_on_objects(self):
        user = User(email=u"john@example.com", password=u"x")
        user2 = User(email=u"papa@example.com", password=u"p")
        group = Group(name=u"Test Group")
        user.groups.add(group)
        obj = DummyModel()
        self.session.add_all([user, user2, obj])
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

        # global role is valid on all object
        assert security.has_role(user, 'global_role', obj)

        security.ungrant_role(user, "reader", obj)
        assert not security.has_role(user, "reader", obj)
        assert security.get_roles(user, obj) == []
        assert security.has_role(user, 'global_role', obj)

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
        # if user2 has Admin role e gets the rights no matter Creator/Ownership
        security.grant_role(user2, Admin)
        assert security.has_role(user2, (Owner, Creator), obj)
        assert security.has_role(user, (Owner, Creator), obj)

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
        assert security.get_roles(user, obj, no_group_roles=True) == []
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

        # when called on unmapped instance
        new_obj = DummyModel()
        assert not security.has_permission(user, READ, new_obj)

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

    def test_add_list_delete_permissions(self):
        obj = DummyModel()
        assert security.get_permissions_assignments(obj) == {}
        self.session.add(obj)
        self.session.flush()

        security.add_permission(READ, Authenticated, obj)
        security.add_permission(READ, Owner, obj)
        security.add_permission(WRITE, Owner, obj)
        assert security.get_permissions_assignments(obj) == {
            READ: {Authenticated,
                   Owner,},
            WRITE: {Owner,},
        }

        security.delete_permission(READ, Authenticated, obj)
        assert security.get_permissions_assignments(obj) == {
            READ: {Owner,},
            WRITE: {Owner,},
        }
        assert security.get_permissions_assignments(obj, READ) == {
            READ: {Owner,},
        }

        # do it twice: it should not crash
        security.add_permission(READ, Owner, obj)
        security.delete_permission(READ, Authenticated, obj)

        # set/get/delete global permission
        security.add_permission(READ, Writer)
        assert security.get_permissions_assignments() == {READ: {Writer,},}

    def test_has_permission_on_objects(self):
        has_permission = security.has_permission
        user = User(email=u"john@example.com", password=u"x")
        group = Group(name=u"Test Group")
        user.groups.add(group)
        obj = DummyModel(creator=user, owner=user)
        self.session.add_all([user, obj])
        self.session.flush()

        # global role provides permissions on any object
        security.grant_role(user, Reader)
        assert has_permission(user, READ, obj=obj)
        assert not has_permission(user, WRITE, obj=obj)

        security.grant_role(user, Writer, obj=obj)
        assert has_permission(user, WRITE, obj=obj)

        # permission assignment
        security.ungrant_role(user, Reader)
        security.ungrant_role(user, Writer, object=obj)
        security.grant_role(user, Authenticated)
        assert not has_permission(user, READ, obj=obj)
        assert not has_permission(user, WRITE, obj=obj)

        pa = PermissionAssignment(role=Authenticated,
                                  permission=READ,
                                  object=obj)
        self.session.add(pa)
        self.session.flush()
        assert has_permission(user, READ, obj=obj)
        assert not has_permission(user, WRITE, obj=obj)

        self.session.delete(pa)
        self.session.flush()
        assert not has_permission(user, READ, obj=obj)

        # Owner / Creator
        for role in (Owner, Creator):
            pa = PermissionAssignment(role=Owner, permission=READ, object=obj)
            self.session.add(pa)
            self.session.flush()
            assert has_permission(user, READ, obj=obj)

            self.session.delete(pa)
            self.session.flush()
            assert not has_permission(user, READ, obj=obj)

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

    def test_query_entity_with_permission(self):
        get_filter = security.query_entity_with_permission
        user = User(email=u"john@example.com", password="x")
        self.session.add(user)

        obj_reader = DummyModel(name=u'reader')
        obj_writer = DummyModel(name=u'writer')
        obj_none = DummyModel(name=u'none')
        self.session.add_all([obj_reader, obj_writer, obj_none])

        self.session.add_all([PermissionAssignment(
            role=Reader, permission=READ,
            object=obj_reader), PermissionAssignment(role=Writer,
                                                     permission=WRITE,
                                                     object=obj_writer)])
        self.session.flush()

        # very unfiltered query returns all objects
        base_query = DummyModel.query
        assert set(base_query.all()) == {obj_reader, obj_writer, obj_none}

        # user has no roles: no objects returned at all
        assert base_query.filter(get_filter(READ, user=user)).all() == []
        assert base_query.filter(get_filter(WRITE, user=user)).all() == []

        # grant object specific roles
        security.grant_role(user, Reader, obj=obj_reader)
        security.grant_role(user, Writer, obj=obj_writer)
        self.session.flush()
        assert base_query.filter(get_filter(READ, user=user)).all() == [
            obj_reader
        ]
        assert base_query.filter(get_filter(WRITE, user=user)).all() == [
            obj_writer
        ]

        # Permission granted to anonymous: objects returned
        pa = PermissionAssignment(role=Anonymous,
                                  permission=WRITE,
                                  object=obj_reader)
        self.session.add(pa)

        assert base_query.filter(get_filter(READ, user=user)).all() == [
            obj_reader
        ]
        assert set(base_query.filter(get_filter(WRITE, user=user)).all()) \
          == set([obj_reader, obj_writer])
        self.session.delete(pa)
        assert base_query.filter(get_filter(WRITE, user=user)).all() == [
            obj_writer
        ]

        # grant global roles
        security.ungrant_role(user, Reader, object=obj_reader)
        security.ungrant_role(user, Writer, object=obj_writer)
        security.grant_role(user, Reader)
        security.grant_role(user, Writer)
        self.session.flush()

        assert base_query.filter(get_filter(READ, user=user)).all() == [
            obj_reader
        ]
        assert base_query.filter(get_filter(WRITE, user=user)).all() == [
            obj_writer
        ]

        # admin role has all permissions
        # 1: local role
        security.ungrant_role(user, Reader)
        security.ungrant_role(user, Writer)
        security.grant_role(user, Admin, obj=obj_reader)
        security.grant_role(user, Admin, obj=obj_none)
        self.session.flush()

        assert set(base_query.filter(get_filter(READ, user=user)).all()) == \
          {obj_reader, obj_none}
        assert set(base_query.filter(get_filter(WRITE, user=user)).all()) == \
          {obj_reader, obj_none}

        # 2: global role
        security.ungrant_role(user, Admin, object=obj_reader)
        security.ungrant_role(user, Admin, object=obj_none)
        security.grant_role(user, Admin)
        self.session.flush()
        assert set(base_query.filter(get_filter(READ, user=user)).all()) == \
            {obj_reader, obj_writer, obj_none}

        # implicit role: Owner, Creator
        security.ungrant_role(user, Admin)
        assert base_query.filter(get_filter(READ, user=user)).all() == []
        assert base_query.filter(get_filter(WRITE, user=user)).all() == []

        obj_reader.creator = user
        obj_writer.owner = user
        self.session.add_all([PermissionAssignment(
            role=Creator, permission=READ,
            object=obj_reader), PermissionAssignment(role=Owner,
                                                     permission=WRITE,
                                                     object=obj_writer)])
        self.session.flush()

        assert base_query.filter(get_filter(READ, user=user)).all() == [
            obj_reader
        ]
        assert base_query.filter(get_filter(WRITE, user=user)).all() == [
            obj_writer
        ]


class PermissionNoSAWarnTestCase(IntegrationTestCase):

    SQLALCHEMY_WARNINGS_AS_ERROR = False

    def test_add_delete_permissions_expunged_obj(self):
        # weird case. In CreateObject based views, usually Entity is instanciated
        # and might be added to session if it has a relationship with an existing
        # object. `init_object` must do `session.expunge(obj)`. But entities will
        # have initialized default permissions during `after_attach`.
        #
        # At save time, the object is added again to session. The bug is that
        # without precaution we may create permissions assignment twice, because
        # assignments created in the first place are not yet again in session.(new,
        # dirty, deleted) and cannot be found with a filtered query on
        # PermissionAssignment because they have not been flushed yet.
        #
        security.add_permission(READ, Owner, None)
        obj = DummyModel()
        # override default permission at instance level
        obj.__default_permissions__ = frozenset({(READ, frozenset({Owner})),})
        self.session.add(
            obj)  # core.entities._setup_default_permissions creates
        # permissions
        security.add_permission(READ, Owner, obj)  # no-op
        self.session.expunge(
            obj)  # obj and its permissions are removed from session

        self.session.add(obj)  # obj in session again. When
        # _setup_default_permissions is called durint
        # `after_flush`, previously created permission are not
        # yet back in session. The cascading rule will add
        # them just after (as of sqlalchemy 0.8, at least)

        # Finally the test! IntegrityError will be raised if we have done something
        # wrong (`Key (permission, role, object_id)=(..., ..., ...) already exists`)
        self.session.flush()

# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from datetime import datetime
from functools import total_ordering

from six import python_2_unicode_compatible, text_type
from sqlalchemy import sql
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import CheckConstraint, Column, ForeignKey, Index, \
    UniqueConstraint
from sqlalchemy.types import Boolean, DateTime, Enum, Integer, String, \
    UnicodeText

from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.core.models.subjects import Group, User
from abilian.core.singleton import UniqueName, UniqueNameType
from abilian.i18n import _l

__all__ = [
    'RoleAssignment',
    'PermissionAssignment',
    'SecurityAudit',
    'InheritSecurity',
    'Permission',
    'MANAGE',
    'READ',
    'WRITE',
    'CREATE',
    'DELETE',
    'Role',
    'Anonymous',
    'Authenticated',
    'Admin',
    'Manager',
    'Creator',
    'Owner',
    'Reader',
    'Writer',
    'RoleType',
]


@total_ordering
@python_2_unicode_compatible
class Permission(UniqueName):
    """Defines permission by name.

    Permission instances are unique by name.
    """
    __slots__ = ('label',)

    def __init__(self, name, label=None, assignable=True):
        UniqueName.__init__(self, name)
        if label is None:
            label = 'permission_' + text_type(name)
        if isinstance(label, text_type):
            label = _l(label)
        self.label = label

    def __str__(self):
        return text_type(self.name)

    def __lt__(self, other):
        return text_type(self.label).__lt__(text_type(other.label))


class PermissionType(UniqueNameType):
    """Store :class:`Permission`

    Usage:: RoleType()
    """
    Type = Permission


@total_ordering
@python_2_unicode_compatible
class Role(UniqueName):
    """Defines role by name. Roles instances are unique by name.

    :param assignable: true if this role is can be assigned through security service.
    Non-assignable roles are roles automatically given depending on context (ex:
    Anonymous/Authenticated).
    """
    __slots__ = ('label', 'assignable')

    def __init__(self, name, label=None, assignable=True):
        UniqueName.__init__(self, name)
        if label is None:
            label = 'role_' + text_type(name)
        if isinstance(label, text_type):
            label = _l(label)
        self.label = label
        self.assignable = assignable

    def __str__(self):
        return text_type(self.name)

    def __repr__(self):
        return "{}({}, {})".format(
            self.__class__.__name__,
            self.name,
            self.label,
        )

    def __lt__(self, other):
        return text_type(self.label).__lt__(text_type(other.label))

    @classmethod
    def assignable_roles(cls):
        return sorted(r for r in cls.__instances__.values() if r.assignable)


class RoleType(UniqueNameType):
    """Store :class:`Role`

    Usage:: RoleType()
    """
    Type = Role


#: marker for role assigned to 'Anonymous'
Anonymous = Role('anonymous', _l('role_anonymous'), assignable=False)

#: marker for role assigned to 'Authenticated'
Authenticated = Role(
    'authenticated',
    _l('role_authenticated'),
    assignable=False,
)

#: marker for `admin` role
Admin = Role('admin', _l('role_administrator'))

#: marker for `manager` role
Manager = Role('manager', _l('role_manager'), assignable=False)

Creator = Role('creator', assignable=False)
Owner = Role('owner', assignable=False)
Reader = Role('reader', assignable=False)
Writer = Role('writer', assignable=False)

# Permissions
READ = Permission('read')
WRITE = Permission('write')
MANAGE = Permission('manage')
CREATE = Permission('create')
DELETE = Permission('delete')


class RoleAssignment(db.Model):
    __tablename__ = "roleassignment"
    __table_args__ = (
        #
        CheckConstraint(
            "(CAST(anonymous AS INTEGER) = 1)"
            " OR "
            "((CAST(anonymous AS INTEGER) = 0)"
            " AND "
            " ((user_id IS NOT NULL AND group_id IS NULL)"
            "  OR "
            "  (user_id IS NULL AND group_id IS NOT NULL)))",
            name="roleassignment_ck_user_xor_group",
        ),
        #
        UniqueConstraint(
            'anonymous',
            'user_id',
            'group_id',
            'role',
            'object_id',
            name='assignment_mapped_role_unique',
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    role = Column(RoleType, index=True, nullable=False)
    anonymous = Column(
        'anonymous',
        Boolean,
        index=True,
        nullable=True,
        default=False,
        server_default=sql.false(),
    )
    user_id = Column(
        Integer,
        ForeignKey('user.id', ondelete='CASCADE'),
        index=True,
    )
    user = relationship(User, lazy='joined')
    group_id = Column(
        Integer,
        ForeignKey('group.id', ondelete='CASCADE'),
        index=True,
    )
    group = relationship(Group, lazy='joined')

    object_id = Column(
        Integer,
        ForeignKey(Entity.id, ondelete='CASCADE'),
        index=True,
    )
    object = relationship(Entity, lazy='select')


# On postgres the UniqueConstraint will not be effective because at least 1
# columns will have NULL value:
#
# From http://www.postgresql.org/docs/9.1/static/ddl-constraints.html
#
# "That means even in the presence of a unique constraint it is possible to
# store duplicate rows that contain a null value in at least one of the
# constrained columns."
#
# The solution is to build specific UNIQUE indexes, only for postgres
#
# noinspection PyComparisonWithNone
def _postgres_indexes():
    role = RoleAssignment.role
    user_id = RoleAssignment.user_id
    group_id = RoleAssignment.group_id
    obj = RoleAssignment.object_id
    anonymous = RoleAssignment.anonymous
    name = 'roleassignment_idx_{}_unique'.format
    engines = ('postgresql',)
    indexes = [
        Index(
            name('user_role'),
            user_id,
            role,
            unique=True,
            postgresql_where=((anonymous == False) & (group_id == None) &
                              (obj == None)),
        ),
        Index(
            name('group_role'),
            group_id,
            role,
            unique=True,
            postgresql_where=((anonymous == False) & (user_id == None) &
                              (obj == None)),
        ),
        Index(
            name('anonymous_role'),
            role,
            unique=True,
            postgresql_where=((anonymous == True) & (user_id == None) &
                              (group_id == None) & (obj == None)),
        ),
        Index(
            name('user_role_object'),
            user_id,
            role,
            obj,
            unique=True,
            postgresql_where=((anonymous == False) & (group_id == None) &
                              (obj != None)),
        ),
        Index(
            name('group_role_object'),
            group_id,
            role,
            obj,
            unique=True,
            postgresql_where=((anonymous == False) & (user_id == None) &
                              (obj != None)),
        ),
        Index(
            name('anonymous_role_object'),
            role,
            obj,
            unique=True,
            postgresql_where=((anonymous == True) & (user_id == None) &
                              (group_id == None) & (obj != None)),
        ),
    ]

    for idx in indexes:
        idx.info['engines'] = engines

    return indexes


_postgres_indexes()
del _postgres_indexes

PERMISSIONS_ATTR = '__permissions__'


class PermissionAssignment(db.Model):
    __tablename__ = 'permission_assignment'
    __table_args__ = (
        UniqueConstraint(
            'permission',
            'role',
            'object_id',
            name='assignments_unique',
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    permission = Column(PermissionType, index=True, nullable=False)
    role = Column(RoleType, index=True, nullable=False)
    object_id = Column(
        Integer,
        ForeignKey(Entity.id, ondelete='CASCADE'),
        index=True,
        nullable=True,
    )
    object = relationship(
        Entity,
        lazy='select',
        backref=backref(
            PERMISSIONS_ATTR,
            lazy='select',
            collection_class=set,
            cascade='all, delete-orphan',
            passive_deletes=True,
        ),
    )

    def __hash__(self):
        return hash((self.permission, self.role, self.object))

    def __eq__(self, other):
        if not isinstance(other, PermissionAssignment):
            return False

        return (
            self.permission == other.permission and
            self.role == other.role and self.object == other.object
        )

    def __neq__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        class_ = self.__class__
        classname = class_.__name__
        return ('<{cls} instance at 0x{id:x} '
                'permission={self.permission.name!r} '
                'role={self.role.name!r} object={self.object!r}>'
                ''.format(cls=classname, id=id(self), self=self))


def _postgres_indexes():
    # we need a unique index for when object_id is NULL; when it's not the
    # uniqueconstraint will just work.
    PA = PermissionAssignment
    name = 'ix_permission_assignment_{}_unique'.format
    engines = ('postgresql',)
    indexes = [
        Index(
            name('permission_role_global'),
            PA.permission,
            PA.role,
            unique=True,
            postgresql_where=(PA.object_id == None),
        ),
    ]

    for idx in indexes:
        idx.info['engines'] = engines

    return indexes


_postgres_indexes()
del _postgres_indexes


class SecurityAudit(db.Model):
    """Logs changes on security."""
    GRANT = 'GRANT'
    REVOKE = 'REVOKE'
    SET_INHERIT = 'SET_INHERIT'
    UNSET_INHERIT = 'UNSET_INHERIT'

    __tablename__ = "securityaudit"
    __table_args__ = (
        # constraint: either a inherit/no_inherit op on an object AND no user no group
        #             either a grant/revoke on a user XOR a group.
        CheckConstraint(
            "(op IN ('{grant}', '{revoke}') "
            " AND object_id IS NOT NULL"
            " AND user_id IS NULL "
            " AND group_id IS NULL "
            " AND (CAST(anonymous AS INTEGER) = 0)"
            ")"
            " OR "
            "(op NOT IN ('{grant}', '{revoke}')"
            " AND "
            " (((CAST(anonymous AS INTEGER) = 1) "
            "   AND user_id IS NULL AND group_id IS NULL)"
            "  OR "
            "  ((CAST(anonymous AS INTEGER) = 0) "
            "   AND ((user_id IS NOT NULL AND group_id IS NULL)"
            "  OR "
            "  (user_id IS NULL AND group_id IS NOT NULL)))"
            "))".format(grant=SET_INHERIT, revoke=UNSET_INHERIT),
            name="securityaudit_ck_user_xor_group",
        ),
    )

    id = Column(Integer, primary_key=True)
    happened_at = Column(DateTime, default=datetime.utcnow, index=True)
    op = Column(
        Enum(
            GRANT,
            REVOKE,
            SET_INHERIT,
            UNSET_INHERIT,
            name='securityaudit_enum_op',
        ),
    )
    role = Column(RoleType)

    manager_id = Column(Integer, ForeignKey(User.id))
    manager = relationship(User, foreign_keys=manager_id)
    anonymous = Column('anonymous', Boolean, nullable=True, default=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship("User", lazy='joined', foreign_keys=user_id)
    group_id = Column(Integer, ForeignKey('group.id'))
    group = relationship("Group", lazy='joined')

    _fk_object_id = Column(Integer, ForeignKey(Entity.id, ondelete="SET NULL"))
    object = relationship(Entity, lazy='select')

    object_id = Column(Integer)
    object_type = Column(String(1000))
    object_name = Column(UnicodeText)


class InheritSecurity(object):
    """Mixin for objects with a parent relation and security inheritance."""
    inherit_security = Column(
        Boolean,
        default=True,
        nullable=False,
        info={'auditable': False},
    )

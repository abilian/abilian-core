# coding=utf-8
"""
"""
from __future__ import absolute_import

from functools import total_ordering
from datetime import datetime

from sqlalchemy.orm import relationship
from sqlalchemy.schema import (
  Column, ForeignKey, Index, UniqueConstraint, CheckConstraint
  )
from sqlalchemy.types import (
  Integer, Enum, DateTime, String, Boolean, TypeDecorator, UnicodeText
  )

from abilian.i18n import _l
from abilian.core.singleton import UniqueName
from abilian.core.entities import Entity
from abilian.core.models.subjects import User, Group
from abilian.core.extensions import db


__all__ = ['RoleAssignment', 'SecurityAudit', 'InheritSecurity',
           'Role', 'Anonymous', 'Authenticated', 'Admin', 'Manager',
           'RoleType']


@total_ordering
class Role(UniqueName):
  """
  Defines role by name. Roles instances are unique by name.

  :param assignable: this role is can be assigned through security service.
  Non-assignable roles are roles automatically given depending on context (ex:
  Anonymous/Authenticated).
  """
  __slots__ = ('label', 'assignable')

  def __init__(self, name, label=None, assignable=True):
    UniqueName.__init__(self, name)
    if label is None:
      label = u'role_' + unicode(name)
    if isinstance(label, unicode):
      label = _l(label)
    self.label = label
    self.assignable = assignable

  def __unicode__(self):
    return unicode(self.label)

  def __lt__(self, other):
    return unicode(self).__lt__(unicode(other))

  @classmethod
  def assignable_roles(cls):
    roles = [r for r in cls.__instances__.values() if r.assignable]
    roles.sort()
    return roles


class RoleType(TypeDecorator):
  """
  Store :class:`Role`

  Usage::
    RoleType()
  """
  impl = String

  def __init__(self, *args, **kwargs):
    kwargs['length'] = 100
    TypeDecorator.__init__(self, *args, **kwargs)

  def process_bind_param(self, value, dialect):
    if value is not None:
      value = str(value)
    return value

  def process_result_value(self, value, dialect):
    if value is not None:
      value = Role(value)
    return value


#: marker for role assigned to 'Anonymous'
Anonymous = Role('anonymous', _l(u'role_anonymous'), assignable=False)

#: marker for role assigned to 'Authenticated'
Authenticated = Role('authenticated', _l(u'role_authenticated'), assignable=False)

#: marker for `admin` role
Admin = Role('admin', _l(u'role_administrator'))

#: marker for `manager` role
Manager = Role('manager', _l(u'role_manager'), assignable=False)


class RoleAssignment(db.Model):
  __tablename__ = "roleassignment"
  __table_args__ = (
    CheckConstraint(
      "(CAST(anonymous AS INTEGER) = 1)"
      " OR "
      "((CAST(anonymous AS INTEGER) = 0)"
      " AND "
      " ((user_id IS NOT NULL AND group_id IS NULL)"
      "  OR "
      "  (user_id IS NULL AND group_id IS NOT NULL)))",
      name="roleassignment_ck_user_xor_group"),
    UniqueConstraint('anonymous', 'user_id', 'group_id', 'role', 'object_id',
                     name='assignment_mapped_role_unique'),
    )

  id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
  role = Column(RoleType, index=True, nullable=False)
  anonymous = Column('anonymous', Boolean, nullable=True, default=False)
  user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'))
  user = relationship(User, lazy='joined')
  group_id = Column(Integer, ForeignKey('group.id', ondelete='CASCADE'))
  group = relationship(Group, lazy='joined')

  object_id = Column(Integer, ForeignKey(Entity.id, ondelete='CASCADE'))
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
        name('user_role'), user_id, role, unique=True,
        postgresql_where=((anonymous == False) & (group_id == None)
                          & (obj == None))
    ),
    Index(
        name('group_role'), group_id, role, unique=True,
        postgresql_where=((anonymous == False) & (user_id == None)
                          & (obj == None))
    ),
    Index(
        name('anonymous_role'), role, unique=True,
        postgresql_where=((anonymous == True)
                          & (user_id == None) & (group_id == None)
                          & (obj == None)),
    ),
    Index(
        name('user_role_object'), user_id, role, obj,
        unique=True,
        postgresql_where=((anonymous == False)
                          & (group_id == None) & (obj != None))
    ),
    Index(
        name('group_role_object'), group_id, role, obj,
        unique=True,
        postgresql_where=((anonymous == False)
                          & (user_id == None) & (obj != None))
    ),
    Index(
        name('anonymous_role_object'), role, obj, unique=True,
        postgresql_where=((anonymous == True)
                          & (user_id == None) & (group_id == None)
                          & (obj != None))
    ),
  ]

  for idx in indexes:
    idx.info['engines'] = engines

  return indexes

_postgres_indexes()
del _postgres_indexes


class SecurityAudit(db.Model):
  """Logs changes on security.
  """
  GRANT = u'GRANT'
  REVOKE = u'REVOKE'
  SET_INHERIT = u'SET_INHERIT'
  UNSET_INHERIT = u'UNSET_INHERIT'

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
        name="securityaudit_ck_user_xor_group"),
      )

  id = Column(Integer, primary_key=True)
  happened_at = Column(DateTime, default=datetime.utcnow, index=True)
  op = Column(Enum(GRANT, REVOKE, SET_INHERIT, UNSET_INHERIT,
                   name='securityaudit_enum_op'))
  role = Column(RoleType)

  manager_id = Column(Integer, ForeignKey(User.id))
  manager = relationship(User, foreign_keys=manager_id)
  anonymous = Column('anonymous', Boolean, nullable=True, default=False)
  user_id = Column(Integer, ForeignKey('user.id'))
  user = relationship("User", lazy='joined', foreign_keys=user_id)
  group_id = Column(Integer, ForeignKey('group.id'))
  group = relationship("Group", lazy='joined')

  _fk_object_id = Column(Integer,
                         ForeignKey(Entity.id, ondelete="SET NULL"))
  object = relationship(Entity, lazy='select')

  object_id = Column(Integer)
  object_type = Column(String(1000))
  object_name = Column(UnicodeText)


class InheritSecurity(object):
  """Mixin for objects with a parent relation and security inheritance.
  """
  inherit_security = Column(Boolean, default=True, nullable=False,
                            info={'auditable': False})

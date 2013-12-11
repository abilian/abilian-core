from datetime import datetime

from sqlalchemy.orm import relationship
from sqlalchemy.schema import (
  Column, ForeignKey, Index, UniqueConstraint, CheckConstraint
  )
from sqlalchemy.types import Integer, Text, Enum, DateTime, String, Boolean
from sqlalchemy.event import listen

from abilian.core.entities import Entity
from abilian.core.subjects import User, Group
from abilian.core.extensions import db


__all__ = ['RoleAssignment', 'SecurityAudit', 'InheritSecurity', 'Anonymous']

#: marker for role assigned to 'Anonymous'
Anonymous = type('AnonymousRole', (object,), {})()

class RoleAssignment(db.Model):
  __tablename__ = "roleassignment"
  __table_args__ =  (
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
  role = Column(Text, index=True, nullable=False)
  anonymous = Column('anonymous', Boolean, nullable=True, default=False)
  user_id = Column(Integer, ForeignKey('user.id'))
  user = relationship(User, lazy='joined')
  group_id = Column(Integer, ForeignKey('group.id'))
  group = relationship(Group, lazy='joined')

  object_id = Column(Integer, ForeignKey(Entity.id))
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
def _get_postgres_indexes():
  role = RoleAssignment.role
  user_id = RoleAssignment.user_id
  group_id = RoleAssignment.group_id
  obj = RoleAssignment.object_id
  anonymous = RoleAssignment.anonymous

  return [
    Index('roleassignment_idx_user_role_unique', user_id, role, unique=True,
          postgresql_where=(anonymous == False) & (group_id == None) & (obj == None)
          ),
    Index('roleassignment_idx_group_role_unique', group_id, role, unique=True,
          postgresql_where=(anonymous == False) & (user_id == None) & (obj == None)
        ),
    Index('roleassignment_idx_anonymous_role_unique', role, unique=True,
          postgresql_where=((anonymous == True)
                            & (user_id == None) & (group_id == None) & (obj == None))
          ),
    Index('roleassignment_idx_user_role_object_unique', user_id, role, obj,
          unique=True,
          postgresql_where=(anonymous == False) & (group_id == None) & (obj != None)
        ),
    Index('roleassignment_idx_group_role_object_unique', group_id, role, obj,
          unique=True,
          postgresql_where=(anonymous == False) & (user_id == None) & (obj != None)
        ),
    Index('roleassignment_idx_anonymous_role_unique', role, obj, unique=True,
          postgresql_where=((anonymous == True)
                            & (user_id == None) & (group_id == None) & (obj != None))
          ),
  ]

_pg_indexes = []


def _create_postgres_indexes(target, connection, **kw):
  if connection.engine.name != 'postgresql':
    return

  if not _pg_indexes:
    _pg_indexes.extend(_get_postgres_indexes())
    # no need to do call 'create' later (especially during tests): once
    # instanciated 'create' statement will be made automatically
    for idx in _pg_indexes:
      idx.create(connection)

listen(RoleAssignment.__table__, "after_create", _create_postgres_indexes)


def _drop_postgres_indexes(target, connection, **kw):
  if connection.engine.name != 'postgresql':
    return

  for idx in _pg_indexes:
    idx.drop(connection)

listen(RoleAssignment.__table__, "before_drop", _drop_postgres_indexes)


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
      "(op IN ('{grant}', '{revoke}') AND object_id IS NOT NULL"
      " AND user_id IS NULL AND group_id IS NULL AND (CAST(anonymous AS INTEGER) = 0))"
      " OR "
      "(op NOT IN ('{grant}', '{revoke}')"
      " AND "
      "(((CAST(anonymous AS INTEGER) = 1) AND user_id IS NULL AND group_id IS NULL)"
      " OR "
      " ((CAST(anonymous AS INTEGER) = 0) AND ((user_id IS NOT NULL AND group_id IS NULL)"
      "  OR "
      "  (user_id IS NULL AND group_id IS NOT NULL)))"
      "))".format(grant=SET_INHERIT, revoke=UNSET_INHERIT),
        name="securityaudit_ck_user_xor_group"),
    )

  id = Column(Integer, primary_key=True)
  happened_at = Column(DateTime, default=datetime.utcnow)
  op = Column(Enum(GRANT, REVOKE, SET_INHERIT, UNSET_INHERIT,
                   name='securityaudit_enum_op'))
  role = Column(String(length=100))

  manager_id = Column(Integer, ForeignKey(User.id))
  manager = relationship(User,
                         primaryjoin='SecurityAudit.manager_id == User.id')
  anonymous = Column('anonymous', Boolean, nullable=True, default=False)
  user_id = Column(Integer, ForeignKey('user.id'))
  user = relationship("User", lazy='joined',
                      primaryjoin='SecurityAudit.user_id == User.id')
  group_id = Column(Integer, ForeignKey('group.id'))
  group = relationship("Group", lazy='joined')

  object_id = Column(Integer, ForeignKey(Entity.id))
  object = relationship(Entity, lazy='select')


class InheritSecurity(object):
  """Mixin for objects with a parent relation and security inheritance.
  """
  inherit_security = Column(Boolean, default=True, nullable=False,
                            info={'auditable': False})

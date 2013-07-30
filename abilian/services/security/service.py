"""
Security service, manages roles and permissions.

Currently very simple (simplisitic?).

Roles and permissions are just strings, and are currently hardcoded.
"""
from itertools import chain

from flask import g
# Work around API change
try:
  from flask.ext.login import AnonymousUserMixin
except ImportError:
  from flask.ext.login import AnonymousUser as AnonymousUserMixin
from werkzeug.local import LocalProxy

from sqlalchemy.orm import subqueryload, object_session
from sqlalchemy import sql

from abilian.core.subjects import User, Group, Principal
from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.services.security.models import SecurityAudit, RoleAssignment, \
  InheritSecurity


def noproxy(obj):
  """ Unwrap obj from werkzeug.local.LocalProxy if needed. This is required if
  one want to test `isinstance(obj, SomeClass)`.
  """
  if isinstance(obj, LocalProxy):
    obj = obj._get_current_object()
  return obj


# Currently hardcoded.
PERMISSION = frozenset(['read', 'write', 'manage'])

__all__ = ['security', 'SecurityError', 'SecurityService',
           'InheritSecurity', 'SecurityAudit']


class SecurityError(Exception):
  pass


class SecurityService(object):

  use_cache = True

  def __init__(self, app=None):
    self.running = False
    if app:
      self.init_app(app)

  def init_app(self, app):
    self.app = app
    app.extensions['security'] = self

  def start(self):
    """Starts the service.
    """
    assert not self.running
    self.running = True

  def stop(self):
    """Stops the service. Every security check will be granted from now on.
    """
    assert self.running
    self.running = False

  def clear(self):
    pass

  def _current_user_manager(self):
    """Returns the current user, or SYSTEM user.
    """
    try:
      return g.user
    except:
      return User.query.get(0)

  # security log
  def entries_for(self, obj, limit=20):
    assert isinstance(obj, Entity)
    object_str = "%s:%s" % (obj.__class__.__name__, obj.id)
    return SecurityAudit.query.filter(SecurityAudit.object == object_str)\
      .order_by(SecurityAudit.happened_at.desc())\
      .limit(limit)

  # inheritance
  def set_inherit_security(self, obj, inherit_security):
    """
    """
    assert isinstance(obj, InheritSecurity)
    assert isinstance(obj, Entity)
    object_str = "%s:%s" % (obj.__class__.__name__, obj.id)

    obj.inherit_security = inherit_security
    db.session.add(obj)

    manager = self._current_user_manager()
    op = (SecurityAudit.SET_INHERIT if inherit_security
          else SecurityAudit.UNSET_INHERIT)
    audit = SecurityAudit(manager=manager, op=op, object=object_str)
    db.session.add(audit)

  #
  # Roles-related API.
  #
  def get_roles(self, user, object=None):
    """
    Gets all the roles attached to given `user`, on a given `object`.
    """
    assert user

    q = RoleAssignment.query
    q = q.filter(RoleAssignment.user_id == user.id)
    if object:
      assert isinstance(object, Entity)
      object_str = "%s:%s" % (object.__class__.__name__, object.id)
      q = q.filter(RoleAssignment.object == object_str)
    ra_list = q.all()
    return [ra.role for ra in ra_list]

  def get_principals(self, role, users=True, groups=True,
                     object=None):
    """ Return all users which are assigned given role
    """
    assert isinstance(role, basestring)
    role = role.strip()
    assert role
    assert (users or groups)
    q = RoleAssignment.query.filter_by(role=role)

    if not users:
      q = q.filter(RoleAssignment.user == None)
    elif not groups:
      q = q.filter(RoleAssignment.group == None)

    if object:
      assert isinstance(object, Entity)
      object_str = "%s:%s" % (object.__class__.__name__, object.id)
      q = q.filter(RoleAssignment.object == object_str)

    return [(ra.user or ra.group) for ra in q.all()]

  def _all_roles(self, principal):
    q = db.session.query(RoleAssignment.object, RoleAssignment.role)

    if isinstance(principal, User):
      filter_cond = (RoleAssignment.user == principal)
      if len(principal.groups) > 0:
         filter_cond |= (RoleAssignment.group in principal.groups)
      q = q.filter(filter_cond)
    else:
      q = q.filter(RoleAssignment.group == principal)

    results = q.all()
    all_roles = {}
    for object_key, role in results:
      all_roles.setdefault(object_key, set()).add(str(role))

    return all_roles

  def _role_cache(self, principal):
    if not self._has_role_cache(principal):
      #FIXME: should call _fill_role_cache?
      principal.__roles_cache__ = {}

    return principal.__roles_cache__

  def _has_role_cache(self, principal):
    return hasattr(principal, "__roles_cache__")

  def _set_role_cache(self, principal, cache):
    principal.__roles_cache__ = cache

  def _fill_role_cache(self, principal, overwrite=False):
    """ Fill role cache for `principal` (User or Group), in order to avoid too
    many queries when checking role access with 'has_role'

    Return role_cache of `principal`
    """
    if not self.use_cache:
      return None

    if not self._has_role_cache(principal) or overwrite:
      self._set_role_cache(principal, self._all_roles(principal))
    return self._role_cache(principal)

  def _fill_role_cache_batch(self, principals, overwrite=False):
    """ Fill role cache for `principals` (Users and/or Groups), in order to
    avoid too many queries when checking role access with 'has_role'
    """
    if not self.use_cache:
      return

    q = RoleAssignment.query
    users = set((u for u in principals if isinstance(u, User)))
    groups = set((g for g in principals if isinstance(g, Group)))
    groups |= set((g for u in users
                     for g in u.groups))

    if not overwrite:
      users = set((u for u in users if not self._has_role_cache(u)))
      groups = set((g for g in groups if not self._has_role_cache(g)))

    if not (users or groups):
      return

    # ensure principals processed here will have role cache. Thus users or
    # groups without any role will have an empty role cache, to avoid unneeded
    # individual DB query when calling self._fill_role_cache(p).
    map(lambda p: self._set_role_cache(p, {}), (p for p in chain(users, groups)))

    filter_cond = []
    if users:
      filter_cond.append(RoleAssignment.user_id.in_((u.id for u in users)))
    if groups:
      filter_cond.append(RoleAssignment.group_id.in_((g.id for g in groups)))

    q = q.filter(sql.or_(*filter_cond))
    ra_users = {}
    ra_groups = {}
    for ra in  q.all():
      if ra.user:
        all_roles = ra_users.setdefault(ra.user, {})
      else:
        all_roles = ra_groups.setdefault(ra.group, {})

      all_roles.setdefault(ra.object, set()).add(str(ra.role))

    for group, all_roles in ra_groups.iteritems():
      self._set_role_cache(group, all_roles)

    for user, all_roles in ra_users.iteritems():
      for g in user.groups:
        group_roles = self._fill_role_cache(g)
        for object_key, roles in group_roles.iteritems():
          obj_roles = all_roles.setdefault(object_key, set())
          obj_roles |= roles

      self._set_role_cache(user, all_roles)

  def has_role(self, user_or_group, role, object=None):
    """
    True if `user_or_group` has `role` (either globally, if `object` is None, or on
    the specific `object`).

    `role` can be a list or tuple of strings

    `object` can be an Entity, a string, or `None`.

    Note: we're using a cache for efficiency here. TODO: check that we're not
    over-caching.

    Note2: caching could also be moved upfront to when the user is loaded.
    """
    if not user_or_group:
      return False

    user_or_group = noproxy(user_or_group)
    if not self.running:
      return True

    if hasattr(user_or_group, 'is_anonymous') and user_or_group.is_anonymous():
      return False

    # admin & manager always have role
    if isinstance(role, basestring):
      role = (role,)
    valid_roles = frozenset(('admin', 'manager') + tuple(role))

    if object:
      assert isinstance(object, Entity)
      object_str = "%s:%s" % (object.__class__.__name__, object.id)
    else:
      object_str = None

    if self.use_cache:
      cache = self._fill_role_cache(user_or_group)

      if 'admin' in cache.get(None, ()):
        # user is a global admin
        return True

      if object_str in cache:
        roles = cache[object_str]
        return len(valid_roles & roles) > 0
      return False

    all_roles = self._all_roles(user_or_group)

    if 'admin' in all_roles.get(None, ()):
      # user is a global admin
      return True

    roles = all_roles.get(object_str, set())
    return len(valid_roles & roles) > 0

  def grant_role(self, user_or_group, role, object=None):
    """
    Grants `role` to `user` (either globally, if `object` is None, or on
    the specific `object`).
    """
    assert user_or_group
    user_or_group = noproxy(user_or_group)
    manager = self._current_user_manager()

    if object:
      assert isinstance(object, Entity)
      object_str = "%s:%s" % (object.__class__.__name__, object.id)
    else:
      object_str = None

    args = dict(role=role, object=object_str)

    if isinstance(user_or_group, User):
      args['user'] = user_or_group
    else:
      args['group'] = user_or_group

    if len(RoleAssignment.query.filter_by(**args).limit(1).all()) > 0:
      # role already granted, nothing to do
      return

    ra = RoleAssignment(**args)
    session = object_session(object) if object is not None else db.session
    session.add(ra)
    audit = SecurityAudit(manager=manager, op=SecurityAudit.GRANT, **args)
    session.add(audit)
    session.flush()

    if hasattr(user_or_group, "__roles_cache__"):
      del user_or_group.__roles_cache__

  def ungrant_role(self, user_or_group, role, object=None):
    """
    Ungrants `role` to `user` (either globally, if `object` is None, or on
    the specific `object`).
    """
    assert user_or_group
    user_or_group = noproxy(user_or_group)
    session = object_session(object) if object is not None else db.session
    manager = self._current_user_manager()

    args = dict(role=role)
    object_str = None
    q = session.query(RoleAssignment)
    q = q.filter(RoleAssignment.role == role)
    if isinstance(user_or_group, User):
      args['user'] = user_or_group
      q = q.filter(RoleAssignment.user_id == user_or_group.id)
    else:
      args['group'] = user_or_group
      q = q.filter(RoleAssignment.group_id == user_or_group.id)

    if object:
      assert isinstance(object, Entity)
      object_str = "%s:%s" % (object.__class__.__name__, object.id)
      q = q.filter(RoleAssignment.object == object_str)

    ra = q.one()
    session.delete(ra)
    args['object'] = object_str
    audit = SecurityAudit(manager=manager, op=SecurityAudit.REVOKE, **args)
    session.add(audit)
    session.flush()

    if hasattr(user_or_group, "__roles_cache__"):
      del user_or_group.__roles_cache__

  def get_role_assignements(self, object):
    q = RoleAssignment.query
    object_str = "%s:%s" % (object.__class__.__name__, object.id)
    q = q.filter(RoleAssignment.object == object_str)\
         .options(subqueryload('user.groups'))

    role_assignments = q.all()

    results = []
    for ra in role_assignments:
      if ra.user_id:
        results.append((ra.user, ra.role))
      else:
        results.append((ra.group, ra.role))
    return results

  #
  # Permission API, currently hardcoded
  #
  def has_permission(self, user, permission, obj=None, inherit=False):
    """ @param `inherit`: check with permission inheritance. By default, check
    only local roles.
    """
    assert permission in PERMISSION
    user = noproxy(user)

    roles = ['manager', 'admin'] # have 'manage' permission

    if permission in ('read', 'write'):
      roles.append('writer')

    if permission == 'read':
      roles.append('reader')

    checked_objs = [obj]

    if inherit and obj is not None:
      while (obj.inherit_security and obj.parent is not None):
        obj = obj.parent
        checked_objs.append(obj)

    principals = [user] + user.groups
    self._fill_role_cache_batch(principals)

    return any((self.has_role(principal, roles, item)
                for principal in principals
                for item in checked_objs))

  def filter_with_permission(self, user, permission, obj_list, inherit=False):
    user = noproxy(user)
    return [ obj for obj in obj_list
             if self.has_permission(user, permission, obj, inherit) ]


# Ugly monkey patch because everything needs to move to Abilian-Core
def has_role(self, role):
  return security.has_role(self, role)

Principal.has_role = has_role
AnonymousUserMixin.has_role = has_role


# Instanciate the service
security = SecurityService()

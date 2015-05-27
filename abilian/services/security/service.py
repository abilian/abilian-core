"""
Security service, manages roles and permissions.

Currently very simple (simplisitic?).

Roles and permissions are just strings, and are currently hardcoded.
"""
from functools import wraps
from itertools import chain

from flask import g, current_app
from sqlalchemy.orm import subqueryload, object_session
from sqlalchemy import sql

from abilian.core.models.subjects import User, Group
from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.core.util import noproxy
from abilian.services import Service, ServiceState
from abilian.services.security.models import (
  SecurityAudit, RoleAssignment, Anonymous, Admin, Manager,
  Owner, Creator,
  InheritSecurity, Role, Permission, READ, WRITE
)


PERMISSION = frozenset(['read', 'write', 'manage'])

__all__ = ['security', 'SecurityError', 'SecurityService',
           'InheritSecurity', 'SecurityAudit']


class SecurityError(Exception):
  pass


class SecurityServiceState(ServiceState):
  """ """
  use_cache = True
  #: True if security has changed
  needs_db_flush = False


def require_flush(fun):
  """ Decorator for methods that need to query security. It ensures all security
  related operations are flushed to DB, but avoids unneeded flushes.
  """
  @wraps(fun)
  def ensure_flushed(service, *args, **kwargs):
    if service.app_state.needs_db_flush:
      session = current_app.db.session()
      if (not session._flushing
          and any(isinstance(m, (RoleAssignment, SecurityAudit))
                  for models in (session.new, session.dirty, session.deleted)
                  for m in models)):
        session.flush()
      service.app_state.needs_db_flush = False

    return fun(service, *args, **kwargs)

  return ensure_flushed


# noinspection PyComparisonWithNone
class SecurityService(Service):
  """ """
  name = 'security'
  AppStateClass = SecurityServiceState

  def init_app(self, app):
    Service.init_app(self, app)
    state = app.extensions[self.name]
    state.use_cache = True

  def _needs_flush(self):
    """ Mark next security queries needs DB flush to have up to date information
    """
    self.app_state.needs_db_flush = True

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
  @require_flush
  def entries_for(self, obj, limit=20):
    assert isinstance(obj, Entity)
    return SecurityAudit.query.filter(SecurityAudit.object == obj)\
      .order_by(SecurityAudit.happened_at.desc())\
      .limit(limit)

  # inheritance
  def set_inherit_security(self, obj, inherit_security):
    """
    """
    assert isinstance(obj, InheritSecurity)
    assert isinstance(obj, Entity)

    obj.inherit_security = inherit_security
    db.session.add(obj)

    manager = self._current_user_manager()
    op = (SecurityAudit.SET_INHERIT if inherit_security
          else SecurityAudit.UNSET_INHERIT)
    audit = SecurityAudit(manager=manager, op=op, object=obj,
                          object_id=obj.id,
                          object_type=obj.entity_type,
                          object_name=obj.name)
    db.session.add(audit)
    self._needs_flush()

  #
  # Roles-related API.
  #
  @require_flush
  def get_roles(self, principal, object=None):
    """
    Gets all the roles attached to given `user`, on a given `object`.
    """
    assert principal
    if hasattr(principal, 'is_anonymous') and principal.is_anonymous():
      return [Anonymous]

    q = db.session.query(RoleAssignment.role)
    filter_col = (RoleAssignment.user
                  if not isinstance(principal, Group)
                  else RoleAssignment.group)
    q = q.filter(filter_col == principal)

    if object is not None:
      assert isinstance(object, Entity)

    q = q.filter(RoleAssignment.object == object)
    roles = {i[0] for i in q.all()}

    if object is not None:
      for attr, role in (('creator', Creator), ('owner', Owner)):
        if getattr(object, attr) == principal:
          roles.add(role)
    return list(roles)

  @require_flush
  def get_principals(self, role, anonymous=True, users=True, groups=True,
                     object=None):
    """
    Return all users which are assigned given role
    """
    if not isinstance(role, Role):
      role = Role(role)
    assert role
    assert (users or groups)
    q = RoleAssignment.query.filter_by(role=role)

    if not anonymous:
      q = q.filter(RoleAssignment.anonymous == False)
    if not users:
      q = q.filter(RoleAssignment.user == None)
    elif not groups:
      q = q.filter(RoleAssignment.group == None)

    q = q.filter(RoleAssignment.object == object)
    principals = {(ra.user or ra.group) for ra in q.all()}

    if object is not None and role in (Creator, Owner):
      p = object.creator if role == Creator else object.owner
      if p:
        principals.add(p)

    return list(principals)

  @require_flush
  def _all_roles(self, principal):
    q = db.session.query(RoleAssignment.object_id, RoleAssignment.role)\
      .outerjoin(Entity)\
      .add_columns(Entity._entity_type)

    if isinstance(principal, User):
      filter_cond = (RoleAssignment.user == principal)
      if len(principal.groups) > 0:
         filter_cond |= (RoleAssignment.group in principal.groups)
      q = q.filter(filter_cond)
    else:
      q = q.filter(RoleAssignment.group == principal)

    results = q.all()
    all_roles = {}
    for object_id, role, object_type in results:
      if object_id is None:
        object_key = None
      else:
        object_key = u'{}:{}'.format(object_type, object_id)
      all_roles.setdefault(object_key, set()).add(role)

    return all_roles

  def _role_cache(self, principal):
    if not self._has_role_cache(principal):
      # FIXME: should call _fill_role_cache?
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
    if not self.app_state.use_cache:
      return None

    if not self._has_role_cache(principal) or overwrite:
      self._set_role_cache(principal, self._all_roles(principal))
    return self._role_cache(principal)

  @require_flush
  def _fill_role_cache_batch(self, principals, overwrite=False):
    """ Fill role cache for `principals` (Users and/or Groups), in order to
    avoid too many queries when checking role access with 'has_role'
    """
    if not self.app_state.use_cache:
      return

    q = db.session.query(RoleAssignment)
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
    for ra in q.all():
      if ra.user:
        all_roles = ra_users.setdefault(ra.user, {})
      else:
        all_roles = ra_groups.setdefault(ra.group, {})

      object_key = (
        u'{}:{:d}'.format(ra.object.entity_type, ra.object_id)
        if ra.object is not None
        else None
      )
      all_roles.setdefault(object_key, set()).add(ra.role)

    for group, all_roles in ra_groups.iteritems():
      self._set_role_cache(group, all_roles)

    for user, all_roles in ra_users.iteritems():
      for gr in user.groups:
        group_roles = self._fill_role_cache(gr)
        for object_key, roles in group_roles.iteritems():
          obj_roles = all_roles.setdefault(object_key, set())
          obj_roles |= roles

      self._set_role_cache(user, all_roles)

  def has_role(self, principal, role, object=None):
    """
    True if `principal` has `role` (either globally, if `object` is None, or on
    the specific `object`).

    :param:role:  can be a list or tuple of strings or a :class:`Role` instance

    `object` can be an :class:`Entity`, a string, or `None`.

    Note: we're using a cache for efficiency here. TODO: check that we're not
    over-caching.

    Note2: caching could also be moved upfront to when the user is loaded.
    """
    if not principal:
      return False

    principal = noproxy(principal)
    if not self.running:
      return True

    if (principal is Anonymous
        or (hasattr(principal, 'is_anonymous') and principal.is_anonymous())):
      return False

    # root always have any role
    if isinstance(principal, User) and principal.id == 0:
      return True

    # admin & manager always have role
    if isinstance(role, (Role, basestring)):
      role = (role,)
    valid_roles = frozenset((Admin, Manager) + tuple(role))

    if object:
      assert isinstance(object, Entity)
      object_key = u"{}:{}".format(object.object_type, unicode(object.id))
    else:
      object_key = None

    if self.app_state.use_cache:
      cache = self._fill_role_cache(principal)

      if Admin in cache.get(None, ()):
        # user is a global admin
        return True

      if object_key in cache:
        roles = cache[object_key]
        return len(valid_roles & roles) > 0
      return False

    all_roles = self._all_roles(principal)

    if Admin in all_roles.get(None, ()):
      # user is a global admin
      return True

    roles = all_roles.get(object_key, set())
    return len(valid_roles & roles) > 0

  def grant_role(self, principal, role, obj=None):
    """
    Grants `role` to `user` (either globally, if `obj` is None, or on
    the specific `obj`).
    """
    assert principal
    principal = noproxy(principal)
    manager = self._current_user_manager()
    session = object_session(obj) if obj is not None else db.session

    args = dict(role=role, object=obj,
                anonymous=False,
                user=None, group=None)

    if (principal is Anonymous
        or (hasattr(principal, 'is_anonymous') and principal.is_anonymous())):
      args['anonymous'] = True
    elif isinstance(principal, User):
      args['user'] = principal
    else:
      args['group'] = principal

    if len(RoleAssignment.query.filter_by(**args).limit(1).all()) > 0:
      # role already granted, nothing to do
      return

    # same as above but in current, not yet flushed objects in session. We
    # cannot call flush() in grant_role() since this method may be called a
    # great number of times in the same transaction, and sqlalchemy limits to
    # 100 flushes before triggering a warning
    for obj in (o for models in (session.new, session.dirty)
                for o in models if isinstance(o, RoleAssignment)):
      if all(getattr(obj, attr) == val for attr, val in args.items()):
        return

    ra = RoleAssignment(**args)
    session.add(ra)
    audit = SecurityAudit(manager=manager, op=SecurityAudit.GRANT, **args)
    if obj is not None:
      audit.object_id = obj.id
      audit.object_type = obj.entity_type
      object_name = u''
      for attr_name in ('name', 'path', '__path_before_delete'):
        if hasattr(obj, attr_name):
          object_name = getattr(obj, attr_name)
      audit.object_name = object_name

    session.add(audit)
    self._needs_flush()

    if hasattr(principal, "__roles_cache__"):
      del principal.__roles_cache__

  def ungrant_role(self, principal, role, object=None):
    """
    Ungrants `role` to `user` (either globally, if `object` is None, or on
    the specific `object`).
    """
    assert principal
    principal = noproxy(principal)
    session = object_session(object) if object is not None else db.session
    manager = self._current_user_manager()

    args = dict(role=role, object=object,
                anonymous=False, user=None, group=None)
    q = session.query(RoleAssignment)
    q = q.filter(RoleAssignment.role == role,
                 RoleAssignment.object == object)

    if (principal is Anonymous
        or (hasattr(principal, 'is_anonymous') and principal.is_anonymous())):
      args['anonymous'] = True
      q.filter(RoleAssignment.anonymous == False,
               RoleAssignment.user == None,
               RoleAssignment.group == None)

    elif isinstance(principal, User):
      args['user'] = principal
      q = q.filter(RoleAssignment.user == principal)
    else:
      args['group'] = principal
      q = q.filter(RoleAssignment.group == principal)

    ra = q.one()
    session.delete(ra)
    audit = SecurityAudit(manager=manager, op=SecurityAudit.REVOKE, **args)
    session.add(audit)
    self._needs_flush()

    if hasattr(principal, "__roles_cache__"):
      del principal.__roles_cache__

  @require_flush
  def get_role_assignements(self, object):
    session = object_session(object) if object is not None else db.session
    if not session:
      session = db.session()
    q = session.query(RoleAssignment)
    q = q.filter(RoleAssignment.object == object)\
         .options(subqueryload('user.groups'))

    role_assignments = q.all()

    results = []
    for ra in role_assignments:
      principal = None
      if ra.anonymous:
        principal = Anonymous
      elif ra.user:
        principal = ra.user
      else:
        principal = ra.group
      results.append((principal, ra.role))
    return results

  #
  # Permission API, currently hardcoded
  #
  def has_permission(self, user, permission, obj=None, inherit=False,
                     roles=None):
    """
    @param `obj`: target object to check permissions.
    @param `inherit`: check with permission inheritance. By default, check only
    local roles.
    @param `roles`: additional valid role or iterable of roles having
                    `permission`.
    """
    if not isinstance(permission, Permission):
      assert permission in PERMISSION
      permission = Permission(permission)
    user = noproxy(user)

    # root always have any permission
    if isinstance(user, User) and user.id == 0:
      return True

    valid_roles = {Manager, Admin}  # have all permissions

    if roles is not None:
      if isinstance(roles, (Role, bytes, unicode)):
        roles = (roles,)

      for r in roles:
        valid_roles.add(Role(r))

    if Anonymous in valid_roles:
      return True

    # implicit role-permission mapping
    if permission in (READ, WRITE,):
      valid_roles.add(Role('writer'))

    if permission == READ:
      valid_roles.add(Role('reader'))

    checked_objs = [None, obj] # first test global roles, then object local
                               # roles

    if inherit and obj is not None:
      while (obj.inherit_security and obj.parent is not None):
        obj = obj.parent
        checked_objs.append(obj)

    principals = [user] + list(user.groups)
    self._fill_role_cache_batch(principals)

    return any((self.has_role(principal, valid_roles, item)
                for principal in principals
                for item in checked_objs))

  def filter_with_permission(self, user, permission, obj_list, inherit=False):
    user = noproxy(user)
    return [ obj for obj in obj_list
             if self.has_permission(user, permission, obj, inherit) ]


# Instanciate the service
security = SecurityService()

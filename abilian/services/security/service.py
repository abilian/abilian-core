# coding=utf-8
"""
Security service, manages roles and permissions.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from functools import wraps
from itertools import chain

import sqlalchemy as sa
from flask import current_app, g
from flask_login import current_user
from future.utils import string_types
from sqlalchemy import sql
from sqlalchemy.orm import object_session, subqueryload

from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.core.models.subjects import Group, User
from abilian.core.util import noproxy
from abilian.services import Service, ServiceState
from abilian.services.security.models import Anonymous as AnonymousRole
from abilian.services.security.models import (
    CREATE, DELETE, MANAGE, PERMISSIONS_ATTR, READ, WRITE, Admin, Authenticated,
    Creator, InheritSecurity, Manager, Owner, Permission, PermissionAssignment,
    Reader, Role, RoleAssignment, SecurityAudit, Writer)

#: list of legacy supported permissions when not using :class:`Permission`
#: instance
PERMISSIONS = frozenset(['read', 'write', 'manage'])

__all__ = ['security', 'SecurityError', 'SecurityService', 'InheritSecurity',
           'SecurityAudit']

#: default security matrix
DEFAULT_PERMISSION_ROLE = dict()
prm = DEFAULT_PERMISSION_ROLE
prm[MANAGE] = frozenset((Admin, Manager,))
prm[WRITE] = frozenset((Admin, Manager, Writer,))
prm[CREATE] = frozenset((Admin, Manager, Writer,))
prm[DELETE] = frozenset((Admin, Manager, Writer,))
prm[READ] = frozenset((Admin, Manager, Writer, Reader,))
del prm


class SecurityError(Exception):
    pass


class SecurityServiceState(ServiceState):
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
            if (not session._flushing and any(
                    isinstance(m, (RoleAssignment, SecurityAudit))
                    for models in (session.new, session.dirty, session.deleted)
                    for m in models)):
                session.flush()
            service.app_state.needs_db_flush = False

        return fun(service, *args, **kwargs)

    return ensure_flushed


def query_pa_no_flush(session, permission, role, obj):
    """
    query for a :class:`PermissionAssignment` using `session` without any
    `flush()`.

    It works by looking in session `new`, `dirty` and `deleted`, and issuing a
    query with no autoflush.

    .. note::

        This function is used by `add_permission` and `delete_permission` to allow
        to add/remove the same assignment twice without issuing any flush. Since
        :class:`Entity` creates its initial permissions in during
        :sqlalchemy:`sqlalchemy.orm.events.SessionEvents.after_attach`, it might be
        problematic to issue a flush when entity is not yet ready to be flushed
        (missing required attributes for example).
    """
    to_visit = [session.deleted, session.dirty, session.new]
    with session.no_autoflush:
        # no_autoflush is required to visit PERMISSIONS_ATTR without emitting a
        # flush()
        if obj:
            to_visit.append(getattr(obj, PERMISSIONS_ATTR))

        permissions = (p for p in chain(*to_visit)
                       if isinstance(p, PermissionAssignment))

        for instance in permissions:
            if (instance.permission == permission and instance.role == role and
                    instance.object == obj):
                return instance

        # last chance: perform a filtered query. If obj is not None, sometimes
        # getattr(obj, PERMISSIONS_ATTR) has objects not present in session not in
        # this query (maybe in a parent session transaction `new`?). This happens
        # when
        if obj is not None and obj.id is None:
            obj = None

        return session.query(PermissionAssignment) \
            .filter(PermissionAssignment.permission == permission,
                    PermissionAssignment.role == role,
                    PermissionAssignment.object == obj) \
            .first()


# noinspection PyComparisonWithNone
class SecurityService(Service):
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

    def _current_user_manager(self, session=None):
        """
        Returns the current user, or SYSTEM user.
        """
        if session is None:
            session = db.session()

        try:
            user = g.user
        except:
            return session.query(User).get(0)

        if sa.orm.object_session(user) is not session:
            # this can happen when called from a celery task during development (with
            # CELERY_ALWAYS_EAGER=True): the task SA session is not app.db.session,
            # and we should not attach this object to the other session, because it
            # can make weird, hard-to-debug errors related to session.identity_map.
            return session.query(User).get(user.id)
        else:
            return user

    # security log
    @require_flush
    def entries_for(self, obj, limit=20):
        assert isinstance(obj, Entity)
        return SecurityAudit.query \
            .filter(SecurityAudit.object == obj) \
            .order_by(SecurityAudit.happened_at.desc()) \
            .limit(limit)

    # inheritance
    def set_inherit_security(self, obj, inherit_security):
        assert isinstance(obj, InheritSecurity)
        assert isinstance(obj, Entity)

        obj.inherit_security = inherit_security
        session = object_session(obj) if obj is not None else db.session
        session.add(obj)

        manager = self._current_user_manager(session=session)
        op = (SecurityAudit.SET_INHERIT if inherit_security else
              SecurityAudit.UNSET_INHERIT)
        audit = SecurityAudit(manager=manager,
                              op=op,
                              object=obj,
                              object_id=obj.id,
                              object_type=obj.entity_type,
                              object_name=obj.name)
        session.add(audit)
        self._needs_flush()

    #
    # Roles-related API.
    #
    @require_flush
    def get_roles(self, principal, object=None, no_group_roles=False):
        """
        Gets all the roles attached to given `principal`, on a given `object`.

        :param principal: a :class:`User` or :class:`Group`

        :param object: an :class:`Entity`

        :param no_group_roles: If `True`, return only direct roles, not roles
        acquired through group membership.
        """
        assert principal
        if hasattr(principal, 'is_anonymous') and principal.is_anonymous():
            return [AnonymousRole]

        q = db.session.query(RoleAssignment.role)
        if isinstance(principal, Group):
            filter_principal = RoleAssignment.group == principal
        else:
            filter_principal = RoleAssignment.user == principal
            if not no_group_roles:
                groups = [g.id for g in principal.groups]
                if groups:
                    filter_principal |= RoleAssignment.group_id.in_(groups)

        q = q.filter(filter_principal)

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
    def get_principals(self,
                       role,
                       anonymous=True,
                       users=True,
                       groups=True,
                       object=None,
                       as_list=True):
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

        if not as_list:
            return principals

        return list(principals)

    @require_flush
    def _all_roles(self, principal):
        q = db.session \
            .query(RoleAssignment.object_id, RoleAssignment.role) \
            .outerjoin(Entity) \
            .add_columns(Entity._entity_type)

        if isinstance(principal, User):
            filter_cond = (RoleAssignment.user == principal)
            if principal.groups:
                group_ids = (g.id for g in principal.groups)
                filter_cond |= (RoleAssignment.group_id.in_(group_ids))

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
        groups |= set((g for u in users for g in u.groups))

        if not overwrite:
            users = set((u for u in users if not self._has_role_cache(u)))
            groups = set((g for g in groups if not self._has_role_cache(g)))

        if not (users or groups):
            return

        # ensure principals processed here will have role cache. Thus users or
        # groups without any role will have an empty role cache, to avoid unneeded
        # individual DB query when calling self._fill_role_cache(p).
        map(lambda p: self._set_role_cache(p, {}),
            (p for p in chain(users, groups)))

        filter_cond = []
        if users:
            filter_cond.append(RoleAssignment.user_id.in_((u.id for u in users
                                                          )))
        if groups:
            filter_cond.append(RoleAssignment.group_id.in_((g.id for g in groups
                                                           )))

        q = q.filter(sql.or_(*filter_cond))
        ra_users = {}
        ra_groups = {}
        for ra in q.all():
            if ra.user:
                all_roles = ra_users.setdefault(ra.user, {})
            else:
                all_roles = ra_groups.setdefault(ra.group, {})

            object_key = (u'{}:{:d}'.format(ra.object.entity_type, ra.object_id)
                          if ra.object is not None else None)
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

    def _clear_role_cache(self, principal):
        if hasattr(principal, "__roles_cache__"):
            del principal.__roles_cache__

        if isinstance(principal, Group):
            for u in principal.members:
                if hasattr(u, '__roles_cache__'):
                    del u.__roles_cache__

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

        if isinstance(role, (Role, string_types)):
            role = (role,)

        # admin & manager always have role
        valid_roles = frozenset((Admin, Manager) + tuple(role))

        if AnonymousRole in valid_roles:
            # everybody has the role 'Anonymous'
            return True

        if (Authenticated in valid_roles and isinstance(principal, User) and
                not principal.is_anonymous()):
            return True

        if (principal is AnonymousRole or
            (hasattr(principal, 'is_anonymous') and principal.is_anonymous())):
            # anonymous user, and anonymous role isn't in valid_roles
            return False

        # root always have any role
        if isinstance(principal, User) and principal.id == 0:
            return True

        if object:
            assert isinstance(object, Entity)
            object_key = u"{}:{}".format(object.object_type, unicode(object.id))
            if Creator in role:
                if object.creator == principal:
                    return True
            if Owner in role:
                if object.owner == principal:
                    return True

        else:
            object_key = None

        all_roles = (self._fill_role_cache(principal) if
                     self.app_state.use_cache else self._all_roles(principal))
        roles = set()
        roles |= all_roles.get(None, set())
        roles |= all_roles.get(object_key, set())
        return len(valid_roles & roles) > 0

    def grant_role(self, principal, role, obj=None):
        """
        Grants `role` to `user` (either globally, if `obj` is None, or on
        the specific `obj`).
        """
        assert principal
        principal = noproxy(principal)
        session = object_session(obj) if obj is not None else db.session
        manager = self._current_user_manager(session=session)
        args = dict(role=role,
                    object=obj,
                    anonymous=False,
                    user=None,
                    group=None)

        if (principal is AnonymousRole or
            (hasattr(principal, 'is_anonymous') and principal.is_anonymous())):
            args['anonymous'] = True
        elif isinstance(principal, User):
            args['user'] = principal
        else:
            args['group'] = principal

        q = session.query(RoleAssignment)
        if q.filter_by(**args).limit(1).count():
            # role already granted, nothing to do
            return

        # same as above but in current, not yet flushed objects in session. We
        # cannot call flush() in grant_role() since this method may be called a
        # great number of times in the same transaction, and sqlalchemy limits to
        # 100 flushes before triggering a warning
        for ra in (o for models in (session.new, session.dirty) for o in models
                   if isinstance(o, RoleAssignment)):
            if all(getattr(ra, attr) == val for attr, val in args.items()):
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
        manager = self._current_user_manager(session=session)

        args = dict(role=role,
                    object=object,
                    anonymous=False,
                    user=None,
                    group=None)
        q = session.query(RoleAssignment)
        q = q.filter(RoleAssignment.role == role,
                     RoleAssignment.object == object)

        if (principal is AnonymousRole or
            (hasattr(principal, 'is_anonymous') and principal.is_anonymous())):
            args['anonymous'] = True
            q.filter(RoleAssignment.anonymous == False,
                     RoleAssignment.user == None, RoleAssignment.group == None)

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
        self._clear_role_cache(principal)

    @require_flush
    def get_role_assignements(self, object):
        session = object_session(object) if object is not None else db.session
        if not session:
            session = db.session()
        q = session.query(RoleAssignment)
        q = q.filter(RoleAssignment.object == object) \
            .options(subqueryload('user.groups'))

        role_assignments = q.all()

        results = []
        for ra in role_assignments:
            principal = None
            if ra.anonymous:
                principal = AnonymousRole
            elif ra.user:
                principal = ra.user
            else:
                principal = ra.group
            results.append((principal, ra.role))
        return results

    #
    # Permission API, currently hardcoded
    #
    def has_permission(self,
                       user,
                       permission,
                       obj=None,
                       inherit=False,
                       roles=None):
        """
        @param `obj`: target object to check permissions.
        @param `inherit`: check with permission inheritance. By default, check only
        local roles.
        @param `roles`: additional valid role or iterable of roles having
                        `permission`.
        """
        if not isinstance(permission, Permission):
            assert permission in PERMISSIONS
            permission = Permission(permission)
        user = noproxy(user)

        if not self.running:
            return True

        session = None
        if obj is not None:
            session = object_session(obj)

        if session is None:
            session = current_app.db.session()

        # root always have any permission
        if isinstance(user, User) and user.id == 0:
            return True

        # valid roles
        # 1: from database
        pa_filter = PermissionAssignment.object == None
        if obj is not None and obj.id is not None:
            pa_filter |= PermissionAssignment.object == obj

        pa_filter &= PermissionAssignment.permission == permission
        valid_roles = session \
            .query(PermissionAssignment.role) \
            .filter(pa_filter)
        valid_roles = {res[0] for res in valid_roles.yield_per(1000)}

        # complete with defaults
        valid_roles |= {Admin}  # always have all permissions
        valid_roles |= DEFAULT_PERMISSION_ROLE.get(permission, set())

        #FIXME: obj.__class__ could define default permisssion matrix too

        if roles is not None:
            if isinstance(roles, (Role, bytes, unicode)):
                roles = (roles,)

            for r in roles:
                valid_roles.add(Role(r))

        #FIXME: query permission_role: global and on object

        if AnonymousRole in valid_roles:
            return True

        if Authenticated in valid_roles and not user.is_anonymous():
            return True

        checked_objs = [None, obj]  # first test global roles, then object local
        # roles

        if inherit and obj is not None:
            while (obj.inherit_security and obj.parent is not None):
                obj = obj.parent
                checked_objs.append(obj)

        principals = [user] + list(user.groups)
        self._fill_role_cache_batch(principals)

        return any((self.has_role(principal, valid_roles, item)
                    for principal in principals for item in checked_objs))

    def query_entity_with_permission(self, permission, user=None, Model=Entity):
        """
        Filter a query on an :class:`Entity` or on of its subclasses.

        Usage::

            read_q = security.query_entity_with_permission(READ, Model=MyModel)
            MyModel.query.filter(read_q)

        It should always be placed before any `.join()` happens in the query; else
        sqlalchemy might join to the "wrong" entity table when joining to other
        :class:`Entity`.

        :param user: user to filter for. Default: `current_user`.

        :param permission: required :class:`Permission`

        :param Model: An :class:`Entity` based class. Useful when there is more than
        on Entity based object in query, or if an alias should be used.

        :returns: a `sqlalchemy.sql.exists()` expression.
        """
        assert isinstance(permission, Permission)
        assert issubclass(Model, Entity)
        RA = sa.orm.aliased(RoleAssignment)
        PA = sa.orm.aliased(PermissionAssignment)
        # id column from entity table. Model.id would refer to 'model' table.
        # this allows the DB to use indexes / foreign key constraints.
        id_column = sa.inspect(Model).primary_key[0]
        creator = Model.creator
        owner = Model.owner

        if not self.running:
            return sa.sql.exists([1])

        if user is None:
            user = current_user._get_current_object()

        # build role CTE
        principal_filter = (RA.anonymous == True)

        if not user.is_anonymous():
            principal_filter |= (RA.user == user)

        if user.groups:
            principal_filter |= RA.group_id.in_([g.id for g in user.groups])

        RA = sa.sql.select([RA], principal_filter).cte()
        permission_exists = \
            sa.sql.exists([1]) \
                .where(sa.sql.and_(PA.permission == permission,
                                   PA.object_id == id_column,
                                   (RA.c.role == PA.role) | (PA.role == AnonymousRole),
                                   (RA.c.object_id == PA.object_id) | (RA.c.object_id == None)))

        # is_admin: self-explanatory. It search for local or global admin
        # role, but PermissionAssignment is not involved, thus it can match on
        # entities that don't have *any permission assignment*, whereas previous
        # expressions cannot.
        is_admin = \
            sa.sql.exists([1]) \
                .where(sa.sql.and_(RA.c.role == Admin,
                                   (RA.c.object_id == id_column) | (RA.c.object_id == None),
                                   principal_filter))

        filter_expr = permission_exists | is_admin

        if user and not user.is_anonymous():
            is_owner_or_creator = sa.sql \
                .exists([1]) \
                .where(sa.sql.and_(PA.permission == permission,
                                   PA.object_id == id_column,
                                   sa.sql.or_((PA.role == Owner) & (owner == user),
                                              (PA.role == Creator) & (creator == user))))
            filter_expr |= is_owner_or_creator

        return filter_expr

    def get_permissions_assignments(self, obj=None, permission=None):
        """
        :param permission: return only roles having this permission

        :returns: an dict where keys are `permissions` and values `roles` iterable.
        """
        session = None
        if obj is not None:
            assert isinstance(obj, Entity)
            session = object_session(obj)

            if obj.id is None:
                obj = None

        if session is None:
            session = current_app.db.session()

        pa = session \
            .query(PermissionAssignment.permission,
                   PermissionAssignment.role) \
            .filter(PermissionAssignment.object == obj)

        if permission:
            pa = pa.filter(PermissionAssignment.permission == permission)

        results = {}
        for permission, role in pa.yield_per(1000):
            results.setdefault(permission, set()).add(role)

        return results

    def add_permission(self, permission, role, obj=None):
        session = None
        if obj is not None:
            session = object_session(obj)

        if session is None:
            session = current_app.db.session()

        pa = query_pa_no_flush(session, permission, role, obj)

        if not pa:
            pa = PermissionAssignment(permission=permission,
                                      role=role,
                                      object=obj)

        # do it in any case: it could have been found in session.deleted
        session.add(pa)

    def delete_permission(self, permission, role, obj=None):
        session = None
        if obj is not None:
            session = object_session(obj)

        if session is None:
            session = current_app.db.session()

        pa = query_pa_no_flush(session, permission, role, obj)

        if pa:
            session.delete(pa)
            if obj:
                # this seems to be required with sqlalchemy > 0.9
                session.expire(obj, [PERMISSIONS_ATTR])

    def filter_with_permission(self, user, permission, obj_list, inherit=False):
        user = noproxy(user)
        return [obj for obj in obj_list
                if self.has_permission(user, permission, obj, inherit)]

# Instanciate the service
security = SecurityService()

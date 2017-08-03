# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from abilian.core.entities import Entity
from abilian.services import security
from abilian.testing import BaseTestCase as AbilianTestCase


class PermissionsTestCase(AbilianTestCase):

    def test_default_permissions(self):

        class MyRestrictedType(Entity):
            __default_permissions__ = {
                security.READ: {security.Anonymous},
                security.WRITE: {security.Owner},
                security.CREATE: {security.Writer},
                security.DELETE: {security.Owner},
            }

        assert isinstance(MyRestrictedType.__default_permissions__, frozenset)

        expected = frozenset({
            (security.READ, frozenset({security.Anonymous})),
            #
            (security.WRITE, frozenset({security.Owner})),
            #
            (security.CREATE, frozenset({security.Writer})),
            #
            (security.DELETE, frozenset({security.Owner})),
        })
        assert MyRestrictedType.__default_permissions__ == expected

        self.app.db.create_all()  # create missing 'mytype' table

        obj = MyRestrictedType(name='test object')
        self.session.add(obj)
        PA = security.PermissionAssignment
        query = self.session.query(PA.role) \
            .filter(PA.object == obj)

        assert query.filter(PA.permission == security.READ).all() \
               == [(security.Anonymous,)]

        assert query.filter(PA.permission == security.WRITE).all() \
               == [(security.Owner,)]

        assert query.filter(PA.permission == security.DELETE).all() \
               == [(security.Owner,)]

        # special case:
        assert query.filter(PA.permission == security.CREATE).all() \
               == []

        security_svc = self.app.services['security']
        permissions = security_svc.get_permissions_assignments(obj)
        assert permissions == {
            security.READ: {security.Anonymous},
            security.WRITE: {security.Owner},
            security.DELETE: {security.Owner},
        }

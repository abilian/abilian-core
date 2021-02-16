""""""
from flask import Flask
from sqlalchemy.orm import Session

from abilian.core.entities import Entity
from abilian.core.sqlalchemy import SQLAlchemy
from abilian.services import security


def test_default_permissions(app: Flask, db: SQLAlchemy, session: Session) -> None:
    class MyRestrictedType(Entity):
        __default_permissions__ = {
            security.READ: {security.Anonymous},
            security.WRITE: {security.Owner},
            security.CREATE: {security.Writer},
            security.DELETE: {security.Owner},
        }

    assert isinstance(MyRestrictedType.__default_permissions__, frozenset)

    expected = frozenset(
        {
            (security.READ, frozenset({security.Anonymous})),
            #
            (security.WRITE, frozenset({security.Owner})),
            #
            (security.CREATE, frozenset({security.Writer})),
            #
            (security.DELETE, frozenset({security.Owner})),
        }
    )
    assert MyRestrictedType.__default_permissions__ == expected

    db.create_all()  # create missing 'mytype' table

    obj = MyRestrictedType(name="test object")
    session.add(obj)
    PA = security.PermissionAssignment
    query = session.query(PA.role).filter(PA.object == obj)

    assert query.filter(PA.permission == security.READ).all() == [(security.Anonymous,)]

    assert query.filter(PA.permission == security.WRITE).all() == [(security.Owner,)]

    assert query.filter(PA.permission == security.DELETE).all() == [(security.Owner,)]

    # special case:
    assert query.filter(PA.permission == security.CREATE).all() == []

    security_svc = app.services["security"]
    permissions = security_svc.get_permissions_assignments(obj)
    assert permissions == {
        security.READ: {security.Anonymous},
        security.WRITE: {security.Owner},
        security.DELETE: {security.Owner},
    }

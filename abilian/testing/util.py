# coding=utf-8
"""Elements to build test cases for an :class:`abilian.app.Application`"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask.testing import FlaskClient
from flask_login import login_user, logout_user
from sqlalchemy.exc import DatabaseError

from abilian.core.models.subjects import User
from abilian.services import get_service

__all__ = (
    "stop_all_services",
    "ensure_services_started",
    "cleanup_db",
    "client_login",
    "login",
)


def client_login(client, user):
    # type: (FlaskClient, User) -> LoginContext

    class LoginContext(object):

        def __enter__(self):
            with client.session_transaction() as session:
                session["user_id"] = user.id

        def __exit__(self, type, value, traceback):
            with client.session_transaction() as session:
                del session["user_id"]

    return LoginContext()


def login(user, remember=False, force=False):
    """Perform user login for `user`, so that code needing a logged-in user can
    work.

    This method can also be used as a context manager, so that logout is
    performed automatically::

        with login(user):
            assert ...

    .. seealso:: :meth:`logout`
    """
    # self._login_tests_sanity_check()
    success = login_user(user, remember=remember, force=force)
    if not success:
        raise ValueError("User is not active, cannot login; or use force=True")

    class LoginContext(object):

        def __enter__(self):
            return None

        def __exit__(self, type, value, traceback):
            logout_user()

    return LoginContext()


def cleanup_db(db):
    """Drop all the tables, in a way that doesn't raise integrity errors."""

    # Need to run this sequence twice for some reason
    _delete_tables(db)
    _delete_tables(db)
    # One more time, just in case ?
    db.drop_all()


def _delete_tables(db):
    for table in reversed(db.metadata.sorted_tables):
        try:
            db.session.execute(table.delete())
        except DatabaseError:
            pass


def ensure_services_started(services):
    for service_name in services:
        service = get_service(service_name)
        if not service.running:
            service.start()


def stop_all_services(app):
    for service in app.services.values():
        if service.running:
            service.stop()

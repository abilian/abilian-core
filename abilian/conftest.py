# coding=utf-8
"""
Configuration and injectable fixtures for Pytest.

Supposed to replace the too-complex current UnitTest-based testing
framework.

DI and functions over complex inheritance hierarchies FTW!
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask_login import login_user
from pytest import fixture, yield_fixture
from sqlalchemy.exc import DatabaseError

from abilian.app import create_app
from abilian.services import get_service


class TestConfig:
    TESTING = True
    SERVER_NAME = 'localhost'
    CELERY_ALWAYS_EAGER = True  # run tasks locally, no async
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
    # CSRF_ENABLED = False


@fixture
def config():
    return TestConfig


@fixture
def app(config):
    # We currently return a fresh app for each test.
    # Using session-scoped app doesn't currently work.
    # Note: the impact on speed is minimal.
    return create_app(config=config)


@yield_fixture
def db(app):
    """Return a fresh db for each test."""
    from abilian.core.extensions import db

    with app.app_context():
        stop_all_services(app)
        ensure_services_started(['repository', 'session_repository'])

        cleanup_db(db)
        db.create_all()
        yield db

        db.session.remove()
        cleanup_db(db)
        stop_all_services(app)


@fixture
def session(db):
    return db.session


@fixture
def client(app, db):
    """Return a Web client, used for testing, bound to a DB session."""
    return app.test_client()


#
# Cleanup utilities
#
def cleanup_db(db):
    """Drop all the tables, in a way that doesn't raise integrity errors."""

    # Need to run this sequence twice for some reason
    for i in range(0, 2):
        delete_tables(db)
    # One more time, just in case ?
    db.drop_all()


def delete_tables(db):
    for table in reversed(db.metadata.sorted_tables):
        try:
            db.session.execute(table.delete())
        except DatabaseError:
            pass


def stop_all_services(app):
    for service in app.services.values():
        if service.running:
            service.stop()


def ensure_services_started(services):
    for service_name in services:
        service = get_service(service_name)
        if not service.running:
            service.start()

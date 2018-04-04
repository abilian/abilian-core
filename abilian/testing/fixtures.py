# coding=utf-8
"""Configuration and injectable fixtures for Pytest.

Can be reused (and overriden) by adding::

   pytest_plugins = ['abilian.testing.fixtures']

to your `conftest.py`.

Supposed to replace the too-complex current UnitTest-based testing
framework. -> DI and functions over complex inheritance hierarchies FTW!
"""

from __future__ import absolute_import, division, print_function, \
    unicode_literals

from pytest import fixture

from abilian.app import create_app
from abilian.testing.util import cleanup_db, ensure_services_started, \
    stop_all_services


class TestConfig:
    TESTING = True
    SERVER_NAME = 'localhost'
    CELERY_ALWAYS_EAGER = True  # run tasks locally, no async
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
    MAIL_SENDER = 'tester@example.com'
    SITE_NAME = "Abilian Test"
    CSRF_ENABLED = True
    WTF_CSRF_ENABLED = True
    BABEL_ACCEPT_LANGUAGES = ['en', 'fr']


@fixture
def config():
    return TestConfig


@fixture
def app(config):
    # We currently return a fresh app for each test.
    # Using session-scoped app doesn't currently work.
    # Note: the impact on speed is minimal.
    return create_app(config=config)


@fixture
def app_context(app):
    with app.app_context() as ctx:
        yield ctx


@fixture
def test_request_context(app):
    with app.test_request_context() as ctx:
        yield ctx


@fixture
def req_ctx(app):
    with app.test_request_context() as req_ctx:
        yield req_ctx


@fixture
def db(app_context):
    """Return a fresh db for each test."""
    from abilian.core.extensions import db

    stop_all_services(app_context.app)
    ensure_services_started(['repository', 'session_repository'])

    cleanup_db(db)
    db.create_all()
    yield db

    db.session.remove()
    cleanup_db(db)
    stop_all_services(app_context.app)


@fixture
def session(db):
    return db.session


@fixture
def db_session(db):
    return db.session


@fixture
def client(app):
    """Return a Web client, used for testing."""
    return app.test_client()

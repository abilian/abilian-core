"""Configuration and injectable fixtures for Pytest.

Can be reused (and overriden) by adding::

   pytest_plugins = ['abilian.testing.fixtures']

to your `conftest.py`.

Replaced the too-complex UnitTest-based testing framework.
-> DI and functions over complex inheritance hierarchies FTW!
"""
from typing import Any, Iterator

from flask import Flask
from flask.ctx import AppContext, RequestContext
from flask.testing import FlaskClient
from pytest import fixture
from sqlalchemy.orm import Session

from abilian.app import create_app
from abilian.core.models.subjects import User
from abilian.core.sqlalchemy import SQLAlchemy
from abilian.testing.util import cleanup_db, ensure_services_started, \
    stop_all_services


class TestConfig:
    TESTING = True
    DEBUG = True
    SECRET_KEY = "SECRET"
    SERVER_NAME = "localhost.localdomain"
    CELERY_ALWAYS_EAGER = True  # run tasks locally, no async
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
    MAIL_SENDER = "tester@example.com"
    SITE_NAME = "Abilian Test"
    # WTF_CSRF_ENABLED = True
    WTF_CSRF_ENABLED = False
    BABEL_ACCEPT_LANGUAGES = ["en", "fr"]


@fixture
def config() -> type:
    return TestConfig


@fixture
def app(config: Any) -> Flask:
    # We currently return a fresh app for each test.
    # Using session-scoped app doesn't currently work.
    # Note: the impact on speed is minimal.
    return create_app(config=config)


@fixture
def app_context(app: Flask) -> Iterator[AppContext]:
    with app.app_context() as ctx:
        yield ctx


@fixture
def test_request_context(app: Flask) -> Iterator[RequestContext]:
    with app.test_request_context() as ctx:
        yield ctx


@fixture
def req_ctx(app: Flask) -> Iterator[RequestContext]:
    with app.test_request_context() as _req_ctx:
        yield _req_ctx


@fixture
def db(app_context: AppContext) -> Iterator[SQLAlchemy]:
    """Return a fresh db for each test."""
    from abilian.core.extensions import db

    stop_all_services(app_context.app)
    ensure_services_started(["repository", "session_repository"])

    cleanup_db(db)
    db.create_all()
    yield db

    db.session.remove()
    cleanup_db(db)
    stop_all_services(app_context.app)


@fixture
def session(db: SQLAlchemy) -> Session:
    return db.session


@fixture
def db_session(db: SQLAlchemy) -> Session:
    return db.session


@fixture
def client(app: Flask) -> FlaskClient:
    """Return a Web client, used for testing."""
    return app.test_client()


@fixture
def user(db: SQLAlchemy) -> User:
    user = User(
        first_name="Joe",
        last_name="Test",
        email="test@example.com",
        password="test",
        can_login=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


@fixture
def admin_user(db: SQLAlchemy) -> User:
    user = User(
        first_name="Jim",
        last_name="Admin",
        email="admin@example.com",
        password="admin",
        can_login=True,
    )
    user.is_admin = True
    db.session.add(user)
    db.session.flush()
    return user


@fixture
def login_user(user: User, client: FlaskClient) -> User:
    with client.session_transaction() as session:
        session["_user_id"] = user.id

    return user


@fixture
def login_admin(admin_user: User, client: FlaskClient) -> User:
    with client.session_transaction() as session:
        session["_user_id"] = admin_user.id

    return admin_user

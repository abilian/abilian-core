from __future__ import annotations

from flask import Flask

from abilian.core.models.subjects import Group, User
from abilian.core.sqlalchemy import SQLAlchemy


def test_non_ascii_password():
    """Ensure we can store and test non-ascii password without any
    UnicodeEncodeError."""
    user = User()

    user.set_password("Hé")

    if not isinstance(user.password, str):
        # when actually retrieved from database, it should be Unicode
        user.password = str(user.password)

    assert user.authenticate("Hé")


def test_user(app: Flask, db: SQLAlchemy):
    user = User(email="test@test.com")
    db.session.add(user)
    db.session.flush()


def test_group(app: Flask, db: SQLAlchemy):
    group = Group(name="test_group")
    db.session.add(group)
    db.session.flush()

    assert group.members_count == 0


def test_follow(app: Flask, db: SQLAlchemy):
    user1 = User(email="test1@test.com")
    user2 = User(email="test2@test.com")
    db.session.add(user1)
    db.session.add(user2)
    db.session.flush()

    assert not user1.is_following(user2)


def test_group_membership(app: Flask, db: SQLAlchemy):
    user = User(email="test@test.com")
    db.session.add(user)
    group = Group(name="test_group")
    db.session.add(group)
    db.session.flush()

    assert not user.is_member_of(group)

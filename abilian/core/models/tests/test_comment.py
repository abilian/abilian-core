""""""
from datetime import datetime, timedelta

from flask import Flask
from pytest import raises

from abilian.core.entities import Entity
from abilian.core.models.comment import Comment, is_commentable, register
from abilian.core.sqlalchemy import SQLAlchemy


@register
class CommentableContent(Entity):
    pass


def test_commentable_interface() -> None:
    assert is_commentable(CommentableContent)

    instance = CommentableContent(name="test instance")
    assert not is_commentable(instance)  # not in DB: no id

    instance.id = 42
    assert is_commentable(instance)
    assert not is_commentable(object)
    assert not is_commentable(object())


def test_cannot_register_non_entities() -> None:
    class Dummy:
        pass

    with raises(ValueError):
        register(Dummy)


def test_default_ordering(app: Flask, db: SQLAlchemy) -> None:
    commentable = CommentableContent(name="commentable objet")
    db.session.add(commentable)

    now = datetime.now()
    c1 = Comment(entity=commentable, body="comment #1")
    c1.created_at = now - timedelta(10)
    db.session.flush()
    c2 = Comment(entity=commentable, body="comment #2")
    c2.created_at = now - timedelta(5)
    db.session.flush()

    query = Comment.query.filter(Comment.entity == commentable)
    assert query.all() == [c1, c2]

    c1.created_at = c2.created_at
    c2.created_at = c1.created_at - timedelta(5)
    assert query.all() == [c2, c1]

# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from datetime import datetime, timedelta

from _pytest.python import raises

from abilian.core.entities import Entity
from abilian.testing import BaseTestCase as AbilianTestCase

from ..comment import Comment, is_commentable, register


@register
class CommentableContent(Entity):
    pass


def test_commentable_interface():
    assert is_commentable(CommentableContent)

    instance = CommentableContent(name='test instance')
    assert not is_commentable(instance)  # not in DB: no id

    instance.id = 42
    assert is_commentable(instance)
    assert not is_commentable(object)
    assert not is_commentable(object())


def test_cannot_register_non_entities():

    class Dummy(object):
        pass

    with raises(ValueError):
        register(Dummy)


class TestComment(AbilianTestCase):

    def test_default_ordering(self):
        commentable = CommentableContent(name='commentable objet')
        self.session.add(commentable)

        now = datetime.now()
        c1 = Comment(entity=commentable, body='comment #1')
        c1.created_at = now - timedelta(10)
        self.session.flush()
        c2 = Comment(entity=commentable, body='comment #2')
        c2.created_at = now - timedelta(5)
        self.session.flush()

        query = Comment.query.filter(Comment.entity == commentable)
        assert query.all() == [c1, c2]

        c1.created_at = c2.created_at
        c2.created_at = c1.created_at - timedelta(5)
        assert query.all() == [c2, c1]

# coding=utf-8
"""
"""
from __future__ import absolute_import

from datetime import datetime, timedelta

import pytest

from abilian.testing import BaseTestCase as AbilianTestCase
from abilian.core.entities import Entity

from ..comment import Comment, is_commentable, register

@register
class CommentableContent(Entity):
  pass


def test_commentable_interface():
  assert is_commentable(CommentableContent)
  assert is_commentable(CommentableContent(name=u'test instance'))
  assert not is_commentable(object)
  assert not is_commentable(object())


def test_cannot_register_non_entities():
  class Dummy(object):
    pass

  with pytest.raises(ValueError):
    register(Dummy)


class TestComment(AbilianTestCase):

  def test_default_ordering(self):
    commentable = CommentableContent(name=u'commentable objet')
    self.session.add(commentable)

    now = datetime.now()
    c1 = Comment(entity=commentable, body=u'comment #1')
    c1.created_at = now - timedelta(10)
    self.session.flush()
    c2 = Comment(entity=commentable, body=u'comment #2')
    c2.created_at = now - timedelta(5)
    self.session.flush()

    query = Comment.query.filter(Comment.entity == commentable)
    assert query.all() == [c1, c2]

    c1.created_at = c2.created_at
    c2.created_at = c1.created_at - timedelta(5)
    assert query.all() == [c2, c1]

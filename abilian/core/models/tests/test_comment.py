# coding=utf-8
"""
"""
from __future__ import absolute_import

from datetime import datetime, timedelta
from abilian.testing import BaseTestCase as AbilianTestCase
from abilian.core.entities import Entity

from ..comment import Comment


class Commentable(Entity):
  pass


class TestComment(AbilianTestCase):

  def test_default_ordering(self):
    commentable = Commentable(name=u'commentable objet')
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

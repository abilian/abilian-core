from abilian.core.entities import Entity, db
from abilian.testing import BaseTestCase

from .service import CommentService, Commentable


class Message(Entity, Commentable):
  pass


class TestComments(BaseTestCase):

  def setUp(self):
    BaseTestCase.setUp(self)
    self.comment_service = CommentService()

  def test_one_comment(self):
    msg = Message()
    db.session.add(msg)
    db.session.flush()

    comment = self.comment_service.create_comment(msg, u"First post!")
    comments = self.comment_service.get_comments(msg)
    self.assertEquals(comments, [comment])

    self.comment_service.delete_comment(comment)
    comments = self.comment_service.get_comments(msg)
    self.assertEquals(comments, [])

  def test_two_comments(self):
    msg = Message()
    db.session.add(msg)
    db.session.flush()

    comment1 = self.comment_service.create_comment(msg, u"First post!")
    comment2 = self.comment_service.create_comment(msg, u"Second post!")

    comments = self.comment_service.get_comments(msg)
    self.assertEquals(comments, [comment1, comment2])

    self.comment_service.delete_comment(comment1)
    comments = self.comment_service.get_comments(msg)
    self.assertEquals(comments, [comment2])

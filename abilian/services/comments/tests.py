from flask.ext.testing import TestCase
from abilian.application import Application
from abilian.core.entities import Entity, db

from .service import CommentService, Commentable


class TestConfig(object):
  SQLALCHEMY_DATABASE_URI = "sqlite://"
  SQLALCHEMY_ECHO = False


class Message(Entity, Commentable):
  pass


class TestComments(TestCase):

  def create_app(self):
    config = TestConfig()
    self.app = Application(config)
    return self.app

  def setUp(self):
    self.app.create_db()
    self.session = db.session
    self.comment_service = CommentService()

  def tearDown(self):
    db.session.remove()
    db.drop_all()

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


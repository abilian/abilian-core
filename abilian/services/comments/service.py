import sqlalchemy as sa

from abilian.core.extensions import db
from abilian.services.comments.models import Comment


class Commentable(object):
  """Mixin trait for commentable objects.

  Currently not used.
  """
  pass


class CommentService(object):
  def __init__(self, app=None):
    if app:
      self.init_app(app)

  def init_app(self, app):
    pass

  def prefetch_comments(self, entities):
    """TODO: prefetch (in SQLAlchemy's object cache) the comments for
    a given list of entities.
    """
    pass

  def get_comments(self, entity):
    """Returns the list of comments on a given commentable entity.
    """
    #assert isinstance(entity, Commentable)
    comments = Comment.query.filter(Comment.entity == entity)
    comments = comments.order_by(Comment.created_at).all()
    return comments

  def create_comment(self, entity, content):
    """Creates and returns a new comment on a given commentable entity.

    If `entity` is not already registered in a sqlalchemy session you will have
    to also add comment to entity session.
    """
    #assert isinstance(entity, Commentable)
    comment = Comment(entity=entity, content=content)
    session = sa.orm.object_session(entity)
    if session:
      session.add(comment)
    return comment

  def delete_comment(self, comment):
    """Deletes an existing comment.
    """
    assert isinstance(comment, Comment)
    db.session.delete(comment)

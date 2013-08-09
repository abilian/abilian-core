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

  def prefetch_comments(self, objects):
    """TODO: prefetch (in SQLAlchemy's object cache) the comments for
    a given list of objects.
    """
    pass

  def get_comments(self, object):
    """Returns the list of comments on a given commentable object.
    """
    #assert isinstance(object, Commentable)
    assert object.id is not None

    object_class = object.__class__.__name__
    comments = Comment.query.filter(Comment.object_class==object_class and
                                    Comment.object_id==object.id)
    comments = comments.order_by(Comment.created_at).all()
    return comments

  def create_comment(self, object, content):
    """Creates and returns a new comment on a given commentable object.
    """
    #assert isinstance(object, Commentable)
    assert object.id is not None

    comment = Comment(object_class=object.__class__.__name__,
                      object_id=object.id,
                      content=content)
    db.session.add(comment)
    db.session.flush()
    return comment

  def delete_comment(self, comment):
    """Deletes an existing comment.
    """
    #assert isinstance(object, Commentable)
    db.session.delete(comment)
    db.session.flush()


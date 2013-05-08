"""
Comment service. (Currently just brainstorming the API).

Both entities and activities should be commentable.
"""


class Comment(object):
  pass


class CommentService(object):

  def get_comments(self, object):
    """Return the list of comments on a given commentable object.
    """

  def create_comment(self, object, text):
    """Creates and returns a new comment on a given commentable object.
    """

  def delete_comment(self, comment):
    """Deletes an existing comment."""

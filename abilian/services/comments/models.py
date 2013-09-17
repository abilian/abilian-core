from sqlalchemy import Column, Unicode, Integer, String

from abilian.core.entities import Entity

# Local constants
MAX_COMMENT_LENGTH = 8000


class Comment(Entity):
  """A Comment on a Commentable object.
  """

  #: "pseudo" foreign key to the object of this comment.
  object_id = Column(Integer, nullable=False)

  #: the class of the object of this comment.
  object_class = Column(String, nullable=False)

  #: the comment's body, as HTML (?).
  content = Column(Unicode(MAX_COMMENT_LENGTH))

  @property
  def target(self):
    cls = None # get the class somehow
    return cls.query.get(self.target_id)

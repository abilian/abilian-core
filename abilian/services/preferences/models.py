"""
Models for user preferences.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey

from abilian.core.extensions import db
from abilian.core.subjects import User


class UserPreference(db.Model):
  """An atom of user preference."""

  __tablename__ = 'user_preference'

  id = Column(Integer, primary_key=True, autoincrement=True)
  user_id = Column(ForeignKey(User.id))
  key = Column(String, nullable=False)
  value = Column(String, nullable=False)

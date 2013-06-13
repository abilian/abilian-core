"""
Models for user preferences.
"""
import json

from sqlalchemy import Column, Integer, String, ForeignKey, Unicode
from sqlalchemy.orm import relation

from abilian.core.extensions import db
from abilian.core.subjects import User


class UserPreference(db.Model):
  """An atom of user preference."""

  __tablename__ = 'user_preference'

  #: Unique id for this preference.
  id = Column(Integer, primary_key=True, autoincrement=True)

  #: The user who set this preference.
  user = relation(User)
  user_id = Column(ForeignKey(User.id))

  #: The key
  key = Column(String, nullable=False)

  #: The value
  _value = Column(Unicode, nullable=False)

  @property
  def value(self):
    return json.loads(self._value)

  @value.setter
  def value(self, value):
    self._value = unicode(json.dumps(value))

  # TODO: use JSON to serialize values?

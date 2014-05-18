# coding=utf-8
"""
Blob. References to files stored in a on-disk repository
"""
from __future__ import absolute_import

import uuid
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.schema import Column
from sqlalchemy.types import Integer

from flask import current_app

from abilian.core.sqlalchemy import UUID, JSONDict
from abilian.core.models.base import Model
from abilian.services import repository_service as repository


class Blob(Model):
  """
  Model for storing large file content.

  Files are stored on-disk, named after their uuid. Repository is located in
  instance folder/data/files.
  """
  __tablename__ = "blob"

  id = Column(Integer(), primary_key=True, autoincrement=True)
  uuid = Column(UUID(), unique=True, nullable=False, default=uuid.uuid4)
  meta = Column(JSONDict())

  def __init__(self, value=None, *args, **kwargs):
    super(Blob, self).__init__(*args, **kwargs)
    if self.uuid is None:
      self.uuid = uuid.uuid4()

    if value is not None:
      self.value = value

  @property
  def file(self):
    """
    Return :class:`pathlib.Path` object used for storing value
    """
    return repository.get(self.uuid)

  @property
  def value(self):
    """
    Binary value content
    """
    v = self.file
    return v.open('rb').read() if v is not None else v

  @value.setter
  def value(self, value):
    """
    Store binary content to applications's repository
    """
    return repository.set(self.uuid, value)

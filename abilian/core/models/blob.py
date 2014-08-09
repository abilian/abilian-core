# coding=utf-8
"""
Blob. References to files stored in a on-disk repository
"""
from __future__ import absolute_import

import uuid

import sqlalchemy as sa
from sqlalchemy.schema import Column
from sqlalchemy.types import Integer

from abilian.core.sqlalchemy import UUID, JSONDict
from abilian.core.models.base import Model
from abilian.services import session_repository_service as repository


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
    return repository.get(self, self.uuid)

  @property
  def value(self):
    """
    Binary value content
    """
    v = self.file
    return v.open('rb').read() if v is not None else v

  @value.setter
  def value(self, value, encoding='utf-8'):
    """
    Store binary content to applications's repository

    :param:content: string, bytes, or any object with a `read()` method
    :param:encoding: encoding to use when content is unicode
    """
    return repository.set(self, self.uuid, value)

  @value.deleter
  def value(self):
    """
    remove value from repository
    """
    return repository.delete(self, self.uuid)


@sa.event.listens_for(sa.orm.Session, 'after_flush')
def _blob_propagate_delete_content(session, flush_context):
  """
  """
  deleted = (obj for obj in session.deleted if isinstance(obj, Blob))
  for blob in deleted:
    del blob.value

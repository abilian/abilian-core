# coding=utf-8
"""
"""
from __future__ import absolute_import

from uuid import UUID
from pathlib import Path
import logging

from abilian.services import Service, ServiceState

log = logging.getLogger(__name__)

_NULL_MARK = object()

class RepositoryServiceState(ServiceState):
  #: :class:`Path` path to application repository
  path = None


class RepositoryService(Service):
  """
  Service for storage of binary objects referenced in database
  """
  name = 'repository'
  AppStateClass = RepositoryServiceState

  def init_app(self, app):
    Service.init_app(self, app)

    path = app.DATA_DIR / 'files'
    if not path.exists():
      path.mkdir(0775)

    with app.app_context():
      self.app_state.path = path.resolve()


  def rel_path(self, uuid):
    """
    contruct relative path from repository top directory to the file named after this uuid.

    :param:uuid: :class:`UUID` instance
    """
    if not isinstance(uuid, UUID):
      raise ValueError('Not an uuid.UUID instance', uuid)

    filename = str(uuid)
    return Path(filename[0:2], filename[2:4], filename)

  def abs_path(self, uuid):
    """
    Return absolute :class:`Path` object for given uuid.

    :param:uuid: :class:`UUID` instance
    """
    top = self.app_state.path
    rel_path = self.rel_path(uuid)
    dest = top / rel_path
    assert top in dest.parents
    return dest


  def get(self, uuid, default=None):
    """
    Return absolute :class:`Path` object for given uuid, if this uuid exists in
    repository.

    :param:uuid: :class:`UUID` instance
    :raises:KeyError if file does not exists
    """
    path = self.abs_path(uuid)
    if not path.exists():
      return default
    return path


  def set(self, uuid, content, encoding='utf-8'):
    """
    Store binary content with uuid as key

    :param:uuid: :class:`UUID` instance
    :param:content: string, bytes, or any object with a `read()` method
    :param:encoding: encoding to use when content is unicode
    """
    dest = self.abs_path(uuid)
    if not dest.parent.exists():
      dest.parent.mkdir(0775, parents=True)

    mode = 'tw'
    if not isinstance(content, unicode):
      mode = 'bw'
      encoding = None

    with dest.open(mode, encoding=encoding) as f:
      if not isinstance(content, basestring):
        content = content.read()
      f.write(content)

  def delete(self, uuid):
    """
    Delete file uuid.

    :param:uuid: :class:`UUID` instance
    :raises:KeyError if file does not exists
    """
    dest = self.abs_path(uuid)
    if not dest.exists():
      raise KeyError('No file can be found for this uuid', uuid)

    dest.unlink()


  def __getitem__(self, uuid):
    v = self.get(uuid, default=_NULL_MARK)
    if v is _NULL_MARK:
      raise KeyError('No file can be found for this uuid', uuid)
    return v

  def __setitem__(self, uuid, content):
    self.set(uuid, content)

  def __delitem__(self, uuid):
    self.delete(uuid)

repository = RepositoryService()

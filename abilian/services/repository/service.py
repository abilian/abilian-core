# coding=utf-8
"""
"""
from __future__ import absolute_import

from uuid import UUID, uuid1
import shutil
from pathlib import Path
import logging

import sqlalchemy as sa
from sqlalchemy.orm.session import Session
from flask import _app_ctx_stack
from flask.signals import appcontext_tearing_down
try:
  from flask.globals import _lookup_app_object
except ImportError:
  # flask < 0.10
  def _lookup_app_object(name):
    top = _app_ctx_stack.top
    if top is None:
      raise RuntimeError(_app_ctx_err_msg)
    return getattr(top, name)


from abilian.core.extensions import db
from abilian.services import Service, ServiceState

log = logging.getLogger(__name__)

_NULL_MARK = object()

def _assert_uuid(uuid):
  if not isinstance(uuid, UUID):
    raise ValueError('Not an uuid.UUID instance', uuid)

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

  # data management: paths and accessors
  def rel_path(self, uuid):
    """
    contruct relative path from repository top directory to the file named after this uuid.

    :param:uuid: :class:`UUID` instance
    """
    _assert_uuid(uuid)
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


_REPOSITORY_TRANSACTION = 'abilian_repository_transaction'


class SessionRepositoryState(ServiceState):
  path = None

  def setup(self, app):
    self.transaction = None
    sa.event.listen(Session, "after_transaction_create", self.create_transaction)
    sa.event.listen(Session, "after_transaction_end", self.end_transaction)
    sa.event.listen(Session, "after_commit", self.commit)
    sa.event.listen(Session, "after_flush", self.flush)
    sa.event.listen(Session, "after_rollback", self.rollback)
    appcontext_tearing_down.connect(self.clear_transaction, app)

  @property
  def transaction(self):
    try:
      return _lookup_app_object(_REPOSITORY_TRANSACTION)
    except AttributeError:
      return None

  @transaction.setter
  def transaction(self, value):
    top = _app_ctx_stack.top
    if top is None:
      raise RuntimeError('working outside of application context')

    setattr(top, _REPOSITORY_TRANSACTION, value)

  # transaction management
  def clear_transaction(self, app=None, exc=None):
    self.transaction = None


  def create_transaction(self, session, transaction):
    if not self.running:
      return

    parent = self.transaction
    root_path = self.path
    self.transaction = RepositoryTransaction(root_path, parent)


  def end_transaction(self, session, transaction):
    if not self.running:
      return

    tr = self.transaction
    if tr is not None:
      self.transaction = tr._parent


  def commit(self, session):
    if not self.running:
      return

    tr = self.transaction
    if tr is None:
      return

    tr.commit(session)

  def flush(self, session, flush_context):
    # when sqlalchemy is flushing it is done in a sub-transaction, not the root
    # one. So when calling our 'commit' from here we are not in our root
    # transaction, so changes will not be written to repository.
    self.commit(session)

  def rollback(self, session):
    if not self.running:
      return

    tr = self.transaction
    if tr is None:
      return

    tr.rollback(session)


class SessionRepositoryService(Service):
  """
  A repository service that is session aware, i.e content is actually
  written or delete at commit time.

  All content is stored using the main :class:`RepositoryService`.
  """
  name = 'session_repository'
  AppStateClass = SessionRepositoryState

  def init_app(self, app):
    Service.init_app(self, app)

    path = Path(app.instance_path, 'tmp', 'files_transactions')
    if not path.exists():
      path.mkdir(0775, parents=True)

    with app.app_context():
      self.app_state.path = path.resolve()
      self.app_state.setup(app)

  # repository interface
  def get(self, uuid, default=None):
    tr = self.app_state.transaction
    try:
      val = tr.get(uuid)
    except KeyError:
      return default

    if val is _NULL_MARK:
      val = repository.get(uuid, default)

    return val

  def set(self, uuid, content, encoding='utf-8'):
    tr = self.app_state.transaction
    tr.set(uuid, content, encoding)

  def delete(self, uuid):
    tr = self.app_state.transaction
    if self.get(uuid) is not None:
      tr.delete(uuid)

  def __getitem__(self, uuid):
    v = self.get(uuid, _NULL_MARK)
    if v is _NULL_MARK:
      raise KeyError('No file can be found for this uuid', uuid)
    return v

  def __setitem__(self, uuid, content):
    self.set(uuid, content)

  def __delitem__(self, uuid):
    self.delete(uuid)


session_repository = SessionRepositoryService()


class RepositoryTransaction(object):

  def __init__(self, root_path, parent=None):
    self.path = root_path / str(uuid1())
    self.path.mkdir(0700)
    self._parent = parent
    self._deleted = set()
    self._set = set()
    self.__cleared = False

  def __del__(self):
    self._clear()

  def _clear(self):
    if self.__cleared:
      return
    # make sure transaction is not usable anymore
    if self.path.exists():
      shutil.rmtree(str(self.path))

    del self.path
    del self._deleted
    del self._set
    self.__cleared = True

  def rollback(self, session=None):
    self._clear()

  def commit(self, session=None):
    """
    merge modified objects into parent transaction.

    Once commited a transaction object is not usable anymore

    :param:session: current sqlalchemy Session
    """
    if self.__cleared:
      return

    if self._parent:
      # nested transaction
      self._commit_parent()
    else:
      self._commit_repository()
    self._clear()

  def _commit_repository(self):
    assert self._parent is None

    for uuid in self._deleted:
      try:
        repository.delete(uuid)
      except KeyError:
        pass

    for uuid in self._set:
      content = self.path / str(uuid)
      repository.set(uuid, content.open('rb'))

  def _commit_parent(self):
    p = self._parent
    p._deleted |= self._deleted
    p._deleted -= self._set

    p._set |= self._set
    p._set -= self._deleted
    for uuid in self._set:
      content_path = self.path / str(uuid)
      # content_path.replace is not available with python < 3.3.
      content_path.rename(p.path / str(uuid))

  def _add_to(self, uuid, dest, other):
    """
    Add `item` to `dest` set, ensuring `item` is not present in `other` set
    """
    _assert_uuid(uuid)
    try:
      other.remove(uuid)
    except KeyError:
      pass
    dest.add(uuid)

  def delete(self, uuid):
    self._add_to(uuid, self._deleted, self._set)

  def set(self, uuid, content, encoding='utf-8'):
    self._add_to(uuid, self._set, self._deleted)

    mode = 'tw'
    if not isinstance(content, unicode):
      mode = 'bw'
      encoding = None

    dest = self.path / str(uuid)
    with dest.open(mode, encoding=encoding) as f:
      if not isinstance(content, basestring):
        content = content.read()
      f.write(content)

  def get(self, uuid):
    if uuid in self._deleted:
      raise KeyError

    if uuid in self._set:
      path = self.path / str(uuid)
      assert path.exists()
      return path

    if self._parent:
      return self._parent.get(uuid)

    return _NULL_MARK
